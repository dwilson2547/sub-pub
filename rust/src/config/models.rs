use std::collections::HashMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::SubPubError;

// ---------------------------------------------------------------------------
// Thread-pool / back-pressure settings
// ---------------------------------------------------------------------------

/// Thread-pool sizing for domain and publish workers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreadPoolConfig {
    /// Maximum number of concurrent worker tasks.
    #[serde(default = "default_max_workers")]
    pub max_workers: usize,

    /// Maximum number of messages queued between pipeline stages.
    #[serde(default = "default_queue_size")]
    pub queue_size: usize,
}

fn default_max_workers() -> usize {
    10
}
fn default_queue_size() -> usize {
    1000
}

impl Default for ThreadPoolConfig {
    fn default() -> Self {
        Self {
            max_workers: default_max_workers(),
            queue_size: default_queue_size(),
        }
    }
}

/// Back-pressure settings for flow queues.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackPressureConfig {
    /// Whether back-pressure is active.
    #[serde(default = "default_true")]
    pub enabled: bool,

    /// Fraction of queue capacity at which producers slow down.
    #[serde(default = "default_high_watermark")]
    pub queue_high_watermark: f64,

    /// Fraction at which producers may resume.
    #[serde(default = "default_low_watermark")]
    pub queue_low_watermark: f64,
}

fn default_true() -> bool {
    true
}
fn default_high_watermark() -> f64 {
    0.8
}
fn default_low_watermark() -> f64 {
    0.5
}

impl Default for BackPressureConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            queue_high_watermark: 0.8,
            queue_low_watermark: 0.5,
        }
    }
}

// ---------------------------------------------------------------------------
// Message-system adapter configuration
// ---------------------------------------------------------------------------

/// Configuration for a single message-system connection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageSystemConfig {
    /// Adapter type identifier (e.g. `"kafka"`, `"mock"`, `"pulsar"`).
    #[serde(rename = "type")]
    pub adapter_type: String,

    /// Free-form key-value connection settings forwarded to the adapter.
    #[serde(default)]
    pub connection: HashMap<String, serde_yaml::Value>,

    /// Optional default topic list for this system.
    #[serde(default)]
    pub topics: Vec<String>,
}

// ---------------------------------------------------------------------------
// Flow-specific configurations
// ---------------------------------------------------------------------------

/// Funnel flow: many sources → one destination.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunnelConfig {
    /// One or more source systems.
    pub sources: Vec<MessageSystemConfig>,

    /// The single destination system.
    pub destination: MessageSystemConfig,

    /// Topic on the destination to publish all messages to.
    pub destination_topic: String,

    #[serde(default)]
    pub thread_pool: ThreadPoolConfig,

    #[serde(default)]
    pub back_pressure: BackPressureConfig,
}

/// How a Fan flow resolves the destination topic for each message.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum DestinationResolver {
    /// Read the destination topic name from a message header.
    Header { header_key: String },

    /// Read the destination topic name from a JSON payload field.
    PayloadKey { payload_key: String },
}

/// Fan flow: one source → many destinations (content-based routing).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FanConfig {
    /// The single source system.
    pub source: MessageSystemConfig,

    /// Topic to consume from.
    pub source_topic: String,

    /// The destination system (router dispatches to topics within it).
    pub destination: MessageSystemConfig,

    /// How to resolve the destination topic for each message.
    pub destination_resolver: DestinationResolver,

    #[serde(default)]
    pub thread_pool: ThreadPoolConfig,

    #[serde(default)]
    pub back_pressure: BackPressureConfig,
}

/// A single source-topic → destination-topic mapping.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OneToOneMapping {
    pub source_topic: String,
    pub destination_topic: String,
}

/// One-to-one flow: fixed topic-to-topic mappings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OneToOneConfig {
    pub source: MessageSystemConfig,
    pub destination: MessageSystemConfig,
    pub mappings: Vec<OneToOneMapping>,

    #[serde(default)]
    pub thread_pool: ThreadPoolConfig,

    #[serde(default)]
    pub back_pressure: BackPressureConfig,
}

// ---------------------------------------------------------------------------
// Top-level configuration
// ---------------------------------------------------------------------------

/// Supported flow modes.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "mode", rename_all = "snake_case")]
pub enum FlowConfig {
    Funnel(FunnelConfig),
    Fan(FanConfig),
    #[serde(rename = "one_to_one")]
    OneToOne(OneToOneConfig),
}

/// Top-level application configuration (loaded from a YAML file).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Optional custom message-processor class path (not yet used in Rust).
    #[serde(default)]
    pub processor: Option<String>,

    /// The flow to run.
    #[serde(flatten)]
    pub flow: FlowConfig,
}

impl Config {
    /// Load a [`Config`] from a YAML file at `path`.
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self, SubPubError> {
        let contents = std::fs::read_to_string(path.as_ref()).map_err(|e| {
            SubPubError::Config(format!(
                "cannot read config file {}: {e}",
                path.as_ref().display()
            ))
        })?;
        serde_yaml::from_str(&contents)
            .map_err(|e| SubPubError::Config(format!("invalid YAML: {e}")))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_thread_pool() {
        let cfg = ThreadPoolConfig::default();
        assert_eq!(cfg.max_workers, 10);
        assert_eq!(cfg.queue_size, 1000);
    }

    #[test]
    fn default_back_pressure() {
        let cfg = BackPressureConfig::default();
        assert!(cfg.enabled);
        assert!((cfg.queue_high_watermark - 0.8).abs() < f64::EPSILON);
        assert!((cfg.queue_low_watermark - 0.5).abs() < f64::EPSILON);
    }
}
