use std::sync::Arc;
use std::time::Duration;

use tokio::sync::mpsc::{self, Receiver, Sender};
use tokio::time::sleep;
use tracing::warn;

use crate::config::BackPressureConfig;
use crate::core::Message;
use crate::domain::MessageProcessor;
use crate::metrics::MetricsCollector;

/// Messages sent through the internal pipeline carry both the message and its
/// intended destination topic.
pub struct PipelineItem {
    pub message: Message,
    pub destination_topic: String,
}

/// Shared context threaded through every stage of a flow.
pub struct FlowContext {
    pub processor: Arc<dyn MessageProcessor>,
    pub metrics: Arc<MetricsCollector>,
    pub back_pressure: BackPressureConfig,
    pub domain_tx: Sender<PipelineItem>,
    pub publish_tx: Sender<PipelineItem>,
}

/// Wait until the queue is below the low-watermark if it is above the
/// high-watermark.  This provides cooperative back-pressure without spinning.
pub async fn apply_back_pressure(cfg: &BackPressureConfig, tx: &Sender<PipelineItem>) {
    if !cfg.enabled {
        return;
    }
    let capacity = tx.max_capacity() as f64;
    let in_flight = (capacity - tx.capacity() as f64) / capacity;
    if in_flight >= cfg.queue_high_watermark {
        let low = cfg.queue_low_watermark;
        loop {
            let current = (capacity - tx.capacity() as f64) / capacity;
            if current < low {
                break;
            }
            sleep(Duration::from_millis(10)).await;
        }
    }
}

/// Spawn the domain-processing stage.
///
/// Each item from `domain_rx` is passed through `processor`.  The result is
/// forwarded to `publish_tx`.  Errors are logged and counted, but do not stop
/// the worker.
pub fn spawn_domain_worker(
    mut domain_rx: Receiver<PipelineItem>,
    publish_tx: Sender<PipelineItem>,
    processor: Arc<dyn MessageProcessor>,
    metrics: Arc<MetricsCollector>,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        while let Some(item) = domain_rx.recv().await {
            let source_topic = item.message.topic.clone();
            match processor.process(item.message).await {
                Ok(processed) => {
                    let dest = item.destination_topic.clone();
                    if publish_tx
                        .send(PipelineItem {
                            message: processed,
                            destination_topic: dest,
                        })
                        .await
                        .is_err()
                    {
                        warn!("publish channel closed; stopping domain worker");
                        break;
                    }
                }
                Err(e) => {
                    metrics.record_source_error(&source_topic);
                    warn!(%e, "processor error; skipping message");
                }
            }
        }
    })
}

/// Build the internal pipeline channels and return a `(domain_tx, publish_tx,
/// domain_rx, publish_rx)` tuple.
pub fn build_pipeline(
    domain_queue_size: usize,
    publish_queue_size: usize,
) -> (
    Sender<PipelineItem>,
    Sender<PipelineItem>,
    Receiver<PipelineItem>,
    Receiver<PipelineItem>,
) {
    let (domain_tx, domain_rx) = mpsc::channel(domain_queue_size);
    let (publish_tx, publish_rx) = mpsc::channel(publish_queue_size);
    (domain_tx, publish_tx, domain_rx, publish_rx)
}
