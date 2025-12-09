"""Authenticated webhook handler with structured logging and RBAC."""
import json
import logging
import hmac
import hashlib
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from flask import Flask, request, jsonify, g, Response
from mira.core.api_key_manager import get_api_key_manager
from mira.core.middleware import require_api_key, require_role


# Configure structured logging
class StructuredLogger:
    """Logger with structured JSON output."""
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self._setup_json_formatter()
    
    def _setup_json_formatter(self) -> None:
        """Set up JSON formatter for structured logging."""
        # Note: In production, use python-json-logger or similar
        # For now, we'll format logs as JSON-like strings
        pass
    
    def _format_message(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """
        Format log message as JSON.
        
        Args:
            level: Log level
            message: Log message
            extra: Extra fields
            
        Returns:
            JSON-formatted log string
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'logger': self.logger.name
        }
        
        if extra:
            log_entry.update(extra)
        
        return json.dumps(log_entry)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self.logger.info(self._format_message('INFO', message, extra))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message('WARNING', message, extra))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self.logger.error(self._format_message('ERROR', message, extra))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message('DEBUG', message, extra))


class AuthenticatedWebhookHandler:
    """
    Handle incoming webhooks with authentication and RBAC.
    
    Provides endpoints for receiving webhooks with role-based access control:
    - Viewer: Can read webhook data
    - Operator: Can execute webhooks
    - Admin: Full access to all webhooks
    """
    
    def __init__(self, secret_key: Optional[str] = None, app: Optional[Flask] = None):
        """
        Initialize the authenticated webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
            app: Optional Flask app instance (if None, creates new app)
        """
        self.app = app or Flask(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = StructuredLogger("mira.authenticated_webhook")
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check() -> tuple[Response, int]:
            """
            Health check endpoint.
            
            Returns:
                Health status information
            """
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'authenticated-webhook-handler',
                'version': '1.0.0',
                'handlers': list(self.handlers.keys())
            }
            
            self.logger.info('Health check requested', extra=health_status)
            return jsonify(health_status), 200
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        @require_api_key
        async def handle_webhook(service: str) -> tuple[Response, int]:
            """
            Handle incoming webhook with authentication and RBAC.
            
            Args:
                service: Service name (e.g., 'github', 'trello')
                
            Returns:
                Response tuple with JSON data and status code
            """
            try:
                # Get API key from context (set by require_api_key decorator)
                api_key = g.api_key
                role = api_key.role
                
                self.logger.info(
                    f"Webhook received from {service}",
                    extra={
                        'service': service,
                        'role': role,
                        'key_id': api_key.key_id,
                        'owner': api_key.owner,
                        'method': request.method,
                        'remote_addr': request.remote_addr
                    }
                )
                
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                        self.logger.warning(
                            'Invalid webhook signature',
                            extra={'service': service, 'role': role}
                        )
                        return jsonify({'error': 'Invalid signature'}), 403
                
                # RBAC enforcement based on permission matrix
                if role == 'viewer':
                    # Viewers can only read webhook data, not trigger actions
                    data = request.json or {}
                    self.logger.info(
                        'Webhook read by viewer',
                        extra={
                            'service': service,
                            'role': role,
                            'data_keys': list(data.keys())
                        }
                    )
                    return jsonify({
                        'status': 'read',
                        'service': service,
                        'message': 'Webhook data received (read-only access)',
                        'data': data
                    }), 200
                
                elif role == 'operator':
                    # Operators can execute webhooks
                    data = request.json or {}
                    
                    # Route to appropriate handler
                    if service in self.handlers:
                        self.logger.info(
                            'Executing webhook handler',
                            extra={'service': service, 'role': role}
                        )
                        response = await self.handlers[service](data)
                        return jsonify(response), 200
                    else:
                        self.logger.warning(
                            'Unknown service',
                            extra={'service': service, 'role': role}
                        )
                        return jsonify({'error': 'Unknown service'}), 404
                
                elif role == 'admin':
                    # Admins have full access
                    data = request.json or {}
                    
                    # Route to appropriate handler
                    if service in self.handlers:
                        self.logger.info(
                            'Executing webhook handler (admin)',
                            extra={'service': service, 'role': role}
                        )
                        response = await self.handlers[service](data)
                        return jsonify(response), 200
                    else:
                        self.logger.warning(
                            'Unknown service (admin)',
                            extra={'service': service, 'role': role}
                        )
                        return jsonify({'error': 'Unknown service'}), 404
                
                else:
                    self.logger.error(
                        'Invalid role',
                        extra={'service': service, 'role': role}
                    )
                    return jsonify({'error': 'Invalid role'}), 403
                
            except Exception as e:
                self.logger.error(
                    f"Error handling webhook: {str(e)}",
                    extra={
                        'service': service,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
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
    
    async def register_handler(
        self,
        service: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        Register a webhook handler for a service.
        
        Args:
            service: Service name (e.g., 'github', 'trello')
            handler: Handler function
        """
        self.handlers[service] = handler
        self.logger.info(
            'Handler registered',
            extra={'service': service, 'handler': handler.__name__}
        )
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
        """
        Start the webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
        """
        self.logger.info(
            'Starting authenticated webhook server',
            extra={'host': host, 'port': port, 'debug': debug}
        )
        self.app.run(host=host, port=port, debug=debug)


async def create_webhook_handler(
    secret_key: Optional[str] = None,
    app: Optional[Flask] = None
) -> AuthenticatedWebhookHandler:
    """
    Create an authenticated webhook handler instance.
    
    Args:
        secret_key: Secret key for webhook signature verification
        app: Optional Flask app instance
        
    Returns:
        AuthenticatedWebhookHandler instance
    """
    return AuthenticatedWebhookHandler(secret_key=secret_key, app=app)
