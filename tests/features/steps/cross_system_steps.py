"""Cross-system routing step definitions"""

import yaml
from pathlib import Path
from behave import given


@given('a one-to-one config routing Kafka to Pulsar')
def step_one_to_one_kafka_to_pulsar_routing(context):
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
                    'group_id': 'cross-system-group',
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
                    'source_topic': 'kafka-src',
                    'destination_topic': 'persistent://public/default/pulsar-dst'
                }
            ]
        }
    }
    
    config_path = Path(context.temp_dir) / 'cross_kafka_to_pulsar.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config routing Pulsar to Kafka')
def step_one_to_one_pulsar_to_kafka_routing(context):
    """Create one-to-one config from Pulsar to Kafka"""
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
                'type': 'pulsar',
                'connection': {
                    'service_url': pulsar_url,
                    'subscription_name': 'pulsar-to-kafka-sub'
                }
            },
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap]
                }
            },
            'mappings': [
                {
                    'source_topic': 'persistent://public/default/pulsar-src',
                    'destination_topic': 'kafka-dst'
                }
            ]
        }
    }
    
    config_path = Path(context.temp_dir) / 'cross_pulsar_to_kafka.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a funnel config with Kafka and Pulsar sources to Kafka destination')
def step_funnel_mixed_sources_to_kafka(context):
    """Create funnel config with mixed Kafka and Pulsar sources"""
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
            'sources': [
                {
                    'type': 'kafka',
                    'connection': {
                        'bootstrap_servers': [kafka_bootstrap],
                        'group_id': 'mixed-kafka-group',
                        'auto_offset_reset': 'earliest'
                    },
                    'topics': ['kafka-input']
                },
                {
                    'type': 'pulsar',
                    'connection': {
                        'service_url': pulsar_url,
                        'subscription_name': 'mixed-pulsar-sub'
                    },
                    'topics': ['persistent://public/default/pulsar-input']
                }
            ],
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap]
                }
            },
            'destination_topic': 'mixed-output'
        }
    }
    
    config_path = Path(context.temp_dir) / 'funnel_mixed_sources.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config routing Iggy to Kafka')
def step_one_to_one_iggy_to_kafka_routing(context):
    """Create one-to-one config from Iggy to Kafka"""
    kafka_bootstrap = context.kafka_container.get_bootstrap_servers()
    iggy_connection = context.iggy_container.get_connection_string()
    
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
                'type': 'iggy',
                'connection': {
                    'server': iggy_connection
                }
            },
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap]
                }
            },
            'mappings': [
                {
                    'source_topic': 'test-stream',
                    'destination_topic': 'kafka-from-iggy'
                }
            ]
        }
    }
    
    config_path = Path(context.temp_dir) / 'cross_iggy_to_kafka.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))


@given('a one-to-one config routing Google Pub/Sub to Kafka')
def step_one_to_one_google_pubsub_to_kafka_routing(context):
    """Create one-to-one config from Google Pub/Sub to Kafka"""
    kafka_bootstrap = context.kafka_container.get_bootstrap_servers()
    pubsub_endpoint = context.google_pubsub_container.get_endpoint()
    
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
                'type': 'google_pubsub',
                'connection': {
                    'project_id': 'test-project',
                    'emulator_host': pubsub_endpoint
                }
            },
            'destination': {
                'type': 'kafka',
                'connection': {
                    'bootstrap_servers': [kafka_bootstrap]
                }
            },
            'mappings': [
                {
                    'source_topic': 'test-topic',
                    'destination_topic': 'kafka-from-pubsub'
                }
            ]
        }
    }
    
    config_path = Path(context.temp_dir) / 'cross_google_pubsub_to_kafka.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    context.current_config = str(config_path)
    context.config_files.append(str(config_path))
