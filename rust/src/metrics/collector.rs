use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use serde::Serialize;

/// Per-topic statistics.
#[derive(Debug, Default, Clone, Serialize)]
pub struct TopicMetrics {
    pub message_count: u64,
    pub total_bytes: u64,
    pub error_count: u64,
    pub last_message_time: Option<std::time::SystemTime>,
}

/// Snapshot of all metrics at a point in time.
#[derive(Debug, Serialize)]
pub struct MetricsSnapshot {
    pub uptime_secs: f64,
    pub source_topics: HashMap<String, TopicMetrics>,
    pub destination_topics: HashMap<String, TopicMetrics>,
    pub total_messages_received: u64,
    pub total_messages_sent: u64,
    pub total_errors: u64,
    /// Overall message throughput (messages per second since start).
    pub messages_per_second: f64,
}

/// Thread-safe metrics collector.
///
/// All methods take `&self` (not `&mut self`) so a single `Arc<MetricsCollector>`
/// can be shared freely across tasks and threads.
#[derive(Debug)]
pub struct MetricsCollector {
    started_at: Instant,
    inner: Arc<Mutex<Inner>>,
}

#[derive(Debug, Default)]
struct Inner {
    source_topics: HashMap<String, TopicMetrics>,
    destination_topics: HashMap<String, TopicMetrics>,
}

impl MetricsCollector {
    /// Create a new collector.
    pub fn new() -> Self {
        Self {
            started_at: Instant::now(),
            inner: Arc::new(Mutex::new(Inner::default())),
        }
    }

    /// Record a message received from a source topic.
    pub fn record_source_message(&self, topic: &str, size: usize) {
        let mut guard = self.inner.lock().expect("metrics lock poisoned");
        let entry = guard.source_topics.entry(topic.to_string()).or_default();
        entry.message_count += 1;
        entry.total_bytes += size as u64;
        entry.last_message_time = Some(std::time::SystemTime::now());
    }

    /// Record a message successfully published to a destination topic.
    pub fn record_destination_message(&self, topic: &str, size: usize) {
        let mut guard = self.inner.lock().expect("metrics lock poisoned");
        let entry = guard
            .destination_topics
            .entry(topic.to_string())
            .or_default();
        entry.message_count += 1;
        entry.total_bytes += size as u64;
        entry.last_message_time = Some(std::time::SystemTime::now());
    }

    /// Record an error on a source topic.
    pub fn record_source_error(&self, topic: &str) {
        let mut guard = self.inner.lock().expect("metrics lock poisoned");
        guard
            .source_topics
            .entry(topic.to_string())
            .or_default()
            .error_count += 1;
    }

    /// Record an error on a destination topic.
    pub fn record_destination_error(&self, topic: &str) {
        let mut guard = self.inner.lock().expect("metrics lock poisoned");
        guard
            .destination_topics
            .entry(topic.to_string())
            .or_default()
            .error_count += 1;
    }

    /// Build a point-in-time snapshot of all metrics.
    pub fn snapshot(&self) -> MetricsSnapshot {
        let guard = self.inner.lock().expect("metrics lock poisoned");
        let uptime = self.started_at.elapsed().as_secs_f64();

        let total_received: u64 = guard.source_topics.values().map(|t| t.message_count).sum();
        let total_sent: u64 = guard
            .destination_topics
            .values()
            .map(|t| t.message_count)
            .sum();
        let total_errors: u64 = guard
            .source_topics
            .values()
            .chain(guard.destination_topics.values())
            .map(|t| t.error_count)
            .sum();

        let msgs_per_sec = if uptime > 0.0 {
            total_received as f64 / uptime
        } else {
            0.0
        };

        MetricsSnapshot {
            uptime_secs: uptime,
            source_topics: guard.source_topics.clone(),
            destination_topics: guard.destination_topics.clone(),
            total_messages_received: total_received,
            total_messages_sent: total_sent,
            total_errors,
            messages_per_second: msgs_per_sec,
        }
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_source_messages() {
        let m = MetricsCollector::new();
        m.record_source_message("topic-a", 100);
        m.record_source_message("topic-a", 200);
        let snap = m.snapshot();
        let t = &snap.source_topics["topic-a"];
        assert_eq!(t.message_count, 2);
        assert_eq!(t.total_bytes, 300);
    }

    #[test]
    fn records_destination_messages() {
        let m = MetricsCollector::new();
        m.record_destination_message("out", 50);
        let snap = m.snapshot();
        assert_eq!(snap.total_messages_sent, 1);
    }

    #[test]
    fn records_errors() {
        let m = MetricsCollector::new();
        m.record_source_error("topic-x");
        m.record_source_error("topic-x");
        let snap = m.snapshot();
        assert_eq!(snap.total_errors, 2);
    }
}
