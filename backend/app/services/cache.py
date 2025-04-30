"""
Redis cache service for caching embeddings and summaries.
"""
import redis
import json
import os
import logging
from typing import Any, Optional, Dict, List
from dotenv import load_dotenv
import time

load_dotenv()

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache service."""
    
    def __init__(self, host=None, port=None, password=None, db=0, ttl=3600):
        """
        Initialize the Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            ttl: Default TTL for cache entries in seconds
        """
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.password = password or os.getenv("REDIS_PASSWORD", None)
        self.db = db
        self.ttl = ttl
        
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True
            )
            logger.info("Connected to Redis")
        except Exception as e:
            logger.exception(f"Failed to connect to Redis: {str(e)}")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        if not self.client:
            return None
            
        try:
            start_time = time.time()
            value = self.client.get(key)
            elapsed = time.time() - start_time
            
            logger.debug(f"Cache get for '{key}' took {elapsed:.4f}s")
            
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return None
        except Exception as e:
            logger.exception(f"Error getting from cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds, or None to use default
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        ttl = ttl if ttl is not None else self.ttl
        
        try:
            start_time = time.time()
            
            # Convert non-string values to JSON
            if not isinstance(value, str):
                value = json.dumps(value)
                
            result = self.client.set(key, value, ex=ttl)
            
            elapsed = time.time() - start_time
            logger.debug(f"Cache set for '{key}' took {elapsed:.4f}s")
            
            return result
        except Exception as e:
            logger.exception(f"Error setting cache: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.exception(f"Error deleting from cache: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists, False otherwise
        """
        if not self.client:
            return False
            
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.exception(f"Error checking cache: {str(e)}")
            return False
    
    def invalidate_conversation(self, conversation_id: str) -> int:
        """
        Invalidate all cache entries for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
            
        try:
            pattern = f"conversation:{conversation_id}:*"
            keys = self.client.keys(pattern)
            
            if not keys:
                return 0
                
            return self.client.delete(*keys)
        except Exception as e:
            logger.exception(f"Error invalidating conversation: {str(e)}")
            return 0

# Global cache instance
cache = RedisCache() 