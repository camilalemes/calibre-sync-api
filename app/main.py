# app/main.py
"""Calibre Sync API - Handles synchronization and comparison operations."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

# Add the project root to sys.path to make imports work
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import application components
from app.config import settings
from app.exceptions import CalibreAPIException
from app.middleware import setup_middleware
from app.models import ErrorResponse, HealthCheckResponse
from app.routers import sync, comparison
from app.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger = get_logger(__name__)
    logger.info("🔄 Starting Calibre Sync API")
    logger.info(f"📚 Library path: {settings.CALIBRE_LIBRARY_PATH}")
    logger.info(f"📂 Replica paths: {len(settings.replica_paths_list)} configured")
    logger.info(f"🌐 API running on {settings.API_HOST}:{settings.API_PORT}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Calibre Sync API")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Setup logging first
    setup_logging(
        level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
    )
    
    logger = get_logger(__name__)
    logger.info("🔧 Configuring Calibre Sync API...")
    
    # Create FastAPI app
    app = FastAPI(
        title="Calibre Sync API",
        description="API for synchronizing Calibre libraries to external devices",
        version=settings.API_VERSION,
        debug=settings.API_DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.API_DEBUG else None,
        redoc_url="/redoc" if settings.API_DEBUG else None,
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(sync.router, prefix="/api/v1", tags=["sync"])
    app.include_router(comparison.router, prefix="/api/v1", tags=["comparison"])
    
    # Add root endpoints
    setup_root_endpoints(app)
    
    logger.info("✅ Calibre Sync API configured successfully")
    return app


def setup_exception_handlers(app: FastAPI):
    """Setup custom exception handlers."""
    
    @app.exception_handler(CalibreAPIException)
    async def calibre_exception_handler(request: Request, exc: CalibreAPIException):
        """Handle Calibre API specific exceptions."""
        logger = get_logger(__name__)
        logger.error(f"Calibre API error: {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="calibre_error",
                message=exc.detail,
                details=exc.details
            ).model_dump()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger = get_logger(__name__)
        logger.warning(f"Validation error: {exc}")
        
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                message="Request validation failed",
                details={"validation_errors": exc.errors()}
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger = get_logger(__name__)
        logger.exception(f"Unhandled exception: {exc}")
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred" if not settings.API_DEBUG else str(exc)
            ).model_dump()
        )


def setup_root_endpoints(app: FastAPI):
    """Setup root level endpoints."""
    
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        """Health check endpoint."""
        from app.services.calibre_service import get_calibre_service
        
        try:
            calibre_service = get_calibre_service()
            # Test calibre availability
            await calibre_service.get_books()
            calibre_available = True
            library_accessible = True
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning(f"Health check failed: {e}")
            calibre_available = False
            library_accessible = False
        
        return HealthCheckResponse(
            success=True,
            message="Sync API is running",
            version=settings.API_VERSION,
            calibre_available=calibre_available,
            library_accessible=library_accessible,
            replica_count=len(settings.replica_paths_list)
        )
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Calibre Sync API",
            "version": settings.API_VERSION,
            "docs_url": "/docs" if settings.API_DEBUG else None,
            "health_url": "/health"
        }


# Create the FastAPI app
app = create_application()


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )