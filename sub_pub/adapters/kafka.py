"""Kafka adapter"""
import logging
from typing import Iterator, List, Optional

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class KafkaSource(MessageSource):
    """Kafka message source"""
    
    def __init__(self, config: dict):
        self.config = config
        self.consumer = None
        
    def connect(self) -> None:
        """Establish connection to Kafka"""
        try:
            from kafka import KafkaConsumer
            
            self.consumer = KafkaConsumer(
                **self.config,
                enable_auto_commit=False
            )
            logger.info("Connected to Kafka source")
        except ImportError:
            logger.error("kafka-python package not installed. Install with: pip install kafka-python")
            raise
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        if self.consumer:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to Kafka topics: {topics}")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages from Kafka"""
        if not self.consumer:
            raise RuntimeError("Consumer not connected")
        
        for record in self.consumer:
            headers = {k: v.decode('utf-8') if isinstance(v, bytes) else str(v) 
                      for k, v in (record.headers or [])}
            
            yield Message(
                payload=record.value,
                headers=headers,
                topic=record.topic,
                key=record.key.decode('utf-8') if record.key else None,
                partition=record.partition,
                offset=record.offset,
                timestamp=record.timestamp
            )
        
    def close(self) -> None:
        """Close Kafka connection"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka source closed")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset"""
        if self.consumer:
            self.consumer.commit()


class KafkaPublisher(MessagePublisher):
    """Kafka message publisher"""
    
    def __init__(self, config: dict):
        self.config = config
        self.producer = None
        
    def connect(self) -> None:
        """Establish connection to Kafka"""
        try:
            from kafka import KafkaProducer
            
            self.producer = KafkaProducer(**self.config)
            logger.info("Connected to Kafka publisher")
        except ImportError:
            logger.error("kafka-python package not installed. Install with: pip install kafka-python")
            raise
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Kafka"""
        if not self.producer:
            raise RuntimeError("Producer not connected")
        
        headers = [(k, v.encode('utf-8')) for k, v in message.headers.items()]
        key = message.key.encode('utf-8') if message.key else None
        
        self.producer.send(
            topic,
            value=message.payload,
            key=key,
            headers=headers
        )
        
    def flush(self) -> None:
        """Flush buffered messages"""
        if self.producer:
            self.producer.flush()
        
    def close(self) -> None:
        """Close Kafka connection"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka publisher closed")
