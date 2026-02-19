"""Iggy adapter (stub)"""
import logging
from typing import Iterator, List, Optional

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class IggySource(MessageSource):
    """Iggy message source (stub implementation)"""
    
    def __init__(self, config: dict):
        self.config = config
        logger.warning("Iggy adapter is a stub - requires actual Iggy client implementation")
        
    def connect(self) -> None:
        """Establish connection to Iggy"""
        logger.info("Iggy source connected (stub)")
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        logger.info(f"Iggy source subscribed to: {topics} (stub)")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages from Iggy"""
        logger.warning("Iggy consume not implemented - returning empty iterator")
        yield from []
        
    def close(self) -> None:
        """Close Iggy connection"""
        logger.info("Iggy source closed (stub)")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset"""
        pass


class IggyPublisher(MessagePublisher):
    """Iggy message publisher (stub implementation)"""
    
    def __init__(self, config: dict):
        self.config = config
        logger.warning("Iggy adapter is a stub - requires actual Iggy client implementation")
        
    def connect(self) -> None:
        """Establish connection to Iggy"""
        logger.info("Iggy publisher connected (stub)")
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Iggy"""
        logger.debug(f"Iggy publish to {topic} (stub): {len(message.payload)} bytes")
        
    def flush(self) -> None:
        """Flush buffered messages"""
        pass
        
    def close(self) -> None:
        """Close Iggy connection"""
        logger.info("Iggy publisher closed (stub)")
