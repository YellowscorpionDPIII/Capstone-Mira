"""Webhook handler for external integrations."""
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, jsonify
from contextlib import nullcontext
import logging
import hmac
import hashlib


class WebhookHandler:
    """
    Handle incoming webhooks from external services.
    
    Provides endpoints for receiving webhooks and routing them to appropriate handlers.
    Enhanced with security features, metrics, and health checks.
    """
    
    def __init__(
        self, 
        secret_key: Optional[str] = None,
        webhook_security=None,
        metrics_collector=None,
        health_check=None,
        maintenance_mode: bool = False
    ):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
            webhook_security: Optional WebhookSecurity instance
            metrics_collector: Optional MetricsCollector instance
            health_check: Optional HealthCheck instance
            maintenance_mode: Whether maintenance mode is enabled
        """
        self.app = Flask(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self.webhook_security = webhook_security
        self.metrics = metrics_collector
        self.health_check = health_check
        self.maintenance_mode = maintenance_mode
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint (liveness probe)."""
            if self.health_check:
                result = self.health_check.check_health()
                return jsonify(result), 200
            return jsonify({'status': 'healthy'}), 200
        
        @self.app.route('/ready', methods=['GET'])
        def ready():
            """Readiness check endpoint with dependency checks."""
            if self.health_check:
                result = self.health_check.check_ready()
                status_code = 200 if result['status'] != 'unhealthy' else 503
                return jsonify(result), status_code
            return jsonify({'status': 'ready'}), 200
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        def handle_webhook(service: str):
            """Handle incoming webhook."""
            if self.metrics:
                self.metrics.increment('webhook.requests', tags={'service': service})
            
            try:
                # Check maintenance mode
                if self.maintenance_mode:
                    if self.metrics:
                        self.metrics.increment('webhook.maintenance_rejected', tags={'service': service})
                    return jsonify({
                        'error': 'Service is in maintenance mode',
                        'status': 'maintenance'
                    }), 503
                
                # Get client IP
                client_ip = request.remote_addr
                
                # Enhanced security checks
                if self.webhook_security:
                    # Get service secret from headers or query params
                    service_secret = request.headers.get('X-Service-Secret')
                    
                    # Authenticate webhook
                    is_auth, reason = self.webhook_security.authenticate_webhook(
                        service, client_ip, service_secret
                    )
                    
                    if not is_auth:
                        if self.metrics:
                            self.metrics.increment(
                                'webhook.auth_failed',
                                tags={'service': service, 'reason': reason}
                            )
                        return jsonify({'error': f'Authentication failed: {reason}'}), 403
                
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    with self.metrics.timer('webhook.signature_verification', tags={'service': service}) if self.metrics else nullcontext():
                        if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                            if self.metrics:
                                self.metrics.increment('webhook.signature_invalid', tags={'service': service})
                            return jsonify({'error': 'Invalid signature'}), 403
                
                data = request.json or {}
                self.logger.info(f"Received webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    with self.metrics.timer('webhook.handler_duration', tags={'service': service}) if self.metrics else nullcontext():
                        response = self.handlers[service](data)
                    
                    if self.metrics:
                        self.metrics.increment('webhook.success', tags={'service': service})
                    return jsonify(response), 200
                else:
                    if self.metrics:
                        self.metrics.increment('webhook.unknown_service', tags={'service': service})
                    return jsonify({'error': 'Unknown service'}), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling webhook: {e}")
                if self.metrics:
                    self.metrics.increment('webhook.errors', tags={'service': service})
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
            service: Service name (e.g., 'github', 'trello')
            handler: Handler function
        """
        self.handlers[service] = handler
        self.logger.info(f"Handler registered for service: {service}")
        
    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """
        Start the webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.logger.info(f"Starting webhook server on {host}:{port}")
        self.app.run(host=host, port=port)
