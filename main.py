"""
Main application entry point for the LLM-powered document query system - FIXED VERSION.
"""

import asyncio
import uvicorn
import logging

from app.api.v1.endpoints.hackrx import router as hackrx_router
from app.api.v1.endpoints.health import router as health_router
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.cors import setup_cors
from app.api.middleware.rate_limit import RateLimitMiddleware
from config.settings import get_settings
from config.logging_config import setup_logging
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="LLM Document Query System",
    description="Production-ready document query system using LLM and vector search",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Setup CORS
setup_cors(app)

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(hackrx_router, prefix="", tags=["hackrx"])
app.include_router(health_router, prefix="", tags=["health"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting LLM Document Query System")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API running on {settings.API_HOST}:{settings.API_PORT}")
    
    # Initialize embedding engine during startup when event loop is running
    try:
        from app.api.v1.dependencies import get_embedding_engine
        embedding_engine = get_embedding_engine()
        await embedding_engine.initialize()
        logger.info("✅ Embedding engine initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize embedding engine: {e}")
        # Don't raise - let the app start but log the error
        logger.warning("Application will continue but embedding functionality may be limited")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down LLM Document Query System")
    
    # Optional: Add cleanup for caches, database connections, etc.
    try:
        from app.api.v1.dependencies import get_cache_service
        cache_service = get_cache_service()
        if cache_service:
            await cache_service.close()
            logger.info("Cache service closed")
    except Exception as e:
        logger.warning(f"Error closing cache service: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.DEBUG,
        log_config=None  # Use our custom logging config
    )
