"""
CORS middleware configuration for cross-origin requests.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

def setup_cors(app: FastAPI) -> None:
    """Setup CORS middleware with appropriate configuration."""
    settings = get_settings()
    
    # Configure CORS origins based on environment
    if settings.DEBUG:
        origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    else:
        origins = [
            "https://your-domain.com",
            "https://www.your-domain.com",
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ],
        expose_headers=["X-Process-Time"],
        max_age=3600,
    )
    
    logger.info("CORS configured for development with localhost access")
