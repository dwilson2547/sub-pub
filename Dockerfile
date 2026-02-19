# Multi-stage build for sub-pub message processor
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and setup files
COPY requirements.txt setup.py README.md ./
COPY sub_pub ./sub_pub

# Install the application with all dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[all]"

# Production image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/sub-pub /usr/local/bin/sub-pub

# Copy application code
COPY sub_pub ./sub_pub
COPY examples ./examples

# Create a non-root user
RUN useradd -m -u 1000 subpub && \
    chown -R subpub:subpub /app

# Switch to non-root user
USER subpub

# Set default config location (can be overridden)
ENV CONFIG_FILE=/app/config/config.yaml

# Expose metrics port (if implemented in future)
EXPOSE 8080

# Health check (basic check if process is running)
# NOTE: This only verifies the process exists, not that it's functioning correctly.
# A more robust health check would require an HTTP metrics endpoint (planned feature).
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "sub-pub" || exit 1

# Default command - requires config to be provided
ENTRYPOINT ["sub-pub"]
CMD ["-c", "/app/config/config.yaml", "-l", "INFO"]
