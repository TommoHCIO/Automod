"""
Redis Caching Layer for Performance Optimization
Provides ~1ms response times for cached data
"""

import json
import asyncio
from typing import Optional, Any, Union
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Async Redis cache manager with TTL support
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 300  # 5 minutes
    
    async def connect(self):
        """Establish connection to Redis"""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis cache")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        Returns None if key doesn't exist or Redis is unavailable
        """
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.warning(f"Cache GET error for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time to live in seconds (default: 300s)
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Serialize if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Cache SET error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache EXISTS error for key '{key}': {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        Args:
            pattern: Redis key pattern (e.g., "user:*")
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache CLEAR_PATTERN error for pattern '{pattern}': {e}")
            return 0
    
    # Helper methods for specific cache types
    
    async def cache_ai_response(self, message_content: str, response: dict, ttl: int = 300):
        """Cache AI moderation response"""
        key = f"ai:message:{hash(message_content)}"
        return await self.set(key, response, ttl)
    
    async def get_ai_response(self, message_content: str) -> Optional[dict]:
        """Get cached AI moderation response"""
        key = f"ai:message:{hash(message_content)}"
        return await self.get(key)
    
    async def cache_user_data(self, user_id: str, guild_id: str, data: dict, ttl: int = 900):
        """Cache user reputation data (15 min TTL)"""
        key = f"user:{guild_id}:{user_id}"
        return await self.set(key, data, ttl)
    
    async def get_user_data(self, user_id: str, guild_id: str) -> Optional[dict]:
        """Get cached user reputation data"""
        key = f"user:{guild_id}:{user_id}"
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: str, guild_id: str):
        """Invalidate user cache after updates"""
        key = f"user:{guild_id}:{user_id}"
        return await self.delete(key)
    
    async def cache_guild_config(self, guild_id: str, config: dict, ttl: int = 3600):
        """Cache guild configuration (1 hour TTL)"""
        key = f"guild:{guild_id}:config"
        return await self.set(key, config, ttl)
    
    async def get_guild_config(self, guild_id: str) -> Optional[dict]:
        """Get cached guild configuration"""
        key = f"guild:{guild_id}:config"
        return await self.get(key)
    
    async def invalidate_guild_cache(self, guild_id: str):
        """Invalidate guild cache after config updates"""
        key = f"guild:{guild_id}:config"
        return await self.delete(key)
