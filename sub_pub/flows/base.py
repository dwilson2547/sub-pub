"""Base flow implementation with thread pool and back-pressure support"""
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Full
import threading
import logging
from typing import Optional
import time

from sub_pub.core.message import Message
from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.domain.processor import MessageProcessor, PassThroughProcessor
from sub_pub.metrics.collector import MetricsCollector
from sub_pub.config.models import ThreadPoolConfig, BackPressureConfig

logger = logging.getLogger(__name__)


class Flow(ABC):
    """Abstract base class for message flows"""
    
    def __init__(
        self,
        thread_pool_config: ThreadPoolConfig,
        back_pressure_config: BackPressureConfig,
        processor: Optional[MessageProcessor] = None
    ):
        self.thread_pool_config = thread_pool_config
        self.back_pressure_config = back_pressure_config
        self.processor = processor or PassThroughProcessor()
        self.metrics = MetricsCollector()
        
        # Thread pool for domain processing
        self.domain_executor = ThreadPoolExecutor(
            max_workers=thread_pool_config.max_workers,
            thread_name_prefix="domain-"
        )
        
        # Thread pool for publishing
        self.publish_executor = ThreadPoolExecutor(
            max_workers=thread_pool_config.max_workers,
            thread_name_prefix="publish-"
        )
        
        # Queues for back-pressure
        self.domain_queue: Queue[tuple[Message, str]] = Queue(
            maxsize=thread_pool_config.queue_size
        )
        self.publish_queue: Queue[tuple[Message, str]] = Queue(
            maxsize=thread_pool_config.queue_size
        )
        
        self._running = False
        self._shutdown_event = threading.Event()
        
    def _check_back_pressure(self, queue: Queue) -> bool:
        """Check if back-pressure should be applied"""
        if not self.back_pressure_config.enabled:
            return False
        
        queue_usage = queue.qsize() / queue.maxsize
        return queue_usage >= self.back_pressure_config.queue_high_watermark
    
    def _wait_for_back_pressure_release(self, queue: Queue) -> None:
        """Wait for back-pressure to be released"""
        while self._running:
            queue_usage = queue.qsize() / queue.maxsize
            if queue_usage <= self.back_pressure_config.queue_low_watermark:
                break
            time.sleep(0.01)  # 10ms sleep
    
    def _domain_worker(self) -> None:
        """Worker thread for domain processing"""
        while self._running:
            try:
                # Get message from domain queue (with timeout for clean shutdown)
                try:
                    message, dest_topic = self.domain_queue.get(timeout=0.1)
                except Exception:
                    continue
                
                try:
                    # Process message through domain layer
                    processed_message = self.processor.process(message)
                    
                    # Apply back-pressure if needed
                    if self._check_back_pressure(self.publish_queue):
                        logger.debug("Back-pressure detected on publish queue, waiting...")
                        self._wait_for_back_pressure_release(self.publish_queue)
                    
                    # Add to publish queue
                    self.publish_queue.put((processed_message, dest_topic))
                    
                except Exception as e:
                    logger.error(f"Error in domain processing: {e}", exc_info=True)
                    self.metrics.record_source_error(message.topic)
                finally:
                    self.domain_queue.task_done()
            except Exception as e:
                logger.error(f"Error in domain worker: {e}", exc_info=True)
    
    def _publish_worker(self, publisher: MessagePublisher) -> None:
        """Worker thread for publishing"""
        while self._running:
            try:
                # Get message from publish queue (with timeout for clean shutdown)
                try:
                    message, dest_topic = self.publish_queue.get(timeout=0.1)
                except Exception:
                    continue
                
                try:
                    # Publish message
                    publisher.publish(message, dest_topic)
                    self.metrics.record_destination_message(dest_topic, message.size())
                    
                except Exception as e:
                    logger.error(f"Error publishing message: {e}", exc_info=True)
                    self.metrics.record_destination_error(dest_topic)
                finally:
                    self.publish_queue.task_done()
            except Exception as e:
                logger.error(f"Error in publish worker: {e}", exc_info=True)
    
    @abstractmethod
    def run(self) -> None:
        """Run the flow"""
        pass
    
    def shutdown(self) -> None:
        """Shutdown the flow"""
        logger.info("Shutting down flow...")
        self._running = False
        self._shutdown_event.set()
        
        # Wait for queues to drain
        self.domain_queue.join()
        self.publish_queue.join()
        
        # Shutdown executors
        self.domain_executor.shutdown(wait=True)
        self.publish_executor.shutdown(wait=True)
        
        logger.info("Flow shutdown complete")
