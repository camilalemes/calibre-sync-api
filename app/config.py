# app/config.py
"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # Calibre Configuration
    CALIBRE_LIBRARY_PATH: str = Field(
        ..., 
        description="Path to the Calibre library directory"
    )
    REPLICA_PATHS: str = Field(
        ..., 
        description="Comma-separated list of replica paths"
    )
    CALIBRE_CMD_PATH: str = Field(
        default="calibredb", 
        description="Path to calibredb executable"
    )
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8001, ge=1, le=65535, description="API port")
    API_DEBUG: bool = Field(default=False, description="Enable debug mode")
    API_VERSION: str = Field(default="1.0.0", description="API version")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # Cache Configuration (for sync operations)
    CACHE_TTL: int = Field(default=300, ge=60, description="Cache TTL in seconds")
    
    # Computed Properties
    @property
    def replica_paths_list(self) -> List[str]:
        """Get replica paths as a list."""
        return [path.strip() for path in self.REPLICA_PATHS.split(",") if path.strip()]
    
    @property
    def library_exists(self) -> bool:
        """Check if the Calibre library path exists."""
        return Path(self.CALIBRE_LIBRARY_PATH).exists()
    
    @property
    def valid_replica_paths(self) -> List[str]:
        """Get list of valid (existing) replica paths."""
        return [path for path in self.replica_paths_list if Path(path).exists()]
    
    # Validators
    @field_validator("CALIBRE_LIBRARY_PATH")
    @classmethod
    def validate_library_path(cls, v: str) -> str:
        """Validate that the library path is not empty."""
        if not v or not v.strip():
            raise ValueError("CALIBRE_LIBRARY_PATH cannot be empty")
        return v.strip()
    
    @field_validator("REPLICA_PATHS")
    @classmethod
    def validate_replica_paths(cls, v: str) -> str:
        """Validate that replica paths is not empty."""
        if not v or not v.strip():
            raise ValueError("REPLICA_PATHS cannot be empty")
        return v.strip()
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got {v}",
                config_key="LOG_LEVEL"
            )
        return v_upper
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()