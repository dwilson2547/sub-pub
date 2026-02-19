"""Google Cloud Pub/Sub adapter"""
import logging
from typing import Iterator, List, Optional

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class GooglePubSubSource(MessageSource):
    """Google Cloud Pub/Sub message source"""
    
    def __init__(self, config: dict):
        self.config = config
        self.subscriber = None
        self.subscription_path = None
        
    def connect(self) -> None:
        """Establish connection to Google Pub/Sub"""
        try:
            from google.cloud import pubsub_v1
            
            self.subscriber = pubsub_v1.SubscriberClient()
            self.subscription_path = self.subscriber.subscription_path(
                self.config['project_id'],
                self.config['subscription_id']
            )
            logger.info("Connected to Google Pub/Sub source")
        except ImportError:
            logger.error("google-cloud-pubsub package not installed. Install with: pip install google-cloud-pubsub")
            raise
        
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics (Google Pub/Sub uses subscriptions)"""
        logger.info(f"Google Pub/Sub uses subscription: {self.subscription_path}")
        
    def consume(self) -> Iterator[Message]:
        """Consume messages from Google Pub/Sub"""
        if not self.subscriber:
            raise RuntimeError("Subscriber not connected")
        
        # This is a simplified version - actual implementation would need to handle
        # the async/callback nature of Google Pub/Sub
        logger.warning("Google Pub/Sub adapter is a stub - requires full async implementation")
        yield from []
        
    def close(self) -> None:
        """Close Google Pub/Sub connection"""
        if self.subscriber:
            self.subscriber.close()
            logger.info("Google Pub/Sub source closed")
        
    def commit(self, message: Optional[Message] = None) -> None:
        """Acknowledge message"""
        pass


class GooglePubSubPublisher(MessagePublisher):
    """Google Cloud Pub/Sub message publisher"""
    
    def __init__(self, config: dict):
        self.config = config
        self.publisher = None
        self.topic_paths = {}
        
    def connect(self) -> None:
        """Establish connection to Google Pub/Sub"""
        try:
            from google.cloud import pubsub_v1
            
            self.publisher = pubsub_v1.PublisherClient()
            logger.info("Connected to Google Pub/Sub publisher")
        except ImportError:
            logger.error("google-cloud-pubsub package not installed. Install with: pip install google-cloud-pubsub")
            raise
        
    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Google Pub/Sub"""
        if not self.publisher:
            raise RuntimeError("Publisher not connected")
        
        # Get or create topic path
        if topic not in self.topic_paths:
            self.topic_paths[topic] = self.publisher.topic_path(
                self.config['project_id'],
                topic
            )
        
        topic_path = self.topic_paths[topic]
        
        # Publish with attributes (headers)
        future = self.publisher.publish(
            topic_path,
            message.payload,
            **message.headers
        )
        
        # Wait for publish to complete (for simplicity)
        future.result()
        
    def flush(self) -> None:
        """Flush buffered messages"""
        pass
        
    def close(self) -> None:
        """Close Google Pub/Sub connection"""
        if self.publisher:
            logger.info("Google Pub/Sub publisher closed")
