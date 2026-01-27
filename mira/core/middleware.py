"""Async Flask middleware for request handling and security."""
import logging
import time
from typing import Callable, Optional, Dict, Any
from functools import wraps
from flask import Flask, request, jsonify, Response, g
from werkzeug.exceptions import HTTPException
import traceback


logger = logging.getLogger("mira.middleware")


class RequestLoggingMiddleware:
    """Middleware for logging all requests."""
    
    def __init__(self, app: Flask):
        """
        Initialize request logging middleware.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up request/response handlers."""
        
        @self.app.before_request
        def before_request() -> None:
            """Log request start and store start time."""
            g.start_time = time.time()
            logger.info(
                f"Request started: {request.method} {request.path}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.user_agent.string if request.user_agent else None
                }
            )
        
        @self.app.after_request
        def after_request(response: Response) -> Response:
            """Log request completion with timing."""
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                logger.info(
                    f"Request completed: {request.method} {request.path} - "
                    f"Status: {response.status_code} - Duration: {duration:.3f}s",
                    extra={
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration': duration
                    }
                )
            return response


class ErrorHandlingMiddleware:
    """Middleware for consistent error handling."""
    
    def __init__(self, app: Flask, debug: bool = False):
        """
        Initialize error handling middleware.
        
        Args:
            app: Flask application instance
            debug: Whether to include debug information in error responses
        """
        self.app = app
        self.debug = debug
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up error handlers."""
        
        @self.app.errorhandler(HTTPException)
        def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
            """Handle HTTP exceptions."""
            response = {
                'error': error.name,
                'message': error.description,
                'status': error.code
            }
            
            logger.warning(
                f"HTTP exception: {error.code} - {error.description}",
                extra={'status_code': error.code, 'path': request.path}
            )
            
            return jsonify(response), error.code or 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(error: Exception) -> tuple[Response, int]:
            """Handle unexpected exceptions."""
            response = {
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'status': 500
            }
            
            if self.debug:
                response['debug'] = {
                    'type': type(error).__name__,
                    'message': str(error),
                    'traceback': traceback.format_exc()
                }
            
            logger.error(
                f"Unexpected exception: {type(error).__name__} - {str(error)}",
                extra={'path': request.path},
                exc_info=True
            )
            
            return jsonify(response), 500


class CORSMiddleware:
    """Middleware for handling Cross-Origin Resource Sharing (CORS)."""
    
    def __init__(
        self,
        app: Flask,
        allowed_origins: Optional[list[str]] = None,
        allowed_methods: Optional[list[str]] = None,
        allowed_headers: Optional[list[str]] = None,
        max_age: int = 3600
    ):
        """
        Initialize CORS middleware.
        
        Args:
            app: Flask application instance
            allowed_origins: List of allowed origins (default: ['*'])
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed headers
            max_age: Max age for preflight requests in seconds
        """
        self.app = app
        self.allowed_origins = allowed_origins or ['*']
        self.allowed_methods = allowed_methods or ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        self.allowed_headers = allowed_headers or ['Content-Type', 'Authorization', 'X-API-Key']
        self.max_age = max_age
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up CORS headers."""
        
        @self.app.after_request
        def add_cors_headers(response: Response) -> Response:
            """Add CORS headers to response."""
            origin = request.headers.get('Origin')
            
            # Check if origin is allowed
            if origin and (
                '*' in self.allowed_origins or
                origin in self.allowed_origins
            ):
                response.headers['Access-Control-Allow-Origin'] = origin
            elif '*' in self.allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = '*'
            
            response.headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response.headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
            response.headers['Access-Control-Max-Age'] = str(self.max_age)
            
            return response
        
        @self.app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
        @self.app.route('/<path:path>', methods=['OPTIONS'])
        def handle_options(path: str) -> Response:
            """Handle OPTIONS preflight requests."""
            return jsonify({'status': 'ok'}), 200


