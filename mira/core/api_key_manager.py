"""API Key Manager for secure key lifecycle management."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib
import json
import os
from enum import Enum


class KeyStatus(Enum):
    """Status of an API key."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    GRACE_PERIOD = "grace_period"


class APIKeyRecord:
    """Represents an API key record."""
    
    def __init__(
        self,
        key_id: str,
        key_hash: str,
        created_at: datetime,
        expires_at: Optional[datetime] = None,
        revoked_at: Optional[datetime] = None,
        grace_period_seconds: int = 86400,  # 24 hours default
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an API key record.
        
        Args:
            key_id: Unique identifier for the key
            key_hash: Hash of the API key
            created_at: Timestamp when key was created
            expires_at: Optional expiration timestamp
            revoked_at: Optional revocation timestamp
            grace_period_seconds: Grace period after expiration
            metadata: Optional metadata for the key
        """
        self.key_id = key_id
        self.key_hash = key_hash
        self.created_at = created_at
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.grace_period_seconds = grace_period_seconds
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            'key_id': self.key_id,
            'key_hash': self.key_hash,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'grace_period_seconds': self.grace_period_seconds,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKeyRecord':
        """Create record from dictionary."""
        return cls(
            key_id=data['key_id'],
            key_hash=data['key_hash'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            revoked_at=datetime.fromisoformat(data['revoked_at']) if data.get('revoked_at') else None,
            grace_period_seconds=data.get('grace_period_seconds', 86400),
            metadata=data.get('metadata', {})
        )


class APIKeyStorage(ABC):
    """Abstract base class for API key storage."""
    
    @abstractmethod
    def save(self, key_id: str, record: APIKeyRecord) -> None:
        """Save an API key record."""
        pass
    
    @abstractmethod
    def get(self, key_id: str) -> Optional[APIKeyRecord]:
        """Retrieve an API key record."""
        pass
    
    @abstractmethod
    def delete(self, key_id: str) -> bool:
        """Delete an API key record."""
        pass
    
    @abstractmethod
    def list_all(self) -> List[APIKeyRecord]:
        """List all API key records."""
        pass


class InMemoryAPIKeyStorage(APIKeyStorage):
    """In-memory storage for API keys."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: Dict[str, APIKeyRecord] = {}
    
    def save(self, key_id: str, record: APIKeyRecord) -> None:
        """Save an API key record."""
        self._storage[key_id] = record
    
    def get(self, key_id: str) -> Optional[APIKeyRecord]:
        """Retrieve an API key record."""
        return self._storage.get(key_id)
    
    def delete(self, key_id: str) -> bool:
        """Delete an API key record."""
        if key_id in self._storage:
            del self._storage[key_id]
            return True
        return False
    
    def list_all(self) -> List[APIKeyRecord]:
        """List all API key records."""
        return list(self._storage.values())


class FileAPIKeyStorage(APIKeyStorage):
    """File-based storage for API keys."""
    
    def __init__(self, storage_path: str):
        """
        Initialize file-based storage.
        
        Args:
            storage_path: Path to the storage file
        """
        self.storage_path = storage_path
        self._ensure_storage_file()
    
    def _ensure_storage_file(self) -> None:
        """Ensure storage file exists."""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump({}, f)
    
    def _load_all(self) -> Dict[str, APIKeyRecord]:
        """Load all records from file."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return {
                    key_id: APIKeyRecord.from_dict(record_data)
                    for key_id, record_data in data.items()
                }
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_all(self, records: Dict[str, APIKeyRecord]) -> None:
        """Save all records to file."""
        data = {
            key_id: record.to_dict()
            for key_id, record in records.items()
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save(self, key_id: str, record: APIKeyRecord) -> None:
        """Save an API key record."""
        records = self._load_all()
        records[key_id] = record
        self._save_all(records)
    
    def get(self, key_id: str) -> Optional[APIKeyRecord]:
        """Retrieve an API key record."""
        records = self._load_all()
        return records.get(key_id)
    
    def delete(self, key_id: str) -> bool:
        """Delete an API key record."""
        records = self._load_all()
        if key_id in records:
            del records[key_id]
            self._save_all(records)
            return True
        return False
    
    def list_all(self) -> List[APIKeyRecord]:
        """List all API key records."""
        records = self._load_all()
        return list(records.values())


class APIKeyManager:
    """Manages API key lifecycle: create, rotate, revoke, and validate."""
    
    def __init__(self, storage: APIKeyStorage, default_expiry_days: int = 90):
        """
        Initialize the API key manager.
        
        Args:
            storage: Storage backend for API keys
            default_expiry_days: Default expiration period in days
        """
        self.storage = storage
        self.default_expiry_days = default_expiry_days
    
    def _generate_key(self) -> str:
        """Generate a secure random API key."""
        return secrets.token_urlsafe(32)
    
    def _hash_key(self, api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _is_key_active(self, key_record: APIKeyRecord, now: Optional[datetime] = None) -> KeyStatus:
        """
        Check if a key is active, considering expiry and grace period.
        
        Args:
            key_record: The API key record to check
            now: Current timestamp (defaults to datetime.utcnow())
            
        Returns:
            KeyStatus indicating the current status of the key
        """
        if now is None:
            now = datetime.utcnow()
        
        # Check if revoked
        if key_record.revoked_at is not None:
            return KeyStatus.REVOKED
        
        # Check if expired
        if key_record.expires_at is not None:
            if now > key_record.expires_at:
                grace_end = key_record.expires_at + timedelta(seconds=key_record.grace_period_seconds)
                if now <= grace_end:
                    return KeyStatus.GRACE_PERIOD
                else:
                    return KeyStatus.EXPIRED
        
        return KeyStatus.ACTIVE
    
    def create(
        self,
        key_id: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        grace_period_seconds: int = 86400,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, APIKeyRecord]:
        """
        Create a new API key.
        
        Args:
            key_id: Optional custom key ID (auto-generated if not provided)
            expires_in_days: Optional expiration period in days
            grace_period_seconds: Grace period after expiration
            metadata: Optional metadata for the key
            
        Returns:
            Tuple of (api_key, key_record)
        """
        # Generate key and ID
        api_key = self._generate_key()
        if key_id is None:
            key_id = f"key_{secrets.token_hex(8)}"
        
        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = None
        if expires_in_days is not None:
            expires_at = created_at + timedelta(days=expires_in_days)
        elif self.default_expiry_days:
            expires_at = created_at + timedelta(days=self.default_expiry_days)
        
        # Create record
        key_record = APIKeyRecord(
            key_id=key_id,
            key_hash=self._hash_key(api_key),
            created_at=created_at,
            expires_at=expires_at,
            grace_period_seconds=grace_period_seconds,
            metadata=metadata
        )
        
        # Save to storage
        self.storage.save(key_id, key_record)
        
        return api_key, key_record
    
    def rotate(self, key_id: str, expires_in_days: Optional[int] = None) -> tuple[str, APIKeyRecord]:
        """
        Rotate an existing API key.
        
        Args:
            key_id: ID of the key to rotate
            expires_in_days: Optional new expiration period in days
            
        Returns:
            Tuple of (new_api_key, key_record)
            
        Raises:
            ValueError: If key_id does not exist
        """
        old_record = self.storage.get(key_id)
        if old_record is None:
            raise ValueError(f"Key ID {key_id} not found")
        
        # Generate new key
        new_api_key = self._generate_key()
        
        # Calculate new expiration
        created_at = datetime.utcnow()
        expires_at = None
        if expires_in_days is not None:
            expires_at = created_at + timedelta(days=expires_in_days)
        elif self.default_expiry_days:
            expires_at = created_at + timedelta(days=self.default_expiry_days)
        
        # Update record
        new_record = APIKeyRecord(
            key_id=key_id,
            key_hash=self._hash_key(new_api_key),
            created_at=created_at,
            expires_at=expires_at,
            grace_period_seconds=old_record.grace_period_seconds,
            metadata=old_record.metadata
        )
        
        # Save updated record
        self.storage.save(key_id, new_record)
        
        return new_api_key, new_record
    
    def revoke(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of the key to revoke
            
        Returns:
            True if key was revoked, False if key not found
        """
        key_record = self.storage.get(key_id)
        if key_record is None:
            return False
        
        # Mark as revoked
        key_record.revoked_at = datetime.utcnow()
        self.storage.save(key_id, key_record)
        
        return True
    
    def validate(self, api_key: str) -> tuple[bool, Optional[str], Optional[KeyStatus]]:
        """
        Validate an API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, key_id, status)
        """
        key_hash = self._hash_key(api_key)
        
        # Search for matching key
        for record in self.storage.list_all():
            if record.key_hash == key_hash:
                status = self._is_key_active(record)
                is_valid = status in (KeyStatus.ACTIVE, KeyStatus.GRACE_PERIOD)
                return is_valid, record.key_id, status
        
        return False, None, None
    
    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a key.
        
        Args:
            key_id: ID of the key
            
        Returns:
            Dictionary with key information or None if not found
        """
        record = self.storage.get(key_id)
        if record is None:
            return None
        
        status = self._is_key_active(record)
        
        return {
            'key_id': record.key_id,
            'created_at': record.created_at.isoformat(),
            'expires_at': record.expires_at.isoformat() if record.expires_at else None,
            'revoked_at': record.revoked_at.isoformat() if record.revoked_at else None,
            'status': status.value,
            'metadata': record.metadata
        }
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """
        List all API keys.
        
        Returns:
            List of key information dictionaries
        """
        keys = []
        for record in self.storage.list_all():
            status = self._is_key_active(record)
            keys.append({
                'key_id': record.key_id,
                'created_at': record.created_at.isoformat(),
                'expires_at': record.expires_at.isoformat() if record.expires_at else None,
                'revoked_at': record.revoked_at.isoformat() if record.revoked_at else None,
                'status': status.value,
                'metadata': record.metadata
            })
        return keys
