"""Funnel flow: many sources -> one destination"""
import logging
from typing import List
import threading

from sub_pub.flows.base import Flow
from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class FunnelFlow(Flow):
    """Funnel flow: read from many sources, publish to one destination"""
    
    def __init__(
        self,
        sources: List[MessageSource],
        destination: MessagePublisher,
        destination_topic: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.sources = sources
        self.destination = destination
        self.destination_topic = destination_topic
        
    def _consume_from_source(self, source: MessageSource) -> None:
        """Consume messages from a single source"""
        try:
            for message in source.consume():
                if not self._running:
                    break
                
                try:
                    # Record source metrics
                    self.metrics.record_source_message(message.topic, message.size())
                    
                    # Apply back-pressure if needed
                    if self._check_back_pressure(self.domain_queue):
                        logger.debug("Back-pressure detected on domain queue, waiting...")
                        self._wait_for_back_pressure_release(self.domain_queue)
                    
                    # Add to domain queue
                    self.domain_queue.put((message, self.destination_topic))
                    
                    # Commit the message
                    source.commit(message)
                    
                except Exception as e:
                    logger.error(f"Error processing message from {message.topic}: {e}", exc_info=True)
                    self.metrics.record_source_error(message.topic)
        except Exception as e:
            logger.error(f"Error consuming from source: {e}", exc_info=True)
    
    def run(self) -> None:
        """Run the funnel flow"""
        self._running = True
        
        # Connect all sources
        for source in self.sources:
            source.connect()
        
        # Connect destination
        self.destination.connect()
        
        # Start domain workers
        domain_threads = []
        for i in range(self.thread_pool_config.max_workers):
            t = threading.Thread(
                target=self._domain_worker,
                name=f"domain-worker-{i}",
                daemon=True
            )
            t.start()
            domain_threads.append(t)
        
        # Start publish workers
        publish_threads = []
        for i in range(self.thread_pool_config.max_workers):
            t = threading.Thread(
                target=lambda: self._publish_worker(self.destination),
                name=f"publish-worker-{i}",
                daemon=True
            )
            t.start()
            publish_threads.append(t)
        
        # Start consumer threads for each source
        consumer_threads = []
        for i, source in enumerate(self.sources):
            t = threading.Thread(
                target=lambda src=source: self._consume_from_source(src),
                name=f"consumer-{i}",
                daemon=True
            )
            t.start()
            consumer_threads.append(t)
        
        logger.info(f"Funnel flow started with {len(self.sources)} sources")
        
        # Wait for shutdown signal
        self._shutdown_event.wait()
        
        # Cleanup
        for thread in consumer_threads + domain_threads + publish_threads:
            thread.join(timeout=5.0)
        
        # Flush and close
        self.destination.flush()
        self.destination.close()
        
        for source in self.sources:
            source.close()
        
        logger.info("Funnel flow stopped")
