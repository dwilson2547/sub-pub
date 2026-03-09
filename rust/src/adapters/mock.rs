use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use async_trait::async_trait;
use tokio::time::sleep;

use crate::core::{Message, MessagePublisher, MessageSource};
use crate::error::SubPubError;

// ---------------------------------------------------------------------------
// MockSource
// ---------------------------------------------------------------------------

/// A test-only [`MessageSource`] that generates synthetic messages at a fixed
/// rate.  Useful for integration tests, demos, and local development without
/// a real message system.
pub struct MockSource {
    topics: Vec<String>,
    /// Counter that increments with each generated message.
    count: u64,
    /// How long to pause between messages (default: 100 ms).
    interval: Duration,
    /// Whether the source has been connected.
    connected: bool,
}

impl MockSource {
    pub fn new() -> Self {
        Self {
            topics: Vec::new(),
            count: 0,
            interval: Duration::from_millis(100),
            connected: false,
        }
    }

    /// Override the interval between generated messages.
    pub fn with_interval(mut self, interval: Duration) -> Self {
        self.interval = interval;
        self
    }
}

impl Default for MockSource {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl MessageSource for MockSource {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        self.connected = true;
        tracing::debug!("MockSource connected");
        Ok(())
    }

    async fn subscribe(&mut self, topics: &[&str]) -> Result<(), SubPubError> {
        self.topics = topics.iter().map(|t| t.to_string()).collect();
        tracing::debug!(?self.topics, "MockSource subscribed");
        Ok(())
    }

    async fn consume(&mut self) -> Result<Option<Message>, SubPubError> {
        if !self.connected {
            return Err(SubPubError::Connection(
                "MockSource not connected".to_string(),
            ));
        }
        if self.topics.is_empty() {
            return Ok(None);
        }

        sleep(self.interval).await;

        self.count += 1;
        let topic = self.topics[((self.count - 1) as usize) % self.topics.len()].clone();
        let payload = format!("mock message #{}", self.count).into_bytes();

        let mut msg = Message::new(payload, topic);
        msg.headers
            .insert("source".to_string(), "mock".to_string());
        msg.headers
            .insert("count".to_string(), self.count.to_string());

        Ok(Some(msg))
    }

    async fn commit(&mut self, _message: &Message) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        self.connected = false;
        tracing::debug!("MockSource closed");
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// MockPublisher
// ---------------------------------------------------------------------------

/// A test-only [`MessagePublisher`] that stores all published messages in
/// memory so tests can inspect them.
#[derive(Clone, Default)]
pub struct MockPublisher {
    /// Shared storage; clones of the publisher see the same messages.
    messages: Arc<Mutex<VecDeque<Message>>>,
    connected: bool,
}

impl MockPublisher {
    pub fn new() -> Self {
        Self::default()
    }

    /// Drain and return all messages published so far.
    pub fn drain(&self) -> Vec<Message> {
        self.messages
            .lock()
            .expect("mock publisher lock poisoned")
            .drain(..)
            .collect()
    }

    /// Return a snapshot of all published messages without draining.
    pub fn messages(&self) -> Vec<Message> {
        self.messages
            .lock()
            .expect("mock publisher lock poisoned")
            .iter()
            .cloned()
            .collect()
    }

    /// How many messages have been published so far.
    pub fn len(&self) -> usize {
        self.messages
            .lock()
            .expect("mock publisher lock poisoned")
            .len()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

#[async_trait]
impl MessagePublisher for MockPublisher {
    async fn connect(&mut self) -> Result<(), SubPubError> {
        self.connected = true;
        tracing::debug!("MockPublisher connected");
        Ok(())
    }

    async fn publish(&mut self, message: &Message, topic: &str) -> Result<(), SubPubError> {
        if !self.connected {
            return Err(SubPubError::Connection(
                "MockPublisher not connected".to_string(),
            ));
        }
        let mut msg = message.clone();
        msg.topic = topic.to_string();
        self.messages
            .lock()
            .expect("mock publisher lock poisoned")
            .push_back(msg);
        Ok(())
    }

    async fn flush(&mut self) -> Result<(), SubPubError> {
        Ok(())
    }

    async fn close(&mut self) -> Result<(), SubPubError> {
        self.connected = false;
        tracing::debug!("MockPublisher closed");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[tokio::test]
    async fn mock_publisher_stores_messages() {
        let mut pub_ = MockPublisher::new();
        pub_.connect().await.unwrap();

        let msg = Message::new(b"hello".to_vec(), "src");
        pub_.publish(&msg, "dest").await.unwrap();

        assert_eq!(pub_.len(), 1);
        let stored = pub_.messages();
        assert_eq!(stored[0].payload, b"hello");
        assert_eq!(stored[0].topic, "dest");
    }

    #[tokio::test]
    async fn mock_source_generates_messages() {
        let mut src = MockSource::new().with_interval(Duration::from_millis(1));
        src.connect().await.unwrap();
        src.subscribe(&["test-topic"]).await.unwrap();

        let msg = src.consume().await.unwrap().unwrap();
        assert_eq!(msg.topic, "test-topic");
        assert!(!msg.payload.is_empty());
        assert_eq!(msg.get_header("source", ""), "mock");
    }
}
