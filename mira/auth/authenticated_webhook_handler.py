"""Enhanced webhook handler with authentication and API key management."""
from typing import Dict, Any, Optional
from flask import request, jsonify
from mira.core.webhook_handler import WebhookHandler
from mira.auth.api_key_manager import ApiKeyManager
from mira.auth.middleware import AuthMiddleware
import logging


class AuthenticatedWebhookHandler(WebhookHandler):
    """
    Enhanced webhook handler with authentication and API key management.
    
    Extends the base webhook handler with:
    - API key authentication
    - Role-based access control
    - Key management endpoints
    - Audit logging
    """
    
    def __init__(
        self,
        api_key_manager: ApiKeyManager,
        secret_key: Optional[str] = None
    ):
        """
        Initialize authenticated webhook handler.
        
        Args:
            api_key_manager: Instance of ApiKeyManager
            secret_key: Secret key for webhook signature verification
        """
        super().__init__(secret_key)
        self.api_key_manager = api_key_manager
        self.auth_middleware = AuthMiddleware(api_key_manager)
        self.logger = logging.getLogger("mira.webhook.authenticated")
        self._setup_auth_routes()
    
    def _setup_auth_routes(self):
        """Set up authentication-protected routes."""
        
        # Override base webhook route with authentication
        @self.app.route('/webhook/<service>', methods=['POST'])
        @self.auth_middleware.require_auth('execute')
        def authenticated_webhook(service: str):
            """Handle authenticated webhook."""
            try:
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    if not self._verify_signature(request.data, request.headers['X-Hub-Signature-256']):
                        return jsonify({'error': 'Invalid signature'}), 403
                
                data = request.json or {}
                
                # Attach API key metadata to webhook data
                if hasattr(request, 'api_key_metadata'):
                    data['_auth'] = {
                        'key_id': request.api_key_metadata.key_id,
                        'role': request.api_key_metadata.role
                    }
                
                self.logger.info(f"Received authenticated webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = self.handlers[service](data)
                    return jsonify(response), 200
                else:
                    return jsonify({'error': 'Unknown service'}), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling authenticated webhook: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        # API Key Management Endpoints
        
        @self.app.route('/api/keys', methods=['POST'])
        @self.auth_middleware.require_auth('manage_keys')
        def create_api_key():
            """Create a new API key (admin only)."""
            try:
                data = request.json or {}
                role = data.get('role')
                name = data.get('name')
                expiry_days = data.get('expiry_days')
                
                if not role:
                    return jsonify({'error': 'Role is required'}), 400
                
                raw_key, api_key = self.api_key_manager.generate_key(
                    role=role,
                    name=name,
                    expiry_days=expiry_days
                )
                
                # Return the raw key only once - never stored in plain text
                return jsonify({
                    'api_key': raw_key,
                    'key_id': api_key.key_id,
                    'role': api_key.role,
                    'expires_at': api_key.expires_at,
                    'warning': 'Save this key securely. It will not be shown again.'
                }), 201
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Error creating API key: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/keys', methods=['GET'])
        @self.auth_middleware.require_auth('manage_keys')
        def list_api_keys():
            """List API keys (admin only)."""
            try:
                role_filter = request.args.get('role')
                status_filter = request.args.get('status')
                
                keys = self.api_key_manager.list_keys(
                    role=role_filter,
                    status=status_filter
                )
                
                # Return sanitized key data (no hashes)
                keys_data = [{
                    'key_id': key.key_id,
                    'role': key.role,
                    'name': key.name,
                    'created_at': key.created_at,
                    'expires_at': key.expires_at,
                    'last_used': key.last_used,
                    'status': key.status
                } for key in keys]
                
                return jsonify({'keys': keys_data}), 200
                
            except Exception as e:
                self.logger.error(f"Error listing API keys: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/keys/<key_id>', methods=['DELETE'])
        @self.auth_middleware.require_auth('manage_keys')
        def revoke_api_key(key_id: str):
            """Revoke an API key (admin only)."""
            try:
                success = self.api_key_manager.revoke_key(key_id)
                
                if success:
                    return jsonify({
                        'message': f'API key {key_id} revoked successfully'
                    }), 200
                else:
                    return jsonify({'error': 'Key not found'}), 404
                    
            except Exception as e:
                self.logger.error(f"Error revoking API key: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/keys/<key_id>/rotate', methods=['POST'])
        @self.auth_middleware.require_auth('manage_keys')
        def rotate_api_key(key_id: str):
            """Rotate an API key (admin only)."""
            try:
                data = request.json or {}
                new_role = data.get('role')
                
                raw_key, api_key = self.api_key_manager.rotate_key(
                    old_key_id=key_id,
                    role=new_role
                )
                
                return jsonify({
                    'api_key': raw_key,
                    'key_id': api_key.key_id,
                    'role': api_key.role,
                    'expires_at': api_key.expires_at,
                    'message': f'Key {key_id} rotated successfully',
                    'warning': 'Save this key securely. It will not be shown again.'
                }), 200
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 404
            except Exception as e:
                self.logger.error(f"Error rotating API key: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/auth/validate', methods=['GET'])
        @self.auth_middleware.require_auth()
        def validate_token():
            """Validate the current API key."""
            try:
                key_metadata = request.api_key_metadata
                return jsonify({
                    'valid': True,
                    'key_id': key_metadata.key_id,
                    'role': key_metadata.role,
                    'expires_at': key_metadata.expires_at,
                    'permissions': ApiKeyManager.ROLE_PERMISSIONS.get(key_metadata.role, [])
                }), 200
            except Exception as e:
                self.logger.error(f"Error validating token: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint (no authentication required)."""
            return jsonify({'status': 'healthy', 'service': 'mira-webhook'}), 200
