"""Webhook handler for external integrations using Quart with OpenAPI documentation."""
from typing import Dict, Any, Callable, Optional
from quart import Quart, request, jsonify
from quart_openapi import Pint, Resource
from dataclasses import dataclass
import logging
import hmac
import hashlib


@dataclass
class WebhookRequest:
    """Webhook request data model."""
    service: str
    data: Dict[str, Any]


@dataclass
class WebhookResponse:
    """Webhook response data model."""
    status: str
    service: str
    message: Optional[str] = None


class WebhookHandler:
    """
    Handle incoming webhooks from external services with OpenAPI documentation.
    
    Provides endpoints for receiving webhooks and routing them to appropriate handlers.
    Includes automatic OpenAPI spec generation at /docs endpoint.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
        """
        self.app = Pint(__name__, title="Mira Webhook API", version="1.0.0")
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Quart routes for webhooks with OpenAPI documentation."""
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        async def handle_webhook(service: str):
            """
            Handle incoming webhook from external service.
            
            Args:
                service: Service name (github, trello, jira, n8n, etc.)
            
            Request Body:
                WebhookRequest: The webhook payload
            
            Returns:
                WebhookResponse: Processing result
            
            Responses:
                200: Webhook processed successfully
                403: Invalid signature
                404: Unknown service
                500: Internal server error
            """
            try:
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    body = await request.get_data()
                    if not self._verify_signature(body, request.headers['X-Hub-Signature-256']):
                        return jsonify({'error': 'Invalid signature', 'status': 'error'}), 403
                
                data = await request.get_json() or {}
                self.logger.info(f"Received webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = await self.handlers[service](data)
                    return jsonify({
                        'status': 'processed',
                        'service': service,
                        'data': response
                    }), 200
                else:
                    return jsonify({
                        'error': 'Unknown service',
                        'status': 'error',
                        'service': service
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling webhook: {e}")
                return jsonify({
                    'error': 'Internal server error',
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        async def health_check():
            """
            Health check endpoint.
            
            Returns:
                dict: Service health status
            
            Responses:
                200: Service is healthy
            """
            return jsonify({
                'status': 'healthy',
                'service': 'mira-webhook',
                'handlers': list(self.handlers.keys())
            }), 200
        
        @self.app.route('/api/services', methods=['GET'])
        async def list_services():
            """
            List all registered webhook services.
            
            Returns:
                dict: List of registered services
            
            Responses:
                200: Successfully retrieved service list
            """
            return jsonify({
                'services': list(self.handlers.keys()),
                'count': len(self.handlers)
            }), 200
                
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
            handler: Handler function (can be async or sync)
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
        self.logger.info(f"OpenAPI docs available at http://{host}:{port}/docs")
        self.app.run(host=host, port=port)
