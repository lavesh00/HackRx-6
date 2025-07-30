"""
Health check endpoint for monitoring system status.
"""

from fastapi import APIRouter, status
from app.models.response_models import HealthResponse
from config.settings import get_settings
import logging
import asyncio
import httpx
import time

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint.
    
    Returns:
        HealthResponse with system status and component health
    """
    start_time = time.time()
    
    try:
        settings = get_settings()
        
        # Check components
        checks = {
            "api": True,  # If we reach here, API is working
            "database": await check_database(),
            "embeddings": await check_embeddings(),
            "llm": await check_llm(),
            "storage": await check_storage()
        }
        
        # Calculate overall health
        all_healthy = all(checks.values())
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        response = HealthResponse(
            status="healthy" if all_healthy else "degraded",
            timestamp=int(time.time()),
            response_time_ms=response_time,
            components=checks,
            version="1.0.0"
        )
        
        if not all_healthy:
            logger.warning(f"Health check failed: {checks}")
        
        return response
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=int(time.time()),
            response_time_ms=round((time.time() - start_time) * 1000, 2),
            components={
                "api": False,
                "database": False,
                "embeddings": False,
                "llm": False,
                "storage": False
            },
            version="1.0.0"
        )

async def check_database() -> bool:
    """Check database connectivity."""
    try:
        from app.database.connection import get_db_session
        from sqlalchemy import text  # Add this import
        
        async with get_db_session() as session:
            # Fix: Wrap SQL in text()
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

async def check_embeddings() -> bool:
    """Check embedding engine availability."""
    try:
        from app.core.embedding_engine import EmbeddingEngine
        engine = EmbeddingEngine()
        await engine.encode(["test"], batch_size=1)
        return True
    except Exception as e:
        logger.error(f"Embeddings health check failed: {e}")
        return False

async def check_llm() -> bool:
    """Check LLM service availability."""
    try:
        from app.core.llm_client import LLMClient
        settings = get_settings()
        client = LLMClient(
            api_key=settings.GOOGLE_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
        await client.generate_response("test", max_tokens=10)
        return True
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return False

async def check_storage() -> bool:
    """Check storage directory accessibility."""
    try:
        import os
        settings = get_settings()
        directories = [
            settings.DATA_DIR,
            settings.EMBEDDINGS_DIR,
            settings.PROCESSED_DOCS_DIR,
            settings.CACHE_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(directory, ".health_check")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        
        return True
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    health = await health_check()
    if health.status == "healthy":
        return {"status": "ready"}
    else:
        return {"status": "not ready"}, status.HTTP_503_SERVICE_UNAVAILABLE

@router.get("/health/alive")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}
