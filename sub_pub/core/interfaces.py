"""Abstract base classes for message sources and publishers"""
from abc import ABC, abstractmethod
from typing import Iterator, Optional
from sub_pub.core.message import Message


class MessageSource(ABC):
    """Abstract base class for message sources"""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the message source"""
        pass
    
    @abstractmethod
    def subscribe(self, topics: list[str]) -> None:
        """Subscribe to one or more topics"""
        pass
    
    @abstractmethod
    def consume(self) -> Iterator[Message]:
        """Consume messages from subscribed topics"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the connection to the message source"""
        pass
    
    @abstractmethod
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset (for systems that support it)"""
        pass


class MessagePublisher(ABC):
    """Abstract base class for message publishers"""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the message destination"""
        pass
    
    @abstractmethod
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to a topic"""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered messages"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the connection to the message destination"""
        pass
