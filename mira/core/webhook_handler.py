"""Webhook handler for external integrations."""
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, jsonify
import logging
import hmac
import hashlib
from mira.core.webhook_security import WebhookAuthenticator, WebhookSecurityConfig, AuthFailureReason
from mira.core.metrics import get_metrics_collector
from mira.core.health import get_health_registry


class WebhookHandler:
    """
    Handle incoming webhooks from external services.
    
    Provides endpoints for receiving webhooks and routing them to appropriate handlers.
    Includes enhanced security, metrics, and health checks.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        security_config: Optional[WebhookSecurityConfig] = None
    ):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification (deprecated, use security_config)
            security_config: Enhanced security configuration
        """
        self.app = Flask(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self.metrics = get_metrics_collector()
        self.health_registry = get_health_registry()
        
        # Initialize security
        if security_config:
            self.security_config = security_config
        elif secret_key:
            # Backward compatibility
            self.security_config = WebhookSecurityConfig(
                secret_key=secret_key,
                require_signature=True
            )
        else:
            self.security_config = WebhookSecurityConfig(require_signature=False)
        
        self.authenticator = WebhookAuthenticator(self.security_config)
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Lightweight health check endpoint."""
            return jsonify(self.health_registry.check_health()), 200
        
        @self.app.route('/ready', methods=['GET'])
        def readiness_check():
            """Comprehensive readiness check endpoint."""
            status = self.health_registry.check_readiness()
            status_code = 200 if status['status'] == 'ready' else 503
            return jsonify(status), status_code
        
        @self.app.route('/metrics', methods=['GET'])
        def metrics_endpoint():
            """Metrics endpoint."""
            return jsonify(self.metrics.get_all_metrics()), 200
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        def handle_webhook(service: str):
            """Handle incoming webhook."""
            # Track auth attempts
            auth_counter = self.metrics.counter(
                'mira_auth_attempts_total',
                labels={'service': service}
            )
            auth_counter.inc()
            
            # Measure webhook processing time
            with self.metrics.time('mira_webhook_duration_seconds', labels={'service': service}):
                try:
                    # Authenticate request using security pipeline
                    client_ip = request.remote_addr or 'unknown'
                    is_authenticated, failure_reason = self.authenticator.authenticate(
                        client_ip=client_ip,
                        payload=request.data,
                        signature_header=request.headers.get('X-Hub-Signature-256'),
                        secret_header=request.headers.get('X-Webhook-Secret')
                    )
                    
                    if not is_authenticated:
                        # Track failed authentication
                        fail_counter = self.metrics.counter(
                            'mira_auth_failures_total',
                            labels={'service': service, 'reason': failure_reason.value}
                        )
                        fail_counter.inc()
                        
                        error_messages = {
                            AuthFailureReason.AUTH_IP_BLOCKED: 'IP address not allowed',
                            AuthFailureReason.AUTH_SECRET_MISMATCH: 'Secret mismatch',
                            AuthFailureReason.AUTH_SIGNATURE_INVALID: 'Invalid signature'
                        }
                        
                        return jsonify({
                            'error': error_messages.get(failure_reason, 'Authentication failed'),
                            'reason': failure_reason.value
                        }), 403
                    
                    # Track successful authentication
                    success_counter = self.metrics.counter(
                        'mira_auth_success_total',
                        labels={'service': service}
                    )
                    success_counter.inc()
                    
                    data = request.json or {}
                    self.logger.info(f"Received webhook from {service}")
                    
                    # Route to appropriate handler
                    if service in self.handlers:
                        response = self.handlers[service](data)
                        
                        # Track successful processing
                        success_counter = self.metrics.counter(
                            'mira_webhook_processed_total',
                            labels={'service': service, 'status': 'success'}
                        )
                        success_counter.inc()
                        
                        return jsonify(response), 200
                    else:
                        # Track unknown service
                        error_counter = self.metrics.counter(
                            'mira_webhook_processed_total',
                            labels={'service': service, 'status': 'unknown_service'}
                        )
                        error_counter.inc()
                        
                        return jsonify({'error': 'Unknown service'}), 404
                        
                except Exception as e:
                    self.logger.error(f"Error handling webhook: {e}", exc_info=True)
                    
                    # Track errors
                    error_counter = self.metrics.counter(
                        'mira_webhook_processed_total',
                        labels={'service': service, 'status': 'error'}
                    )
                    error_counter.inc()
                    
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
