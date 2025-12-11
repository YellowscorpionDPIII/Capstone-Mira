"""Enhanced webhook security with IP validation, secret checking, and signature verification."""
from enum import Enum
from typing import Optional, List, Set
import hmac
import hashlib
import ipaddress
import logging


class AuthFailureReason(Enum):
    """Reasons for authentication failure."""
    AUTH_IP_BLOCKED = "ip_blocked"
    AUTH_SECRET_MISMATCH = "secret_mismatch"
    AUTH_SIGNATURE_INVALID = "signature_invalid"
    AUTH_SUCCESS = "success"


class WebhookSecurityConfig:
    """Configuration for webhook security."""
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
        require_signature: bool = True,
        require_secret: bool = False,
        require_ip_whitelist: bool = False
    ):
        """
        Initialize webhook security configuration.
        
        Args:
            secret_key: Secret key for HMAC signature verification
            allowed_ips: List of allowed IP addresses/CIDR ranges
            require_signature: Whether to require signature verification
            require_secret: Whether to require secret header
            require_ip_whitelist: Whether to enforce IP whitelist
        """
        self.secret_key = secret_key
        self.require_signature = require_signature
        self.require_secret = require_secret
        self.require_ip_whitelist = require_ip_whitelist
        
        # Pre-validate and convert IP CIDR at startup
        self.allowed_networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()
        if allowed_ips:
            for ip_or_cidr in allowed_ips:
                try:
                    # Try parsing as network (CIDR)
                    network = ipaddress.ip_network(ip_or_cidr, strict=False)
                    self.allowed_networks.add(network)
                except ValueError as e:
                    raise ValueError(f"Invalid IP/CIDR configuration: {ip_or_cidr}") from e


class WebhookAuthenticator:
    """Handles webhook authentication pipeline."""
    
    def __init__(self, config: WebhookSecurityConfig):
        """
        Initialize webhook authenticator.
        
        Args:
            config: Security configuration
        """
        self.config = config
        self.logger = logging.getLogger("mira.webhook.security")
    
    def authenticate(
        self,
        client_ip: str,
        payload: bytes,
        signature_header: Optional[str] = None,
        secret_header: Optional[str] = None
    ) -> tuple[bool, AuthFailureReason]:
        """
        Authenticate webhook request with pipeline: IP → secret → signature.
        
        Args:
            client_ip: Client IP address
            payload: Request payload bytes
            signature_header: Signature from request header
            secret_header: Secret from request header
            
        Returns:
            Tuple of (is_authenticated, failure_reason)
        """
        # Step 1: Check IP whitelist
        if self.config.require_ip_whitelist:
            ip_valid = self._check_ip(client_ip)
            if not ip_valid:
                self.logger.warning(f"IP blocked: {client_ip}")
                return False, AuthFailureReason.AUTH_IP_BLOCKED
        
        # Step 2: Check secret header
        if self.config.require_secret:
            secret_valid = self._check_secret(secret_header)
            if not secret_valid:
                self.logger.warning(f"Secret mismatch from IP: {client_ip}")
                return False, AuthFailureReason.AUTH_SECRET_MISMATCH
        
        # Step 3: Check signature
        if self.config.require_signature and self.config.secret_key:
            signature_valid = self._check_signature(payload, signature_header)
            if not signature_valid:
                self.logger.warning(f"Invalid signature from IP: {client_ip}")
                return False, AuthFailureReason.AUTH_SIGNATURE_INVALID
        
        self.logger.info(f"Webhook authenticated from IP: {client_ip}")
        return True, AuthFailureReason.AUTH_SUCCESS
    
    def _check_ip(self, client_ip: str) -> bool:
        """
        Check if client IP is in allowed networks.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if IP is allowed
        """
        if not self.config.allowed_networks:
            return True
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for network in self.config.allowed_networks:
                if client_addr in network:
                    return True
        except ValueError:
            self.logger.error(f"Invalid IP address: {client_ip}")
            return False
        
        return False
    
    def _check_secret(self, secret_header: Optional[str]) -> bool:
        """
        Check if secret header matches configured secret.
        
        Args:
            secret_header: Secret from request header
            
        Returns:
            True if secret is valid
        """
        if not self.config.secret_key:
            return True
        
        if secret_header is None:
            return False
        
        return hmac.compare_digest(secret_header, self.config.secret_key)
    
    def _check_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Verify HMAC signature of payload.
        
        Args:
            payload: Request payload bytes
            signature_header: Signature from request header
            
        Returns:
            True if signature is valid
        """
        if not self.config.secret_key:
            return True
        
        if signature_header is None:
            return False
        
        # Support multiple signature formats
        expected_signatures = [
            # GitHub format: sha256=<hex>
            'sha256=' + hmac.new(
                self.config.secret_key.encode(),
                payload,
                hashlib.sha256
            ).hexdigest(),
            # Raw hex format
            hmac.new(
                self.config.secret_key.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
        ]
        
        for expected in expected_signatures:
            if hmac.compare_digest(expected, signature_header):
                return True
        
        return False
