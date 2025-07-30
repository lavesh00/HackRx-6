"""
API dependencies for dependency injection - FIXED VERSION.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, status
from app.core.document_processor import DocumentProcessor
from app.core.embedding_engine import EmbeddingEngine
from app.core.llm_client import LLMClient
from app.core.query_processor import QueryProcessor
from app.services.cache_service import CacheService, InMemoryCache
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.query_service import QueryService
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

@lru_cache()
def get_document_processor() -> DocumentProcessor:
    """Get document processor instance."""
    return DocumentProcessor()

@lru_cache()
def get_embedding_engine() -> EmbeddingEngine:
    """Get embedding engine instance."""
    settings = get_settings()
    return EmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_dir=settings.EMBEDDINGS_DIR
    )

@lru_cache()
def get_llm_client() -> LLMClient:
    """Get LLM client instance."""
    settings = get_settings()
    
    if not settings.GOOGLE_API_KEY:
        logger.warning("Google API key not configured. LLM functionality will be limited.")
    
    return LLMClient(
        api_key=settings.GOOGLE_API_KEY,
        model_name=settings.GEMINI_MODEL,
        rate_limit=settings.GEMINI_RATE_LIMIT
    )

@lru_cache()
def get_cache_service() -> Optional[CacheService]:
    """Get cache service instance if enabled."""
    settings = get_settings()
    
    if settings.REDIS_ENABLED:
        try:
            from app.services.cache_service import CacheService
            return CacheService(redis_url=settings.REDIS_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache service: {e}")
            logger.info("Falling back to in-memory cache")
            return InMemoryCache()
    else:
        logger.info("Using in-memory cache (Redis disabled)")
        return InMemoryCache()

def get_query_processor(
    document_processor: DocumentProcessor = Depends(get_document_processor),
    embedding_engine: EmbeddingEngine = Depends(get_embedding_engine),
    llm_client: LLMClient = Depends(get_llm_client),
    cache_service: Optional[CacheService] = Depends(get_cache_service)
) -> QueryProcessor:
    """Get query processor instance with all dependencies."""
    return QueryProcessor(
        document_processor=document_processor,
        embedding_engine=embedding_engine,
        llm_client=llm_client,
        cache_service=cache_service
    )

def get_document_service(
    document_processor: DocumentProcessor = Depends(get_document_processor),
    cache_service: Optional[CacheService] = Depends(get_cache_service)
) -> DocumentService:
    """Get document service instance."""
    return DocumentService(
        document_processor=document_processor,
        cache_service=cache_service
    )

def get_embedding_service(
    embedding_engine: EmbeddingEngine = Depends(get_embedding_engine),
    cache_service: Optional[CacheService] = Depends(get_cache_service)
) -> EmbeddingService:
    """Get embedding service instance."""
    return EmbeddingService(
        embedding_engine=embedding_engine,
        cache_service=cache_service
    )

def get_query_service(
    query_processor: QueryProcessor = Depends(get_query_processor),
    cache_service: Optional[CacheService] = Depends(get_cache_service)
) -> QueryService:
    """Get query service instance."""
    return QueryService(
        query_processor=query_processor,
        cache_service=cache_service
    )
