# Calibre Sync API

FastAPI-based synchronization service for Calibre ebook libraries. This service handles intelligent sync operations between your main Calibre library and replica locations (local folders, NAS, cloud storage).

## Overview

The Calibre Sync API provides automated synchronization capabilities for Calibre libraries, designed to run on the machine where Calibre is installed (typically Windows). It intelligently syncs books to replica locations while maintaining proper file organization and metadata.

## Features

- 🔄 **Intelligent Sync**: Smart synchronization with change detection
- 📚 **Multi-Destination**: Sync to multiple replica locations simultaneously  
- 🏷️ **Metadata-Driven**: Uses Calibre metadata for file naming and organization
- 📁 **Format Organization**: Automatically organizes files by format (epub/, pdf/, etc.)
- 🔍 **Comparison Tools**: Compare library contents with replicas
- 🌐 **REST API**: Full REST API for remote sync management
- 📊 **Detailed Reporting**: Comprehensive sync operation reports
- 🐳 **Docker Ready**: Full containerization support
- 🔧 **Health Monitoring**: Built-in health checks and status endpoints

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd calibre-sync-api

# Create and edit configuration
cp .env.example .env
# Edit .env with your paths

# Build and run
docker-compose up -d

# Check status
curl http://localhost:8001/health
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CALIBRE_LIBRARY_PATH="/path/to/calibre/library"
export REPLICA_PATHS="/path/to/replica1,/path/to/replica2"

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| **Calibre Configuration** |
| `CALIBRE_LIBRARY_PATH` | Path to Calibre library directory | **Required** | `/Users/user/Calibre Library` |
| `REPLICA_PATHS` | Comma-separated replica destinations | **Required** | `/mnt/nas/books,/backup/books` |
| `CALIBRE_CMD_PATH` | Path to calibredb executable | `calibredb` | `/usr/bin/calibredb` |
| **API Configuration** |
| `API_HOST` | API server host | `0.0.0.0` | `0.0.0.0` |
| `API_PORT` | API server port | `8001` | `8001` |
| `API_DEBUG` | Enable debug mode | `false` | `true` |
| `API_VERSION` | API version string | `1.0.0` | `1.0.0` |
| **Logging Configuration** |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `LOG_FILE` | Log file path (optional) | `None` | `/app/logs/sync.log` |
| **Performance Configuration** |
| `CACHE_TTL` | Cache TTL in seconds | `300` | `600` |
| **Docker Configuration** |
| `PUID` | User ID for file permissions | `1000` | `1000` |
| `PGID` | Group ID for file permissions | `1000` | `1000` |
| `TZ` | Timezone | `UTC` | `America/New_York` |

### Docker Compose Example

```yaml
version: '3.8'
services:
  calibre-sync:
    image: calibre-sync-api:latest
    container_name: calibre-sync
    ports:
      - "8001:8001"
    volumes:
      # Calibre library (read-only recommended)
      - "/path/to/calibre/library:/app/data/calibre-library:ro"
      # Replica destinations
      - "/path/to/local/replica:/app/data/local-replica"
      - "/mnt/nas/books:/app/data/nas-replica"
      # Logs and config
      - "./logs:/app/logs"
      - "./config:/config"
    environment:
      - CALIBRE_LIBRARY_PATH=/app/data/calibre-library
      - REPLICA_PATHS=/app/data/local-replica,/app/data/nas-replica
      - LOG_LEVEL=INFO
      - LOG_FILE=/app/logs/sync.log
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## API Endpoints

### Sync Operations
- `POST /api/v1/sync/trigger` - Start synchronization process
- `GET /api/v1/sync/status` - Get current sync status and progress
- `POST /api/v1/sync/stop` - Stop running synchronization
- `GET /api/v1/sync/history` - Get sync operation history

### Comparison & Analysis
- `GET /api/v1/comparison/compare` - Compare library with replicas
- `GET /api/v1/comparison/status` - Get comparison results
- `GET /api/v1/comparison/differences` - Get detailed differences

### System & Health
- `GET /health` - Application health check
- `GET /api/v1/system/info` - System information and configuration
- `GET /` - API information and version

### Interactive Documentation
- `GET /docs` - Swagger UI (when debug enabled)
- `GET /redoc` - ReDoc documentation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Calibre Sync   │    │   Calibre       │    │   Replica       │
│  UI (Angular)   │───▶│   Sync API      │───▶│   Locations     │
│   Port 4201     │    │   Port 8001     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────┬───────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Calibre Library │    │ Local + NAS     │
                       │   (Master)      │    │   Replicas      │
                       └─────────────────┘    └─────────────────┘
```

### Integration with Other Services

This API works alongside:
- **[Calibre Sync UI](../calibre-sync-ui/)**: Angular frontend for sync management
- **[Ebook Management API](../ebook-management-api/)**: Read-only API for book browsing
- **[Ebook Management UI](../ebook-management-ui/)**: Web interface for book browsing

## Sync Process

### How Synchronization Works

