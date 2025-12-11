"""API Key Manager with rotation and expiry support."""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import logging


@dataclass
class APIKey:
    """Represents an API key with metadata."""
    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    rotated_from: Optional[str] = None
    revoked: bool = False
    metadata: Dict = field(default_factory=dict)
    last_used_at: Optional[datetime] = None
    requests_per_hour: Optional[int] = None
    usage_count: int = 0


class APIKeyManager:
    """
    Manages API keys with rotation and expiry support.
    
    Features:
    - Generate API keys with optional expiry
    - Rotate keys without disrupting active clients
    - Validate keys and check expiry
    - Revoke keys
    - Audit trail via audit logger
    """
    
    def __init__(self, audit_logger=None):
        """
        Initialize API Key Manager.
        
        Args:
            audit_logger: Optional audit logger instance
        """
        self.keys: Dict[str, APIKey] = {}
        self.audit_logger = audit_logger
        self.logger = logging.getLogger("mira.security.api_key_manager")
        
    def generate_key(
        self, 
        name: str, 
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict] = None,
        requests_per_hour: Optional[int] = None
    ) -> tuple[str, str]:
        """
        Generate a new API key.
        
        Args:
            name: Descriptive name for the key
            expires_in_days: Optional expiry in days
            metadata: Optional metadata to attach to the key
            requests_per_hour: Optional usage quota (requests per hour)
            
        Returns:
            Tuple of (key_id, raw_key)
        """
        # Generate secure random key
        raw_key = secrets.token_urlsafe(32)
        key_hash = self._hash_key(raw_key)
        key_id = secrets.token_urlsafe(16)
        
        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store key
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {},
            requests_per_hour=requests_per_hour
        )
        self.keys[key_id] = api_key
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log_event(
                'api_key_created',
                {
                    'key_id': key_id,
                    'name': name,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'requests_per_hour': requests_per_hour
                }
            )
        
        self.logger.info(f"API key created: {key_id} (name: {name})")
        return key_id, raw_key
    
    def rotate_key(self, old_key_id: str, grace_period_days: int = 7) -> tuple[str, str]:
        """
        Rotate an API key with grace period.
        
        Args:
            old_key_id: ID of the key to rotate
            grace_period_days: Days to keep old key valid
            
        Returns:
            Tuple of (new_key_id, new_raw_key)
            
        Raises:
            ValueError: If old key doesn't exist
        """
        if old_key_id not in self.keys:
            raise ValueError(f"Key not found: {old_key_id}")
        
        old_key = self.keys[old_key_id]
        if old_key.revoked:
            raise ValueError(f"Cannot rotate revoked key: {old_key_id}")
        
        # Generate new key with same properties
        new_key_id, new_raw_key = self.generate_key(
            name=old_key.name,
            expires_in_days=grace_period_days,
            metadata={**old_key.metadata, 'rotated_from': old_key_id}
        )
        
        # Mark new key as rotated
        self.keys[new_key_id].rotated_from = old_key_id
        
        # Set expiry on old key (grace period)
        old_key.expires_at = datetime.utcnow() + timedelta(days=grace_period_days)
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log_event(
                'api_key_rotated',
                {
                    'old_key_id': old_key_id,
                    'new_key_id': new_key_id,
                    'grace_period_days': grace_period_days
                }
            )
        
        self.logger.info(f"API key rotated: {old_key_id} -> {new_key_id}")
        return new_key_id, new_raw_key
    
    def validate_key(self, raw_key: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate an API key.
        
        Args:
            raw_key: Raw API key to validate
            
        Returns:
            Tuple of (is_valid, key_id, reason)
        """
        key_hash = self._hash_key(raw_key)
        
        # Find matching key
        for key_id, api_key in self.keys.items():
            if api_key.key_hash == key_hash:
                # Check if revoked
                if api_key.revoked:
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            'api_key_validation_failed',
                            {'key_id': key_id, 'reason': 'revoked'}
                        )
                    return False, key_id, 'revoked'
                
                # Check if expired
                if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            'api_key_validation_failed',
                            {'key_id': key_id, 'reason': 'expired'}
                        )
                    return False, key_id, 'expired'
                
                # Check usage quota
                if api_key.requests_per_hour:
                    # Check requests in the last hour
                    hour_ago = datetime.utcnow() - timedelta(hours=1)
                    if api_key.last_used_at and api_key.last_used_at > hour_ago:
                        # In production, would track actual request counts
                        # For now, we'll just update the last_used_at
                        pass
                
                # Update usage tracking
                api_key.last_used_at = datetime.utcnow()
                api_key.usage_count += 1
                
                # Valid key
                if self.audit_logger:
                    self.audit_logger.log_event(
                        'api_key_validation_success',
                        {'key_id': key_id}
                    )
                return True, key_id, None
        
        # Key not found
        if self.audit_logger:
            self.audit_logger.log_event(
                'api_key_validation_failed',
                {'reason': 'not_found'}
            )
        return False, None, 'not_found'
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of key to revoke
            
        Returns:
            True if revoked successfully
        """
        if key_id not in self.keys:
            return False
        
        self.keys[key_id].revoked = True
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log_event(
                'api_key_revoked',
                {'key_id': key_id}
            )
        
        self.logger.info(f"API key revoked: {key_id}")
        return True
    
    def list_keys(self, include_revoked: bool = False) -> List[Dict]:
        """
        List all API keys.
        
        Args:
            include_revoked: Whether to include revoked keys
            
        Returns:
            List of key information (excluding hashes)
        """
        keys_info = []
        for key_id, api_key in self.keys.items():
            if not include_revoked and api_key.revoked:
                continue
            
            keys_info.append({
                'key_id': key_id,
                'name': api_key.name,
                'created_at': api_key.created_at.isoformat(),
                'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None,
                'revoked': api_key.revoked,
                'rotated_from': api_key.rotated_from,
                'metadata': api_key.metadata,
                'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                'usage_count': api_key.usage_count,
                'requests_per_hour': api_key.requests_per_hour
            })
        
        return keys_info
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired and revoked keys.
        
        Returns:
            Number of keys removed
        """
        now = datetime.utcnow()
        to_remove = []
        
        for key_id, api_key in self.keys.items():
            if api_key.revoked or (api_key.expires_at and now > api_key.expires_at):
                # Keep keys for audit trail for 30 days after expiry
                if api_key.expires_at and (now - api_key.expires_at).days > 30:
                    to_remove.append(key_id)
                elif api_key.revoked and (now - api_key.created_at).days > 30:
                    to_remove.append(key_id)
        
        for key_id in to_remove:
            del self.keys[key_id]
            self.logger.info(f"Cleaned up expired key: {key_id}")
        
        return len(to_remove)
    
    def rotate_unused_keys(self, days_unused: int = 90) -> List[tuple[str, str]]:
        """
        Automatically rotate keys that haven't been used in the specified period.
        
        Args:
            days_unused: Number of days of inactivity before rotation
            
        Returns:
            List of tuples (old_key_id, new_key_id) for rotated keys
        """
        now = datetime.utcnow()
        rotated = []
        
        for key_id, api_key in list(self.keys.items()):
            if api_key.revoked:
                continue
            
            # Check if key hasn't been used
            if api_key.last_used_at is None:
                # Never used - check age
                days_since_creation = (now - api_key.created_at).days
                if days_since_creation >= days_unused:
                    try:
                        new_key_id, _ = self.rotate_key(key_id, grace_period_days=7)
                        rotated.append((key_id, new_key_id))
                        self.logger.info(f"Auto-rotated unused key: {key_id} -> {new_key_id}")
                    except ValueError as e:
                        self.logger.error(f"Failed to rotate key {key_id}: {e}")
            else:
                # Check last usage
                days_since_use = (now - api_key.last_used_at).days
                if days_since_use >= days_unused:
                    try:
                        new_key_id, _ = self.rotate_key(key_id, grace_period_days=7)
                        rotated.append((key_id, new_key_id))
                        self.logger.info(f"Auto-rotated inactive key: {key_id} -> {new_key_id}")
                    except ValueError as e:
                        self.logger.error(f"Failed to rotate key {key_id}: {e}")
        
        return rotated
    
    def export_key_inventory_csv(self, filepath: str) -> bool:
        """
        Export key inventory to CSV for compliance audits.
        
        Args:
            filepath: Path to output CSV file
            
        Returns:
            True if export successful
        """
        import csv
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = [
                    'key_id', 'name', 'created_at', 'expires_at', 
                    'last_used_at', 'usage_count', 'requests_per_hour',
                    'revoked', 'rotated_from', 'status'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                now = datetime.utcnow()
                for key_id, api_key in self.keys.items():
                    # Determine status
                    if api_key.revoked:
                        status = 'revoked'
                    elif api_key.expires_at and now > api_key.expires_at:
                        status = 'expired'
                    else:
                        status = 'active'
                    
                    writer.writerow({
                        'key_id': key_id,
                        'name': api_key.name,
                        'created_at': api_key.created_at.isoformat(),
                        'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else '',
                        'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else '',
                        'usage_count': api_key.usage_count,
                        'requests_per_hour': api_key.requests_per_hour or '',
                        'revoked': api_key.revoked,
                        'rotated_from': api_key.rotated_from or '',
                        'status': status
                    })
            
            self.logger.info(f"Exported key inventory to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export key inventory: {e}")
            return False
    
    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
