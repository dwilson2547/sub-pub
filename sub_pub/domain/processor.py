"""Domain processor for message transformation"""
from abc import ABC, abstractmethod
from sub_pub.core.message import Message


class MessageProcessor(ABC):
    """Abstract base class for message processors"""
    
    @abstractmethod
    def process(self, message: Message) -> Message:
        """Process a message and return the transformed message"""
        pass


class PassThroughProcessor(MessageProcessor):
    """Default pass-through processor that doesn't modify messages"""
    
    def process(self, message: Message) -> Message:
        """Return the message unchanged"""
        return message


class AsyncMessageProcessor(ABC):
    """Abstract base class for async message processors"""

    @abstractmethod
    async def process(self, message: Message) -> Message:
        """Process a message and return the transformed message"""
        pass


class AsyncPassThroughProcessor(AsyncMessageProcessor):
    """Default async pass-through processor that doesn't modify messages"""

    async def process(self, message: Message) -> Message:
        """Return the message unchanged"""
        return message
