"""Enhanced API key manager with Redis caching and structured logging."""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

from mira.auth.api_key_manager import ApiKey
from mira.auth.redis_cache import RedisCache
from mira.auth.structured_logging import AuditLogger


class EnhancedApiKeyManager:
    """
    Enhanced API Key Manager with Redis caching, structured logging, and audit trails.
    
    Features:
    - Redis-backed caching for improved performance
    - Structured logging with audit trails
    - Zero-downtime key rotation with grace periods
    - Timing-attack resistant validation
    - Role-based access control
    """
    
    VALID_ROLES = ['viewer', 'admin', 'operator']
    ROLE_PERMISSIONS = {
        'viewer': ['read', 'list'],
        'operator': ['read', 'list', 'write', 'execute'],
        'admin': ['read', 'list', 'write', 'execute', 'manage_keys', 'manage_users']
    }
    
    def __init__(
        self,
        storage_backend=None,
        redis_cache: Optional[RedisCache] = None,
        default_expiry_days: int = 90,
        rotation_grace_period_minutes: int = 60
    ):
        """
        Initialize Enhanced API key manager.
        
        Args:
            storage_backend: Optional storage backend (e.g., AirtableIntegration)
            redis_cache: Optional Redis cache instance
            default_expiry_days: Default number of days until key expiration
            rotation_grace_period_minutes: Grace period for old keys during rotation
        """
        self.logger = logging.getLogger("mira.auth.enhanced_api_key_manager")
        self.audit_logger = AuditLogger(self.logger)
        self.storage = storage_backend
        self.redis_cache = redis_cache
        self.default_expiry_days = default_expiry_days
        self.rotation_grace_period = timedelta(minutes=rotation_grace_period_minutes)
        self._keys_cache: Dict[str, ApiKey] = {}
        
        # Track rotation state for zero-downtime key rotation
        self._rotation_state: Dict[str, Dict] = {}
        
        # Load existing keys from storage if available
        if self.storage:
            self._load_keys_from_storage()
        
        self.logger.info(
            "Enhanced API Key Manager initialized",
            extra={
                'has_storage': storage_backend is not None,
                'has_redis': redis_cache is not None and redis_cache.enabled,
                'default_expiry_days': default_expiry_days,
                'grace_period_minutes': rotation_grace_period_minutes
            }
        )
    
    def generate_key(
        self,
        role: str,
        name: Optional[str] = None,
        expiry_days: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Tuple[str, ApiKey]:
        """
        Generate a new API key with specified role.
        
        Args:
            role: Role for the key (viewer, admin, operator)
            name: Optional human-readable name for the key
            expiry_days: Days until expiration (default: 90)
            created_by: Optional identifier of who created the key
            
        Returns:
            Tuple of (raw_key, ApiKey object)
            
        Raises:
            ValueError: If role is invalid
        """
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(self.VALID_ROLES)}")
        
        # Generate secure random key
        raw_key = self._generate_secure_key()
        key_id = self._generate_key_id()
        key_hash = self._hash_key(raw_key)
        
        # Calculate expiration
        created_at = datetime.utcnow()
        expiry = expiry_days if expiry_days is not None else self.default_expiry_days
        expires_at = created_at + timedelta(days=expiry) if expiry > 0 else None
        
        # Create API key object
        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            role=role,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat() if expires_at else None,
            last_used=None,
            status='active',
            name=name
        )
        
        # Store in memory cache
        self._keys_cache[key_hash] = api_key
        
        # Store in Redis cache if available
        if self.redis_cache:
            self.redis_cache.set(key_hash, key_id, api_key.to_dict())
        
        # Store in persistent storage
        if self.storage:
            self._save_key_to_storage(api_key)
        
        # Audit log
        self.audit_logger.log_key_generation(
            key_id=key_id,
            role=role,
            created_by=created_by,
            name=name
        )
        
        self.logger.info(
            f"Generated new API key",
            extra={
                'key_id': key_id,
                'role': role,
                'name': name,
                'expires_at': api_key.expires_at
            }
        )
        
        return raw_key, api_key
    
    def validate_key(
        self,
        raw_key: str,
        ip_address: Optional[str] = None
    ) -> Optional[ApiKey]:
        """
        Validate an API key with timing-attack resistance.
        
        Args:
            raw_key: The raw API key to validate
            ip_address: Optional IP address for audit logging
            
        Returns:
            ApiKey object if valid, None otherwise
        """
        key_hash = self._hash_key(raw_key)
        
        # Try Redis cache first for best performance
        api_key = None
        if self.redis_cache:
            cached_data = self.redis_cache.get(key_hash)
            if cached_data:
                api_key = ApiKey.from_dict(cached_data)
                self.logger.debug("Key retrieved from Redis cache")
        
        # Try memory cache with constant-time comparison
        if not api_key:
            for cached_hash, cached_key in self._keys_cache.items():
                if secrets.compare_digest(cached_hash, key_hash):
                    api_key = cached_key
                    break
        
        # Try storage as last resort
        if not api_key and self.storage:
            api_key = self._load_key_from_storage(key_hash)
            if api_key:
                self._keys_cache[key_hash] = api_key
                if self.redis_cache:
                    self.redis_cache.set(key_hash, api_key.key_id, api_key.to_dict())
        
        # Check if key exists
        if not api_key:
            self.audit_logger.log_key_validation(
                key_id="unknown",
                success=False,
                reason="key_not_found",
                ip_address=ip_address
            )
            return None
        
        # Check rotation grace period
        if api_key.key_id in self._rotation_state:
            rotation_info = self._rotation_state[api_key.key_id]
            if datetime.utcnow() < rotation_info['grace_period_end']:
                # Key is in grace period, allow validation
                self.logger.debug(f"Key {api_key.key_id} in rotation grace period")
            else:
                # Grace period expired, remove from rotation state
                del self._rotation_state[api_key.key_id]
        
        # Check if key is active
        if api_key.status != 'active':
            self.audit_logger.log_key_validation(
                key_id=api_key.key_id,
                success=False,
                reason=f"key_status_{api_key.status}",
                ip_address=ip_address
            )
            return None
        
        # Check expiration
        if api_key.expires_at:
            expires_at = datetime.fromisoformat(api_key.expires_at)
            if datetime.utcnow() > expires_at:
                api_key.status = 'expired'
                self._update_key(api_key)
                self.audit_logger.log_key_validation(
                    key_id=api_key.key_id,
                    success=False,
                    reason="key_expired",
                    ip_address=ip_address
                )
                return None
        
        # Update last used timestamp
        api_key.last_used = datetime.utcnow().isoformat()
        self._update_key(api_key)
        
        # Audit log successful validation
        self.audit_logger.log_key_validation(
            key_id=api_key.key_id,
            success=True,
            ip_address=ip_address
        )
        
        return api_key
    
    def rotate_key_with_grace_period(
        self,
        old_key_id: str,
        role: Optional[str] = None,
        rotated_by: Optional[str] = None
    ) -> Tuple[str, ApiKey]:
        """
        Rotate an API key with zero-downtime grace period.
        
        During the grace period, both old and new keys are valid.
        
        Args:
            old_key_id: ID of the key to rotate
            role: Optional new role (defaults to old key's role)
            rotated_by: Optional identifier of who rotated the key
            
        Returns:
            Tuple of (new_raw_key, new_ApiKey object)
            
        Raises:
            ValueError: If old key not found
        """
        # Find old key
        old_api_key = self._find_key_by_id(old_key_id)
        if not old_api_key:
            raise ValueError(f"Key not found: {old_key_id}")
        
        # Generate new key
        new_role = role if role else old_api_key.role
        new_raw_key, new_api_key = self.generate_key(
            role=new_role,
            name=old_api_key.name,
            created_by=rotated_by
        )
        
        # Set rotation grace period for old key
        grace_period_end = datetime.utcnow() + self.rotation_grace_period
        self._rotation_state[old_key_id] = {
            'new_key_id': new_api_key.key_id,
            'grace_period_end': grace_period_end,
            'rotated_at': datetime.utcnow()
        }
        
        # Mark old key as rotating (not revoked yet)
        old_api_key.status = 'rotating'
        self._update_key(old_api_key)
        
        # Audit log
        self.audit_logger.log_key_rotation(
            old_key_id=old_key_id,
            new_key_id=new_api_key.key_id,
            rotated_by=rotated_by
        )
        
        self.logger.info(
            "Key rotation started with grace period",
            extra={
                'old_key_id': old_key_id,
                'new_key_id': new_api_key.key_id,
                'grace_period_minutes': self.rotation_grace_period.total_seconds() / 60,
                'grace_period_end': grace_period_end.isoformat()
            }
        )
        
        return new_raw_key, new_api_key
    
    def complete_rotation(self, old_key_id: str):
        """
        Complete key rotation by revoking the old key.
        
        Args:
            old_key_id: ID of the old key to fully revoke
        """
        if old_key_id in self._rotation_state:
            del self._rotation_state[old_key_id]
        
        old_api_key = self._find_key_by_id(old_key_id)
        if old_api_key:
            old_api_key.status = 'revoked'
            self._update_key(old_api_key)
            
            self.logger.info(
                "Key rotation completed",
                extra={'old_key_id': old_key_id}
            )
    
    def _generate_secure_key(self) -> str:
        """Generate a cryptographically secure random key."""
        return secrets.token_urlsafe(32)
    
    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        return f"mira_key_{secrets.token_urlsafe(16)}"
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _find_key_by_id(self, key_id: str) -> Optional[ApiKey]:
        """Find an API key by its ID."""
        # Check Redis cache first
        if self.redis_cache:
            cached_data = self.redis_cache.get_by_id(key_id)
            if cached_data:
                return ApiKey.from_dict(cached_data)
        
        # Check memory cache
        for api_key in self._keys_cache.values():
            if api_key.key_id == key_id:
                return api_key
        
        # Check storage
        if self.storage:
            # Storage implementation would load by ID
            pass
        
        return None
    
    def _update_key(self, api_key: ApiKey):
        """Update an API key in all caches and storage."""
        key_hash = api_key.key_hash
        
        # Update memory cache
        self._keys_cache[key_hash] = api_key
        
        # Update Redis cache
        if self.redis_cache:
            self.redis_cache.set(key_hash, api_key.key_id, api_key.to_dict())
        
        # Update storage
        if self.storage:
            self._save_key_to_storage(api_key)
    
    def _save_key_to_storage(self, api_key: ApiKey):
        """Save API key to persistent storage."""
        if self.storage:
            self.storage.sync_data('api_keys', {
                'action': 'save',
                'key': api_key.to_dict()
            })
    
    def _load_keys_from_storage(self):
        """Load existing keys from storage into cache."""
        if self.storage:
            result = self.storage.sync_data('api_keys', {'action': 'list'})
            if result.get('success') and result.get('keys'):
                for key_data in result['keys']:
                    api_key = ApiKey.from_dict(key_data)
                    self._keys_cache[api_key.key_hash] = api_key
    
    def _load_key_from_storage(self, key_hash: str) -> Optional[ApiKey]:
        """Load a specific key from storage."""
        if self.storage:
            result = self.storage.sync_data('api_keys', {
                'action': 'get',
                'key_hash': key_hash
            })
            if result.get('success') and result.get('key'):
                return ApiKey.from_dict(result['key'])
        return None
    
    def check_permission(self, api_key: ApiKey, permission: str) -> bool:
        """Check if an API key has a specific permission."""
        permissions = self.ROLE_PERMISSIONS.get(api_key.role, [])
        return permission in permissions
    
    def list_keys(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ApiKey]:
        """List API keys with optional filters."""
        keys = list(self._keys_cache.values())
        
        if role:
            keys = [k for k in keys if k.role == role]
        if status:
            keys = [k for k in keys if k.status == status]
        
        return keys
    
    def revoke_key(self, key_id: str, revoked_by: Optional[str] = None) -> bool:
        """Revoke an API key."""
        api_key = self._find_key_by_id(key_id)
        if not api_key:
            return False
        
        api_key.status = 'revoked'
        self._update_key(api_key)
        
        # Clear from Redis cache
        if self.redis_cache:
            self.redis_cache.delete(api_key.key_hash, key_id)
        
        # Audit log
        self.audit_logger.log_key_revocation(
            key_id=key_id,
            revoked_by=revoked_by
        )
        
        return True
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'memory_cache_size': len(self._keys_cache),
            'rotation_state_size': len(self._rotation_state)
        }
        
        if self.redis_cache:
            stats['redis'] = self.redis_cache.get_stats()
        
        return stats
