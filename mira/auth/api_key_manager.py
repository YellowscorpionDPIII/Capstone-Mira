"""API key management for HITL environment."""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ApiKey:
    """Represents an API key with metadata."""
    key_id: str
    key_hash: str
    role: str
    created_at: str
    expires_at: Optional[str]
    last_used: Optional[str]
    status: str  # 'active', 'expired', 'revoked'
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiKey':
        """Create from dictionary."""
        return cls(**data)


class ApiKeyManager:
    """
    Manages API keys for the Mira HITL environment.
    
    Features:
    - Secure key generation using cryptographic random
    - Role-based access control (viewer, admin, operator)
    - Key expiration and rotation
    - Persistent storage integration (Airtable)
    - Audit logging
    """
    
    # Valid roles in the HITL ecosystem
    VALID_ROLES = ['viewer', 'admin', 'operator']
    
    # Role permissions mapping
    ROLE_PERMISSIONS = {
        'viewer': ['read', 'list'],
        'operator': ['read', 'list', 'write', 'execute'],
        'admin': ['read', 'list', 'write', 'execute', 'manage_keys', 'manage_users']
    }
    
    def __init__(self, storage_backend=None, default_expiry_days: int = 90):
        """
        Initialize API key manager.
        
        Args:
            storage_backend: Optional storage backend (e.g., AirtableIntegration)
            default_expiry_days: Default number of days until key expiration
        """
        self.logger = logging.getLogger("mira.auth.api_key_manager")
        self.storage = storage_backend
        self.default_expiry_days = default_expiry_days
        self._keys_cache: Dict[str, ApiKey] = {}
        
        # Load existing keys from storage if available
        if self.storage:
            self._load_keys_from_storage()
    
    def generate_key(
        self,
        role: str,
        name: Optional[str] = None,
        expiry_days: Optional[int] = None
    ) -> tuple[str, ApiKey]:
        """
        Generate a new API key with specified role.
        
        Args:
            role: Role for the key (viewer, admin, operator)
            name: Optional human-readable name for the key
            expiry_days: Days until expiration (default: 90)
            
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
        
        # Store in cache and persistent storage
        self._keys_cache[key_hash] = api_key
        if self.storage:
            self._save_key_to_storage(api_key)
        
        self.logger.info(f"Generated new API key: {key_id} with role: {role}")
        
        return raw_key, api_key
    
    def validate_key(self, raw_key: str) -> Optional[ApiKey]:
        """
        Validate an API key and return its metadata.
        
        Args:
            raw_key: The raw API key to validate
            
        Returns:
            ApiKey object if valid, None otherwise
        """
        key_hash = self._hash_key(raw_key)
        
        # Check cache first
        api_key = self._keys_cache.get(key_hash)
        
        # If not in cache, try loading from storage
        if not api_key and self.storage:
            api_key = self._load_key_from_storage(key_hash)
            if api_key:
                self._keys_cache[key_hash] = api_key
        
        if not api_key:
            self.logger.warning("API key validation failed: key not found")
            return None
        
        # Check if key is active
        if api_key.status != 'active':
            self.logger.warning(f"API key validation failed: key status is {api_key.status}")
            return None
        
        # Check expiration
        if api_key.expires_at:
            expires_at = datetime.fromisoformat(api_key.expires_at)
            if datetime.utcnow() > expires_at:
                self.logger.warning(f"API key validation failed: key expired at {api_key.expires_at}")
                api_key.status = 'expired'
                self._update_key(api_key)
                return None
        
        # Update last used timestamp
        api_key.last_used = datetime.utcnow().isoformat()
        self._update_key(api_key)
        
        self.logger.info(f"API key validated successfully: {api_key.key_id}")
        return api_key
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of the key to revoke
            
        Returns:
            True if revoked successfully
        """
        api_key = self._find_key_by_id(key_id)
        if not api_key:
            self.logger.warning(f"Cannot revoke key: {key_id} not found")
            return False
        
        api_key.status = 'revoked'
        self._update_key(api_key)
        
        self.logger.info(f"Revoked API key: {key_id}")
        return True
    
    def rotate_key(self, old_key_id: str, role: Optional[str] = None) -> tuple[str, ApiKey]:
        """
        Rotate an API key by creating a new one and revoking the old.
        
        Args:
            old_key_id: ID of the key to rotate
            role: Optional new role (defaults to old key's role)
            
        Returns:
            Tuple of (new_raw_key, new_ApiKey)
            
        Raises:
            ValueError: If old key not found
        """
        old_key = self._find_key_by_id(old_key_id)
        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")
        
        # Use old key's role if not specified
        new_role = role or old_key.role
        
        # Generate new key
        new_raw_key, new_api_key = self.generate_key(
            role=new_role,
            name=f"Rotated from {old_key_id}"
        )
        
        # Revoke old key
        self.revoke_key(old_key_id)
        
        self.logger.info(f"Rotated API key: {old_key_id} -> {new_api_key.key_id}")
        
        return new_raw_key, new_api_key
    
    def list_keys(self, role: Optional[str] = None, status: Optional[str] = None) -> List[ApiKey]:
        """
        List API keys with optional filtering.
        
        Args:
            role: Optional role filter
            status: Optional status filter
            
        Returns:
            List of ApiKey objects
        """
        keys = list(self._keys_cache.values())
        
        if role:
            keys = [k for k in keys if k.role == role]
        
        if status:
            keys = [k for k in keys if k.status == status]
        
        return keys
    
    def check_permission(self, api_key: ApiKey, permission: str) -> bool:
        """
        Check if an API key has a specific permission.
        
        Args:
            api_key: The ApiKey to check
            permission: Permission to check (e.g., 'read', 'write', 'manage_keys')
            
        Returns:
            True if key has permission
        """
        role_permissions = self.ROLE_PERMISSIONS.get(api_key.role, [])
        return permission in role_permissions
    
    def _generate_secure_key(self) -> str:
        """Generate a cryptographically secure API key."""
        # Generate 32 bytes (256 bits) and encode as URL-safe base64
        return secrets.token_urlsafe(32)
    
    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        return f"mira_key_{secrets.token_hex(8)}"
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _find_key_by_id(self, key_id: str) -> Optional[ApiKey]:
        """Find a key by its ID."""
        for api_key in self._keys_cache.values():
            if api_key.key_id == key_id:
                return api_key
        
        # Try loading from storage
        if self.storage:
            api_key = self._load_key_from_storage_by_id(key_id)
            if api_key:
                self._keys_cache[api_key.key_hash] = api_key
                return api_key
        
        return None
    
    def _update_key(self, api_key: ApiKey):
        """Update a key in cache and storage."""
        self._keys_cache[api_key.key_hash] = api_key
        if self.storage:
            self._save_key_to_storage(api_key)
    
    def _load_keys_from_storage(self):
        """Load all keys from storage backend."""
        if not self.storage:
            return
        
        try:
            # Get keys from storage (Airtable)
            response = self.storage.sync_data('api_keys', {'action': 'list'})
            if response.get('success') and 'keys' in response:
                for key_data in response['keys']:
                    api_key = ApiKey.from_dict(key_data)
                    self._keys_cache[api_key.key_hash] = api_key
                self.logger.info(f"Loaded {len(response['keys'])} keys from storage")
        except Exception as e:
            self.logger.error(f"Error loading keys from storage: {e}")
    
    def _save_key_to_storage(self, api_key: ApiKey):
        """Save a key to storage backend."""
        if not self.storage:
            return
        
        try:
            self.storage.sync_data('api_keys', {
                'action': 'save',
                'key': api_key.to_dict()
            })
        except Exception as e:
            self.logger.error(f"Error saving key to storage: {e}")
    
    def _load_key_from_storage(self, key_hash: str) -> Optional[ApiKey]:
        """Load a specific key from storage by hash."""
        if not self.storage:
            return None
        
        try:
            response = self.storage.sync_data('api_keys', {
                'action': 'get',
                'key_hash': key_hash
            })
            if response.get('success') and 'key' in response:
                return ApiKey.from_dict(response['key'])
        except Exception as e:
            self.logger.error(f"Error loading key from storage: {e}")
        
        return None
    
    def _load_key_from_storage_by_id(self, key_id: str) -> Optional[ApiKey]:
        """Load a specific key from storage by ID."""
        if not self.storage:
            return None
        
        try:
            response = self.storage.sync_data('api_keys', {
                'action': 'get_by_id',
                'key_id': key_id
            })
            if response.get('success') and 'key' in response:
                return ApiKey.from_dict(response['key'])
        except Exception as e:
            self.logger.error(f"Error loading key from storage: {e}")
        
        return None
