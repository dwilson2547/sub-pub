# Sub-Pub Rust Rewrite — Progress Tracker

This document tracks the status of the Rust rewrite of the Python `sub-pub`
project.  Update it as work is completed or priorities change.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete and tested |
| 🔧 | In progress |
| ⬜ | Not started |
| 🚫 | Blocked / deferred |

---

## Completed

| Item | Notes |
|------|-------|
| ✅ `rust/` directory and Cargo project | `Cargo.toml`, `src/` scaffold |
| ✅ `core::Message` | Mirrors Python `Message` dataclass; serializable, cloneable |
| ✅ `core::MessageSource` trait | Async `connect / subscribe / consume / commit / close` |
| ✅ `core::MessagePublisher` trait | Async `connect / publish / flush / close` |
| ✅ `config::models` | All Python config dataclasses ported (`ThreadPoolConfig`, `BackPressureConfig`, `MessageSystemConfig`, `FunnelConfig`, `FanConfig`, `OneToOneConfig`, top-level `Config`) |
| ✅ YAML config loading | `Config::from_file(path)` using `serde_yaml` |
| ✅ `error::SubPubError` | Unified error enum via `thiserror` |
| ✅ `domain::MessageProcessor` trait | Async `process(message) → message` |
| ✅ `domain::PassThroughProcessor` | Default no-op implementation |
| ✅ `metrics::MetricsCollector` | Thread-safe; per-topic message/byte/error counters + `snapshot()` |
| ✅ `adapters::mock` | Full `MockSource` + `MockPublisher` with in-memory storage |
| ✅ `adapters::kafka` (stub) | Compiles; logs warning; returns error on `consume/publish` |
| ✅ `adapters::pulsar` (stub) | Compiles; logs warning; returns error on `consume/publish` |
| ✅ `adapters::eventhubs` (stub) | Compiles; logs warning; returns error on `consume/publish` |
| ✅ `adapters::google_pubsub` (stub) | Compiles; logs warning; returns error on `consume/publish` |
| ✅ `adapters::factory` | `create_source` / `create_publisher` factory functions |
| ✅ `flows::base` | Pipeline channels, back-pressure helper, domain-worker spawner |
| ✅ `flows::OneToOneFlow` | Full consumer + domain + publish pipeline with graceful shutdown |
| ✅ `flows::FunnelFlow` | Per-source consumer tasks → shared domain + publish pipeline |
| ✅ `flows::FanFlow` | Single consumer + header/payload-based destination routing |
| ✅ `src/main.rs` | CLI (`--config`, `--log-level`), signal handling, flow dispatch, metrics print |
| ✅ Unit tests (12) | Core, config, domain, metrics, mock adapter |
| ✅ Example YAML configs | `mock-one-to-one.yaml`, `mock-funnel.yaml`, `mock-fan.yaml` |

---

## Remaining Work

### Adapters (high priority)

| Item | Notes |
|------|-------|
| ⬜ Kafka adapter (full) | Enable `kafka` feature; wire up `rdkafka` consumer/producer |
| ⬜ Pulsar adapter (full) | Use `pulsar` crate; handle subscription / acknowledgement |
| ⬜ Azure Event Hubs adapter | Use `azure-messaging-eventhubs` crate |
| ⬜ Google Cloud Pub/Sub adapter | Use `google-cloud-pubsub` crate |
| ⬜ Iggy adapter | Use official Iggy Rust client |

### Flows (medium priority)

| Item | Notes |
|------|-------|
| ⬜ Async `OneToOneFlow` | Fully non-blocking, no blocking `consume` calls |
| ⬜ Multi-worker domain pipeline | Multiple parallel domain-worker tasks |
| ⬜ Multi-worker publish pipeline | Multiple parallel publish tasks |
| ⬜ Dead-letter / retry logic | Configurable retry policy on publish errors |

### Metrics / Observability (medium priority)

| Item | Notes |
|------|-------|
| ⬜ OpenTelemetry integration | Port `metrics/otel.py` using `opentelemetry` crate |
| ⬜ HTTP metrics endpoint | Expose Prometheus-style `/metrics` on port 8080 |

### Configuration (low priority)

| Item | Notes |
|------|-------|
| ⬜ Dynamic processor loading | Load custom `MessageProcessor` from a shared library at runtime |
| ⬜ Per-source topic override | Allow each funnel source to specify its own topics in config |

### Testing (ongoing)

| Item | Notes |
|------|-------|
| ⬜ Integration tests with `MockSource/MockPublisher` | Run a full flow end-to-end in tests |
| ⬜ BDD / Gherkin tests | Port Python `behave` scenarios to Rust (e.g. `cucumber` crate) |
| ⬜ Benchmark suite | `criterion` benchmarks for throughput and latency |

### Operations (low priority)

| Item | Notes |
|------|-------|
| ⬜ Docker image | Multi-stage `Dockerfile` for the Rust binary |
| ⬜ Helm chart update | Add Rust image variant to existing Helm chart |
| ⬜ CI / CD | Add Rust build + test steps to `.github/workflows/ci-cd.yml` |

---

## Architecture Notes

See [ARCHITECTURE.md](ARCHITECTURE.md) for a module-level overview of the
Rust implementation.
