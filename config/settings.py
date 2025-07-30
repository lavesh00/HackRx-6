"""
Application settings and configuration management.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Environment Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=1, description="Number of worker processes")
    DEBUG: bool = Field(default=True, description="Debug mode")  # Changed to True for development
    
    # Authentication
    BEARER_TOKEN: str = Field(
        default="c1be80ee89dc9bdfea91d3a85be77235fdd24ca2063395b84d1b716548a6d9ac",
        description="Bearer token for API authentication"
    )
    
    # Google Gemini API
    GOOGLE_API_KEY: str = Field(default="", description="Google API key for Gemini")
    GEMINI_MODEL: str = Field(default="gemini-pro", description="Gemini model name")
    GEMINI_RATE_LIMIT: int = Field(default=15, description="Gemini API rate limit per minute")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./data/app.db", description="Database URL")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    REDIS_ENABLED: bool = Field(default=False, description="Enable Redis caching")
    
    # File Storage
    DATA_DIR: str = Field(default="./data", description="Data directory")
    EMBEDDINGS_DIR: str = Field(default="./data/embeddings", description="Embeddings directory")
    PROCESSED_DOCS_DIR: str = Field(default="./data/processed_docs", description="Processed documents directory")
    CACHE_DIR: str = Field(default="./data/cache", description="Cache directory")
    
    # Performance Settings
    MAX_WORKERS: int = Field(default=4, description="Maximum worker threads")
    CHUNK_SIZE: int = Field(default=512, description="Text chunk size for processing")
    CHUNK_OVERLAP: int = Field(default=50, description="Overlap between text chunks")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for embedding generation")
    MAX_TOKENS: int = Field(default=1000000, description="Maximum tokens per day")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Similarity threshold for matching")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format")
    LOG_FILE: str = Field(default="./logs/app.log", description="Log file path")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This will ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.EMBEDDINGS_DIR, exist_ok=True)
        os.makedirs(self.PROCESSED_DOCS_DIR, exist_ok=True)
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
