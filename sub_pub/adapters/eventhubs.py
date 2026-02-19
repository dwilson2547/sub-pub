"""Azure Event Hubs adapter"""
import logging
from typing import Iterator, List, Optional
import json

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class EventHubsSource(MessageSource):
    """Azure Event Hubs message source"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        
    def connect(self) -> None:
        """Establish connection to Event Hubs"""
        try:
            from azure.eventhub import EventHubConsumerClient
            
            self.client = EventHubConsumerClient.from_connection_string(
                self.config['connection_string'],
                consumer_group=self.config.get('consumer_group', '$Default'),
                **{k: v for k, v in self.config.items() 
                   if k not in ['connection_string', 'consumer_group']}
            )
            logger.info("Connected to Event Hubs source")
        except ImportError:
            logger.error("azure-eventhub package not installed. Install with: pip install azure-eventhub")
            raise
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics (Event Hubs doesn't have topics, uses partitions)"""
        logger.info(f"Event Hubs subscribed (topics parameter not used)")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages from Event Hubs"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        def on_event(partition_context, event):
            headers = event.properties if event.properties else {}
            
            return Message(
                payload=event.body,
                headers={k: str(v) for k, v in headers.items()},
                topic=f"eventhub-{partition_context.partition_id}",
                partition=int(partition_context.partition_id),
                offset=event.offset,
                timestamp=event.enqueued_time
            )
        
        # This is a simplified version - actual implementation would need to handle
        # the async nature of Event Hubs
        logger.warning("Event Hubs adapter is a stub - requires full async implementation")
        yield from []
        
    def close(self) -> None:
        """Close Event Hubs connection"""
        if self.client:
            self.client.close()
            logger.info("Event Hubs source closed")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit checkpoint"""
        pass


class EventHubsPublisher(MessagePublisher):
    """Azure Event Hubs message publisher"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        
    def connect(self) -> None:
        """Establish connection to Event Hubs"""
        try:
            from azure.eventhub import EventHubProducerClient
            
            self.client = EventHubProducerClient.from_connection_string(
                self.config['connection_string'],
                **{k: v for k, v in self.config.items() if k != 'connection_string'}
            )
            logger.info("Connected to Event Hubs publisher")
        except ImportError:
            logger.error("azure-eventhub package not installed. Install with: pip install azure-eventhub")
            raise
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Event Hubs"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        from azure.eventhub import EventData
        
        event = EventData(message.payload)
        event.properties = message.headers
        
        # This is a simplified version - actual implementation needs batch handling
        logger.warning("Event Hubs adapter is a stub - requires full async implementation")
        
    def flush(self) -> None:
        """Flush buffered messages"""
        pass
        
    def close(self) -> None:
        """Close Event Hubs connection"""
        if self.client:
            self.client.close()
            logger.info("Event Hubs publisher closed")
