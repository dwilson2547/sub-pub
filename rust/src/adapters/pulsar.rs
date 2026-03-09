use async_trait::async_trait;

use crate::core::{Message, MessagePublisher, MessageSource};
use crate::error::SubPubError;

/// Stub Apache Pulsar source.
pub struct PulsarSource {
    pub service_url: String,
    pub subscription: String,
    pub topics: Vec<String>,
}

impl PulsarSource {
    pub fn new(service_url: impl Into<String>, subscription: impl Into<String>) -> Self {
        Self {
            service_url: service_url.into(),
            subscription: subscription.into(),
            topics: Vec::new(),
        }
    }
}

#[async_trait]
impl MessageSource for PulsarSource {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("PulsarSource: full implementation pending");
        Ok(())
    }

    async fn subscribe(&mut self, topics: &[&str]) -> Result<(), SubPubError> {
        self.topics = topics.iter().map(|t| t.to_string()).collect();
        Ok(())
    }

    async fn consume(&mut self) -> Result<Option<Message>, SubPubError> {
        Err(SubPubError::Adapter(
            "PulsarSource: full implementation pending".to_string(),
        ))
    }

    async fn commit(&mut self, _message: &Message) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}

/// Stub Apache Pulsar publisher.
pub struct PulsarPublisher {
    pub service_url: String,
}

impl PulsarPublisher {
    pub fn new(service_url: impl Into<String>) -> Self {
        Self {
            service_url: service_url.into(),
        }
    }
}

#[async_trait]
impl MessagePublisher for PulsarPublisher {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("PulsarPublisher: full implementation pending");
        Ok(())
    }

    async fn publish(&mut self, _message: &Message, _topic: &str) -> Result<(), SubPubError> {
        Err(SubPubError::Adapter(
            "PulsarPublisher: full implementation pending".to_string(),
        ))
    }

    async fn flush(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}
