# Sub-Pub

Extreme performance pub-sub message processor written in Python. Process messages between different pub-sub systems with high throughput, back-pressure support, and comprehensive metrics.

## Features

- **Three Run Modes**:
  - **Funnel**: Read from many sources, publish to one destination
  - **Fan**: Read from one source, publish to many destinations (based on message content)
  - **One-to-One**: Multiple independent source-to-destination mappings

- **High Performance**:
  - Thread pool-based parallel processing
  - Configurable worker threads and queue sizes
  - Back-pressure support to prevent overwhelming downstream systems

- **Extensible Domain Layer**:
  - Pass-through processing by default
  - Pluggable custom message processors
  - Easy to add transformation logic

- **Comprehensive Metrics**:
  - Message count and size tracking
  - Per-topic metrics for sources and destinations
  - Message rate calculations
  - Error tracking
  - Ready for Grafana dashboards

- **Supported Message Systems**:
  - Apache Kafka
  - Apache Pulsar
  - Azure Event Hubs
  - Google Cloud Pub/Sub
  - Iggy (stub)
  - Mock (for testing)

## Installation

### Basic Installation

```bash
pip install -e .
```

### With Specific Adapters

```bash
# For Kafka support
pip install -e ".[kafka]"

# For Pulsar support
pip install -e ".[pulsar]"

# For all adapters
pip install -e ".[all]"
```

## Quick Start

### 1. Create a Configuration File

See `examples/` directory for sample configurations:

- `funnel-config.yaml` - Many sources to one destination
- `fan-config.yaml` - One source to many destinations
- `one-to-one-config.yaml` - Multiple source-destination pairs
- `mock-config.yaml` - Testing with mock adapters

### 2. Run Sub-Pub

```bash
sub-pub -c examples/mock-config.yaml -l INFO
```

Or using Python directly:

```bash
python -m sub_pub.main -c examples/mock-config.yaml -l INFO
```

## Configuration

### Funnel Mode

Read from multiple sources and aggregate to a single destination:

```yaml
mode: funnel

thread_pool:
  max_workers: 20
  queue_size: 2000

back_pressure:
  enabled: true
  queue_high_watermark: 0.8
  queue_low_watermark: 0.5

funnel:
  sources:
    - type: kafka
      connection:
        bootstrap_servers: ['localhost:9092']
        group_id: 'sub-pub-group'
      topics:
        - 'topic-a'
        - 'topic-b'
  
  destination:
    type: kafka
    connection:
      bootstrap_servers: ['localhost:9094']
  
  destination_topic: 'aggregated-topic'
```

### Fan Mode

Read from one source and route to many destinations based on message content:

```yaml
mode: fan

fan:
  source:
    type: kafka
    connection:
      bootstrap_servers: ['localhost:9092']
  
  source_topic: 'input-topic'
  
  destination:
    type: kafka
    connection:
      bootstrap_servers: ['localhost:9094']
  
  # Route based on header value
  destination_resolver:
    type: 'header'
    key: 'destination_topic'
  
  # Or route based on JSON payload field
  # destination_resolver:
  #   type: 'payload_key'
  #   key: 'routing_key'
```

### One-to-One Mode

Multiple independent topic mappings:

```yaml
mode: one_to_one

one_to_one:
  source:
    type: kafka
    connection:
      bootstrap_servers: ['localhost:9092']
  
  destination:
    type: kafka
    connection:
      bootstrap_servers: ['localhost:9094']
  
  mappings:
    - source_topic: 'orders'
      destination_topic: 'orders-processed'
    - source_topic: 'payments'
      destination_topic: 'payments-processed'
```

## Custom Message Processors

Create a custom processor to transform messages:

```python
# my_processors.py
from sub_pub.domain.processor import MessageProcessor
from sub_pub.core.message import Message

class MyCustomProcessor(MessageProcessor):
    def process(self, message: Message) -> Message:
        # Add custom logic here
        message.headers['processed_by'] = 'my-processor'
        return message
```

Reference it in your config:

```yaml
processor_class: "my_processors.MyCustomProcessor"
```

## Performance Tuning

### Thread Pool Configuration

```yaml
thread_pool:
  max_workers: 20    # Number of parallel workers
  queue_size: 2000   # Queue size for each processing stage
```

- **max_workers**: Number of threads for domain processing and publishing
- **queue_size**: Maximum messages in queue before applying back-pressure

### Back-Pressure Configuration

```yaml
back_pressure:
  enabled: true
  queue_high_watermark: 0.8  # Apply back-pressure at 80% full
  queue_low_watermark: 0.5   # Release back-pressure at 50% full
```

