use async_trait::async_trait;

use crate::core::{Message, MessagePublisher, MessageSource};
use crate::error::SubPubError;

/// Stub Kafka source.  Requires the `kafka` feature to be fully implemented.
pub struct KafkaSource {
    pub bootstrap_servers: String,
    pub group_id: String,
    pub topics: Vec<String>,
}

impl KafkaSource {
    pub fn new(bootstrap_servers: impl Into<String>, group_id: impl Into<String>) -> Self {
        Self {
            bootstrap_servers: bootstrap_servers.into(),
            group_id: group_id.into(),
            topics: Vec::new(),
        }
    }
}

#[async_trait]
impl MessageSource for KafkaSource {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!(
            "KafkaSource: full implementation pending (enable the `kafka` feature flag)"
        );
        Ok(())
    }

    async fn subscribe(&mut self, topics: &[&str]) -> Result<(), SubPubError> {
        self.topics = topics.iter().map(|t| t.to_string()).collect();
        Ok(())
    }

    async fn consume(&mut self) -> Result<Option<Message>, SubPubError> {
        Err(SubPubError::Adapter(
            "KafkaSource: full implementation pending".to_string(),
        ))
    }

    async fn commit(&mut self, _message: &Message) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}

/// Stub Kafka publisher.
pub struct KafkaPublisher {
    pub bootstrap_servers: String,
}

impl KafkaPublisher {
    pub fn new(bootstrap_servers: impl Into<String>) -> Self {
        Self {
            bootstrap_servers: bootstrap_servers.into(),
        }
    }
}

#[async_trait]
impl MessagePublisher for KafkaPublisher {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!(
            "KafkaPublisher: full implementation pending (enable the `kafka` feature flag)"
        );
        Ok(())
    }

    async fn publish(&mut self, _message: &Message, _topic: &str) -> Result<(), SubPubError> {
        Err(SubPubError::Adapter(
            "KafkaPublisher: full implementation pending".to_string(),
        ))
    }

    async fn flush(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}
