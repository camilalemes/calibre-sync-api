# Dockerfile for Calibre Sync App (runs on Windows PC)
FROM python:3.11-slim

# Install system dependencies including Calibre
RUN apt-get update && apt-get install -y \
    # Basic system tools
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    # Install Calibre from package manager
    calibre \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for volumes
RUN mkdir -p /app/data/calibre-library \
             /app/data/replicas \
             /app/logs \
             /config/logs

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app /config
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]