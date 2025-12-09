"""Redis cache layer for API key management."""
import json
import logging
from typing import Optional, List, Dict, Any
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception
    RedisConnectionError = Exception

class RedisCache:
    """Redis-based cache for API keys with fallback support."""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl: int = 3600,
        enabled: bool = True
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional password for Redis
            ttl: Time-to-live for cached items in seconds
            enabled: Whether caching is enabled
        """
        self.logger = logging.getLogger("mira.auth.redis_cache")
        self.enabled = enabled and REDIS_AVAILABLE
        self.ttl = ttl
        self.client: Optional['redis.Redis'] = None
        
        if not REDIS_AVAILABLE and enabled:
            self.logger.warning("Redis not available - caching disabled. Install redis-py to enable.")
            self.enabled = False
            return
        
        if self.enabled:
            try:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self.client.ping()
                self.logger.info(f"Redis cache connected to {host}:{port}/{db}")
            except (RedisConnectionError, RedisError) as e:
                self.logger.error(f"Failed to connect to Redis: {e}. Caching disabled.")
                self.enabled = False
                self.client = None
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a Redis key with namespace."""
        return f"mira:apikey:{prefix}:{identifier}"
    
    def get(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get API key by hash from cache.
        
        Args:
            key_hash: Hash of the API key
            
        Returns:
            API key data if found, None otherwise
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            redis_key = self._make_key("hash", key_hash)
            data = self.client.get(redis_key)
            if data:
                self.logger.debug(f"Cache hit for key hash: {key_hash[:8]}...")
                return json.loads(data)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            self.logger.warning(f"Redis get error: {e}")
            return None
    
    def get_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get API key by ID from cache.
        
        Args:
            key_id: ID of the API key
            
        Returns:
            API key data if found, None otherwise
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            redis_key = self._make_key("id", key_id)
            data = self.client.get(redis_key)
            if data:
                self.logger.debug(f"Cache hit for key ID: {key_id}")
                return json.loads(data)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            self.logger.warning(f"Redis get_by_id error: {e}")
            return None
    
    def set(self, key_hash: str, key_id: str, api_key_data: Dict[str, Any]) -> bool:
        """
        Store API key in cache with both hash and ID indexes.
        
        Args:
            key_hash: Hash of the API key
            key_id: ID of the API key
            api_key_data: API key data to cache
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            data_str = json.dumps(api_key_data)
            
            # Store by hash
            hash_key = self._make_key("hash", key_hash)
            self.client.setex(hash_key, self.ttl, data_str)
            
            # Store by ID for lookups
            id_key = self._make_key("id", key_id)
            self.client.setex(id_key, self.ttl, data_str)
            
            self.logger.debug(f"Cached key: {key_id}")
            return True
        except (RedisError, json.JSONEncodeError, TypeError) as e:
            self.logger.warning(f"Redis set error: {e}")
            return False
    
    def delete(self, key_hash: str, key_id: str) -> bool:
        """
        Remove API key from cache.
        
        Args:
            key_hash: Hash of the API key
            key_id: ID of the API key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            hash_key = self._make_key("hash", key_hash)
            id_key = self._make_key("id", key_id)
            
            self.client.delete(hash_key, id_key)
            self.logger.debug(f"Invalidated cache for key: {key_id}")
            return True
        except RedisError as e:
            self.logger.warning(f"Redis delete error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """
        Clear all API key cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            pattern = self._make_key("*", "*")
            keys = list(self.client.scan_iter(pattern))
            if keys:
                self.client.delete(*keys)
                self.logger.info(f"Cleared {len(keys)} cached API keys")
            return True
        except RedisError as e:
            self.logger.error(f"Redis clear_all error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self.client:
            return {
                'enabled': False,
                'available': REDIS_AVAILABLE,
                'keys': 0
            }
        
        try:
            info = self.client.info('stats')
            pattern = self._make_key("*", "*")
            key_count = len(list(self.client.scan_iter(pattern, count=1000)))
            
            return {
                'enabled': True,
                'available': True,
                'keys': key_count,
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except RedisError as e:
            self.logger.error(f"Redis get_stats error: {e}")
            return {
                'enabled': True,
                'available': False,
                'error': str(e)
            }
    
    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    def healthcheck(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            return self.client.ping()
        except RedisError:
            return False
