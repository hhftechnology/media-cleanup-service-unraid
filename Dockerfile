# Use balenalib Alpine Python image as base
FROM balenalib/amd64-alpine-python:3.11-3.16

# Add labels for better container management
LABEL maintainer="HHF Technology <discourse@hhf.technology>"
LABEL description="media-cleanup-service-unraid"
LABEL version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN addgroup -S mediaclean && \
    adduser -S -G mediaclean mediaclean

# Create necessary directories
RUN mkdir -p /app /config /logs /data && \
    chown mediaclean:mediaclean /app /config /logs /data

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    curl \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY media_cleanup.py entrypoint.sh ./
COPY config.yaml /config/

# Set proper permissions
RUN chmod +x entrypoint.sh && \
    chown -R mediaclean:mediaclean /app /config /logs

# Switch to non-root user
USER mediaclean

# Set up healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8989/api/v3/system/status || exit 1

# Set default configuration path
ENV CONFIG_PATH=/config/config.yaml

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]