"""Fan flow: one source -> many destinations"""
import logging
import threading
import json

from sub_pub.flows.base import Flow
from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class FanFlow(Flow):
    """Fan flow: read from one source, publish to many destinations based on message content"""
    
    def __init__(
        self,
        source: MessageSource,
        source_topic: str,
        destination: MessagePublisher,
        destination_resolver: dict,  # {'type': 'header'/'payload_key', 'key': 'topic_name'}
        **kwargs
    ):
        super().__init__(**kwargs)
        self.source = source
        self.source_topic = source_topic
        self.destination = destination
        self.destination_resolver = destination_resolver
        
    def _resolve_destination_topic(self, message: Message) -> str:
        """Resolve the destination topic from the message"""
        resolver_type = self.destination_resolver['type']
        key = self.destination_resolver['key']
        
        if resolver_type == 'header':
            return message.get_header(key, 'default')
        elif resolver_type == 'payload_key':
            try:
                payload = json.loads(message.payload.decode('utf-8'))
                return payload.get(key, 'default')
            except Exception as e:
                logger.warning(f"Failed to parse payload for destination resolution: {e}")
                return 'default'
        else:
            logger.warning(f"Unknown resolver type: {resolver_type}")
            return 'default'
    
    def _consume_messages(self) -> None:
        """Consume messages from source"""
        try:
            for message in self.source.consume():
                if not self._running:
                    break
                
                try:
                    # Record source metrics
                    self.metrics.record_source_message(message.topic, message.size())
                    
                    # Resolve destination topic
                    dest_topic = self._resolve_destination_topic(message)
                    
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
        """Run the fan flow"""
        self._running = True
        
        # Connect source and destination
        self.source.connect()
        self.source.subscribe([self.source_topic])
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
        
        logger.info(f"Fan flow started from {self.source_topic}")
        
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
        
        logger.info("Fan flow stopped")
