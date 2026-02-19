# Sub-Pub End-to-End Test Suite

This directory contains a comprehensive Gherkin-based test suite for sub-pub that uses testcontainers to spin up temporary message system services and validate end-to-end functionality.

## Overview

The test suite uses:
- **Behave** (Python BDD framework) for Gherkin feature files and step definitions
- **Testcontainers** for spinning up temporary Docker containers
- **pytest-bdd** (optional) for additional testing capabilities

## Supported Message Systems

The test suite supports the following message systems via testcontainers:

- ✅ **Apache Kafka** - Confluent Platform container
- ✅ **Apache Pulsar** - Official Pulsar container
- ✅ **Iggy** - Official Iggy container
- ✅ **Google Cloud Pub/Sub** - Emulator container

## Installation

### Prerequisites

1. **Docker**: Must be installed and running
2. **Python 3.10+**: Required for sub-pub
3. **Dependencies**: Install test dependencies

```bash
# Install sub-pub with test dependencies
pip install -e ".[test,all]"

# Or install just the essentials
pip install -e ".[test,kafka,pulsar]"
```

### Verify Installation

```bash
# Check if behave is installed
behave --version

# Check if Docker is running
docker ps
```

## Running Tests

### Run All Tests

```bash
# Run all feature tests
behave tests/features/

# Run with verbose output
behave tests/features/ -v
```

### Run Specific Feature Files

```bash
# Run only funnel mode tests
behave tests/features/funnel.feature

# Run only fan mode tests
behave tests/features/fan.feature

# Run only one-to-one mode tests
behave tests/features/one_to_one.feature

# Run cross-system tests
behave tests/features/cross_system.feature
```

### Run Tests by Tags

Tests are tagged by message system for selective execution:

```bash
# Run only Kafka tests
behave tests/features/ --tags=kafka

# Run only Pulsar tests
behave tests/features/ --tags=pulsar

# Run Kafka or Pulsar tests
behave tests/features/ --tags=kafka,pulsar

# Run cross-system tests (requires multiple containers)
behave tests/features/ --tags="kafka and pulsar"

# Run Iggy tests
behave tests/features/ --tags=iggy

# Run Google Pub/Sub tests
behave tests/features/ --tags=google_pubsub
```

### Run Specific Scenarios

```bash
# Run a specific scenario by name
behave tests/features/ --name="Funnel messages from two Kafka sources"

# Run scenarios matching a pattern
behave tests/features/ --name=".*high.*volume.*"
```

## Test Structure

```
tests/
├── features/                 # Gherkin feature files
│   ├── environment.py       # Behave hooks and fixtures
│   ├── funnel.feature       # Funnel mode tests
│   ├── fan.feature          # Fan mode tests
│   ├── one_to_one.feature   # One-to-one mode tests
│   └── cross_system.feature # Cross-system routing tests
├── steps/                    # Step definitions
│   ├── common_steps.py      # Container and config steps
│   ├── message_steps.py     # Publishing and validation steps
│   └── cross_system_steps.py # Cross-system routing steps
└── support/                  # Test utilities
    ├── containers.py        # Testcontainer wrappers
    └── helpers.py           # Message helpers and validators
```

## Feature Scenarios

### Funnel Mode

Test aggregating messages from multiple sources into one destination:

```gherkin
Scenario: Funnel messages from two Kafka sources to one Kafka destination
  Given a Kafka container is running
  And a funnel config with 2 Kafka sources and 1 Kafka destination
  When I publish message "message1" to source topic "source-topic-1"
  And I publish message "message2" to source topic "source-topic-2"
  And I start sub-pub with the funnel config
  And I wait for 5 seconds
  Then destination topic "funnel-destination" should receive 2 messages
```

### Fan Mode

Test routing messages from one source to multiple destinations:

```gherkin
Scenario: Fan messages based on header routing
  Given a Kafka container is running
  And a fan config with header-based routing using key "destination_topic"
  When I publish message "order-data" with header "destination_topic" = "orders"
  And I start sub-pub with the fan config
  Then destination topic "orders" should receive 1 message
```

