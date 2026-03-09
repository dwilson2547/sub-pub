//! # sub-pub (Rust rewrite)
//!
//! Extreme-performance pub-sub message processor.
//!
//! ## Crate layout
//!
//! | Module | Purpose |
//! |--------|---------|
//! [`core`] | [`Message`] type and [`MessageSource`] / [`MessagePublisher`] traits |
//! [`config`] | YAML-driven configuration models |
//! [`domain`] | [`MessageProcessor`] trait and pass-through default |
//! [`metrics`] | Thread-safe [`MetricsCollector`] |
//! [`adapters`] | Concrete source/publisher implementations (Mock, Kafka stub, …) |
//! [`flows`] | Flow engines (OneToOne, Funnel, Fan) |
//! [`error`] | Unified [`SubPubError`] type |

pub mod adapters;
pub mod config;
pub mod core;
pub mod domain;
pub mod error;
pub mod flows;
pub mod metrics;
