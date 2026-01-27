"""Authentication middleware for webhooks and API endpoints."""
from functools import wraps
from typing import Callable, Optional
from flask import request, jsonify
import logging


class AuthMiddleware:
    """
    Authentication middleware for securing webhook endpoints.
    
    Validates API keys and enforces role-based access control.
    """
    
    def __init__(self, api_key_manager):
        """
        Initialize authentication middleware.
        
        Args:
            api_key_manager: Instance of ApiKeyManager
        """
        self.api_key_manager = api_key_manager
        self.logger = logging.getLogger("mira.auth.middleware")
    
    def require_auth(self, required_permission: Optional[str] = None):
        """
        Decorator to require authentication for an endpoint.
        
        Args:
            required_permission: Optional specific permission required
            
        Returns:
            Decorated function
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Extract API key from header
                auth_header = request.headers.get('Authorization')
                
                if not auth_header:
                    self.logger.warning("Authentication failed: No Authorization header")
                    return jsonify({'error': 'Missing Authorization header'}), 401
                
                # Parse Bearer token
                if not auth_header.startswith('Bearer '):
                    self.logger.warning("Authentication failed: Invalid Authorization format")
                    return jsonify({'error': 'Invalid Authorization format. Use: Bearer <api_key>'}), 401
                
                api_key = auth_header[7:]  # Remove "Bearer " prefix
                
                # Validate API key
                key_metadata = self.api_key_manager.validate_key(api_key)
                
                if not key_metadata:
                    self.logger.warning(f"Authentication failed: Invalid or expired API key")
                    return jsonify({'error': 'Invalid or expired API key'}), 401
                
                # Check permission if required
                if required_permission:
                    if not self.api_key_manager.check_permission(key_metadata, required_permission):
                        self.logger.warning(
                            f"Authorization failed: Key {key_metadata.key_id} lacks permission: {required_permission}"
                        )
                        return jsonify({
                            'error': f'Insufficient permissions. Required: {required_permission}'
                        }), 403
                
                # Log successful authentication
                self.logger.info(
                    f"Authenticated: {key_metadata.key_id} (role: {key_metadata.role}) "
                    f"for {request.method} {request.path}"
                )
                
                # Attach key metadata to request for use in endpoint
                request.api_key_metadata = key_metadata
                
                # Call the original function
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def optional_auth(self):
        """
        Decorator for optional authentication.
        
        If API key is provided, it will be validated and attached to request.
        If not provided, request continues without authentication.
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                auth_header = request.headers.get('Authorization')
                
                if auth_header and auth_header.startswith('Bearer '):
                    api_key = auth_header[7:]
                    key_metadata = self.api_key_manager.validate_key(api_key)
                    
                    if key_metadata:
                        request.api_key_metadata = key_metadata
                        self.logger.info(
                            f"Authenticated (optional): {key_metadata.key_id} (role: {key_metadata.role})"
                        )
                    else:
                        self.logger.warning("Optional authentication: Invalid API key provided")
                else:
                    request.api_key_metadata = None
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
