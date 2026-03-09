use async_trait::async_trait;

use crate::core::Message;
use crate::error::SubPubError;

/// Trait for processing (transforming) a message before it is published.
///
/// Implementors receive a message, may mutate or replace it, and return the
/// (possibly modified) message.  Returning an error signals that the message
/// should be skipped / dead-lettered.
#[async_trait]
pub trait MessageProcessor: Send + Sync {
    async fn process(&self, message: Message) -> Result<Message, SubPubError>;
}

// ---------------------------------------------------------------------------
// Built-in processors
// ---------------------------------------------------------------------------

/// Pass-through processor: returns the message unchanged.
///
/// This is the default processor used by all flows when no custom processor is
/// configured.
pub struct PassThroughProcessor;

#[async_trait]
impl MessageProcessor for PassThroughProcessor {
    async fn process(&self, message: Message) -> Result<Message, SubPubError> {
        Ok(message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::Message;

    #[tokio::test]
    async fn pass_through_returns_message_unchanged() {
        let proc = PassThroughProcessor;
        let msg = Message::new(b"hello".to_vec(), "test");
        let result = proc.process(msg.clone()).await.unwrap();
        assert_eq!(result.payload, msg.payload);
        assert_eq!(result.topic, msg.topic);
    }
}
