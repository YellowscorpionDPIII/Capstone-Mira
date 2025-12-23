"""Audit logger for security events."""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events."""
    API_KEY_CREATED = "api_key_created"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_VALIDATION_SUCCESS = "api_key_validation_success"
    API_KEY_VALIDATION_FAILED = "api_key_validation_failed"
    WEBHOOK_AUTH_SUCCESS = "webhook_auth_success"
    WEBHOOK_AUTH_FAILED = "webhook_auth_failed"
    IP_BLOCKED = "ip_blocked"
    IP_ALLOWED = "ip_allowed"


class AuditLogger:
    """
    Dedicated audit log sink for authentication and security events.
    
    Provides structured logging of all authentication decisions,
    key lifecycle events, and security-related activities.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize audit logger.
        
        Args:
            log_file: Optional file path for audit logs
        """
        self.logger = logging.getLogger("mira.audit")
        self.logger.setLevel(logging.INFO)
        
        # Create structured formatter
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., 'api_key_created')
            details: Event-specific details
            user_id: Optional user identifier
            ip_address: Optional IP address
        """
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details
        }
        
        if user_id:
            audit_entry['user_id'] = user_id
        
        if ip_address:
            audit_entry['ip_address'] = ip_address
        
        # Log as structured JSON
        self.logger.info(json.dumps(audit_entry))
    
    def log_authentication(
        self,
        success: bool,
        method: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """
        Log authentication attempt.
        
        Args:
            success: Whether authentication succeeded
            method: Authentication method (e.g., 'api_key', 'webhook_secret')
            details: Additional details
            ip_address: Optional IP address
        """
        event_type = 'authentication_success' if success else 'authentication_failed'
        self.log_event(
            event_type,
            {
                'method': method,
                **details
            },
            ip_address=ip_address
        )
    
    def log_key_lifecycle(
        self,
        action: str,
        key_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log API key lifecycle event.
        
        Args:
            action: Action type (create, rotate, revoke)
            key_id: Key identifier
            details: Optional additional details
        """
        self.log_event(
            f'api_key_{action}',
            {
                'key_id': key_id,
                **(details or {})
            }
        )
