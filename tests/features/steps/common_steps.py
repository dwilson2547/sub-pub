"""Common step definitions for Behave tests"""

import json
import time
import subprocess
import yaml
from pathlib import Path
from behave import given, when, then


# Container setup steps

@given('a Kafka container is running')
def step_kafka_container_running(context):
    """Ensure Kafka container is running"""
    if not hasattr(context, 'kafka_container'):
        kafka = context.container_manager.start_kafka()
        from tests.support.helpers import KafkaTestHelper
        context.helpers['kafka'] = KafkaTestHelper(kafka.get_bootstrap_servers())
        context.kafka_container = kafka
    # Wait for Kafka to be ready
    time.sleep(2)


@given('a Pulsar container is running')
def step_pulsar_container_running(context):
    """Ensure Pulsar container is running"""
    if not hasattr(context, 'pulsar_container'):
        pulsar = context.container_manager.start_pulsar()
        from tests.support.helpers import PulsarTestHelper
        context.helpers['pulsar'] = PulsarTestHelper(pulsar.get_service_url())
        context.pulsar_container = pulsar
    # Wait for Pulsar to be ready
    time.sleep(2)


@given('an Iggy container is running')
def step_iggy_container_running(context):
    """Ensure Iggy container is running"""
    if not hasattr(context, 'iggy_container'):
        iggy = context.container_manager.start_iggy()
        context.iggy_container = iggy
    # Wait for Iggy to be ready
    time.sleep(2)


@given('a Google Pub/Sub emulator is running')
def step_google_pubsub_emulator_running(context):
    """Ensure Google Pub/Sub emulator is running"""
    if not hasattr(context, 'google_pubsub_container'):
        pubsub = context.container_manager.start_google_pubsub()
        context.google_pubsub_container = pubsub
    # Wait for emulator to be ready
    time.sleep(2)


# Configuration steps

@given('a funnel config with {source_count:d} Kafka sources and {dest_count:d} Kafka destination')
def step_funnel_config_kafka(context, source_count, dest_count):
    """Create funnel config with Kafka sources and destination"""
    assert dest_count == 1, "Funnel mode supports only 1 destination"
    
    bootstrap_servers = context.kafka_container.get_bootstrap_servers()
    
    config = {
        'mode': 'funnel',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'funnel': {
            'sources': [],
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers]
                }
            },
            'destination_topic': 'funnel-destination'
        }
    }
    
    # Add sources
    for i in range(1, source_count + 1):
        config['funnel']['sources'].append({
            'type': 'kafka',
            'connection': {
                'bootstrap_servers': [bootstrap_servers],
                'group_id': f'test-group-{i}',
                'auto_offset_reset': 'earliest'
            },
            'topics': [f'source-topic-{i}']
        })
    
    # Save config
    config_path = Path(context.temp_dir) / f'funnel_kafka_{source_count}to{dest_count}.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a funnel config with {source_count:d} Pulsar sources and {dest_count:d} Pulsar destination')
def step_funnel_config_pulsar(context, source_count, dest_count):
    """Create funnel config with Pulsar sources and destination"""
    assert dest_count == 1, "Funnel mode supports only 1 destination"
    
    service_url = context.pulsar_container.get_service_url()
    
    config = {
        'mode': 'funnel',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'funnel': {
            'sources': [],
            'destination': {
                'type': 'pulsar',
                'connection': {
                    'service_url': service_url
                }
            },
            'destination_topic': 'persistent://public/default/funnel-dest'
        }
    }
    
    # Add sources
    for i in range(1, source_count + 1):
        config['funnel']['sources'].append({
            'type': 'pulsar',
            'connection': {
                'service_url': service_url,
                'subscription_name': f'test-sub-{i}'
            },
            'topics': [f'persistent://public/default/source{i}']
        })
    
    # Save config
    config_path = Path(context.temp_dir) / f'funnel_pulsar_{source_count}to{dest_count}.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a funnel config with {source_count:d} Kafka source and {dest_count:d} Pulsar destination')
