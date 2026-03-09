# Sub-Pub Rust Rewrite — Architecture

This document describes the module layout and design decisions for the Rust
rewrite of the Python `sub-pub` project.

---

## Module Layout

```
rust/
├── Cargo.toml
├── src/
│   ├── lib.rs          – crate root; re-exports all public modules
│   ├── main.rs         – binary entry point (CLI, signal handling)
│   ├── error.rs        – unified SubPubError enum
│   ├── core/
│   │   ├── mod.rs
│   │   ├── message.rs      – Message struct
│   │   └── interfaces.rs   – MessageSource / MessagePublisher traits
│   ├── config/
│   │   ├── mod.rs
│   │   └── models.rs       – Config, FlowConfig, MessageSystemConfig, …
│   ├── domain/
│   │   ├── mod.rs
│   │   └── processor.rs    – MessageProcessor trait + PassThroughProcessor
│   ├── metrics/
│   │   ├── mod.rs
│   │   └── collector.rs    – MetricsCollector + MetricsSnapshot
│   ├── adapters/
│   │   ├── mod.rs
│   │   ├── factory.rs      – create_source / create_publisher factories
│   │   ├── mock.rs         – MockSource + MockPublisher (full)
│   │   ├── kafka.rs        – KafkaSource + KafkaPublisher (stub)
│   │   ├── pulsar.rs       – PulsarSource + PulsarPublisher (stub)
│   │   ├── eventhubs.rs    – EventHubsSource + EventHubsPublisher (stub)
│   │   └── google_pubsub.rs – GooglePubSubSource + GooglePubSubPublisher (stub)
│   └── flows/
│       ├── mod.rs
│       ├── base.rs         – shared pipeline helpers (channels, back-pressure, workers)
│       ├── one_to_one.rs   – OneToOneFlow
│       ├── funnel.rs       – FunnelFlow
│       └── fan.rs          – FanFlow
└── examples/
    ├── mock-one-to-one.yaml
    ├── mock-funnel.yaml
    └── mock-fan.yaml
```

---

## Pipeline Model

Every flow uses a two-stage async channel pipeline:

```
Source(s)
    │
    ▼  (domain_tx → domain_rx)
Domain Worker(s)   ← MessageProcessor::process()
    │
    ▼  (publish_tx → publish_rx)
Publish Worker(s)  → MessagePublisher::publish()
    │
    ▼
Destination
```

Channels are bounded (`mpsc`), which provides natural back-pressure: when the
domain queue is full, source consumers yield automatically.  An explicit
watermark-based back-pressure helper (`apply_back_pressure`) adds a secondary
layer by actively sleeping consumers when the high-watermark is exceeded and
resuming only after the level drops below the low-watermark.

---

## Key Design Decisions

### Async-first

Unlike the Python implementation (which uses `threading.Thread` + blocking
queues), the Rust rewrite is built on **Tokio** tasks and `mpsc` channels.
This gives the same concurrency model with far lower per-task overhead and
eliminates the Global Interpreter Lock.

### Trait objects (`Box<dyn Trait>`)

`MessageSource`, `MessagePublisher`, and `MessageProcessor` are all defined as
traits and used as `Box<dyn Trait>`.  This matches the Python abstract-base-class
design and allows the adapter type to be selected at runtime from the YAML config.

### `SubPubError` enum

All errors are unified into a single `SubPubError` enum (via `thiserror`).
This avoids propagating concrete library error types across module boundaries
and makes call-sites ergonomic.

### `Arc<MetricsCollector>`

The metrics collector is wrapped in an `Arc` so it can be shared across
multiple tasks without locking the entire flow struct.  Internal state is
protected by a `Mutex`; each individual method takes `&self`.

### Serde + serde_yaml for configuration

The Python project uses PyYAML + dataclasses.  The Rust port uses
`serde` + `serde_yaml` with `#[derive(Serialize, Deserialize)]` to achieve
the same effect with zero boilerplate.  `#[serde(flatten)]` on `FlowConfig`
means the YAML does not need a nested `flow:` key — the `mode` discriminant
lives at the top level.

### Feature flags

The `kafka` feature flag gates the `rdkafka` dependency so users who don't
need Kafka avoid a large C library.  Future features (`pulsar`, `eventhubs`,
`google_pubsub`) will follow the same pattern once fully implemented.

---

## Running Locally

```bash
# Build (debug)
cargo build

# Run tests
cargo test

# Run with mock config
cargo run -- --config examples/mock-one-to-one.yaml --log-level DEBUG

# Build release binary
cargo build --release
./target/release/sub-pub --config examples/mock-one-to-one.yaml
```

---

## Dependencies

| Crate | Purpose |
|-------|---------|
| `tokio` | Async runtime |
| `async-trait` | `async fn` in trait definitions |
| `serde` / `serde_yaml` / `serde_json` | Configuration + JSON payload parsing |
| `clap` | CLI argument parsing |
| `tracing` / `tracing-subscriber` | Structured logging |
| `chrono` | Timestamps on `Message` |
| `anyhow` / `thiserror` | Error handling |
| `uuid` | Unique message IDs (future use) |
| `rdkafka` (optional) | Kafka adapter (behind `kafka` feature flag) |
