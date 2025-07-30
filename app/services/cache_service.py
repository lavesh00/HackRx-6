"""
Cache service for Redis-based caching operations.
"""

import json
import logging
import pickle
from typing import Any, Optional, Union
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.utils.exceptions import CacheError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service."""
    
    def __init__(self, redis_url: str):
        if not REDIS_AVAILABLE:
            raise CacheError("Redis not available. Install redis package.")
        
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.settings = get_settings()
        
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Cache service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            raise CacheError(f"Cache initialization failed: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            data = await self.redis_client.get(key)
            if data is None:
                return None
            
            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(data)
                
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            # Try to serialize as JSON first, then pickle
            try:
                serialized_data = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                serialized_data = pickle.dumps(value)
            
            await self.redis_client.set(key, serialized_data, ex=ttl)
            return True
            
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
            
        except Exception as e:
            logger.warning(f"Cache clear pattern failed for {pattern}: {e}")
            return 0
    
    async def get_cache_info(self) -> dict:
        """Get cache statistics and information."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            info = await self.redis_client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get cache info: {e}")
            return {}
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Cache service connection closed")

class InMemoryCache:
    """Simple in-memory cache fallback."""
    
    def __init__(self):
        self.cache = {}
        self.ttl_data = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        import time
        
        if key not in self.cache:
            return None
        
        # Check TTL
        if key in self.ttl_data:
            if time.time() > self.ttl_data[key]:
                del self.cache[key]
                del self.ttl_data[key]
                return None
        
        return self.cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        import time
        
        self.cache[key] = value
        
        if ttl:
            self.ttl_data[key] = time.time() + ttl
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        if key in self.cache:
            del self.cache[key]
            if key in self.ttl_data:
                del self.ttl_data[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        value = await self.get(key)
        return value is not None
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern (simple implementation)."""
        import fnmatch
        
        keys_to_delete = [
            key for key in self.cache.keys() 
            if fnmatch.fnmatch(key, pattern)
        ]
        
        for key in keys_to_delete:
            await self.delete(key)
        
        return len(keys_to_delete)
    
    async def get_cache_info(self) -> dict:
        """Get cache information."""
        return {
            'type': 'in_memory',
            'total_keys': len(self.cache),
            'memory_usage': 'N/A'
        }
    
    async def close(self) -> None:
        """Close cache (no-op for memory cache)."""
        pass
