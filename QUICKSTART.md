# Sub-Pub Quick Reference

## Installation

```bash
# Basic installation
pip install -e .

# With Kafka support
pip install -e ".[kafka]"

# With all adapters
pip install -e ".[all]"
```

## Running Sub-Pub

```bash
# Basic usage
sub-pub -c config.yaml

# With specific log level
sub-pub -c config.yaml -l DEBUG

# Or using Python module
python -m sub_pub.main -c config.yaml -l INFO
```

## Configuration Quick Start

### Funnel Mode (Many → One)

```yaml
mode: funnel
thread_pool:
  max_workers: 20
  queue_size: 2000
back_pressure:
  enabled: true
funnel:
  sources:
    - type: kafka
      connection: {...}
      topics: ['topic-a', 'topic-b']
  destination:
    type: kafka
    connection: {...}
  destination_topic: 'output'
```

### Fan Mode (One → Many)

```yaml
mode: fan
fan:
  source:
    type: kafka
    connection: {...}
  source_topic: 'input'
  destination:
    type: kafka
    connection: {...}
  destination_resolver:
    type: 'header'  # or 'payload_key'
    key: 'destination_topic'
```

### One-to-One Mode

```yaml
mode: one_to_one
one_to_one:
  source:
    type: kafka
    connection: {...}
  destination:
    type: kafka
    connection: {...}
  mappings:
    - source_topic: 'orders'
      destination_topic: 'orders-processed'
```

## Supported Message Systems

| System | Type Name | Status | Installation |
|--------|-----------|--------|--------------|
| Kafka | `kafka` | ✅ Full | `pip install kafka-python` |
| Pulsar | `pulsar` | ✅ Full | `pip install pulsar-client` |
| Event Hubs | `eventhubs` | ⚠️ Stub | `pip install azure-eventhub` |
| Google Pub/Sub | `google_pubsub` | ⚠️ Stub | `pip install google-cloud-pubsub` |
| Iggy | `iggy` | ⚠️ Stub | Not available |
| Mock | `mock` | ✅ Full | Built-in |

## Custom Processors

Create a processor:

```python
from sub_pub.domain.processor import MessageProcessor
from sub_pub.core.message import Message

class MyProcessor(MessageProcessor):
    def process(self, message: Message) -> Message:
        # Your logic here
        message.headers['processed'] = 'true'
        return message
```

Use in config:

```yaml
processor_class: "my_module.MyProcessor"
```

## Performance Tuning

| Setting | Default | Low Volume | High Volume |
|---------|---------|------------|-------------|
| max_workers | 20 | 5 | 50+ |
| queue_size | 2000 | 100 | 10000 |
| high_watermark | 0.8 | 0.6 | 0.9 |
| low_watermark | 0.5 | 0.3 | 0.7 |

## Common Connection Configs

### Kafka

```yaml
connection:
  bootstrap_servers: ['localhost:9092']
  group_id: 'sub-pub'
  auto_offset_reset: 'earliest'
  # Producer settings
  linger_ms: 10
  compression_type: 'lz4'
```

### Pulsar

```yaml
connection:
  service_url: 'pulsar://localhost:6650'
  subscription_name: 'sub-pub'
```

### Event Hubs

```yaml
connection:
  connection_string: 'Endpoint=...'
  consumer_group: '$Default'
```

### Google Pub/Sub

```yaml
connection:
  project_id: 'my-project'
  subscription_id: 'my-subscription'
```

## Metrics

### Available Metrics

- `message_count` - Total messages processed
- `total_bytes` - Total data volume
- `error_count` - Failed operations
- `rate_per_second` - Current throughput
- `last_message_time` - Last message timestamp

### Viewing Metrics

Metrics are printed on shutdown:

```
Source metrics: {
  'topic-a': {
    'message_count': 1000,
    'total_bytes': 524288,
    'rate_per_second': 100.5
  }
}
```

## Signal Handling

| Signal | Action |
|--------|--------|
| SIGINT (Ctrl+C) | Graceful shutdown with metrics |
| SIGTERM | Graceful shutdown with metrics |

## Troubleshooting

### Low Throughput
- Increase `max_workers`
- Increase `queue_size`
- Check network latency

### High Memory Usage
- Reduce `queue_size`
- Reduce `max_workers`
- Enable back-pressure

### Frequent Back-Pressure
- Increase `queue_size`
- Optimize destination config
- Check destination capacity

### Message Loss
- Check error logs
- Verify connectivity
- Review commit settings

## Examples

All examples are in the `examples/` directory:

- `funnel-config.yaml` - Funnel mode
- `fan-config.yaml` - Fan mode
- `one-to-one-config.yaml` - One-to-one mode
- `mock-config.yaml` - Testing with mocks
- `custom_processors.py` - Custom processor examples

## Testing

```bash
# Run basic test
python test_basic.py

# Run with mock config
python -m sub_pub.main -c examples/mock-config.yaml
```

## More Information

- Full documentation: `README.md`
- Architecture guide: `ARCHITECTURE.md`
- GitHub: https://github.com/dwilson2547/sub-pub