def step_funnel_config_kafka_to_pulsar(context, source_count, dest_count):
    """Create funnel config from Kafka to Pulsar"""
    assert dest_count == 1, "Funnel mode supports only 1 destination"
    
    kafka_bootstrap = context.kafka_container.get_bootstrap_servers()
    pulsar_url = context.pulsar_container.get_service_url()
    
    config = {
        'mode': 'funnel',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'funnel': {
            'sources': [{
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap],
                    'group_id': 'kafka-to-pulsar-group',
                    'auto_offset_reset': 'earliest'
                },
                'topics': ['kafka-source']
            }],
            'destination': {
                'type': 'pulsar',
                'connection': {
                    'service_url': pulsar_url
                }
            },
            'destination_topic': 'persistent://public/default/kafka-to-pulsar'
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / 'funnel_kafka_to_pulsar.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a fan config with header-based routing using key "{header_key}"')
def step_fan_config_header_routing(context, header_key):
    """Create fan config with header-based routing"""
    bootstrap_servers = context.kafka_container.get_bootstrap_servers()
    
    config = {
        'mode': 'fan',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'fan': {
            'source': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers],
                    'group_id': 'fan-test-group',
                    'auto_offset_reset': 'earliest'
                }
            },
            'source_topic': 'fan-source',
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers]
                }
            },
            'destination_resolver': {
                'type': 'header',
                'key': header_key
            }
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / 'fan_header_routing.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a fan config with payload-based routing using key "{payload_key}"')
def step_fan_config_payload_routing(context, payload_key):
    """Create fan config with payload-based routing"""
    bootstrap_servers = context.kafka_container.get_bootstrap_servers()
    
    config = {
        'mode': 'fan',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'fan': {
            'source': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers],
                    'group_id': 'fan-test-group',
                    'auto_offset_reset': 'earliest'
                }
            },
            'source_topic': 'fan-source',
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers]
                }
            },
            'destination_resolver': {
                'type': 'payload_key',
                'key': payload_key
            }
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / 'fan_payload_routing.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a fan config with Pulsar header-based routing using key "{header_key}"')
def step_fan_config_pulsar_header_routing(context, header_key):
    """Create fan config for Pulsar with header-based routing"""
    service_url = context.pulsar_container.get_service_url()
    
    config = {
        'mode': 'fan',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'fan': {
            'source': {
                'type': 'pulsar',
                'connection': {
                    'service_url': service_url,
                    'subscription_name': 'fan-test-sub'
                }
            },
            'source_topic': 'persistent://public/default/fan-input',
            'destination': {
                'type': 'pulsar',
                'connection': {
                    'service_url': service_url
                }
            },
            'destination_resolver': {
                'type': 'header',
                'key': header_key
            }
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / 'fan_pulsar_header_routing.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config with {mapping_count:d} topic mappings')
@given('a one-to-one config with {mapping_count:d} topic mapping')
def step_one_to_one_config_kafka(context, mapping_count):
    """Create one-to-one config with topic mappings"""
    bootstrap_servers = context.kafka_container.get_bootstrap_servers()
    
    # Define available mappings
    all_mappings = [
        {'source_topic': 'ordered-input', 'destination_topic': 'ordered-output'},
        {'source_topic': 'orders', 'destination_topic': 'orders-processed'},
        {'source_topic': 'payments', 'destination_topic': 'payments-processed'},
        {'source_topic': 'inventory', 'destination_topic': 'inventory-processed'},
        {'source_topic': 'high-volume-1', 'destination_topic': 'high-volume-1-out'},
        {'source_topic': 'high-volume-2', 'destination_topic': 'high-volume-2-out'},
    ]
    
    # Select mappings based on count
    mappings = all_mappings[:mapping_count]
    
    config = {
        'mode': 'one_to_one',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'one_to_one': {
            'source': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers],
                    'group_id': 'one-to-one-test-group',
                    'auto_offset_reset': 'earliest'
                }
            },
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [bootstrap_servers]
                }
            },
            'mappings': mappings
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / f'one_to_one_{mapping_count}_mappings.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config with {mapping_count:d} Pulsar topic mappings')
def step_one_to_one_config_pulsar(context, mapping_count):
    """Create one-to-one config for Pulsar"""
    service_url = context.pulsar_container.get_service_url()
    
    mappings = [
        {
            'source_topic': 'persistent://public/default/input1',
            'destination_topic': 'persistent://public/default/output1'
        },
        {
            'source_topic': 'persistent://public/default/input2',
            'destination_topic': 'persistent://public/default/output2'
        },
    ][:mapping_count]
    
    config = {
        'mode': 'one_to_one',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'one_to_one': {
            'source': {
                'type': 'pulsar',
                'connection': {
                    'service_url': service_url,
                    'subscription_name': 'one-to-one-test-sub'
                }
            },
            'destination': {
                'type': 'pulsar',
                'connection': {
                    'service_url': service_url
                }
            },
            'mappings': mappings
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / f'one_to_one_pulsar_{mapping_count}_mappings.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config with Kafka source and Pulsar destination')
def step_one_to_one_config_kafka_to_pulsar(context):
    """Create one-to-one config from Kafka to Pulsar"""
    kafka_bootstrap = context.kafka_container.get_bootstrap_servers()
    pulsar_url = context.pulsar_container.get_service_url()
    
    config = {
        'mode': 'one_to_one',
        'thread_pool': {
            'max_workers': 10,
            'queue_size': 1000
        },
        'back_pressure': {
            'enabled': True,
            'queue_high_watermark': 0.8,
            'queue_low_watermark': 0.5
        },
        'one_to_one': {
            'source': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap],
                    'group_id': 'kafka-to-pulsar-group',
                    'auto_offset_reset': 'earliest'
                }
            },
            'destination': {
                'type': 'pulsar',
                'connection': {
                    'service_url': pulsar_url
                }
            },
            'mappings': [
                {
                    'source_topic': 'kafka-orders',
                    'destination_topic': 'persistent://public/default/pulsar-orders'
                },
                {
                    'source_topic': 'kafka-payments',
                    'destination_topic': 'persistent://public/default/pulsar-payments'
                }
            ]
        }
    }
    
    # Save config
    config_path = Path(context.temp_dir) / 'one_to_one_kafka_to_pulsar.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))
