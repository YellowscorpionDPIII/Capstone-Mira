"""Authenticated webhook handler with async support using Quart."""
from typing import Dict, Any, Callable, Optional
from quart import Quart, request, jsonify
import structlog
import hmac
import hashlib
import time
from datetime import datetime
import redis.asyncio as aioredis


class AuthenticatedWebhookHandler:
    """
    Async webhook handler with authentication, Redis caching, and structured logging.
    
    Provides authenticated endpoints for receiving webhooks with key validation,
    caching, and comprehensive logging.
    """
    
    def __init__(
        self, 
        secret_key: Optional[str] = None,
        redis_url: str = "redis://localhost:6379",
        api_keys: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialize the authenticated webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
            redis_url: Redis connection URL for caching
            api_keys: Dictionary of API keys with their metadata
                     Format: {key_id: {key: str, role: str, expiry: int}}
        """
        self.app = Quart(__name__)
        self.secret_key = secret_key
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.api_keys = api_keys or {}
        self.handlers: Dict[str, Callable] = {}
        
        # Metrics for health endpoint
        self.cache_hits = 0
        self.cache_misses = 0
        self.active_keys_count = len(self.api_keys)
        
        # Setup structured logging
        self.logger = structlog.get_logger("mira.auth.webhook")
        self._setup_middleware()
        self._setup_routes()
        
    async def _init_redis(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.logger.info("redis_connected", url=self.redis_url)
    
    def _setup_middleware(self):
        """Set up structlog middleware for request logging."""
        
        @self.app.before_request
        async def log_request():
            """Log incoming requests with structured data."""
            # Get API key from header
            key_id = request.headers.get('X-API-Key-ID', 'anonymous')
            
            # Get role from validated key (will be set by authenticate)
            role = getattr(request, 'role', 'unknown')
            
            # Get client IP
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Log with structured context
            structlog.contextvars.bind_contextvars(
                key_id=key_id,
                role=role,
                client_ip=client_ip,
                timestamp=datetime.utcnow().isoformat(),
                method=request.method,
                path=request.path
            )
            
            self.logger.info(
                "request_received",
                key_id=key_id,
                role=role,
                client_ip=client_ip,
                timestamp=datetime.utcnow().isoformat()
            )
    
    def _setup_routes(self):
        """Set up Quart routes for webhooks."""
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        async def handle_webhook(service: str):
            """Handle incoming authenticated webhook."""
            try:
                # Authenticate request
                auth_result = await self._authenticate_request()
                if not auth_result['authenticated']:
                    self.logger.warning("authentication_failed", reason=auth_result['reason'])
                    return jsonify({'error': 'Authentication failed'}), 401
                
                # Store role for logging middleware
                request.role = auth_result['role']
                
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    body = await request.get_data()
                    if not self._verify_signature(body, request.headers['X-Hub-Signature-256']):
                        self.logger.warning("signature_verification_failed")
                        return jsonify({'error': 'Invalid signature'}), 403
                
                data = await request.json or {}
                self.logger.info("webhook_received", service=service, key_id=auth_result['key_id'])
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = await self.handlers[service](data)
                    return jsonify(response), 200
                else:
                    self.logger.warning("unknown_service", service=service)
                    return jsonify({'error': 'Unknown service'}), 404
                    
            except Exception as e:
                self.logger.error("webhook_error", error=str(e), exc_info=True)
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/healthz', methods=['GET'])
        async def health_check():
            """Health check endpoint with metrics."""
            try:
                # Calculate cache hit rate
                total_requests = self.cache_hits + self.cache_misses
                cache_hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0
                
                health_data = {
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'metrics': {
                        'active_keys_count': self.active_keys_count,
                        'cache_hit_rate': round(cache_hit_rate, 2),
                        'cache_hits': self.cache_hits,
                        'cache_misses': self.cache_misses
                    }
                }
                
                self.logger.info("health_check", **health_data['metrics'])
                return jsonify(health_data), 200
                
            except Exception as e:
                self.logger.error("health_check_error", error=str(e))
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e)
                }), 500
    
    async def _authenticate_request(self) -> Dict[str, Any]:
        """
        Authenticate incoming request using API key with Redis caching.
        
        Returns:
            Dictionary with authentication result
        """
        key_id = request.headers.get('X-API-Key-ID')
        api_key = request.headers.get('X-API-Key')
        
        if not key_id or not api_key:
            return {
                'authenticated': False,
                'reason': 'Missing API key or key ID'
            }
        
        # Initialize Redis if needed
        await self._init_redis()
        
        # Try to get from cache first
        cache_key = f"api_key:{key_id}"
        cached_data = None
        
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    self.cache_hits += 1
                    self.logger.debug("cache_hit", key_id=key_id)
                else:
                    self.cache_misses += 1
                    self.logger.debug("cache_miss", key_id=key_id)
            except Exception as e:
                self.logger.warning("redis_error", error=str(e))
                self.cache_misses += 1
        
        # Validate key
        if cached_data:
            # Use cached validation result
            import json
            key_data = json.loads(cached_data)
        elif key_id in self.api_keys:
            key_data = self.api_keys[key_id]
            
            # Cache the key data with TTL
            if self.redis_client and 'expiry' in key_data:
                try:
                    import json
                    ttl = key_data['expiry'] - int(time.time())
                    if ttl > 0:
                        await self.redis_client.setex(
                            cache_key,
                            ttl,
                            json.dumps(key_data)
                        )
                        self.logger.debug("key_cached", key_id=key_id, ttl=ttl)
                except Exception as e:
                    self.logger.warning("cache_set_error", error=str(e))
        else:
            return {
                'authenticated': False,
                'reason': 'Invalid key ID'
            }
        
        # Verify the key matches
        if key_data.get('key') != api_key:
            return {
                'authenticated': False,
                'reason': 'Invalid API key'
            }
        
        # Check expiry
        if 'expiry' in key_data and key_data['expiry'] < int(time.time()):
            return {
                'authenticated': False,
                'reason': 'API key expired'
            }
        
        return {
            'authenticated': True,
            'key_id': key_id,
            'role': key_data.get('role', 'user')
        }
    
    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Request payload
            signature: Signature from header
            
        Returns:
            True if signature is valid
        """
        if not self.secret_key:
            return True
            
        expected = 'sha256=' + hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def register_handler(
        self, 
        service: str, 
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Register a webhook handler for a service.
        
        Args:
            service: Service name (e.g., 'github', 'trello')
            handler: Async handler function
        """
        self.handlers[service] = handler
        self.logger.info("handler_registered", service=service)
    
    def add_api_key(self, key_id: str, key: str, role: str = "user", expiry: Optional[int] = None):
        """
        Add an API key for authentication.
        
        Args:
            key_id: Unique identifier for the key
            key: The actual API key value
            role: Role associated with this key
            expiry: Unix timestamp when key expires (optional)
        """
        self.api_keys[key_id] = {
            'key': key,
            'role': role,
            'expiry': expiry
        }
        self.active_keys_count = len(self.api_keys)
        self.logger.info("api_key_added", key_id=key_id, role=role)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("redis_connection_closed")
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, **kwargs):
        """
        Start the webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            **kwargs: Additional arguments passed to Quart.run()
        """
        self.logger.info("starting_webhook_server", host=host, port=port)
        self.app.run(host=host, port=port, **kwargs)
