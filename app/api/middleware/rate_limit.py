"""
Rate limiting middleware to prevent abuse.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque
from typing import Dict, Deque
import time
import logging
import asyncio

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds
        self.request_times: Dict[str, Deque[float]] = defaultdict(deque)
        self.cleanup_interval = 300  # Cleanup every 5 minutes
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through rate limiting middleware."""
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = self.get_client_ip(request)
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self.cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Check rate limit
        if self.is_rate_limited(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for client {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record request
        self.request_times[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(self.request_times[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limit."""
        request_times = self.request_times[client_ip]
        
        # Remove expired entries
        while request_times and current_time - request_times[0] > self.window_size:
            request_times.popleft()
        
        # Check if rate limit exceeded
        return len(request_times) >= self.requests_per_minute
    
    async def cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old request entries to prevent memory leaks."""
        clients_to_remove = []
        
        for client_ip, request_times in self.request_times.items():
            # Remove expired entries
            while request_times and current_time - request_times[0] > self.window_size:
                request_times.popleft()
            
            # Mark empty queues for removal
            if not request_times:
                clients_to_remove.append(client_ip)
        
        # Remove empty entries
        for client_ip in clients_to_remove:
            del self.request_times[client_ip]
        
        logger.debug(f"Rate limiter cleanup: removed {len(clients_to_remove)} empty entries")
