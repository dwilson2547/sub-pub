"""One-to-one flow: multiple source-destination pairs"""
import logging
import threading
from typing import List, Dict

from sub_pub.flows.base import Flow
from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message
from sub_pub.config.models import OneToOneMapping

logger = logging.getLogger(__name__)


class OneToOneFlow(Flow):
    """One-to-one flow: multiple independent source->destination mappings"""
    
    def __init__(
        self,
        source: MessageSource,
        destination: MessagePublisher,
        mappings: List[OneToOneMapping],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.source = source
        self.destination = destination
        self.mappings = mappings
        
        # Build mapping dict for quick lookup
        self.topic_map: Dict[str, str] = {
            m.source_topic: m.destination_topic 
            for m in mappings
        }
        
    def _consume_messages(self) -> None:
        """Consume messages from source"""
        try:
            for message in self.source.consume():
                if not self._running:
                    break
                
                try:
                    # Check if this topic has a mapping
                    dest_topic = self.topic_map.get(message.topic)
                    if dest_topic is None:
                        logger.debug(f"No mapping found for topic {message.topic}, skipping")
                        continue
                    
                    # Record source metrics
                    self.metrics.record_source_message(message.topic, message.size())
                    
                    # Apply back-pressure if needed
                    if self._check_back_pressure(self.domain_queue):
                        logger.debug("Back-pressure detected on domain queue, waiting...")
                        self._wait_for_back_pressure_release(self.domain_queue)
                    
                    # Add to domain queue
                    self.domain_queue.put((message, dest_topic))
                    
                    # Commit the message
                    self.source.commit(message)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    self.metrics.record_source_error(message.topic)
        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)
    
    def run(self) -> None:
        """Run the one-to-one flow"""
        self._running = True
        
        # Connect source and destination
        self.source.connect()
        source_topics = [m.source_topic for m in self.mappings]
        self.source.subscribe(source_topics)
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
        
        # Start consumer thread
        consumer_thread = threading.Thread(
            target=self._consume_messages,
            name="consumer",
            daemon=True
        )
        consumer_thread.start()
        
        logger.info(f"One-to-one flow started with {len(self.mappings)} mappings")
        
        # Wait for shutdown signal
        self._shutdown_event.wait()
        
        # Cleanup
        consumer_thread.join(timeout=5.0)
        for thread in domain_threads + publish_threads:
            thread.join(timeout=5.0)
        
        # Flush and close
        self.destination.flush()
        self.destination.close()
        self.source.close()
        
        logger.info("One-to-one flow stopped")
