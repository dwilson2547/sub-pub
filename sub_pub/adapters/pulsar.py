"""Pulsar adapter"""
import logging
from typing import Iterator, List, Optional

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class PulsarSource(MessageSource):
    """Pulsar message source"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self.consumer = None
        
    def connect(self) -> None:
        """Establish connection to Pulsar"""
        try:
            import pulsar
            
            service_url = self.config.pop('service_url')
            self.client = pulsar.Client(service_url)
            logger.info("Connected to Pulsar source")
        except ImportError:
            logger.error("pulsar-client package not installed. Install with: pip install pulsar-client")
            raise
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        if self.client:
            self.consumer = self.client.subscribe(
                topics,
                subscription_name=self.config.get('subscription_name', 'sub-pub'),
                **{k: v for k, v in self.config.items() if k != 'subscription_name'}
            )
            logger.info(f"Subscribed to Pulsar topics: {topics}")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages from Pulsar"""
        if not self.consumer:
            raise RuntimeError("Consumer not connected")
        
        while True:
            msg = self.consumer.receive()
            
            headers = dict(msg.properties()) if msg.properties() else {}
            
            yield Message(
                payload=msg.data(),
                headers=headers,
                topic=msg.topic_name(),
                key=msg.partition_key() or None,
                timestamp=msg.publish_timestamp()
            )
        
    def close(self) -> None:
        """Close Pulsar connection"""
        if self.consumer:
            self.consumer.close()
        if self.client:
            self.client.close()
            logger.info("Pulsar source closed")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Acknowledge message"""
        # In Pulsar, we'd need to store the actual pulsar message to ack it
        # For now, this is a simplified version
        pass


class PulsarPublisher(MessagePublisher):
    """Pulsar message publisher"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self.producers = {}  # topic -> producer
        
    def connect(self) -> None:
        """Establish connection to Pulsar"""
        try:
            import pulsar
            
            service_url = self.config.pop('service_url')
            self.client = pulsar.Client(service_url)
            logger.info("Connected to Pulsar publisher")
        except ImportError:
            logger.error("pulsar-client package not installed. Install with: pip install pulsar-client")
            raise
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Pulsar"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        # Create producer for topic if not exists
        if topic not in self.producers:
            self.producers[topic] = self.client.create_producer(topic)
        
        producer = self.producers[topic]
        
        producer.send(
            message.payload,
            properties=message.headers,
            partition_key=message.key
        )
        
    def flush(self) -> None:
        """Flush buffered messages"""
        for producer in self.producers.values():
            producer.flush()
        
    def close(self) -> None:
        """Close Pulsar connection"""
        for producer in self.producers.values():
            producer.close()
        if self.client:
            self.client.close()
            logger.info("Pulsar publisher closed")
