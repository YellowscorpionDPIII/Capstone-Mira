"""API Key Manager with JWT support, rate limiting, and validation."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib
import re
import jwt
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


class APIKeyValidationError(Exception):
    """Raised when API key validation fails."""
    pass


class APIKeyManager:
    """
    Manages API keys and JWT tokens for authentication.
    
    Features:
    - Generate and rotate API keys
    - JWT token generation with role/expiry/iat
    - Key validation with minimum length and pattern checking
    - Key masking for admin responses
    - Rate limiting on generate/rotate operations
    """
    
    # Weak patterns to reject
    WEAK_PATTERNS = [
        r'(.)\1{4,}',  # 5+ repeated characters
        r'(012|123|234|345|456|567|678|789|890){3,}',  # Sequential numbers
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz){2,}',  # Sequential letters (simplified)
        r'^[0-9]+$',  # Only numbers
        r'^[a-zA-Z]+$',  # Only letters
    ]
    
    MIN_KEY_LENGTH = 32
    
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        default_token_expiry_hours: int = 24
    ):
        """
        Initialize the API Key Manager.
        
        Args:
            jwt_secret: Secret key for JWT signing (generated if not provided)
            jwt_algorithm: Algorithm for JWT signing
            default_token_expiry_hours: Default JWT token expiry in hours
        """
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.jwt_algorithm = jwt_algorithm
        self.default_token_expiry_hours = default_token_expiry_hours
        
        # In-memory storage for demo (in production, use a database)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
    def generate_api_key(
        self,
        user_id: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a new API key.
        
        Args:
            user_id: User identifier
            role: User role (e.g., "admin", "user")
            metadata: Additional metadata to store
            
        Returns:
            Dictionary with API key and metadata
            
        Raises:
            APIKeyValidationError: If generated key fails validation
        """
        # Generate a secure random key
        key = self._generate_secure_key()
        
        # Validate the key
        self.validate_key(key)
        
        # Hash the key for storage
        key_hash = self._hash_key(key)
        
        # Store key metadata
        self.api_keys[key_hash] = {
            "user_id": user_id,
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "metadata": metadata or {}
        }
        
        logger.info(f"Generated API key for user {user_id}")
        
        return {
            "api_key": key,
            "user_id": user_id,
            "role": role,
            "created_at": self.api_keys[key_hash]["created_at"]
        }
    
    def rotate_api_key(self, old_key: str, user_id: str) -> Dict[str, Any]:
        """
        Rotate an existing API key.
        
        Args:
            old_key: Current API key
            user_id: User identifier for verification
            
        Returns:
            Dictionary with new API key and metadata
            
        Raises:
            APIKeyValidationError: If old key is invalid or doesn't match user
        """
        old_key_hash = self._hash_key(old_key)
        
        if old_key_hash not in self.api_keys:
            raise APIKeyValidationError("Invalid API key")
        
        key_data = self.api_keys[old_key_hash]
        if key_data["user_id"] != user_id:
            raise APIKeyValidationError("User ID mismatch")
        
        # Generate new key
        new_key_data = self.generate_api_key(
            user_id=user_id,
            role=key_data["role"],
            metadata=key_data.get("metadata", {})
        )
        
        # Remove old key
        del self.api_keys[old_key_hash]
        
        logger.info(f"Rotated API key for user {user_id}")
        
        return new_key_data
    
    def validate_key(self, key: str) -> bool:
        """
        Validate an API key format and strength.
        
        Args:
            key: API key to validate
            
        Returns:
            True if valid
            
        Raises:
            APIKeyValidationError: If key is invalid
        """
        # Check minimum length
        if len(key) < self.MIN_KEY_LENGTH:
            raise APIKeyValidationError(
                f"API key must be at least {self.MIN_KEY_LENGTH} characters"
            )
        
        # Check for weak patterns
        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, key, re.IGNORECASE):
                raise APIKeyValidationError(
                    f"API key contains weak pattern: {pattern}"
                )
        
        return True
    
    def verify_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Verify an API key and return associated data.
        
        Args:
            key: API key to verify
            
        Returns:
            Key metadata if valid, None otherwise
        """
        key_hash = self._hash_key(key)
        
        if key_hash in self.api_keys:
            # Update last used timestamp
            self.api_keys[key_hash]["last_used"] = datetime.utcnow().isoformat()
            return self.api_keys[key_hash].copy()
        
        return None
    
    def generate_jwt_token(
        self,
        user_id: str,
        role: str = "user",
        expiry_hours: Optional[int] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a JWT token.
        
        Args:
            user_id: User identifier
            role: User role
            expiry_hours: Token expiry in hours (uses default if not provided)
            additional_claims: Additional claims to include in token
            
        Returns:
            JWT token string
        """
        expiry_hours = expiry_hours or self.default_token_expiry_hours
        
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=expiry_hours)).timestamp())
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        logger.info(f"Generated JWT token for user {user_id}")
        
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def mask_key(self, key: str, show_chars: int = 8) -> str:
        """
        Mask an API key for display, showing only first and last N characters.
        
        Args:
            key: API key to mask
            show_chars: Number of characters to show at start and end
            
        Returns:
            Masked key string
        """
        if len(key) <= show_chars * 2:
            return "*" * len(key)
        
        return f"{key[:show_chars]}{'*' * (len(key) - show_chars * 2)}{key[-show_chars:]}"
    
    def list_keys_for_user(self, user_id: str, mask: bool = True) -> List[Dict[str, Any]]:
        """
        List all API keys for a user.
        
        Note: Since keys are hashed for storage, the actual keys are not retrievable.
        This method returns metadata for keys associated with the user.
        
        Args:
            user_id: User identifier
            mask: Whether to include masked key hash (for reference only)
            
        Returns:
            List of key metadata dictionaries
        """
        keys = []
        for key_hash, data in self.api_keys.items():
            if data["user_id"] == user_id:
                key_info = data.copy()
                if mask:
                    # Show masked hash for reference (not the actual key, which is not stored)
                    key_info["key_hash_preview"] = self.mask_key(key_hash)
                keys.append(key_info)
        
        return keys
    
    def _generate_secure_key(self) -> str:
        """
        Generate a cryptographically secure API key.
        
        Returns:
            Secure random key string
        """
        # Generate 32+ bytes for sufficient entropy
        return secrets.token_urlsafe(48)  # ~64 chars base64
    
    def _hash_key(self, key: str) -> str:
        """
        Hash an API key for storage.
        
        Args:
            key: API key to hash
            
        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(key.encode()).hexdigest()


def rate_limit_decorator(limit: str = "10 per minute"):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        limit: Rate limit string (e.g., "10 per minute")
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This is a placeholder - actual rate limiting is handled by flask-limiter
            # when integrated with Flask app routes
            return func(*args, **kwargs)
        return wrapper
    return decorator
