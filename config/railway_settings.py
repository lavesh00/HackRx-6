"""
Railway-specific settings configuration.
"""
import os
from pydantic_settings import BaseSettings

class RailwaySettings(BaseSettings):
    """Railway production settings."""
    
    # Railway automatically provides PORT
    API_HOST: str = "0.0.0.0"
    API_PORT: int = int(os.getenv("PORT", 8000))
    API_WORKERS: int = 1  # Railway handles scaling
    DEBUG: bool = False  # Always False in production
    
    # Authentication
    BEARER_TOKEN: str = os.getenv("BEARER_TOKEN", "")
    
    # Google Gemini API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_RATE_LIMIT: int = int(os.getenv("GEMINI_RATE_LIMIT", "15"))
    
    # Database - Railway will provide DATABASE_URL for PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    
    # Redis - Railway can provide Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    
    # File Storage
    DATA_DIR: str = "./data"
    EMBEDDINGS_DIR: str = "./data/embeddings"
    PROCESSED_DOCS_DIR: str = "./data/processed_docs"
    CACHE_DIR: str = "./data/cache"
    
    # Performance settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "8"))
    CONCURRENT_REQUESTS: int = int(os.getenv("CONCURRENT_REQUESTS", "6"))
    MAX_QUERY_VARIATIONS: int = int(os.getenv("MAX_QUERY_VARIATIONS", "2"))
    MAX_CONTEXT_CHUNKS: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "2"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "350"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000000"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    LOG_FILE: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
