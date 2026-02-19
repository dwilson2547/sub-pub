"""Configuration management for sub-pub"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import yaml


@dataclass
class ThreadPoolConfig:
    """Thread pool configuration"""
    max_workers: int = 10
    queue_size: int = 1000


@dataclass
class BackPressureConfig:
    """Back-pressure configuration"""
    enabled: bool = True
    queue_high_watermark: float = 0.8  # 80% full triggers back-pressure
    queue_low_watermark: float = 0.5   # 50% full releases back-pressure


@dataclass
class MessageSystemConfig:
    """Configuration for a message system"""
    type: str  # kafka, pulsar, eventhubs, iggy, google_pubsub
    connection: Dict[str, Any]
    topics: Optional[List[str]] = None


@dataclass
class FunnelConfig:
    """Configuration for funnel mode (many -> one)"""
    sources: List[MessageSystemConfig]
    destination: MessageSystemConfig
    destination_topic: str


@dataclass
class FanConfig:
    """Configuration for fan mode (one -> many)"""
    source: MessageSystemConfig
    source_topic: str
    destination: MessageSystemConfig
    destination_resolver: Dict[str, str]  # type: header or payload_key, key: the key to look up


@dataclass
class OneToOneMapping:
    """Single source-destination mapping"""
    source_topic: str
    destination_topic: str


@dataclass
class OneToOneConfig:
    """Configuration for one-to-one mode"""
    source: MessageSystemConfig
    destination: MessageSystemConfig
    mappings: List[OneToOneMapping]


@dataclass
class Config:
    """Main configuration"""
    mode: str  # funnel, fan, one_to_one
    thread_pool: ThreadPoolConfig
    back_pressure: BackPressureConfig
    processor_class: Optional[str] = None  # Fully qualified class name
    funnel: Optional[FunnelConfig] = None
    fan: Optional[FanConfig] = None
    one_to_one: Optional[OneToOneConfig] = None
    
    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        """Load configuration from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse thread pool config
        thread_pool_data = data.get('thread_pool', {})
        thread_pool = ThreadPoolConfig(
            max_workers=thread_pool_data.get('max_workers', 10),
            queue_size=thread_pool_data.get('queue_size', 1000)
        )
        
        # Parse back-pressure config
        back_pressure_data = data.get('back_pressure', {})
        back_pressure = BackPressureConfig(
            enabled=back_pressure_data.get('enabled', True),
            queue_high_watermark=back_pressure_data.get('queue_high_watermark', 0.8),
            queue_low_watermark=back_pressure_data.get('queue_low_watermark', 0.5)
        )
        
        mode = data['mode']
        
        # Parse mode-specific config
        funnel = None
        fan = None
        one_to_one = None
        
        if mode == 'funnel':
            funnel_data = data['funnel']
            sources = [
                MessageSystemConfig(**src) 
                for src in funnel_data['sources']
            ]
            destination = MessageSystemConfig(**funnel_data['destination'])
            funnel = FunnelConfig(
                sources=sources,
                destination=destination,
                destination_topic=funnel_data['destination_topic']
            )
        elif mode == 'fan':
            fan_data = data['fan']
            source = MessageSystemConfig(**fan_data['source'])
            destination = MessageSystemConfig(**fan_data['destination'])
            fan = FanConfig(
                source=source,
                source_topic=fan_data['source_topic'],
                destination=destination,
                destination_resolver=fan_data['destination_resolver']
            )
        elif mode == 'one_to_one':
            oto_data = data['one_to_one']
            source = MessageSystemConfig(**oto_data['source'])
            destination = MessageSystemConfig(**oto_data['destination'])
            mappings = [
                OneToOneMapping(**m) 
                for m in oto_data['mappings']
            ]
            one_to_one = OneToOneConfig(
                source=source,
                destination=destination,
                mappings=mappings
            )
        
        return cls(
            mode=mode,
            thread_pool=thread_pool,
            back_pressure=back_pressure,
            processor_class=data.get('processor_class'),
            funnel=funnel,
            fan=fan,
            one_to_one=one_to_one
        )
