"""API Key Management system for Mira platform."""
import secrets
import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
from mira.core.rbac import Role


class APIKey:
    """Represents an API key with metadata."""
    
    def __init__(
        self,
        key_id: str,
        user_id: str,
        role: Role,
        name: str = "",
        hashed_key: str = "",
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        is_active: bool = True,
        last_used_at: Optional[datetime] = None,
    ):
        """
        Initialize an API key.
        
        Args:
            key_id: Unique identifier for the key
            user_id: User who owns the key
            role: User's role
            name: Human-readable name for the key
            hashed_key: Hashed version of the key
            created_at: Creation timestamp
            expires_at: Expiration timestamp
            is_active: Whether the key is active
            last_used_at: Last usage timestamp
        """
        self.key_id = key_id
        self.user_id = user_id
        self.role = role if isinstance(role, Role) else Role(role)
        self.name = name
        self.hashed_key = hashed_key
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at
        self.is_active = is_active
        self.last_used_at = last_used_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert API key to dictionary."""
        return {
            'key_id': self.key_id,
            'user_id': self.user_id,
            'role': self.role.value,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKey':
        """Create API key from dictionary."""
        return cls(
            key_id=data['key_id'],
            user_id=data['user_id'],
            role=data['role'],
            name=data.get('name', ''),
            hashed_key=data.get('hashed_key', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            is_active=data.get('is_active', True),
            last_used_at=datetime.fromisoformat(data['last_used_at']) if data.get('last_used_at') else None,
        )


class APIKeyManager:
    """Manage API keys for authentication and authorization."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize API key manager.
        
        Args:
            storage_path: Path to store API keys (JSON file)
        """
        self.logger = logging.getLogger("mira.api_keys")
        self.storage_path = storage_path or "/tmp/mira_api_keys.json"
        self.keys: Dict[str, APIKey] = {}
        self._load_keys()
    
    def _hash_key(self, key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Args:
            key: Raw API key
            
        Returns:
            Hashed key
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _generate_key(self) -> str:
        """
        Generate a new API key.
        
        Returns:
            New API key string
        """
        return f"mira_{secrets.token_urlsafe(32)}"
    
    def _load_keys(self):
        """Load API keys from storage."""
        try:
            path = Path(self.storage_path)
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.keys = {
                        key_id: APIKey.from_dict(key_data)
                        for key_id, key_data in data.items()
                    }
                self.logger.info(f"Loaded {len(self.keys)} API keys from storage")
        except Exception as e:
            self.logger.error(f"Error loading API keys: {e}")
            self.keys = {}
    
    def _save_keys(self):
        """Save API keys to storage."""
        try:
            path = Path(self.storage_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                key_id: key.to_dict()
                for key_id, key in self.keys.items()
            }
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.keys)} API keys to storage")
        except Exception as e:
            self.logger.error(f"Error saving API keys: {e}")
    
    def generate_key(
        self,
        user_id: str,
        role: Role,
        name: str = "",
        expires_in_days: Optional[int] = None
    ) -> tuple[str, APIKey]:
        """
        Generate a new API key.
        
        Args:
            user_id: User ID who owns the key
            role: User's role
            name: Human-readable name for the key
            expires_in_days: Number of days until expiration (None = no expiration)
            
        Returns:
            Tuple of (raw_key, api_key_object)
        """
        key = self._generate_key()
        key_id = secrets.token_urlsafe(16)
        hashed_key = self._hash_key(key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            role=role,
            name=name,
            hashed_key=hashed_key,
            expires_at=expires_at,
        )
        
        self.keys[key_id] = api_key
        self._save_keys()
        
        self.logger.info(f"Generated API key {key_id} for user {user_id} with role {role.value}")
        return key, api_key
    
    def validate_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key and return associated metadata.
        
        Args:
            key: Raw API key
            
        Returns:
            APIKey object if valid, None otherwise
        """
        hashed = self._hash_key(key)
        
        for api_key in self.keys.values():
            if api_key.hashed_key == hashed:
                # Check if key is active
                if not api_key.is_active:
                    self.logger.warning(f"Attempted use of inactive key {api_key.key_id}")
                    return None
                
                # Check if key is expired
                if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                    self.logger.warning(f"Attempted use of expired key {api_key.key_id}")
                    return None
                
                # Update last used timestamp
                api_key.last_used_at = datetime.utcnow()
                self._save_keys()
                
                return api_key
        
        return None
    
    def list_keys(self, user_id: Optional[str] = None) -> List[APIKey]:
        """
        List API keys, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of API keys
        """
        keys = list(self.keys.values())
        
        if user_id:
            keys = [k for k in keys if k.user_id == user_id]
        
        return keys
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke (deactivate) an API key.
        
        Args:
            key_id: Key ID to revoke
            
        Returns:
            True if revoked, False if not found
        """
        if key_id in self.keys:
            self.keys[key_id].is_active = False
            self._save_keys()
            self.logger.info(f"Revoked API key {key_id}")
            return True
        
        self.logger.warning(f"Attempted to revoke non-existent key {key_id}")
        return False
    
    def delete_key(self, key_id: str) -> bool:
        """
        Permanently delete an API key.
        
        Args:
            key_id: Key ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if key_id in self.keys:
            del self.keys[key_id]
            self._save_keys()
            self.logger.info(f"Deleted API key {key_id}")
            return True
        
        self.logger.warning(f"Attempted to delete non-existent key {key_id}")
        return False
    
    def get_key(self, key_id: str) -> Optional[APIKey]:
        """
        Get an API key by ID.
        
        Args:
            key_id: Key ID
            
        Returns:
            APIKey object if found, None otherwise
        """
        return self.keys.get(key_id)


# Global API key manager instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(storage_path: Optional[str] = None) -> APIKeyManager:
    """
    Get the global API key manager instance.
    
    Args:
        storage_path: Optional storage path
        
    Returns:
        API key manager instance
    """
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(storage_path)
    return _api_key_manager
