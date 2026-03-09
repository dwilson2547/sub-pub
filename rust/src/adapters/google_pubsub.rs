use async_trait::async_trait;

use crate::core::{Message, MessagePublisher, MessageSource};
use crate::error::SubPubError;

/// Stub Google Cloud Pub/Sub source.
pub struct GooglePubSubSource {
    pub project_id: String,
    pub subscription: String,
}

impl GooglePubSubSource {
    pub fn new(project_id: impl Into<String>, subscription: impl Into<String>) -> Self {
        Self {
            project_id: project_id.into(),
            subscription: subscription.into(),
        }
    }
}

#[async_trait]
impl MessageSource for GooglePubSubSource {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("GooglePubSubSource: full implementation pending");
        Ok(())
    }

    async fn subscribe(&mut self, _topics: &[&str]) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn consume(&mut self) -> Result<Option<Message>, SubPubError> {
        Err(SubPubError::Adapter(
            "GooglePubSubSource: full implementation pending".to_string(),
        ))
    }

    async fn commit(&mut self, _message: &Message) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}

/// Stub Google Cloud Pub/Sub publisher.
pub struct GooglePubSubPublisher {
    pub project_id: String,
}

impl GooglePubSubPublisher {
    pub fn new(project_id: impl Into<String>) -> Self {
        Self {
            project_id: project_id.into(),
        }
    }
}

#[async_trait]
impl MessagePublisher for GooglePubSubPublisher {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("GooglePubSubPublisher: full implementation pending");
        Ok(())
    }

    async fn publish(&mut self, _message: &Message, _topic: &str) -> Result<(), SubPubError> {
        Err(SubPubError::Adapter(
            "GooglePubSubPublisher: full implementation pending".to_string(),
        ))
    }

    async fn flush(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}
