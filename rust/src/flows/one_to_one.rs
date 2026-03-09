use std::collections::HashMap;
use std::sync::Arc;

use tracing::{error, info, warn};

use crate::config::OneToOneConfig;
use crate::domain::MessageProcessor;
use crate::error::SubPubError;
use crate::metrics::MetricsCollector;

use super::base::{apply_back_pressure, build_pipeline, spawn_domain_worker, PipelineItem};

/// One-to-one flow: each message arriving on a source topic is forwarded to
/// its configured destination topic, with optional processing in between.
///
/// Multiple topic-to-topic mappings can be served by a single flow instance —
/// messages whose source topic does not appear in `mappings` are silently
/// skipped.
pub struct OneToOneFlow {
    cfg: OneToOneConfig,
    processor: Arc<dyn MessageProcessor>,
    metrics: Arc<MetricsCollector>,
}

impl OneToOneFlow {
    pub fn new(
        cfg: OneToOneConfig,
        processor: Arc<dyn MessageProcessor>,
        metrics: Arc<MetricsCollector>,
    ) -> Self {
        Self {
            cfg,
            processor,
            metrics,
        }
    }

    /// Run the flow until `shutdown_rx` fires or a fatal error occurs.
    pub async fn run(
        self,
        shutdown_rx: tokio::sync::watch::Receiver<bool>,
    ) -> Result<(), SubPubError> {
        use crate::adapters::{create_publisher, create_source};

        // Build the topic-to-topic mapping for fast lookup.
        let mapping: HashMap<String, String> = self
            .cfg
            .mappings
            .iter()
            .map(|m| (m.source_topic.clone(), m.destination_topic.clone()))
            .collect();

        if mapping.is_empty() {
            return Err(SubPubError::Config(
                "OneToOneConfig: no topic mappings defined".to_string(),
            ));
        }

        // Collect all source topics.
        let source_topics: Vec<String> = mapping.keys().cloned().collect();
        let source_topic_refs: Vec<&str> = source_topics.iter().map(String::as_str).collect();

        // Build source and publisher.
        let mut source = create_source(&self.cfg.source)?;
        let mut publisher = create_publisher(&self.cfg.destination)?;
        source.connect().await?;
        source.subscribe(&source_topic_refs).await?;
        publisher.connect().await?;

        let queue_size = self.cfg.thread_pool.queue_size;
        let (domain_tx, publish_tx, domain_rx, mut publish_rx) =
            build_pipeline(queue_size, queue_size);

        // Spawn domain-processing worker.
        let _domain_handle = spawn_domain_worker(
            domain_rx,
            publish_tx.clone(),
            Arc::clone(&self.processor),
            Arc::clone(&self.metrics),
        );

        // Spawn publish worker.
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

        info!("OneToOneFlow started; topics: {:?}", source_topics);

        // Consumer loop.
        loop {
            // Honour shutdown signal.
            if *shutdown_rx.borrow() {
                break;
            }

            apply_back_pressure(&self.cfg.back_pressure, &domain_tx).await;

            match source.consume().await {
                Ok(Some(msg)) => {
                    let src_topic = msg.topic.clone();
                    match mapping.get(&src_topic) {
                        Some(dest_topic) => {
                            let size = msg.size();
                            self.metrics.record_source_message(&src_topic, size);
                            let dest = dest_topic.clone();
                            if domain_tx
                                .send(PipelineItem {
                                    message: msg,
                                    destination_topic: dest,
                                })
                                .await
                                .is_err()
                            {
                                warn!("domain channel closed; stopping consumer");
                                break;
                            }
                        }
                        None => {
                            warn!(%src_topic, "no mapping for topic; skipping");
                        }
                    }
                }
                Ok(None) => {
                    info!("source exhausted; stopping flow");
                    break;
                }
                Err(e) => {
                    error!(%e, "consume error");
                    self.metrics.record_source_error("unknown");
                }
            }

            // Check shutdown again after potentially blocking on consume.
            if shutdown_rx.has_changed().unwrap_or(false) && *shutdown_rx.borrow() {
                break;
            }
        }

        // Graceful shutdown: close the domain channel so downstream workers
        // drain their queues before exiting.
        drop(domain_tx);
        let _ = source.close().await;
        info!("OneToOneFlow stopped");
        Ok(())
    }
}
