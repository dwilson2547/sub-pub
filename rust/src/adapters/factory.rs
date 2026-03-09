use std::collections::HashMap;

use crate::config::MessageSystemConfig;
use crate::core::{MessagePublisher, MessageSource};
use crate::error::SubPubError;

use super::{
    eventhubs::{EventHubsPublisher, EventHubsSource},
    google_pubsub::{GooglePubSubPublisher, GooglePubSubSource},
    kafka::{KafkaPublisher, KafkaSource},
    mock::{MockPublisher, MockSource},
    pulsar::{PulsarPublisher, PulsarSource},
};

fn get_str<'a>(
    map: &'a HashMap<String, serde_yaml::Value>,
    key: &str,
    fallback: &'a str,
) -> &'a str {
    map.get(key)
        .and_then(|v| v.as_str())
        .unwrap_or(fallback)
}

/// Create a [`MessageSource`] from the given configuration.
pub fn create_source(cfg: &MessageSystemConfig) -> Result<Box<dyn MessageSource>, SubPubError> {
    match cfg.adapter_type.as_str() {
        "mock" => Ok(Box::new(MockSource::new())),
        "kafka" => {
            let servers = get_str(&cfg.connection, "bootstrap_servers", "localhost:9092");
            let group_id = get_str(&cfg.connection, "group_id", "sub-pub");
            Ok(Box::new(KafkaSource::new(servers, group_id)))
        }
        "pulsar" => {
            let url = get_str(&cfg.connection, "service_url", "pulsar://localhost:6650");
            let sub = get_str(&cfg.connection, "subscription", "sub-pub");
            Ok(Box::new(PulsarSource::new(url, sub)))
        }
        "eventhubs" => {
            let conn_str = get_str(&cfg.connection, "connection_string", "");
            let group = get_str(&cfg.connection, "consumer_group", "$Default");
            Ok(Box::new(EventHubsSource::new(conn_str, group)))
        }
        "google_pubsub" => {
            let project = get_str(&cfg.connection, "project_id", "");
            let sub = get_str(&cfg.connection, "subscription", "");
            Ok(Box::new(GooglePubSubSource::new(project, sub)))
        }
        unknown => Err(SubPubError::Config(format!(
            "unknown adapter type: {unknown}"
        ))),
    }
}

/// Create a [`MessagePublisher`] from the given configuration.
pub fn create_publisher(
    cfg: &MessageSystemConfig,
) -> Result<Box<dyn MessagePublisher>, SubPubError> {
    match cfg.adapter_type.as_str() {
        "mock" => Ok(Box::new(MockPublisher::new())),
        "kafka" => {
            let servers = get_str(&cfg.connection, "bootstrap_servers", "localhost:9092");
            Ok(Box::new(KafkaPublisher::new(servers)))
        }
        "pulsar" => {
            let url = get_str(&cfg.connection, "service_url", "pulsar://localhost:6650");
            Ok(Box::new(PulsarPublisher::new(url)))
        }
        "eventhubs" => {
            let conn_str = get_str(&cfg.connection, "connection_string", "");
            Ok(Box::new(EventHubsPublisher::new(conn_str)))
        }
        "google_pubsub" => {
            let project = get_str(&cfg.connection, "project_id", "");
            Ok(Box::new(GooglePubSubPublisher::new(project)))
        }
        unknown => Err(SubPubError::Config(format!(
            "unknown adapter type: {unknown}"
        ))),
    }
}
