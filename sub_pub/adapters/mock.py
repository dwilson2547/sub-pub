"""Mock adapter for testing and development"""
import logging
import time
from typing import Iterator, List, Optional
from datetime import datetime

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class MockSource(MessageSource):
    """Mock message source for testing"""
    
    def __init__(self, config: dict):
        self.config = config
        self.subscribed_topics: List[str] = []
        self._connected = False
        self._message_count = 0
        
    def connect(self) -> None:
        """Establish connection"""
        logger.info("Mock source connected")
        self._connected = True
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        self.subscribed_topics = topics
        logger.info(f"Mock source subscribed to: {topics}")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages (generates mock messages)"""
        while self._connected:
            for topic in self.subscribed_topics:
                self._message_count += 1
                yield Message(
                    payload=f"Mock message {self._message_count}".encode('utf-8'),
                    headers={'source': 'mock', 'count': str(self._message_count)},
                    topic=topic,
                    key=f"key-{self._message_count}",
                    timestamp=datetime.now()
                )
                time.sleep(0.1)  # Slow down for testing
                
    def close(self) -> None:
        """Close connection"""
        self._connected = False
        logger.info("Mock source closed")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset"""
        pass  # No-op for mock


class MockPublisher(MessagePublisher):
    """Mock message publisher for testing"""
    
    def __init__(self, config: dict):
        self.config = config
        self._connected = False
        self.published_messages: List[tuple[Message, str]] = []
        
    def connect(self) -> None:
        """Establish connection"""
        logger.info("Mock publisher connected")
        self._connected = True
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message"""
        self.published_messages.append((message, topic))
        logger.debug(f"Mock published to {topic}: {len(message.payload)} bytes")
        
    def flush(self) -> None:
        """Flush buffered messages"""
        logger.info(f"Mock publisher flushed {len(self.published_messages)} messages")
        
    def close(self) -> None:
        """Close connection"""
        self._connected = False
        logger.info("Mock publisher closed")
