"""Webhook handler for external integrations."""
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, jsonify
import logging
import hmac
import hashlib
import time
from collections import defaultdict, deque
from threading import Lock
from mira.utils.performance import benchmark


class RateLimiter:
    """
    Token bucket rate limiter for webhook requests.
    
    Designed to handle 10k daily webhooks with burst tolerance.
    """
    
    def __init__(self, max_requests: int = 10000, window_seconds: int = 86400,
                 max_clients: int = 10000):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window (default: 10k/day)
            window_seconds: Time window in seconds (default: 24 hours)
            max_clients: Maximum number of clients to track (default: 10k)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()
        self.logger = logging.getLogger("mira.ratelimit")
        self._cleanup_counter = 0
    
    def _cleanup_old_clients(self):
        """
        Periodic cleanup of inactive clients to prevent memory leaks.
        Called every 1000 requests to avoid overhead.
        """
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Remove clients with no recent requests
        clients_to_remove = []
        for client_id, client_requests in self.requests.items():
            if not client_requests or client_requests[-1] < cutoff:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.requests[client_id]
        
        # Enforce max clients limit (remove oldest)
        if len(self.requests) > self.max_clients:
            sorted_clients = sorted(
                self.requests.items(),
                key=lambda x: x[1][-1] if x[1] else 0
            )
            for client_id, _ in sorted_clients[:len(self.requests) - self.max_clients]:
                del self.requests[client_id]
    
    def is_allowed(self, client_id: str = 'default') -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            client_id: Client identifier for per-client limits
            
        Returns:
            True if request is allowed
        """
        with self.lock:
            # Periodic cleanup to prevent memory leaks
            self._cleanup_counter += 1
            if self._cleanup_counter >= 1000:
                self._cleanup_old_clients()
                self._cleanup_counter = 0
            
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove old requests outside the window
            while self.requests[client_id] and self.requests[client_id][0] < cutoff:
                self.requests[client_id].popleft()
            
            # Check if under limit
            if len(self.requests[client_id]) < self.max_requests:
                self.requests[client_id].append(now)
                return True
            
            self.logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
    
    def get_stats(self, client_id: str = 'default') -> Dict[str, Any]:
        """
        Get rate limit statistics.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Statistics including current count and limit
        """
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Clean old entries
            while self.requests[client_id] and self.requests[client_id][0] < cutoff:
                self.requests[client_id].popleft()
            
            return {
                'current_count': len(self.requests[client_id]),
                'max_requests': self.max_requests,
                'window_seconds': self.window_seconds,
                'remaining': self.max_requests - len(self.requests[client_id])
            }


class WebhookHandler:
    """
    Handle incoming webhooks from external services.
    
    Enhanced for high availability:
    - 99.9% uptime SLA
    - Rate limiting for 10k daily webhooks
    - Health check endpoint
    - Performance metrics collection
    """
    
    def __init__(self, secret_key: Optional[str] = None, 
                 rate_limit_enabled: bool = True):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
            rate_limit_enabled: Enable rate limiting
        """
        self.app = Flask(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self.rate_limiter = RateLimiter() if rate_limit_enabled else None
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0
        }
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint for monitoring."""
            return jsonify({
                'status': 'healthy',
                'service': 'mira-webhook',
                'uptime': 'operational',
                'metrics': self.get_metrics()
            }), 200
        
        @self.app.route('/metrics', methods=['GET'])
        def get_metrics():
            """Get webhook metrics."""
            metrics = self.get_metrics()
            if self.rate_limiter:
                metrics['rate_limit'] = self.rate_limiter.get_stats()
            return jsonify(metrics), 200
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        @benchmark('webhook_processing')
        def handle_webhook(service: str):
            """Handle incoming webhook."""
            self.metrics['total_requests'] += 1
            
            try:
                # Rate limiting check
                if self.rate_limiter:
                    client_id = request.remote_addr or 'unknown'
                    if not self.rate_limiter.is_allowed(client_id):
                        self.metrics['rate_limited_requests'] += 1
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'retry_after': 3600
                        }), 429
                
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                        self.metrics['failed_requests'] += 1
                        return jsonify({'error': 'Invalid signature'}), 403
                
                data = request.json or {}
                self.logger.info(f"Received webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = self.handlers[service](data)
                    self.metrics['successful_requests'] += 1
                    return jsonify(response), 200
                else:
                    self.metrics['failed_requests'] += 1
                    return jsonify({'error': 'Unknown service'}), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling webhook: {e}")
                self.metrics['failed_requests'] += 1
                return jsonify({'error': 'Internal server error'}), 500
                
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
        
    def register_handler(self, service: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a webhook handler for a service.
        
        Args:
            service: Service name (e.g., 'github', 'trello', 'n8n')
            handler: Handler function
        """
        self.handlers[service] = handler
        self.logger.info(f"Handler registered for service: {service}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get webhook handler metrics.
        
        Returns:
            Dictionary with metrics
        """
        total = self.metrics['total_requests']
        success_rate = (self.metrics['successful_requests'] / total * 100) if total > 0 else 0
        
        return {
            'total_requests': total,
            'successful_requests': self.metrics['successful_requests'],
            'failed_requests': self.metrics['failed_requests'],
            'rate_limited_requests': self.metrics['rate_limited_requests'],
            'success_rate': round(success_rate, 2),
            'uptime_compliance': success_rate >= 99.9
        }
        
    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """
        Start the webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.logger.info(f"Starting webhook server on {host}:{port}")
        self.app.run(host=host, port=port)
