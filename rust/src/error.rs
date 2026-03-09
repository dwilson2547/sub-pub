use thiserror::Error;

/// Top-level error type for the sub-pub library.
#[derive(Debug, Error)]
pub enum SubPubError {
    /// The backing message system returned an error.
    #[error("adapter error: {0}")]
    Adapter(String),

    /// Configuration is invalid or missing.
    #[error("configuration error: {0}")]
    Config(String),

    /// An I/O or connection error occurred.
    #[error("connection error: {0}")]
    Connection(String),

    /// Message processing failed.
    #[error("processing error: {0}")]
    Processing(String),

    /// A required serialization / deserialization step failed.
    #[error("serialization error: {0}")]
    Serialization(String),

    /// Catch-all for unexpected errors.
    #[error("unexpected error: {0}")]
    Unexpected(#[from] anyhow::Error),
}
