"""Webhook handler for external integrations."""
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, jsonify, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging
import hmac
import hashlib


class WebhookHandler:
    """
    Handle incoming webhooks from external services.
    
    Provides endpoints for receiving webhooks and routing them to appropriate handlers.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
        """
        self.app = Flask(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        def handle_webhook(service: str):
            """Handle incoming webhook."""
            try:
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                        return jsonify({'error': 'Invalid signature'}), 403
                
                data = request.json or {}
                self.logger.info(f"Received webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = self.handlers[service](data)
                    return jsonify(response), 200
                else:
                    return jsonify({'error': 'Unknown service'}), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling webhook: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/metrics', methods=['GET'])
        def metrics():
            """Expose Prometheus metrics endpoint."""
            try:
                return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
            except Exception as e:
                self.logger.error(f"Error generating metrics: {e}")
                return jsonify({'error': 'Failed to generate metrics'}), 500
                
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
