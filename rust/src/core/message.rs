use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// A message travelling through the pub-sub pipeline.
///
/// Mirrors the Python `Message` dataclass while adding Rust idioms (ownership,
/// `Option` instead of `None` defaults, etc.).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Raw message payload bytes.
    pub payload: Vec<u8>,

    /// Arbitrary string key-value headers attached to the message.
    #[serde(default)]
    pub headers: HashMap<String, String>,

    /// The topic this message was consumed from.
    pub topic: String,

    /// Optional partition key.
    #[serde(default)]
    pub key: Option<String>,

    /// Source partition (if applicable).
    #[serde(default)]
    pub partition: Option<i32>,

    /// Source offset (if applicable).
    #[serde(default)]
    pub offset: Option<i64>,

    /// When the message was created / received.
    #[serde(default = "Utc::now")]
    pub timestamp: DateTime<Utc>,
}

impl Message {
    /// Construct a minimal message with just a payload and topic.
    pub fn new(payload: impl Into<Vec<u8>>, topic: impl Into<String>) -> Self {
        Self {
            payload: payload.into(),
            headers: HashMap::new(),
            topic: topic.into(),
            key: None,
            partition: None,
            offset: None,
            timestamp: Utc::now(),
        }
    }

    /// Total size in bytes (payload + header content).
    pub fn size(&self) -> usize {
        self.payload.len()
            + self
                .headers
                .iter()
                .map(|(k, v)| k.len() + v.len())
                .sum::<usize>()
    }

    /// Retrieve a header value by key, returning `default` if absent.
    pub fn get_header<'a>(&'a self, key: &str, default: &'a str) -> &'a str {
        self.headers.get(key).map(String::as_str).unwrap_or(default)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_message_has_empty_headers() {
        let msg = Message::new(b"hello".to_vec(), "test-topic");
        assert!(msg.headers.is_empty());
        assert_eq!(msg.topic, "test-topic");
        assert_eq!(msg.payload, b"hello");
    }

    #[test]
    fn size_includes_payload_and_headers() {
        let mut msg = Message::new(b"data".to_vec(), "t");
        msg.headers.insert("k".to_string(), "v".to_string());
        // payload=4, header key=1, header val=1 → 6
        assert_eq!(msg.size(), 6);
    }

    #[test]
    fn get_header_returns_default_when_absent() {
        let msg = Message::new(vec![], "t");
        assert_eq!(msg.get_header("missing", "fallback"), "fallback");
    }

    #[test]
    fn get_header_returns_value_when_present() {
        let mut msg = Message::new(vec![], "t");
        msg.headers.insert("dest".to_string(), "orders".to_string());
        assert_eq!(msg.get_header("dest", ""), "orders");
    }
}