1. **Library Scan**: Scans Calibre library using metadata.db
2. **Change Detection**: Identifies new/modified books since last sync
3. **File Organization**: Organizes books by format in subdirectories
4. **Smart Naming**: Renames files using "Title - Author.ext" from metadata
5. **Multi-Destination**: Syncs to all configured replica locations
6. **Cleanup**: Removes files deleted from master library
7. **Reporting**: Generates detailed operation reports

### Sync Features

- **Dry Run Mode**: Test sync operations without making changes
- **Incremental Sync**: Only processes changed files
- **Format Filtering**: Sync specific formats only
- **Parallel Processing**: Multi-threaded operations for performance
- **Error Recovery**: Handles network interruptions and file locks
- **Progress Tracking**: Real-time sync progress monitoring

## Deployment

### Production Deployment

```bash
# Build production image
docker build -t calibre-sync-api:latest .

# Deploy with environment file
docker run -d \
  --name calibre-sync \
  --restart unless-stopped \
  -p 8001:8001 \
  -v /path/to/calibre/library:/library:ro \
  -v /path/to/replicas:/replicas \
  --env-file .env \
  calibre-sync-api:latest
```

### Windows Deployment

For Windows systems with Calibre installed:

```powershell
# Using Docker Desktop
docker-compose up -d

# Or run directly
$env:CALIBRE_LIBRARY_PATH="C:\Users\YourUser\Documents\Calibre Library"
$env:REPLICA_PATHS="C:\ebook-replicas,\\nas-server\books"
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Linux/macOS Deployment

```bash
# Set up environment
export CALIBRE_LIBRARY_PATH="/home/user/Calibre Library"
export REPLICA_PATHS="/mnt/nas/books,/backup/ebooks"

# Run with Docker
docker-compose up -d

# Or run directly
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks (optional)
pre-commit install

# Run tests
pytest tests/

# Run with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker Development

```bash
# Build development image
docker build -t calibre-sync-api:dev .

# Run development container
docker run -it --rm \
  -p 8001:8001 \
  -v $(pwd):/app \
  -v /path/to/test-library:/library:ro \
  calibre-sync-api:dev
```

## Monitoring & Logging

### Health Monitoring
- **Health Endpoint**: `GET /health` returns detailed system status
- **Sync Status**: Real-time sync operation monitoring
- **Error Tracking**: Comprehensive error logging and reporting

### Logging Configuration
- **Structured Logging**: JSON format logs with request tracing
- **Log Levels**: Configurable logging levels (DEBUG, INFO, WARNING, ERROR)
- **File Rotation**: Automatic log rotation and archival
- **Operation Logs**: Detailed sync operation logging

## Troubleshooting

### Common Issues

**Library Path Not Found**
```bash
# Verify library path exists
ls -la "/path/to/calibre/library"

# Check permissions
stat "/path/to/calibre/library/metadata.db"
```

**Replica Path Issues**
```bash
# Check replica paths
docker exec calibre-sync ls -la /app/data/

# Test write permissions
docker exec calibre-sync touch /app/data/replica/test-file
```

**Calibre Command Not Found**
```bash
# Check calibredb availability
docker exec calibre-sync calibredb --version

# Verify Calibre installation
which calibredb
```

**Permission Errors**
```bash
# Fix permissions (adjust PUID/PGID)
docker-compose down
# Edit docker-compose.yml with correct PUID/PGID
docker-compose up -d
```

**Sync Failures**
```bash
# Check logs
docker logs calibre-sync

# Enable debug logging
# Set LOG_LEVEL=DEBUG in environment
docker-compose restart
```

### Debug Mode

Enable comprehensive debugging:

```env
API_DEBUG=true
LOG_LEVEL=DEBUG
```

This enables:
- Detailed request/response logging
- Interactive API documentation at `/docs`
- Extended error messages
- Performance metrics

## Performance Tuning

### Large Libraries

```env
# Adjust cache settings for large libraries
CACHE_TTL=600

# Increase timeouts for slow storage
SYNC_TIMEOUT=7200

# Enable batch processing
SYNC_BATCH_SIZE=50
```

### Network Storage

```env
# Optimize for network replicas
NETWORK_TIMEOUT=300
RETRY_ATTEMPTS=3
CHUNK_SIZE=8192
```

## Security Considerations

- **Read-Only Library**: Mount Calibre library as read-only when possible
- **User Permissions**: Use appropriate PUID/PGID for file access
- **Network Access**: Restrict API access to trusted networks
- **Backup Strategy**: Ensure replica locations are backed up

## Related Projects

- **[Calibre Sync UI](../calibre-sync-ui/)**: Angular frontend for sync management
- **[Ebook Management API](../ebook-management-api/)**: Read-only API for book access
- **[Ebook Management UI](../ebook-management-ui/)**: Web interface for book browsing
- **[Library Browser App](../library-browser-app/)**: Android client application

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is part of the Ebook Management System suite.

---

**Perfect for**: Calibre users wanting automated library synchronization, homelab enthusiasts, and anyone managing large ebook collections across multiple locations.