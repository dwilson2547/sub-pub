"""Main application entry point"""
import argparse
import logging
import signal
import sys
from importlib import import_module

from sub_pub.config.models import Config
from sub_pub.adapters.factory import create_source, create_publisher
from sub_pub.flows.funnel import FunnelFlow
from sub_pub.flows.fan import FanFlow
from sub_pub.flows.one_to_one import OneToOneFlow
from sub_pub.domain.processor import PassThroughProcessor

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_processor(processor_class_name: str):
    """Dynamically load a message processor class"""
    if not processor_class_name:
        return PassThroughProcessor()
    
    try:
        module_name, class_name = processor_class_name.rsplit('.', 1)
        module = import_module(module_name)
        processor_class = getattr(module, class_name)
        return processor_class()
    except Exception as e:
        logger.error(f"Failed to load processor class {processor_class_name}: {e}")
        raise


def create_funnel_flow(config: Config):
    """Create and configure a funnel flow"""
    if not config.funnel:
        raise ValueError("Funnel configuration is missing")
    
    # Create sources
    sources = []
    for src_config in config.funnel.sources:
        source = create_source(src_config.type, src_config.connection)
        source.connect()
        source.subscribe(src_config.topics or [])
        sources.append(source)
    
    # Create destination
    destination = create_publisher(
        config.funnel.destination.type,
        config.funnel.destination.connection
    )
    
    # Load processor
    processor = load_processor(config.processor_class)
    
    # Create flow
    return FunnelFlow(
        sources=sources,
        destination=destination,
        destination_topic=config.funnel.destination_topic,
        thread_pool_config=config.thread_pool,
        back_pressure_config=config.back_pressure,
        processor=processor
    )


def create_fan_flow(config: Config):
    """Create and configure a fan flow"""
    if not config.fan:
        raise ValueError("Fan configuration is missing")
    
    # Create source
    source = create_source(config.fan.source.type, config.fan.source.connection)
    
    # Create destination
    destination = create_publisher(
        config.fan.destination.type,
        config.fan.destination.connection
    )
    
    # Load processor
    processor = load_processor(config.processor_class)
    
    # Create flow
    return FanFlow(
        source=source,
        source_topic=config.fan.source_topic,
        destination=destination,
        destination_resolver=config.fan.destination_resolver,
        thread_pool_config=config.thread_pool,
        back_pressure_config=config.back_pressure,
        processor=processor
    )


def create_one_to_one_flow(config: Config):
    """Create and configure a one-to-one flow"""
    if not config.one_to_one:
        raise ValueError("One-to-one configuration is missing")
    
    # Create source
    source = create_source(
        config.one_to_one.source.type,
        config.one_to_one.source.connection
    )
    
    # Create destination
    destination = create_publisher(
        config.one_to_one.destination.type,
        config.one_to_one.destination.connection
    )
    
    # Load processor
    processor = load_processor(config.processor_class)
    
    # Create flow
    return OneToOneFlow(
        source=source,
        destination=destination,
        mappings=config.one_to_one.mappings,
        thread_pool_config=config.thread_pool,
        back_pressure_config=config.back_pressure,
        processor=processor
    )


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description='Sub-Pub: Extreme Performance Pub-Sub Message Processor'
    )
    parser.add_argument(
        '-c', '--config',
        required=True,
        help='Path to configuration file (YAML)'
    )
    parser.add_argument(
        '-l', '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    config = Config.from_yaml(args.config)
    
    # Create flow based on mode
    logger.info(f"Starting in {config.mode} mode")
    
    if config.mode == 'funnel':
        flow = create_funnel_flow(config)
    elif config.mode == 'fan':
        flow = create_fan_flow(config)
    elif config.mode == 'one_to_one':
        flow = create_one_to_one_flow(config)
    else:
        logger.error(f"Unknown mode: {config.mode}")
        sys.exit(1)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        flow.shutdown()
        
        # Print final metrics
        metrics = flow.metrics.get_metrics()
        logger.info("Final metrics:")
        logger.info(f"  Uptime: {metrics['uptime_seconds']:.2f}s")
        logger.info(f"  Source metrics: {metrics['source_metrics']}")
        logger.info(f"  Destination metrics: {metrics['destination_metrics']}")
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the flow
    try:
        flow.run()
    except Exception as e:
        logger.error(f"Error running flow: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