### One-to-One Mode

Test fixed topic mappings between systems:

```gherkin
Scenario: One-to-one mapping between Kafka topics
  Given a Kafka container is running
  And a one-to-one config with 3 topic mappings
  When I publish message "order-123" to topic "orders"
  And I start sub-pub with the one-to-one config
  Then destination topic "orders-processed" should receive 1 message
```

### Cross-System Integration

Test routing between different message systems:

```gherkin
Scenario: Kafka to Pulsar message routing
  Given a Kafka container is running
  And a Pulsar container is running
  And a one-to-one config routing Kafka to Pulsar
  When I publish message "test" to Kafka topic "kafka-src"
  And I start sub-pub with the one-to-one config
  Then Pulsar topic "persistent://public/default/pulsar-dst" should receive 1 message
```

## Writing New Tests

### 1. Create a Feature File

Create a new `.feature` file in `tests/features/`:

```gherkin
Feature: My New Feature
  As a user
  I want to test something
  So that I can be confident it works

  @kafka
  Scenario: Test scenario name
    Given a Kafka container is running
    When I do something
    Then I expect some result
```

### 2. Add Step Definitions

If you need new steps, add them to `tests/steps/`:

```python
from behave import given, when, then

@when('I do something')
def step_do_something(context):
    # Your implementation
    pass

@then('I expect some result')
def step_expect_result(context):
    # Your assertions
    assert something, "Failure message"
```

### 3. Tag Your Scenarios

Use tags to control which containers are started:

- `@kafka` - Starts Kafka container
- `@pulsar` - Starts Pulsar container
- `@iggy` - Starts Iggy container
- `@google_pubsub` - Starts Google Pub/Sub emulator

## Container Management

### Container Lifecycle

- **Startup**: Containers are started based on scenario tags
- **Cleanup**: Containers are automatically stopped after tests
- **Reuse**: Containers are reused across scenarios with the same tags

### Manual Container Control

For debugging, you can manually manage containers:

```python
from tests.support.containers import ContainerManager

# Create manager
manager = ContainerManager()

# Start containers
kafka = manager.start_kafka()
pulsar = manager.start_pulsar()

# Get connection info
bootstrap_servers = kafka.get_bootstrap_servers()
service_url = pulsar.get_service_url()

# Stop all containers
manager.stop_all()
```

## Troubleshooting

### Docker Issues

```bash
# Check if Docker is running
docker ps

# Check Docker resources
docker info

# Clean up old containers
docker container prune -f
```

### Container Startup Failures

If containers fail to start:

1. Check Docker logs: `docker logs <container-id>`
2. Increase timeout in `containers.py`
3. Verify port availability
4. Check Docker resources (memory, disk)

### Test Failures

```bash
# Run with verbose output
behave tests/features/ -v

# Run with no capture (see all output)
behave tests/features/ --no-capture

# Run specific scenario for debugging
behave tests/features/funnel.feature --name="Funnel messages from two Kafka"
```

### Message Not Received

If messages aren't being received:

1. Check sub-pub logs in test output
2. Increase wait times in scenarios
3. Verify topic names match configuration
4. Check container networking

## Performance Considerations

### Test Execution Time

- **Kafka tests**: ~30-60 seconds per scenario
- **Pulsar tests**: ~45-90 seconds per scenario
- **Cross-system tests**: ~60-120 seconds per scenario

Container startup is the main time cost. Scenarios with the same tags reuse containers to improve performance.

### Parallel Execution

Behave supports parallel execution, but it's disabled by default for container tests to avoid port conflicts:

```bash
# Sequential execution (default)
behave tests/features/

# Parallel execution (experimental)
behave tests/features/ --jobs=4
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e ".[test,all]"
      
      - name: Run Kafka tests
        run: behave tests/features/ --tags=kafka
      
      - name: Run Pulsar tests
        run: behave tests/features/ --tags=pulsar
```

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Use descriptive scenario names
3. Tag scenarios appropriately
4. Add comments for complex logic
5. Update this README if adding new features

## License

Same as sub-pub project (MIT License)
