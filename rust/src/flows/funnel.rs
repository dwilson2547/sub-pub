use std::sync::Arc;

use tracing::{error, info, warn};

use crate::config::FunnelConfig;
use crate::domain::MessageProcessor;
use crate::error::SubPubError;
use crate::metrics::MetricsCollector;

use super::base::{apply_back_pressure, build_pipeline, spawn_domain_worker, PipelineItem};

/// Funnel flow: many sources → one destination.
///
/// Each source is consumed in a dedicated Tokio task.  All messages are
/// funnelled into a shared domain-processing stage and then forwarded to the
/// single destination topic.
pub struct FunnelFlow {
    cfg: FunnelConfig,
    processor: Arc<dyn MessageProcessor>,
    metrics: Arc<MetricsCollector>,
}

impl FunnelFlow {
    pub fn new(
        cfg: FunnelConfig,
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
        mut shutdown_rx: tokio::sync::watch::Receiver<bool>,
    ) -> Result<(), SubPubError> {
        use crate::adapters::{create_publisher, create_source};

        if self.cfg.sources.is_empty() {
            return Err(SubPubError::Config(
                "FunnelConfig: at least one source is required".to_string(),
            ));
        }

        let dest_topic = self.cfg.destination_topic.clone();
        let queue_size = self.cfg.thread_pool.queue_size;
        let back_pressure = self.cfg.back_pressure.clone();

        let (domain_tx, publish_tx, domain_rx, mut publish_rx) =
            build_pipeline(queue_size, queue_size);

        // Spawn one consumer task per source.
        let mut source_handles = Vec::new();
        for source_cfg in &self.cfg.sources {
            let mut source = create_source(source_cfg)?;
            source.connect().await?;

            let topics: Vec<&str> = source_cfg.topics.iter().map(String::as_str).collect();
            if !topics.is_empty() {
                source.subscribe(&topics).await?;
            }

            let dtx = domain_tx.clone();
            let dest = dest_topic.clone();
            let bp = back_pressure.clone();
            let metrics = Arc::clone(&self.metrics);
            let srx = shutdown_rx.clone();

            let handle = tokio::spawn(async move {
                loop {
                    if *srx.borrow() {
                        break;
                    }
                    apply_back_pressure(&bp, &dtx).await;

                    match source.consume().await {
                        Ok(Some(msg)) => {
                            let src_topic = msg.topic.clone();
                            let size = msg.size();
                            metrics.record_source_message(&src_topic, size);
                            if dtx
                                .send(PipelineItem {
                                    message: msg,
                                    destination_topic: dest.clone(),
                                })
                                .await
                                .is_err()
                            {
                                warn!("domain channel closed; stopping funnel consumer");
                                break;
                            }
                        }
                        Ok(None) => break,
                        Err(e) => {
                            error!(%e, "funnel source consume error");
                            metrics.record_source_error("unknown");
                        }
                    }

                    if srx.has_changed().unwrap_or(false) && *srx.borrow() {
                        break;
                    }
                }
                let _ = source.close().await;
            });
            source_handles.push(handle);
        }

        // Drop the extra clone of domain_tx so the channel closes when all
        // source tasks finish.
        drop(domain_tx);

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

        info!("FunnelFlow started with {} sources", self.cfg.sources.len());

        // Wait for shutdown signal.
        let _ = shutdown_rx.changed().await;
        for handle in source_handles {
            handle.abort();
        }

        info!("FunnelFlow stopped");
        Ok(())
    }
}
