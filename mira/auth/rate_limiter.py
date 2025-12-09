"""Redis-backed rate limiter for API endpoints."""
from typing import Optional
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import logging

logger = logging.getLogger(__name__)

# Global limiter instance
_limiter: Optional[Limiter] = None


def get_limiter(
    app=None,
    redis_url: str = "redis://localhost:6379/0",
    default_limits: Optional[list] = None
) -> Limiter:
    """
    Get or create the rate limiter instance.
    
    Args:
        app: Flask application instance
        redis_url: Redis connection URL
        default_limits: Default rate limits to apply globally
        
    Returns:
        Limiter instance
    """
    global _limiter
    
    if _limiter is None:
        # Try to connect to Redis, fall back to memory storage if unavailable
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            storage_uri = redis_url
            logger.info("Using Redis for rate limiting storage")
        except (redis.ConnectionError, redis.RedisError) as e:
            logger.warning(f"Redis unavailable, falling back to memory storage: {e}")
            storage_uri = "memory://"
        
        _limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=storage_uri,
            default_limits=default_limits or [],
            strategy="fixed-window"
        )
        
        if app is not None:
            _limiter.init_app(app)
            
    return _limiter


def reset_limiter():
    """Reset the global limiter instance (useful for testing)."""
    global _limiter
    _limiter = None
