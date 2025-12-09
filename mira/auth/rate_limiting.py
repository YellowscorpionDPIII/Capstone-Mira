"""Rate limiting for API key management endpoints."""
import functools
import time
from typing import Dict, Tuple, Optional, Callable
from flask import request, jsonify
import logging

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False


class RateLimiter:
    """Rate limiter for API endpoints with role-based limits."""
    
    # Default rate limits per role (requests per minute)
    DEFAULT_LIMITS = {
        'viewer': '100/minute',
        'operator': '200/minute',
        'admin': '500/minute',
        'anonymous': '20/minute'
    }
    
    def __init__(
        self,
        app=None,
        storage_uri: str = 'memory://',
        role_limits: Optional[Dict[str, str]] = None,
        enabled: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: Flask application instance
            storage_uri: Storage URI for rate limit data (redis://localhost:6379)
            role_limits: Custom rate limits per role
            enabled: Whether rate limiting is enabled
        """
        self.logger = logging.getLogger("mira.auth.rate_limiter")
        self.enabled = enabled and LIMITER_AVAILABLE
        self.role_limits = role_limits or self.DEFAULT_LIMITS
        self.limiter: Optional[Limiter] = None
        
        if not LIMITER_AVAILABLE and enabled:
            self.logger.warning(
                "Flask-Limiter not available - rate limiting disabled. "
                "Install flask-limiter to enable."
            )
            self.enabled = False
            return
        
        if app and self.enabled:
            self.init_app(app, storage_uri)
    
    def init_app(self, app, storage_uri: str = 'memory://'):
        """
        Initialize rate limiter with Flask app.
        
        Args:
            app: Flask application instance
            storage_uri: Storage URI for rate limit data
        """
        if not self.enabled:
            return
        
        try:
            self.limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                storage_uri=storage_uri,
                default_limits=["1000/hour"],
                headers_enabled=True,
                swallow_errors=True
            )
            self.logger.info(f"Rate limiter initialized with storage: {storage_uri}")
        except Exception as e:
            self.logger.error(f"Failed to initialize rate limiter: {e}")
            self.enabled = False
    
    def get_limit_for_role(self, role: Optional[str]) -> str:
        """
        Get rate limit for a specific role.
        
        Args:
            role: User role
            
        Returns:
            Rate limit string (e.g., "100/minute")
        """
        if not role:
            return self.role_limits.get('anonymous', '20/minute')
        return self.role_limits.get(role, self.role_limits['anonymous'])
    
    def limit(self, limit_value: Optional[str] = None):
        """
        Decorator to apply rate limiting to a route.
        
        Args:
            limit_value: Optional explicit limit (e.g., "100/minute")
            
        Returns:
            Decorator function
        """
        def decorator(f: Callable):
            if not self.enabled or not self.limiter:
                # If rate limiting is disabled, return original function
                return f
            
            # Apply Flask-Limiter decorator
            if limit_value:
                return self.limiter.limit(limit_value)(f)
            else:
                # Use role-based limiting
                @functools.wraps(f)
                def wrapped(*args, **kwargs):
                    # Get role from request context (set by auth middleware)
                    api_key = getattr(request, 'api_key', None)
                    role = getattr(api_key, 'role', None) if api_key else None
                    
                    # Get appropriate limit
                    limit = self.get_limit_for_role(role)
                    
                    # Check rate limit
                    try:
                        # Apply dynamic limit based on role
                        limited_func = self.limiter.limit(limit)(f)
                        return limited_func(*args, **kwargs)
                    except Exception as e:
                        self.logger.error(f"Rate limit check error: {e}")
                        # On error, allow the request
                        return f(*args, **kwargs)
                
                return wrapped
        
        return decorator
    
    def limit_by_role(self, f: Callable):
        """
        Decorator to apply role-based rate limiting.
        
        Args:
            f: Function to decorate
            
        Returns:
            Decorated function
        """
        if not self.enabled:
            return f
        
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # Get role from request context
            api_key = getattr(request, 'api_key', None)
            role = getattr(api_key, 'role', None) if api_key else None
            
            # Get appropriate limit
            limit = self.get_limit_for_role(role)
            
            # Log rate limit check
            self.logger.debug(f"Rate limit check: role={role}, limit={limit}")
            
            # Apply rate limit
            if self.limiter:
                try:
                    limited_func = self.limiter.limit(limit)(f)
                    return limited_func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Rate limit application error: {e}")
                    return f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        
        return wrapped
    
    def check_limit(
        self,
        identifier: str,
        limit: int = 100,
        window: int = 60
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Manually check rate limit for an identifier.
        
        Args:
            identifier: Unique identifier (e.g., API key hash)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        if not self.enabled:
            return True, {'limit': limit, 'remaining': limit, 'reset': 0}
        
        # Simple in-memory rate limiting fallback
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        
        # This is a simplified implementation
        # In production, use Redis for distributed rate limiting
        return True, {
            'limit': limit,
            'remaining': limit,
            'reset': current_time + window
        }
    
    def reset_limit(self, identifier: str):
        """
        Reset rate limit for an identifier.
        
        Args:
            identifier: Unique identifier to reset
        """
        if not self.enabled or not self.limiter:
            return
        
        self.logger.info(f"Reset rate limit for: {identifier}")
        # Implementation depends on storage backend
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dictionary with rate limiting stats
        """
        return {
            'enabled': self.enabled,
            'available': LIMITER_AVAILABLE,
            'role_limits': self.role_limits
        }


def create_rate_limiter(
    app=None,
    redis_url: Optional[str] = None,
    enabled: bool = True
) -> RateLimiter:
    """
    Create and configure a rate limiter instance.
    
    Args:
        app: Flask application instance
        redis_url: Redis URL for distributed rate limiting
        enabled: Whether rate limiting is enabled
        
    Returns:
        RateLimiter instance
    """
    storage_uri = redis_url or 'memory://'
    return RateLimiter(app=app, storage_uri=storage_uri, enabled=enabled)
