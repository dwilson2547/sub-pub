use std::sync::Arc;

use serde_json::Value as JsonValue;
use tracing::{error, info, warn};

use crate::config::{DestinationResolver, FanConfig};
use crate::domain::MessageProcessor;
use crate::error::SubPubError;
use crate::metrics::MetricsCollector;

use super::base::{apply_back_pressure, build_pipeline, spawn_domain_worker, PipelineItem};

/// Fan flow: one source → many destinations (content-based routing).
///
/// The destination topic for each message is resolved either from a message
/// header or from a field in the JSON payload, according to
/// [`DestinationResolver`].  Messages that cannot be resolved fall back to a
/// topic named `"default"`.
pub struct FanFlow {
    cfg: FanConfig,
    processor: Arc<dyn MessageProcessor>,
    metrics: Arc<MetricsCollector>,
}

impl FanFlow {
    pub fn new(
        cfg: FanConfig,
        processor: Arc<dyn MessageProcessor>,
        metrics: Arc<MetricsCollector>,
    ) -> Self {
        Self {
            cfg,
            processor,
            metrics,
        }
    }

    fn resolve_destination(&self, item: &PipelineItem) -> String {
        match &self.cfg.destination_resolver {
            DestinationResolver::Header { header_key } => {
                item.message.get_header(header_key, "default").to_string()
            }
            DestinationResolver::PayloadKey { payload_key } => {
                let parsed: Result<JsonValue, _> =
                    serde_json::from_slice(&item.message.payload);
                match parsed {
                    Ok(JsonValue::Object(map)) => map
                        .get(payload_key)
                        .and_then(|v| v.as_str())
                        .unwrap_or("default")
                        .to_string(),
                    _ => "default".to_string(),
                }
            }
        }
    }

    /// Run the flow until `shutdown_rx` fires or a fatal error occurs.
    pub async fn run(
        self,
        shutdown_rx: tokio::sync::watch::Receiver<bool>,
    ) -> Result<(), SubPubError> {
        use crate::adapters::{create_publisher, create_source};

        let queue_size = self.cfg.thread_pool.queue_size;
        let (domain_tx, publish_tx, domain_rx, mut publish_rx) =
            build_pipeline(queue_size, queue_size);

        // Spawn domain-processing worker.
        let _domain_handle = spawn_domain_worker(
            domain_rx,
            publish_tx,
            Arc::clone(&self.processor),
            Arc::clone(&self.metrics),
        );

        // Spawn publish worker.
        let mut publisher = create_publisher(&self.cfg.destination)?;
        publisher.connect().await?;

        let metrics_pub = Arc::clone(&self.metrics);
        let _publish_handle = tokio::spawn(async move {
            while let Some(item) = publish_rx.recv().await {
                let topic = &item.destination_topic;
                let size = item.message.size();
                match publisher.publish(&item.message, topic).await {
                    Ok(()) => metrics_pub.record_destination_message(topic, size),
                    Err(e) => {
                        error!(%e, %topic, "publish error");
                        metrics_pub.record_destination_error(topic);
                    }
                }
            }
            let _ = publisher.flush().await;
            let _ = publisher.close().await;
        });

        // Connect source.
        let mut source = create_source(&self.cfg.source)?;
        source.connect().await?;
        source
            .subscribe(&[&self.cfg.source_topic])
            .await?;

        info!("FanFlow started; source topic: {}", self.cfg.source_topic);

        loop {
            if *shutdown_rx.borrow() {
                break;
            }

            apply_back_pressure(&self.cfg.back_pressure, &domain_tx).await;

            match source.consume().await {
                Ok(Some(msg)) => {
                    let src_topic = msg.topic.clone();
                    let size = msg.size();
                    self.metrics.record_source_message(&src_topic, size);

                    // Resolve destination topic before moving `msg` into
                    // PipelineItem (we need message headers / payload).
                    let item = PipelineItem {
                        destination_topic: String::new(), // placeholder
                        message: msg,
                    };
                    let dest_topic = self.resolve_destination(&item);

                    if domain_tx
                        .send(PipelineItem {
                            destination_topic: dest_topic,
                            ..item
                        })
                        .await
                        .is_err()
                    {
                        warn!("domain channel closed; stopping fan consumer");
                        break;
                    }
                }
                Ok(None) => {
                    info!("source exhausted; stopping flow");
                    break;
                }
                Err(e) => {
                    error!(%e, "fan source consume error");
                    self.metrics.record_source_error(&self.cfg.source_topic);
                }
            }

            if shutdown_rx.has_changed().unwrap_or(false) && *shutdown_rx.borrow() {
                break;
            }
        }

        drop(domain_tx);
        let _ = source.close().await;
        info!("FanFlow stopped");
        Ok(())
    }
}
