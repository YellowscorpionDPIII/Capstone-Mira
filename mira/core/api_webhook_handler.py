"""Enhanced webhook handler with API key management endpoints."""
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, jsonify
import logging
import hmac
import hashlib

from mira.core.rbac import Role, Permission, require_permission, get_rbac_manager
from mira.core.api_key_manager import get_api_key_manager


class APIWebhookHandler:
    """
    Enhanced webhook handler with API key management and RBAC.
    
    Provides endpoints for:
    - API key management (CRUD operations)
    - Webhook handling with role-based access control
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize the API webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
        """
        self.app = Flask(__name__)
        self.secret_key = secret_key
        self.webhook_handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.api_webhook")
        self.key_manager = get_api_key_manager()
        self.rbac_manager = get_rbac_manager()
        self._setup_routes()
    
    def _authenticate_request(self):
        """
        Authenticate request using API key from Authorization header.
        
        Sets request.user_role and request.user_id if authentication succeeds.
        """
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        validated_key = self.key_manager.validate_key(api_key)
        
        if validated_key:
            request.user_role = validated_key.role
            request.user_id = validated_key.user_id
            return validated_key
        
        return None
    
    def _setup_routes(self):
        """Set up Flask routes for API key management and webhooks."""
        
        @self.app.before_request
        def before_request():
            """Authenticate all API requests."""
            if request.path.startswith('/api/') or request.path.startswith('/webhook/'):
                authenticated = self._authenticate_request()
                if not authenticated:
                    return jsonify({'error': 'Invalid or missing API key'}), 401
        
        @self.app.route('/api/keys', methods=['GET'])
        def list_keys():
            """
            List API keys based on user role.
            
            - Viewers: List own keys only
            - Operators: List all keys
            - Admins: List all keys with full details
            """
            user_role = getattr(request, 'user_role', None)
            user_id = getattr(request, 'user_id', None)
            
            if not user_role or not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check permissions
            if self.rbac_manager.has_permission(user_role, Permission.LIST_ALL_KEYS):
                # Operators and Admins can list all keys
                keys = self.key_manager.list_keys()
            elif self.rbac_manager.has_permission(user_role, Permission.LIST_OWN_KEYS):
                # Viewers can only list their own keys
                keys = self.key_manager.list_keys(user_id=user_id)
            else:
                return jsonify({'error': 'Permission denied'}), 403
            
            # Convert to dict and remove sensitive data for non-admins
            keys_data = [k.to_dict() for k in keys]
            
            # Admins get full details, others get limited info
            if user_role != Role.ADMIN:
                for key_data in keys_data:
                    key_data.pop('hashed_key', None)
            
            return jsonify({
                'keys': keys_data,
                'count': len(keys_data)
            }), 200
        
        @self.app.route('/api/keys', methods=['POST'])
        @require_permission(Permission.GENERATE_KEYS)
        def generate_key():
            """
            Generate a new API key.
            
            Required: Operator or Admin role
            
            Request body:
            {
                "name": "My API Key",
                "role": "viewer",  // viewer, operator, or admin
                "expires_in_days": 365  // optional
            }
            """
            data = request.json or {}
            
            # Validate required fields
            if 'role' not in data:
                return jsonify({'error': 'Role is required'}), 400
            
            try:
                role = Role(data['role'].lower())
            except ValueError:
                return jsonify({'error': 'Invalid role. Must be viewer, operator, or admin'}), 400
            
            # Only admins can generate keys for admin role
            user_role = getattr(request, 'user_role', None)
            if role == Role.ADMIN and user_role != Role.ADMIN:
                return jsonify({'error': 'Only admins can generate admin keys'}), 403
            
            # Generate key for the requesting user or specified user (admins only)
            user_id = data.get('user_id', getattr(request, 'user_id', None))
            
            # Only admins can generate keys for other users
            if user_id != request.user_id and user_role != Role.ADMIN:
                return jsonify({'error': 'Cannot generate keys for other users'}), 403
            
            name = data.get('name', '')
            expires_in_days = data.get('expires_in_days')
            
            raw_key, api_key = self.key_manager.generate_key(
                user_id=user_id,
                role=role,
                name=name,
                expires_in_days=expires_in_days
            )
            
            return jsonify({
                'message': 'API key generated successfully',
                'key': raw_key,  # Only shown once!
                'key_id': api_key.key_id,
                'key_info': api_key.to_dict()
            }), 201
        
        @self.app.route('/api/keys/<key_id>', methods=['DELETE'])
        @require_permission(Permission.REVOKE_KEYS)
        def revoke_key(key_id: str):
            """
            Revoke an API key.
            
            Required: Admin role only
            """
            success = self.key_manager.revoke_key(key_id)
            
            if success:
                return jsonify({
                    'message': f'API key {key_id} revoked successfully'
                }), 200
            else:
                return jsonify({'error': 'Key not found'}), 404
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        def handle_webhook(service: str):
            """
            Handle incoming webhook with role-based access.
            
            - Viewers: Read-only access to webhook data
            - Operators: Can execute webhooks
            - Admins: Full access
            """
            try:
                user_role = getattr(request, 'user_role', None)
                
                if not user_role:
                    return jsonify({'error': 'Authentication required'}), 401
                
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                        return jsonify({'error': 'Invalid signature'}), 403
                
                data = request.json or {}
                self.logger.info(f"Received webhook from {service} by user with role {user_role.value}")
                
                # Check webhook permissions
                if self.rbac_manager.has_permission(user_role, Permission.EXECUTE_WEBHOOKS):
                    # Execute webhook
                    if service in self.webhook_handlers:
                        response = self.webhook_handlers[service](data)
                        return jsonify(response), 200
                    else:
                        return jsonify({'error': 'Unknown service'}), 404
                
                elif self.rbac_manager.has_permission(user_role, Permission.READ_WEBHOOKS):
                    # Read-only access for viewers
                    return jsonify({
                        'status': 'received',
                        'service': service,
                        'message': 'Webhook received but not executed (read-only access)'
                    }), 200
                
                else:
                    return jsonify({'error': 'Permission denied'}), 403
                    
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
        self.webhook_handlers[service] = handler
        self.logger.info(f"Handler registered for service: {service}")
    
    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """
        Start the API/webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.logger.info(f"Starting API/webhook server on {host}:{port}")
        self.app.run(host=host, port=port)
