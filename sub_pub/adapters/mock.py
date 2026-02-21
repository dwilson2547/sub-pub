"""Mock adapter for testing and development"""
import asyncio
import logging
import time
from typing import AsyncIterator, Iterator, List, Optional
from datetime import datetime

from sub_pub.core.interfaces import (
    AsyncMessagePublisher,
    AsyncMessageSource,
    MessagePublisher,
    MessageSource,
)
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


class AsyncMockSource(AsyncMessageSource):
    """Async mock message source for testing"""

    def __init__(self, messages: Optional[List[Message]] = None):
        self.subscribed_topics: List[str] = []
        self._connected = False
        self._message_count = 0
        # Pre-defined messages to yield (if None, generates mock messages)
        self._messages = messages

    async def connect(self) -> None:
        """Establish connection"""
        logger.info("Async mock source connected")
        self._connected = True

    async def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        self.subscribed_topics = topics
        logger.info(f"Async mock source subscribed to: {topics}")

    async def consume(self) -> AsyncIterator[Message]:
        """Consume messages (yields pre-defined messages or generates mock ones)"""
        if self._messages is not None:
            for message in self._messages:
                if not self._connected:
                    break
                yield message
        else:
            while self._connected:
                for topic in self.subscribed_topics:
                    if not self._connected:
                        return
                    self._message_count += 1
                    yield Message(
                        payload=f"Async mock message {self._message_count}".encode("utf-8"),
                        headers={"source": "async_mock", "count": str(self._message_count)},
                        topic=topic,
                        key=f"key-{self._message_count}",
                        timestamp=datetime.now(),
                    )
                    await asyncio.sleep(0.1)

    async def close(self) -> None:
        """Close connection"""
        self._connected = False
        logger.info("Async mock source closed")

    async def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset"""
        pass  # No-op for mock


class AsyncMockPublisher(AsyncMessagePublisher):
    """Async mock message publisher for testing"""

    def __init__(self):
        self._connected = False
        self.published_messages: List[tuple[Message, str]] = []

    async def connect(self) -> None:
        """Establish connection"""
        logger.info("Async mock publisher connected")
        self._connected = True

    async def publish(self, message: Message, topic: str) -> None:
        """Publish a message"""
        self.published_messages.append((message, topic))
        logger.debug(f"Async mock published to {topic}: {len(message.payload)} bytes")

    async def flush(self) -> None:
        """Flush buffered messages"""
        logger.info(f"Async mock publisher flushed {len(self.published_messages)} messages")

    async def close(self) -> None:
        """Close connection"""
        self._connected = False
        logger.info("Async mock publisher closed")
