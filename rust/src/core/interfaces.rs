use async_trait::async_trait;

use crate::core::message::Message;
use crate::error::SubPubError;

/// Trait for anything that can produce messages (a message source / consumer).
///
/// Implementations are responsible for connecting to their backing system,
/// subscribing to topics, and delivering messages one at a time via `consume`.
#[async_trait]
pub trait MessageSource: Send + Sync {
    /// Establish a connection to the backing message system.
    async fn connect(&mut self) -> Result<(), SubPubError>;

    /// Subscribe to the given list of topics.
    async fn subscribe(&mut self, topics: &[&str]) -> Result<(), SubPubError>;

    /// Fetch the next available message.  Returns `None` when the source is
    /// exhausted or closed.
    async fn consume(&mut self) -> Result<Option<Message>, SubPubError>;

    /// Acknowledge / commit the given message so it won't be re-delivered.
    async fn commit(&mut self, message: &Message) -> Result<(), SubPubError>;

    /// Cleanly shut down this source.
    async fn close(&mut self) -> Result<(), SubPubError>;
}

/// Trait for anything that can accept and forward messages (a publisher).
#[async_trait]
pub trait MessagePublisher: Send + Sync {
    /// Establish a connection to the backing message system.
    async fn connect(&mut self) -> Result<(), SubPubError>;

    /// Publish a single message to `topic`.
    async fn publish(&mut self, message: &Message, topic: &str) -> Result<(), SubPubError>;

    /// Flush any buffered messages, ensuring they are delivered.
    async fn flush(&mut self) -> Result<(), SubPubError>;

    /// Cleanly shut down this publisher.
    async fn close(&mut self) -> Result<(), SubPubError>;
}
