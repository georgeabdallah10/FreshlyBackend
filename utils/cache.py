"""
Caching utilities for improved performance
Supports both in-memory and Redis caching strategies
"""
import logging
import pickle
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
import asyncio
from datetime import datetime, timedelta

from core.settings import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry['expires']:
                    logger.debug(f"Cache HIT: {key}")
                    return entry['value']
                else:
                    # Expired, remove it
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED: {key}")
            
            logger.debug(f"Cache MISS: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = settings.CACHE_TTL_SECONDS
        
        expires = datetime.now() + timedelta(seconds=ttl)
        
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': expires
            }
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache CLEARED")

    async def cleanup_expired(self) -> None:
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = []
        
        async with self._lock:
            for key, entry in self._cache.items():
                if now >= entry['expires']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")


class RedisCache:
    """Redis-based cache (for production use)"""
    
    def __init__(self):
        self._redis = None
        self._connected = False
    
    async def _connect(self):
        """Connect to Redis if available"""
        if not settings.REDIS_URL:
            logger.warning("Redis URL not configured, falling back to in-memory cache")
            return False
        
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(settings.REDIS_URL)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._connected and not await self._connect():
            return None
        
        try:
            data = await self._redis.get(key)
            if data:
                logger.debug(f"Redis HIT: {key}")
                return pickle.loads(data)
            logger.debug(f"Redis MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in Redis cache"""
        if not self._connected and not await self._connect():
            return
        
        if ttl is None:
            ttl = settings.CACHE_TTL_SECONDS
        
        try:
            data = pickle.dumps(value)
            await self._redis.setex(key, ttl, data)
            logger.debug(f"Redis SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from Redis"""
        if not self._connected:
            return
        
        try:
            await self._redis.delete(key)
            logger.debug(f"Redis DELETE: {key}")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")


# Global cache instance
_cache_instance = None


def get_cache():
    """Get cache instance (Redis if available, otherwise in-memory)"""
    global _cache_instance
    if _cache_instance is None:
        if settings.REDIS_URL:
            _cache_instance = RedisCache()
        else:
            _cache_instance = InMemoryCache()
    return _cache_instance


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int = None, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            func_key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            cache = get_cache()
            
            # Try to get from cache
            result = await cache.get(func_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(func_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we'll use asyncio to handle cache operations
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def invalidate_cache_pattern(pattern: str):
    """Invalidate all cache keys matching a pattern"""
    cache = get_cache()
    
    if isinstance(cache, RedisCache) and cache._connected:
        try:
            keys = await cache._redis.keys(pattern)
            if keys:
                await cache._redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    else:
        # For in-memory cache, we'd need to implement pattern matching
        logger.warning("Pattern-based cache invalidation not supported for in-memory cache")


# Cache cleanup task
async def cache_cleanup_task():
    """Background task to cleanup expired cache entries"""
    cache = get_cache()
    
    if isinstance(cache, InMemoryCache):
        while True:
            try:
                await cache.cleanup_expired()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup task error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
