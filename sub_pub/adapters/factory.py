"""Factory for creating message sources and publishers"""
import logging
from typing import Union

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.adapters.mock import MockSource, MockPublisher
from sub_pub.adapters.kafka import KafkaSource, KafkaPublisher
from sub_pub.adapters.pulsar import PulsarSource, PulsarPublisher
from sub_pub.adapters.eventhubs import EventHubsSource, EventHubsPublisher
from sub_pub.adapters.google_pubsub import GooglePubSubSource, GooglePubSubPublisher
from sub_pub.adapters.iggy import IggySource, IggyPublisher

logger = logging.getLogger(__name__)


def create_source(adapter_type: str, config: dict) -> MessageSource:
    """Create a message source based on the adapter type"""
    adapters = {
        'mock': MockSource,
        'kafka': KafkaSource,
        'pulsar': PulsarSource,
        'eventhubs': EventHubsSource,
        'google_pubsub': GooglePubSubSource,
        'iggy': IggySource,
    }
    
    adapter_class = adapters.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
    
    logger.info(f"Creating {adapter_type} source")
    return adapter_class(config)


def create_publisher(adapter_type: str, config: dict) -> MessagePublisher:
    """Create a message publisher based on the adapter type"""
    adapters = {
        'mock': MockPublisher,
        'kafka': KafkaPublisher,
        'pulsar': PulsarPublisher,
        'eventhubs': EventHubsPublisher,
        'google_pubsub': GooglePubSubPublisher,
        'iggy': IggyPublisher,
    }
    
    adapter_class = adapters.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
    
    logger.info(f"Creating {adapter_type} publisher")
    return adapter_class(config)
