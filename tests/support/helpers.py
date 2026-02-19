"""Helper utilities for publishing and consuming messages during tests"""

import json
import time
from typing import List, Dict, Any, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError


class KafkaTestHelper:
    """Helper for Kafka message operations in tests"""
    
    def __init__(self, bootstrap_servers: str):
        """Initialize Kafka test helper
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        
    def create_producer(self):
        """Create Kafka producer"""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8') if isinstance(v, dict) else v.encode('utf-8') if isinstance(v, str) else v
            )
        return self.producer
        
    def create_consumer(self, topics: List[str], group_id: str = "test-group"):
        """Create Kafka consumer
        
        Args:
            topics: Topics to subscribe to
            group_id: Consumer group ID
        """
        if not self.consumer:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda m: m.decode('utf-8') if m else None,
                consumer_timeout_ms=10000  # 10 second timeout
            )
        return self.consumer
        
    def publish_message(self, topic: str, message: Any, key: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """Publish a message to Kafka topic
        
        Args:
            topic: Topic name
            message: Message to publish (dict or string)
            key: Optional message key
            headers: Optional message headers
        """
        producer = self.create_producer()
        
        # Convert headers to bytes if provided
        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode('utf-8') if isinstance(v, str) else v) for k, v in headers.items()]
        
        # Publish message
        future = producer.send(
            topic,
            value=message,
            key=key.encode('utf-8') if key else None,
            headers=kafka_headers
        )
        
        # Wait for send to complete
        try:
            record_metadata = future.get(timeout=10)
            return record_metadata
        except KafkaError as e:
            raise Exception(f"Failed to publish message: {e}")
            
    def consume_messages(self, topics: List[str], count: int = 1, timeout: int = 30) -> List[Dict[str, Any]]:
        """Consume messages from Kafka topics
        
        Args:
            topics: Topics to consume from
            count: Number of messages to consume
            timeout: Timeout in seconds
            
        Returns:
            List of consumed messages with metadata
            
        Note:
            Creates a new consumer with unique group ID for each call to avoid
            subscription conflicts. Consumer groups will accumulate in Kafka
            metadata but are automatically cleaned up by Kafka's group coordinator
            after the configured timeout.
        """
        # Create a new consumer for each consume operation to avoid subscription conflicts
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"test-consumer-{int(time.time() * 1000)}",  # Unique group ID per consume
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            # Handle both UTF-8 and non-UTF-8 byte values gracefully
            value_deserializer=lambda m: m.decode('utf-8', errors='replace') if m else None,
            consumer_timeout_ms=10000  # 10 second timeout
        )
        
        messages = []
        start_time = time.time()
        
        try:
            while len(messages) < count and (time.time() - start_time) < timeout:
                for message in consumer:
                    msg_dict = {
                        'topic': message.topic,
                        'partition': message.partition,
                        'offset': message.offset,
                        'key': message.key.decode('utf-8') if message.key else None,
                        'value': message.value,
                        'headers': {k: v.decode('utf-8') if isinstance(v, bytes) else v 
                                   for k, v in (message.headers or [])}
                    }
                    messages.append(msg_dict)
                    
                    if len(messages) >= count:
                        break
        finally:
            consumer.close()
                    
        return messages
        
    def close(self):
        """Close producer and consumer"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


class PulsarTestHelper:
    """Helper for Pulsar message operations in tests"""
    
    def __init__(self, service_url: str):
        """Initialize Pulsar test helper
        
        Args:
            service_url: Pulsar service URL
        """
        self.service_url = service_url
        self.client = None
        self.producers = {}
        self.consumers = {}
        
    def get_client(self):
        """Get or create Pulsar client"""
        if not self.client:
            import pulsar
            self.client = pulsar.Client(self.service_url)
        return self.client
        
    def publish_message(self, topic: str, message: Any, properties: Optional[Dict[str, str]] = None):
        """Publish a message to Pulsar topic
        
        Args:
            topic: Topic name
            message: Message to publish
            properties: Optional message properties
        """
        client = self.get_client()
        
        if topic not in self.producers:
            self.producers[topic] = client.create_producer(topic)
            
        producer = self.producers[topic]
        
        # Convert message to bytes
        if isinstance(message, dict):
            message_bytes = json.dumps(message).encode('utf-8')
        elif isinstance(message, str):
            message_bytes = message.encode('utf-8')
        else:
            message_bytes = message
            
        # Publish message
        producer.send(message_bytes, properties=properties)
        
    def consume_messages(self, topics: List[str], subscription: str, count: int = 1, timeout: int = 30) -> List[Dict[str, Any]]:
        """Consume messages from Pulsar topics
        
        Args:
            topics: Topics to consume from
            subscription: Subscription name
            count: Number of messages to consume
            timeout: Timeout in seconds
            
        Returns:
            List of consumed messages with metadata
        """
        client = self.get_client()
        
        # Create consumer if not exists
        consumer_key = f"{','.join(topics)}:{subscription}"
        if consumer_key not in self.consumers:
            self.consumers[consumer_key] = client.subscribe(
                topics,
                subscription_name=subscription,
                consumer_type=pulsar.ConsumerType.Shared
            )
            
        consumer = self.consumers[consumer_key]
        
        messages = []
        start_time = time.time()
        
        while len(messages) < count and (time.time() - start_time) < timeout:
            try:
                msg = consumer.receive(timeout_millis=1000)
                
                msg_dict = {
                    'topic': msg.topic_name(),
                    'message_id': str(msg.message_id()),
                    'data': msg.data().decode('utf-8', errors='replace'),
                    'properties': dict(msg.properties())
                }
                messages.append(msg_dict)
                
                # Acknowledge message
                consumer.acknowledge(msg)
                
            except Exception as e:
                # Check if we've exceeded timeout
                if time.time() - start_time >= timeout:
                    import logging
                    logging.debug(f"Timeout reached while consuming Pulsar messages: {e}")
                    break
                # Otherwise, likely a receive timeout, continue trying
                    
        return messages
        
    def close(self):
        """Close all producers, consumers, and client"""
        for producer in self.producers.values():
            producer.close()
        for consumer in self.consumers.values():
            consumer.close()
        if self.client:
            self.client.close()


class MessageValidator:
    """Validator for message content and metadata"""
    
    @staticmethod
    def validate_message_content(message: Dict[str, Any], expected_content: Any) -> bool:
        """Validate message content
        
        Args:
            message: Message dictionary
            expected_content: Expected content (string or dict)
            
        Returns:
            True if content matches
        """
        actual = message.get('value') or message.get('data')
        
        # Handle JSON comparison
        if isinstance(expected_content, dict):
            try:
                actual_dict = json.loads(actual) if isinstance(actual, str) else actual
                return actual_dict == expected_content
            except json.JSONDecodeError:
                return False
                
        # String comparison
        return str(actual) == str(expected_content)
        
    @staticmethod
    def validate_message_header(message: Dict[str, Any], header_key: str, header_value: str) -> bool:
        """Validate message header
        
        Args:
            message: Message dictionary
            header_key: Header key to check
            header_value: Expected header value
            
        Returns:
            True if header matches
        """
        headers = message.get('headers') or message.get('properties') or {}
        return headers.get(header_key) == header_value
        
    @staticmethod
    def validate_message_count(messages: List[Dict[str, Any]], expected_count: int) -> bool:
        """Validate message count
        
        Args:
            messages: List of messages
            expected_count: Expected count
            
        Returns:
            True if count matches
        """
        return len(messages) == expected_count