class RateLimitMiddleware:
    """Middleware for global rate limiting."""
    
    def __init__(
        self,
        app: Flask,
        default_limit: int = 100,
        window_seconds: int = 60
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: Flask application instance
            default_limit: Default request limit per window
            window_seconds: Time window in seconds
        """
        self.app = app
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.request_history: Dict[str, list[float]] = {}
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up rate limiting."""
        
        @self.app.before_request
        def check_rate_limit() -> Optional[tuple[Response, int]]:
            """Check rate limit for incoming request."""
            # Skip rate limiting for OPTIONS requests
            if request.method == 'OPTIONS':
                return None
            
            # Use IP address as identifier
            client_id = request.remote_addr or 'unknown'
            current_time = time.time()
            
            # Initialize history for new clients
            if client_id not in self.request_history:
                self.request_history[client_id] = []
            
            # Clean old requests
            cutoff = current_time - self.window_seconds
            self.request_history[client_id] = [
                req for req in self.request_history[client_id]
                if req > cutoff
            ]
            
            # Check limit
            if len(self.request_history[client_id]) >= self.default_limit:
                logger.warning(
                    f"Rate limit exceeded for {client_id}",
                    extra={'client_id': client_id, 'limit': self.default_limit}
                )
                return jsonify({
                    'error': 'Too Many Requests',
                    'message': f'Rate limit exceeded: {self.default_limit} requests per {self.window_seconds} seconds'
                }), 429
            
            # Record request
            self.request_history[client_id].append(current_time)
            return None


class SecurityHeadersMiddleware:
    """Middleware for adding security headers."""
    
    def __init__(self, app: Flask):
        """
        Initialize security headers middleware.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up security headers."""
        
        @self.app.after_request
        def add_security_headers(response: Response) -> Response:
            """Add security headers to response."""
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # Enable XSS protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Strict transport security (HTTPS only)
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Content Security Policy
            response.headers['Content-Security-Policy'] = "default-src 'self'"
            
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response


def setup_middleware(
    app: Flask,
    enable_logging: bool = True,
    enable_error_handling: bool = True,
    enable_cors: bool = True,
    enable_rate_limiting: bool = True,
    enable_security_headers: bool = True,
    cors_origins: Optional[list[str]] = None,
    rate_limit: int = 100,
    rate_window: int = 60,
    debug: bool = False
) -> None:
    """
    Set up all middleware for a Flask application.
    
    Args:
        app: Flask application instance
        enable_logging: Enable request logging middleware
        enable_error_handling: Enable error handling middleware
        enable_cors: Enable CORS middleware
        enable_rate_limiting: Enable rate limiting middleware
        enable_security_headers: Enable security headers middleware
        cors_origins: List of allowed CORS origins
        rate_limit: Request limit for rate limiting
        rate_window: Time window for rate limiting in seconds
        debug: Enable debug mode for error responses
    """
    if enable_logging:
        RequestLoggingMiddleware(app)
        logger.info("Request logging middleware enabled")
    
    if enable_error_handling:
        ErrorHandlingMiddleware(app, debug=debug)
        logger.info("Error handling middleware enabled")
    
    if enable_cors:
        CORSMiddleware(app, allowed_origins=cors_origins)
        logger.info(f"CORS middleware enabled with origins: {cors_origins or ['*']}")
    
    if enable_rate_limiting:
        RateLimitMiddleware(app, default_limit=rate_limit, window_seconds=rate_window)
        logger.info(f"Rate limiting middleware enabled: {rate_limit} requests per {rate_window}s")
    
    if enable_security_headers:
        SecurityHeadersMiddleware(app)
        logger.info("Security headers middleware enabled")


def require_api_key(func: Callable) -> Callable:
    """
    Decorator to require API key authentication.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        """Wrapper function that checks for API key."""
        from mira.core.api_key_manager import get_api_key_manager
        
        # Get API key from header
        api_key_header = request.headers.get('X-API-Key')
        if not api_key_header:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'API key required'
            }), 401
        
        # Parse key_id and key from header (format: key_id:key)
        try:
            key_id, key = api_key_header.split(':', 1)
        except ValueError:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid API key format'
            }), 401
        
        # Validate key
        manager = await get_api_key_manager()
        api_key = await manager.validate_key(key_id, key)
        
        if not api_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid or expired API key'
            }), 401
        
        # Store API key info in request context
        g.api_key = api_key
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to require specific role(s) for access.
    
    Args:
        allowed_roles: Roles that are allowed to access the endpoint
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Wrapper function that checks role."""
            if not hasattr(g, 'api_key'):
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Authentication required'
                }), 401
            
            if g.api_key.role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f"Requires one of the following roles: {', '.join(allowed_roles)}"
                }), 403
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
