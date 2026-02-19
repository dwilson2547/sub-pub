# Architecture and Performance Guide

## Architecture Overview

Sub-Pub follows a pipeline architecture with three main stages:

```
┌─────────────────┐
│     SOURCE      │  Consumes messages from source system(s)
│   (Consumer)    │  - Thread-safe message consumption
└────────┬────────┘  - Multiple sources in Funnel mode
         │
         ↓
┌─────────────────┐
│  DOMAIN QUEUE   │  Queue with back-pressure
│   (Max: 2000)   │  - Configurable queue size
└────────┬────────┘  - High/low water marks
         │
         ↓
┌─────────────────┐
│     DOMAIN      │  Message processing layer
│   (Processor)   │  - Thread pool (default: 20 workers)
└────────┬────────┘  - Extensible processors
         │
         ↓
┌─────────────────┐
│ PUBLISH QUEUE   │  Queue with back-pressure
│   (Max: 2000)   │  - Configurable queue size
└────────┬────────┘  - High/low water marks
         │
         ↓
┌─────────────────┐
│   PUBLISHER     │  Publishes messages to destination(s)
│  (Producer)     │  - Thread pool (default: 20 workers)
└─────────────────┘  - Batch publishing where supported
```

## Performance Characteristics

### Thread Pool Design

Each flow maintains multiple thread pools:

1. **Domain Thread Pool**: Processes messages through the domain layer
   - Default: 20 workers
   - Configurable via `thread_pool.max_workers`

2. **Publish Thread Pool**: Publishes processed messages
   - Default: 20 workers
   - Same configuration as domain pool

3. **Consumer Threads**: 
   - Funnel mode: One thread per source
   - Fan/OneToOne: Single consumer thread

### Back-Pressure Mechanism

Back-pressure prevents overwhelming downstream systems:

- **High Watermark (default 80%)**: Triggers back-pressure
  - Consumption slows down
  - Upstream processing waits

- **Low Watermark (default 50%)**: Releases back-pressure
  - Normal consumption resumes
  - Processing continues

### Queue Sizing

Default queue size is 2000 messages per stage:

```yaml
thread_pool:
  queue_size: 2000  # Messages buffered between stages
```

**Tuning Guidelines:**
- Higher queue size = More memory, better throughput on spikes
- Lower queue size = Less memory, faster back-pressure
- Typical range: 100-10000 depending on message size

## Performance Tuning

### 1. Thread Pool Sizing

**For CPU-bound processing:**
```yaml
thread_pool:
  max_workers: 8  # Number of CPU cores
```

**For I/O-bound processing (network calls):**
```yaml
thread_pool:
  max_workers: 50  # More threads for I/O wait
```

**For high-throughput pass-through:**
```yaml
thread_pool:
  max_workers: 20  # Balanced for most cases
  queue_size: 5000  # Larger buffer
```

### 2. Back-Pressure Tuning

**Strict back-pressure (quick response to slowdowns):**
```yaml
back_pressure:
  enabled: true
  queue_high_watermark: 0.6  # Trigger early
  queue_low_watermark: 0.3   # Release conservatively
```

**Lenient back-pressure (handle traffic spikes):**
```yaml
back_pressure:
  enabled: true
  queue_high_watermark: 0.9  # Trigger late
  queue_low_watermark: 0.7   # Release aggressively
```

**Disabled (maximum throughput, risk of overflow):**
```yaml
back_pressure:
  enabled: false
```

### 3. Message System Configuration

**Kafka Consumer Tuning:**
```yaml
source:
  type: kafka
  connection:
    bootstrap_servers: ['localhost:9092']
    group_id: 'sub-pub'
    fetch_min_bytes: 50000        # Wait for 50KB before returning
    fetch_max_wait_ms: 500        # Max wait time
    max_partition_fetch_bytes: 1048576  # 1MB per partition
```

**Kafka Producer Tuning:**
```yaml
destination:
  type: kafka
  connection:
    bootstrap_servers: ['localhost:9094']
    linger_ms: 10                 # Wait 10ms to batch
    batch_size: 32768             # 32KB batches
    compression_type: 'lz4'       # Compress messages
```

