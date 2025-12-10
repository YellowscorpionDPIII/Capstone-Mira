"""Webhook security module with IP filtering and shared secrets."""
import ipaddress
from typing import Set, Dict, Optional
import logging


class WebhookSecurity:
    """
    Security controls for webhooks.
    
    Features:
    - IP allow/deny lists
    - Per-service shared secrets
    - Multiple authentication mechanisms
    """
    
    def __init__(self, audit_logger=None):
        """
        Initialize webhook security.
        
        Args:
            audit_logger: Optional audit logger instance
        """
        self.ip_allowlist: Set[str] = set()
        self.ip_denylist: Set[str] = set()
        self.service_secrets: Dict[str, str] = {}
        self.audit_logger = audit_logger
        self.logger = logging.getLogger("mira.security.webhook")
        
    def add_ip_to_allowlist(self, ip_address: str):
        """
        Add IP address or CIDR range to allowlist.
        
        Args:
            ip_address: IP address or CIDR notation (e.g., '192.168.1.0/24')
        """
        try:
            # Validate IP address format
            ipaddress.ip_network(ip_address, strict=False)
            self.ip_allowlist.add(ip_address)
            self.logger.info(f"Added IP to allowlist: {ip_address}")
        except ValueError as e:
            self.logger.error(f"Invalid IP address: {ip_address} - {e}")
            raise
    
    def add_ip_to_denylist(self, ip_address: str):
        """
        Add IP address or CIDR range to denylist.
        
        Args:
            ip_address: IP address or CIDR notation
        """
        try:
            ipaddress.ip_network(ip_address, strict=False)
            self.ip_denylist.add(ip_address)
            self.logger.info(f"Added IP to denylist: {ip_address}")
        except ValueError as e:
            self.logger.error(f"Invalid IP address: {ip_address} - {e}")
            raise
    
    def set_service_secret(self, service: str, secret: str):
        """
        Set shared secret for a service.
        
        Args:
            service: Service name (e.g., 'github', 'trello')
            secret: Shared secret for the service
        """
        self.service_secrets[service] = secret
        self.logger.info(f"Set shared secret for service: {service}")
    
    def check_ip_allowed(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if an IP address is allowed.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Check denylist first
            for denied_range in self.ip_denylist:
                if ip in ipaddress.ip_network(denied_range, strict=False):
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            'ip_blocked',
                            {'ip_address': ip_address, 'reason': 'in_denylist'}
                        )
                    return False, 'in_denylist'
            
            # If allowlist is empty, allow all (except denied)
            if not self.ip_allowlist:
                return True, None
            
            # Check allowlist
            for allowed_range in self.ip_allowlist:
                if ip in ipaddress.ip_network(allowed_range, strict=False):
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            'ip_allowed',
                            {'ip_address': ip_address}
                        )
                    return True, None
            
            # Not in allowlist
            if self.audit_logger:
                self.audit_logger.log_event(
                    'ip_blocked',
                    {'ip_address': ip_address, 'reason': 'not_in_allowlist'}
                )
            return False, 'not_in_allowlist'
            
        except ValueError as e:
            self.logger.error(f"Invalid IP address format: {ip_address} - {e}")
            return False, 'invalid_ip'
    
    def verify_service_secret(self, service: str, provided_secret: str) -> bool:
        """
        Verify shared secret for a service.
        
        Args:
            service: Service name
            provided_secret: Secret provided by the service
            
        Returns:
            True if secret is valid
        """
        if service not in self.service_secrets:
            self.logger.warning(f"No secret configured for service: {service}")
            return False
        
        is_valid = self.service_secrets[service] == provided_secret
        
        if self.audit_logger:
            self.audit_logger.log_event(
                'webhook_auth_success' if is_valid else 'webhook_auth_failed',
                {'service': service, 'method': 'shared_secret'}
            )
        
        return is_valid
    
    def authenticate_webhook(
        self,
        service: str,
        ip_address: str,
        secret: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Authenticate a webhook request.
        
        Args:
            service: Service name
            ip_address: Source IP address
            secret: Optional shared secret
            
        Returns:
            Tuple of (is_authenticated, reason)
        """
        # Check IP first
        ip_allowed, ip_reason = self.check_ip_allowed(ip_address)
        if not ip_allowed:
            return False, f'ip_{ip_reason}'
        
        # If service has a secret configured, verify it
        if service in self.service_secrets:
            if not secret:
                return False, 'missing_secret'
            
            if not self.verify_service_secret(service, secret):
                return False, 'invalid_secret'
        
        # Authentication successful
        if self.audit_logger:
            self.audit_logger.log_event(
                'webhook_auth_success',
                {'service': service, 'ip_address': ip_address}
            )
        
        return True, None
