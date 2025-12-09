"""Webhook handler for external integrations."""
from typing import Dict, Any, Callable, Optional, Set
from flask import Flask, request, jsonify
import logging
import hmac
import hashlib
import secrets
import os


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
        self.operator_keys: Set[str] = set()
        self.logger = logging.getLogger("mira.webhook")
        self._load_operator_keys()
        self._setup_routes()
        
    def _load_operator_keys(self):
        """Load operator keys from environment or file."""
        # Load from environment variable
        env_keys = os.getenv('OPERATOR_KEYS', '')
        if env_keys:
            for key in env_keys.split(','):
                key = key.strip()
                if key:
                    self.operator_keys.add(key)
        
        # Load from file if exists - use configurable path
        keys_file = os.getenv('OPERATOR_KEYS_FILE', 
                             os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'operator_keys.txt'))
        if os.path.exists(keys_file):
            with open(keys_file, 'r') as f:
                for line in f:
                    key = line.strip()
                    if key and not key.startswith('#'):
                        self.operator_keys.add(key)
        
        self.logger.info(f"Loaded {len(self.operator_keys)} operator keys")
    
    def generate_operator_key(self) -> str:
        """
        Generate a new operator key for webhook authentication.
        
        Returns:
            Generated operator key
        """
        key = f"op_{secrets.token_hex(16)}"
        self.operator_keys.add(key)
        
        # Save to file - use configurable path
        keys_file = os.getenv('OPERATOR_KEYS_FILE',
                             os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'operator_keys.txt'))
        os.makedirs(os.path.dirname(keys_file), exist_ok=True)
        with open(keys_file, 'a') as f:
            f.write(f"{key}\n")
        
        self.logger.info(f"Generated new operator key: {key}")
        return key
    
    def _verify_operator_key(self, key: str) -> bool:
        """
        Verify operator key.
        
        Args:
            key: Operator key from request header
            
        Returns:
            True if key is valid
        """
        return key in self.operator_keys
    
    def _setup_routes(self):
        """Set up Flask routes for webhooks."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({'status': 'healthy', 'service': 'mira-webhook'}), 200
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        def handle_webhook(service: str):
            """Handle incoming webhook."""
            try:
                # Verify operator key if provided
                operator_key = request.headers.get('X-Operator-Key')
                if operator_key:
                    if not self._verify_operator_key(operator_key):
                        self.logger.warning(f"Invalid operator key for {service}")
                        return jsonify({'error': 'Invalid operator key'}), 403
                
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
