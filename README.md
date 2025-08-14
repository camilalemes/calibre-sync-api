# Calibre Sync API

This application handles synchronization and comparison operations between Calibre libraries and replica locations. It's designed to run on the Windows PC where Calibre is installed.

## Features

- **Sync Operations**: Synchronize Calibre library to replica locations
- **Comparison**: Compare library contents with replicas
- **Health Monitoring**: API health checks and status monitoring
- **File Operations**: Intelligent file copying, renaming, and organization

## Configuration

### Environment Variables

- `CALIBRE_LIBRARY_PATH`: Path to your Calibre library
- `REPLICA_PATHS`: Comma-separated list of replica destinations
- `CALIBRE_CMD_PATH`: Path to calibredb executable (default: "calibredb")
- `LOG_LEVEL`: Logging level (default: "INFO")
- `LOG_FILE`: Path to log file (optional)

### Docker Deployment

1. **Update docker-compose.yaml**:
   - Replace `C:/Users/YourUser/Documents/Calibre Library` with your actual Calibre library path
   - Replace `C:/Users/YourUser/Documents/ebook-replicas` with your local replica path
   - Update NAS IP address if different from `192.168.50.216`

2. **Build and run**:
   ```bash
   docker compose up -d
   ```

3. **Access the API**:
   - Health check: http://localhost:8001/health
   - API docs: http://localhost:8001/docs (if debug enabled)

## API Endpoints

### Sync Operations
- `POST /api/v1/sync/trigger` - Trigger sync operation
- `GET /api/v1/sync/status` - Get sync status
- `POST /api/v1/sync/stop` - Stop running sync

### Comparison
- `GET /api/v1/comparison/compare` - Compare library with replicas

### Health
- `GET /health` - Application health check

## Architecture

This app works in conjunction with the **Ebook Management API** which provides read-only access to the ebook collection from your server/NAS.

- **Calibre Sync API** (this app): Runs on Windows PC, handles write operations and sync
- **Ebook Management API**: Runs on server, provides read-only book listing from NAS replica

## Development

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export CALIBRE_LIBRARY_PATH="/path/to/calibre/library"
   export REPLICA_PATHS="/path/to/replica1,/path/to/replica2"
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

### Docker Development

```bash
# Build image
docker build -t calibre-sync .

# Run container
docker run -d --name calibre-sync -p 8001:8001 \
  -e CALIBRE_LIBRARY_PATH="/path/to/library" \
  -e REPLICA_PATHS="/path/to/replica1,/path/to/replica2" \
  calibre-sync
```