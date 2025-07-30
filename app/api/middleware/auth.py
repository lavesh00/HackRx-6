"""
Authentication middleware for API security.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import get_settings
import logging
import time

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for bearer token validation."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.exempt_paths = {"/health", "/health/ready", "/health/alive", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through authentication middleware."""
        start_time = time.time()
        
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return response
        
        # Check for authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            logger.warning(f"Missing authorization header for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header required"}
            )
        
        # Validate bearer token format
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid auth scheme: {scheme}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid authentication scheme"}
                )
        except ValueError:
            logger.warning("Invalid authorization header format")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"}
            )
        
        # Validate token
        if token != self.settings.BEARER_TOKEN:
            logger.warning(f"Invalid token attempt from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication token"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Log request processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
