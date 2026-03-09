use async_trait::async_trait;

use crate::core::{Message, MessagePublisher, MessageSource};
use crate::error::SubPubError;

/// Stub Azure Event Hubs source.
pub struct EventHubsSource {
    pub connection_string: String,
    pub consumer_group: String,
    pub topics: Vec<String>,
}

impl EventHubsSource {
    pub fn new(
        connection_string: impl Into<String>,
        consumer_group: impl Into<String>,
    ) -> Self {
        Self {
            connection_string: connection_string.into(),
            consumer_group: consumer_group.into(),
            topics: Vec::new(),
        }
    }
}

#[async_trait]
impl MessageSource for EventHubsSource {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("EventHubsSource: full implementation pending");
        Ok(())
    }

    async fn subscribe(&mut self, topics: &[&str]) -> Result<(), SubPubError> {
        self.topics = topics.iter().map(|t| t.to_string()).collect();
        Ok(())
    }

    async fn consume(&mut self) -> Result<Option<Message>, SubPubError> {
        Err(SubPubError::Adapter(
            "EventHubsSource: full implementation pending".to_string(),
        ))
    }

    async fn commit(&mut self, _message: &Message) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}

/// Stub Azure Event Hubs publisher.
pub struct EventHubsPublisher {
    pub connection_string: String,
}

impl EventHubsPublisher {
    pub fn new(connection_string: impl Into<String>) -> Self {
        Self {
            connection_string: connection_string.into(),
        }
    }
}

#[async_trait]
impl MessagePublisher for EventHubsPublisher {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        tracing::warn!("EventHubsPublisher: full implementation pending");
        Ok(())
    }

    async fn publish(&mut self, _message: &Message, _topic: &str) -> Result<(), SubPubError> {
        Err(SubPubError::Adapter(
            "EventHubsPublisher: full implementation pending".to_string(),
        ))
    }

    async fn flush(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }
}
