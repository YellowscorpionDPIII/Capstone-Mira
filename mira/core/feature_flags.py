"""Feature flags and configuration validation with Pydantic."""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from enum import Enum


class FeatureFlagPriority(Enum):
    """Priority levels for feature flags."""
    MAINTENANCE = 1  # Highest priority
    RATE_LIMIT = 2
    NORMAL = 3


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    enabled: bool = Field(default=False, description="Enable rate limiting")
    requests_per_minute: int = Field(
        default=60,
        gt=0,
        description="Maximum requests per minute"
    )
    burst_size: int = Field(
        default=10,
        gt=0,
        description="Maximum burst size"
    )
    
    @field_validator('burst_size')
    @classmethod
    def validate_burst_size(cls, v, info):
        """Ensure burst size is reasonable."""
        if 'requests_per_minute' in info.data:
            rpm = info.data['requests_per_minute']
            if v > rpm:
                raise ValueError(f"burst_size ({v}) cannot exceed requests_per_minute ({rpm})")
        return v


class MaintenanceModeConfig(BaseModel):
    """Configuration for maintenance mode."""
    enabled: bool = Field(default=False, description="Enable maintenance mode")
    message: Optional[str] = Field(
        default=None,
        description="Maintenance mode message displayed to users"
    )
    allowed_ips: Optional[List[str]] = Field(
        default=None,
        description="IPs allowed during maintenance mode"
    )
    
    @model_validator(mode='after')
    def validate_message_when_enabled(self):
        """Ensure message is provided when maintenance mode is enabled."""
        if self.enabled and not self.message:
            raise ValueError("maintenance mode requires a message when enabled")
        return self


class WebhookSecurityConfigModel(BaseModel):
    """Pydantic model for webhook security configuration."""
    enabled: bool = Field(default=True, description="Enable webhook security")
    secret_key: Optional[str] = Field(default=None, description="Secret key for signatures")
    allowed_ips: Optional[List[str]] = Field(
        default=None,
        description="List of allowed IP addresses/CIDR ranges"
    )
    require_signature: bool = Field(
        default=True,
        description="Require HMAC signature verification"
    )
    require_secret: bool = Field(
        default=False,
        description="Require secret header"
    )
    require_ip_whitelist: bool = Field(
        default=False,
        description="Enforce IP whitelist"
    )
    
    @model_validator(mode='after')
    def validate_signature_requirements(self):
        """Ensure secret_key is provided when signature verification is required."""
        if self.require_signature and not self.secret_key:
            raise ValueError("require_signature needs secret_key to be set")
        if self.require_secret and not self.secret_key:
            raise ValueError("require_secret needs secret_key to be set")
        return self


class APIKeyConfigModel(BaseModel):
    """Pydantic model for API key configuration."""
    enabled: bool = Field(default=False, description="Enable API key authentication")
    default_expiry_days: int = Field(
        default=90,
        gt=0,
        description="Default expiration period in days"
    )
    grace_period_seconds: int = Field(
        default=86400,
        gt=0,
        description="Grace period after expiration in seconds"
    )
    storage_backend: str = Field(
        default="memory",
        description="Storage backend: 'memory' or 'file'"
    )
    storage_path: Optional[str] = Field(
        default=None,
        description="Path for file-based storage"
    )
    
    @model_validator(mode='after')
    def validate_storage_path(self):
        """Ensure storage_path is provided when using file backend."""
        if self.storage_backend == "file" and not self.storage_path:
            raise ValueError("storage_path must be provided when storage_backend is 'file'")
        return self


class MetricsConfig(BaseModel):
    """Configuration for metrics collection."""
    enabled: bool = Field(default=True, description="Enable metrics collection")
    export_interval_seconds: int = Field(
        default=60,
        gt=0,
        description="Interval for exporting metrics"
    )


class FeatureFlagsConfig(BaseModel):
    """Main feature flags configuration."""
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    maintenance_mode: MaintenanceModeConfig = Field(default_factory=MaintenanceModeConfig)
    webhook_security: WebhookSecurityConfigModel = Field(default_factory=WebhookSecurityConfigModel)
    api_keys: APIKeyConfigModel = Field(default_factory=APIKeyConfigModel)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    
    def get_active_restrictions(self) -> List[str]:
        """
        Get list of active restrictions based on priority.
        
        Returns:
            List of active restriction names in priority order
        """
        restrictions = []
        
        # Priority 1: Maintenance mode (bypasses everything)
        if self.maintenance_mode.enabled:
            restrictions.append("maintenance_mode")
            return restrictions  # Short-circuit, nothing else matters
        
        # Priority 2: Rate limiting
        if self.rate_limit.enabled:
            restrictions.append("rate_limit")
        
        return restrictions
    
    def is_maintenance_mode(self) -> bool:
        """Check if maintenance mode is active."""
        return self.maintenance_mode.enabled
    
    def is_rate_limited(self) -> bool:
        """Check if rate limiting is active (and not in maintenance)."""
        return self.rate_limit.enabled and not self.maintenance_mode.enabled