## Flow-Specific Considerations

### Funnel Mode

**Best for:**
- Aggregating multiple data sources
- Consolidating logs/events
- Multi-region data collection

**Performance tips:**
- Each source runs in its own thread
- Consider source system limits
- Balance source throughput

### Fan Mode

**Best for:**
- Dynamic routing based on message content
- Topic-based event distribution
- Content-based message routing

**Performance tips:**
- Header-based routing is faster than payload parsing
- Use simple routing logic
- Consider destination topic cardinality

### One-to-One Mode

**Best for:**
- Fixed topic mappings
- Multi-tenant data pipelines
- Parallel independent streams

**Performance tips:**
- All topics share consumer/publisher threads
- Good for many low-volume topics
- Efficient resource sharing

## Monitoring and Metrics

### Available Metrics

Per-topic metrics include:
- `message_count`: Total messages processed
- `total_bytes`: Total data volume
- `error_count`: Failed messages
- `rate_per_second`: Current throughput
- `last_message_time`: Timestamp of last message

### Grafana Dashboard Queries

Example Prometheus queries (when metrics endpoint is added):

```promql
# Message throughput by source topic
rate(sub_pub_source_messages_total[5m])

# Data volume by destination
rate(sub_pub_destination_bytes_total[5m])

# Error rate
rate(sub_pub_errors_total[5m])

# Queue utilization
sub_pub_queue_size / sub_pub_queue_capacity
```

## Common Performance Issues

### Issue: Low Throughput

**Symptoms:**
- Messages processing slowly
- Low CPU usage

**Solutions:**
1. Increase `max_workers`
2. Increase `queue_size`
3. Check network latency
4. Optimize domain processor

### Issue: High Memory Usage

**Symptoms:**
- Memory grows over time
- OOM errors

**Solutions:**
1. Reduce `queue_size`
2. Reduce `max_workers`
3. Enable back-pressure
4. Check for memory leaks in processor

### Issue: Message Loss

**Symptoms:**
- Source metrics > Destination metrics
- Error count increasing

**Solutions:**
1. Check destination connectivity
2. Review error logs
3. Add retry logic
4. Increase timeout values

### Issue: Back-Pressure Triggering Frequently

**Symptoms:**
- Logs show "Back-pressure detected"
- Slow overall throughput

**Solutions:**
1. Increase `queue_size`
2. Increase `max_workers` for publish pool
3. Optimize publisher configuration
4. Check destination system capacity

## Best Practices

1. **Start Conservative**: Begin with default settings and tune based on metrics

2. **Monitor Metrics**: Watch message rates, error rates, and queue utilization

3. **Test Under Load**: Use realistic workloads for performance testing

4. **Gradual Tuning**: Change one parameter at a time

5. **Resource Limits**: Set appropriate OS limits (file descriptors, network buffers)

6. **Error Handling**: Implement proper error handling in custom processors

7. **Graceful Shutdown**: Always shutdown cleanly to avoid message loss

## Example High-Performance Configuration

```yaml
mode: one_to_one

thread_pool:
  max_workers: 50      # High parallelism
  queue_size: 10000    # Large buffer

back_pressure:
  enabled: true
  queue_high_watermark: 0.85
  queue_low_watermark: 0.60

one_to_one:
  source:
    type: kafka
    connection:
      bootstrap_servers: ['kafka1:9092', 'kafka2:9092']
      group_id: 'sub-pub-high-perf'
      fetch_min_bytes: 100000
      max_partition_fetch_bytes: 2097152
  
  destination:
    type: kafka
    connection:
      bootstrap_servers: ['kafka3:9092', 'kafka4:9092']
      linger_ms: 5
      batch_size: 65536
      compression_type: 'lz4'
  
  mappings:
    - source_topic: 'high-volume-topic'
      destination_topic: 'processed-topic'
```

This configuration can handle 100k+ messages/second depending on:
- Message size
- Network latency
- Hardware resources
- Domain processor complexity
