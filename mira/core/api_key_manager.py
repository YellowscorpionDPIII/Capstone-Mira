"""API Key Manager with RBAC and security features."""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass, field
import logging


# Valid roles for RBAC
VALID_ROLES = ['viewer', 'operator', 'admin']


@dataclass
class ApiKey:
    """Represents an API key with metadata."""
    
    key_id: str
    key_hash: str
    name: str
    role: str
    owner: str
    created_at: datetime
    last_used: Optional[datetime] = None
    revoked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitInfo:
    """Rate limit tracking information."""
    
    requests: List[float] = field(default_factory=list)
    max_requests: int = 100
    window_seconds: int = 60


def validator(field: str, valid_values: Optional[List[str]] = None):
    """
    Decorator for validating field values.
    
    Args:
        field: Field name to validate
        valid_values: List of valid values for the field
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get the value to validate
            if field == 'role' and 'role' in kwargs:
                value = kwargs['role']
                if valid_values and value not in valid_values:
                    raise ValueError(f"Invalid {field}: {value}. Must be one of {valid_values}")
            elif field == 'name' and 'name' in kwargs:
                value = kwargs['name']
                if not value or not isinstance(value, str) or len(value.strip()) == 0:
                    raise ValueError(f"Invalid {field}: name must be a non-empty string")
            
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator for rate limiting API requests.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, key_id: str, *args, **kwargs):
            current_time = time.time()
            
            # Initialize rate limit info if not exists
            if key_id not in self._rate_limits:
                self._rate_limits[key_id] = RateLimitInfo(
                    max_requests=max_requests,
                    window_seconds=window_seconds
                )
            
            rate_info = self._rate_limits[key_id]
            
            # Remove old requests outside the window
            cutoff_time = current_time - rate_info.window_seconds
            rate_info.requests = [req for req in rate_info.requests if req > cutoff_time]
            
            # Check if rate limit exceeded
            if len(rate_info.requests) >= rate_info.max_requests:
                raise PermissionError(
                    f"Rate limit exceeded: {rate_info.max_requests} requests per "
                    f"{rate_info.window_seconds} seconds"
                )
            
            # Add current request
            rate_info.requests.append(current_time)
            
            return await func(self, key_id, *args, **kwargs)
        return wrapper
    return decorator


class ApiKeyManager:
    """
    Manages API keys with RBAC, rate limiting, and security features.
    
    Implements the RBAC Permission Matrix:
    - Viewer: Can list own keys, read webhooks
    - Operator: Can list all keys, generate keys, execute webhooks
    - Admin: Full access - list/CRUD all keys, revoke keys, access all webhooks
    """
    
    def __init__(self):
        """Initialize the API key manager."""
        self._keys: Dict[str, ApiKey] = {}
        self._rate_limits: Dict[str, RateLimitInfo] = {}
        self.logger = logging.getLogger("mira.api_key_manager")
        
    async def generate_key(
        self,
        name: str,
        role: str,
        owner: str,
        requester_role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate a new API key.
        
        Args:
            name: Descriptive name for the key
            role: Role to assign (viewer, operator, admin)
            owner: Owner of the key
            requester_role: Role of the user requesting key generation
            metadata: Optional metadata
            
        Returns:
            Dictionary containing key_id and plaintext key
            
        Raises:
            PermissionError: If requester doesn't have permission
            ValueError: If invalid role or name
        """
        # Check permissions - only operator and admin can generate keys
        if requester_role not in ['operator', 'admin']:
            raise PermissionError(
                f"Role '{requester_role}' cannot generate API keys. "
                "Requires 'operator' or 'admin' role."
            )
        
        # Validate inputs
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
        
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            raise ValueError("Name must be a non-empty string")
        
        # Generate secure random key
        plaintext_key = secrets.token_urlsafe(32)
        key_id = secrets.token_urlsafe(16)
        
        # Hash the key for storage
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        
        # Create API key object
        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name.strip(),
            role=role,
            owner=owner,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store the key
        self._keys[key_id] = api_key
        
        self.logger.info(
            f"API key generated: key_id={key_id}, role={role}, owner={owner}, "
            f"requester_role={requester_role}"
        )
        
        return {
            'key_id': key_id,
            'key': plaintext_key,
            'role': role,
            'name': name.strip()
        }
    
    @rate_limit(max_requests=100, window_seconds=60)
    async def validate_key(self, key_id: str, plaintext_key: str) -> Optional[ApiKey]:
        """
        Validate an API key and return its metadata.
        
        Args:
            key_id: The key ID
            plaintext_key: The plaintext key to validate
            
        Returns:
            ApiKey object if valid, None otherwise
        """
        if key_id not in self._keys:
            self.logger.warning(f"Validation failed: key_id={key_id} not found")
            return None
        
        api_key = self._keys[key_id]
        
        # Check if revoked
        if api_key.revoked:
            self.logger.warning(f"Validation failed: key_id={key_id} is revoked")
            return None
        
        # Validate key hash
        provided_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        if provided_hash != api_key.key_hash:
            self.logger.warning(f"Validation failed: invalid key for key_id={key_id}")
            return None
        
        # Update last used timestamp
        api_key.last_used = datetime.utcnow()
        
        self.logger.debug(f"API key validated: key_id={key_id}, role={api_key.role}")
        return api_key
    
    async def revoke_key(self, key_id: str, requester_role: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The key ID to revoke
            requester_role: Role of the user requesting revocation
            
        Returns:
            True if revoked successfully
            
        Raises:
            PermissionError: If requester doesn't have permission
        """
        # Only admins can revoke keys
        if requester_role != 'admin':
            raise PermissionError(
                f"Role '{requester_role}' cannot revoke API keys. "
                "Requires 'admin' role."
            )
        
        if key_id not in self._keys:
            return False
        
        self._keys[key_id].revoked = True
        self.logger.info(f"API key revoked: key_id={key_id}, requester_role={requester_role}")
        return True
    
    async def list_keys(
        self,
        requester_role: str,
        requester_owner: str
    ) -> List[Dict[str, Any]]:
        """
        List API keys based on requester's role.
        
        Args:
            requester_role: Role of the user requesting the list
            requester_owner: Owner identifier of the requester
            
        Returns:
            List of API key information (without sensitive data)
        """
        keys = []
        
        for key_id, api_key in self._keys.items():
            # Viewers can only see their own keys
            if requester_role == 'viewer' and api_key.owner != requester_owner:
                continue
            
            # Operators and admins can see all keys
            keys.append({
                'key_id': key_id,
                'name': api_key.name,
                'role': api_key.role,
                'owner': api_key.owner,
                'created_at': api_key.created_at.isoformat(),
                'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
                'revoked': api_key.revoked,
                'metadata': api_key.metadata
            })
        
        self.logger.info(
            f"Listed {len(keys)} API keys for requester_role={requester_role}, "
            f"owner={requester_owner}"
        )
        return keys
    
    async def check_permission(
        self,
        key_id: str,
        endpoint: str,
        method: str
    ) -> bool:
        """
        Check if an API key has permission to access an endpoint.
        
        Implements RBAC Permission Matrix:
        - GET /api/keys: viewer (own), operator (all), admin (all)
        - POST /api/keys: operator, admin
        - DELETE /api/keys/:id: admin only
        - POST /webhook/:service: viewer (read), operator (execute), admin (all)
        
        Args:
            key_id: The key ID
            endpoint: The endpoint path
            method: HTTP method (GET, POST, DELETE, etc.)
            
        Returns:
            True if permission granted
        """
        if key_id not in self._keys:
            return False
        
        api_key = self._keys[key_id]
        
        if api_key.revoked:
            return False
        
        role = api_key.role
        
        # Permission matrix implementation
        if endpoint.startswith('/api/keys'):
            if method == 'GET':
                # All roles can GET (but viewers limited to own keys in list_keys)
                return True
            elif method == 'POST':
                # Only operator and admin can create keys
                return role in ['operator', 'admin']
            elif method == 'DELETE':
                # Only admin can delete/revoke keys
                return role == 'admin'
        
        elif endpoint.startswith('/webhook/'):
            # All roles have some webhook access
            # Specific access control handled in webhook handler
            return True
        
        # Default deny
        return False
    
    async def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific API key.
        
        Args:
            key_id: The key ID
            
        Returns:
            Dictionary with key information (without sensitive data)
        """
        if key_id not in self._keys:
            return None
        
        api_key = self._keys[key_id]
        return {
            'key_id': key_id,
            'name': api_key.name,
            'role': api_key.role,
            'owner': api_key.owner,
            'created_at': api_key.created_at.isoformat(),
            'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
            'revoked': api_key.revoked,
            'metadata': api_key.metadata
        }


# Global API key manager instance
_manager: Optional[ApiKeyManager] = None


async def get_api_key_manager() -> ApiKeyManager:
    """
    Get the global API key manager instance.
    
    Returns:
        ApiKeyManager instance
    """
    global _manager
    if _manager is None:
        _manager = ApiKeyManager()
    return _manager