Back-pressure prevents overwhelming downstream systems by slowing consumption when queues fill up.

## Metrics

Sub-Pub tracks comprehensive metrics:

- **Source Metrics** (per topic):
  - Message count
  - Total bytes processed
  - Error count
  - Message rate (messages/second)
  - Last message timestamp

- **Destination Metrics** (per topic):
  - Message count
  - Total bytes sent
  - Error count
  - Message rate (messages/second)
  - Last message timestamp

Metrics are logged on shutdown and can be exposed via HTTP endpoint for Prometheus/Grafana integration (future enhancement).

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌───────────────┐
│   Source    │ --> │  Domain  │ --> │   Publisher   │
│  (Consume)  │     │ (Process)│     │   (Publish)   │
└─────────────┘     └──────────┘     └───────────────┘
      ↓                   ↓                    ↓
  Thread Pool        Thread Pool         Thread Pool
  + Back-Pressure    + Back-Pressure     + Back-Pressure
```

Each stage runs in its own thread pool with independent back-pressure control.

## Deployment

### Docker

Build and run with Docker:

```bash
# Build the image
docker build -t sub-pub:latest .

# Run with a config file
docker run -v $(pwd)/examples:/app/config sub-pub:latest -c /app/config/mock-config.yaml -l INFO
```

### Kubernetes

Deploy to Kubernetes using Helm:

```bash
# Install with default values
helm install sub-pub ./helm/sub-pub

# Install with custom values
helm install sub-pub ./helm/sub-pub -f custom-values.yaml
```

See [helm/KUBERNETES.md](helm/KUBERNETES.md) for detailed Kubernetes deployment instructions.

## CI/CD Pipeline

The repository uses a GitHub Actions CI/CD pipeline (`.github/workflows/ci-cd.yml`) with the following stages:

- **test** – runs `pytest tests/` on every pull request or push to `main`
- **publish-snapshot** – on pull requests, builds and pushes a Docker snapshot image to Docker Hub
- **release** – on push to `main`, creates a GitHub Release, publishes the Docker image, and publishes the Helm chart to Docker Hub as an OCI artifact

### Required GitHub Secrets

The pipeline requires the following repository secrets to be configured under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | A Docker Hub Personal Access Token with **Read & Write** scope |

> **Note:** Without these secrets configured, the Docker image push and Helm chart publish steps will fail with `401 Unauthorized`.

### Installing the Published Helm Chart

Once a release has been published, you can install the Helm chart directly from Docker Hub's OCI registry:

```bash
helm install sub-pub oci://registry-1.docker.io/<DOCKERHUB_USERNAME>/sub-pub --version <version>
```

### Pipeline Failure: Helm Publish 401 Unauthorized

If you see an error like the following in the `release` job:

```
Error: failed to perform "Exists" on destination: HEAD
"https://registry-1.docker.io/v2/<user>/charts/sub-pub/manifests/...":
response status code 401: Unauthorized
```

This was caused by the `helm push` target using a three-component OCI path
(`registry-1.docker.io/USERNAME/charts/sub-pub`) that Docker Hub does not
support — Docker Hub OCI repositories only accept two-component paths
(`namespace/repository`).

**Fix applied:** The `helm push` target was changed from
`oci://registry-1.docker.io/$DOCKERHUB_USERNAME/charts` →
`oci://registry-1.docker.io/$DOCKERHUB_USERNAME`, which pushes the chart
to `registry-1.docker.io/USERNAME/sub-pub:VERSION` — a valid Docker Hub
repository path.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[all]"

# Run with mock config for testing
python -m sub_pub.main -c examples/mock-config.yaml -l DEBUG
```

### Project Structure

```
sub_pub/
├── core/           # Core abstractions (Message, interfaces)
├── adapters/       # Message system adapters (Kafka, Pulsar, etc.)
├── domain/         # Domain layer (message processors)
├── flows/          # Flow implementations (Funnel, Fan, OneToOne)
├── metrics/        # Metrics collection
├── config/         # Configuration management
└── main.py         # Application entry point
```

## Roadmap

- [ ] HTTP endpoint for live metrics
- [ ] Prometheus metrics exporter
- [ ] Message filtering capabilities
- [ ] Multiple destination servers support
- [ ] Message batching optimization
- [ ] Async I/O support for better performance
- [ ] Complete Event Hubs and Google Pub/Sub implementations
- [ ] Iggy adapter implementation
- [ ] Dead letter queue support
- [ ] Message retry logic

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
