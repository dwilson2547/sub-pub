use std::sync::Arc;

use clap::Parser;
use tokio::sync::watch;
use tracing::info;
use tracing_subscriber::{EnvFilter, fmt};

use sub_pub::config::{Config, FlowConfig};
use sub_pub::domain::PassThroughProcessor;
use sub_pub::error::SubPubError;
use sub_pub::flows::{FanFlow, FunnelFlow, OneToOneFlow};
use sub_pub::metrics::MetricsCollector;

/// Extreme-performance pub-sub message processor (Rust rewrite).
#[derive(Parser, Debug)]
#[command(name = "sub-pub", version, about)]
struct Args {
    /// Path to the YAML configuration file.
    #[arg(short, long, value_name = "FILE")]
    config: String,

    /// Log level (TRACE | DEBUG | INFO | WARN | ERROR).
    #[arg(short, long, default_value = "INFO")]
    log_level: String,
}

#[tokio::main]
async fn main() -> Result<(), SubPubError> {
    let args = Args::parse();

    // Initialise structured logging.
    fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new(&args.log_level)),
        )
        .init();

    info!("sub-pub starting");

    let cfg = Config::from_file(&args.config)?;

    let metrics = Arc::new(MetricsCollector::new());
    let processor = Arc::new(PassThroughProcessor);

    // Build a shutdown channel.  When the watch value changes to `true` every
    // flow will gracefully stop.
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    // Register CTRL-C / SIGTERM handlers.
    let shutdown_tx_clone = shutdown_tx.clone();
    tokio::spawn(async move {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to listen for ctrl-c");
        info!("shutdown signal received");
        let _ = shutdown_tx_clone.send(true);
    });

    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let shutdown_tx_term = shutdown_tx.clone();
        tokio::spawn(async move {
            let mut sigterm =
                signal(SignalKind::terminate()).expect("failed to register SIGTERM handler");
            sigterm.recv().await;
            info!("SIGTERM received");
            let _ = shutdown_tx_term.send(true);
        });
    }

    // Run the configured flow.
    match cfg.flow {
        FlowConfig::OneToOne(flow_cfg) => {
            info!("starting one-to-one flow");
            let flow = OneToOneFlow::new(flow_cfg, processor, Arc::clone(&metrics));
            flow.run(shutdown_rx).await?;
        }
        FlowConfig::Funnel(flow_cfg) => {
            info!("starting funnel flow");
            let flow = FunnelFlow::new(flow_cfg, processor, Arc::clone(&metrics));
            flow.run(shutdown_rx).await?;
        }
        FlowConfig::Fan(flow_cfg) => {
            info!("starting fan flow");
            let flow = FanFlow::new(flow_cfg, processor, Arc::clone(&metrics));
            flow.run(shutdown_rx).await?;
        }
    }

    // Print final metrics on exit.
    let snap = metrics.snapshot();
    info!(
        uptime_secs = snap.uptime_secs,
        total_received = snap.total_messages_received,
        total_sent = snap.total_messages_sent,
        total_errors = snap.total_errors,
        msgs_per_sec = snap.messages_per_second,
        "final metrics"
    );

    Ok(())
}
