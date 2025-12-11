"""Tests for feature flags and configuration validation."""
import unittest
from pydantic import ValidationError
from mira.core.feature_flags import (
    RateLimitConfig,
    MaintenanceModeConfig,
    WebhookSecurityConfigModel,
    APIKeyConfigModel,
    FeatureFlagsConfig,
    FeatureFlagPriority
)


class TestRateLimitConfig(unittest.TestCase):
    """Test cases for rate limit configuration."""
    
    def test_valid_config(self):
        """Test valid rate limit configuration."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            burst_size=20
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.requests_per_minute, 100)
        self.assertEqual(config.burst_size, 20)
    
    def test_positive_requests_per_minute(self):
        """Test that requests_per_minute must be positive."""
        with self.assertRaises(ValidationError):
            RateLimitConfig(requests_per_minute=0)
        
        with self.assertRaises(ValidationError):
            RateLimitConfig(requests_per_minute=-1)
    
    def test_positive_burst_size(self):
        """Test that burst_size must be positive."""
        with self.assertRaises(ValidationError):
            RateLimitConfig(burst_size=0)
        
        with self.assertRaises(ValidationError):
            RateLimitConfig(burst_size=-1)
    
    def test_burst_size_validation(self):
        """Test that burst_size cannot exceed requests_per_minute."""
        with self.assertRaises(ValidationError):
            RateLimitConfig(
                requests_per_minute=60,
                burst_size=100
            )


class TestMaintenanceModeConfig(unittest.TestCase):
    """Test cases for maintenance mode configuration."""
    
    def test_valid_config(self):
        """Test valid maintenance mode configuration."""
        config = MaintenanceModeConfig(
            enabled=True,
            message="System under maintenance",
            allowed_ips=["10.0.0.1"]
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.message, "System under maintenance")
        self.assertEqual(len(config.allowed_ips), 1)
    
    def test_message_required_when_enabled(self):
        """Test that message is required when maintenance mode is enabled."""
        with self.assertRaises(ValidationError) as ctx:
            MaintenanceModeConfig(enabled=True)
        
        self.assertIn("maintenance mode requires a message", str(ctx.exception))
    
    def test_disabled_without_message(self):
        """Test that disabled maintenance mode doesn't require message."""
        config = MaintenanceModeConfig(enabled=False)
        
        self.assertFalse(config.enabled)
        self.assertIsNone(config.message)


class TestWebhookSecurityConfigModel(unittest.TestCase):
    """Test cases for webhook security configuration."""
    
    def test_valid_config(self):
        """Test valid webhook security configuration."""
        config = WebhookSecurityConfigModel(
            enabled=True,
            secret_key="test_secret",
            allowed_ips=["192.168.1.0/24"],
            require_signature=True
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.secret_key, "test_secret")
    
    def test_require_signature_needs_secret_key(self):
        """Test that require_signature needs secret_key."""
        with self.assertRaises(ValidationError) as ctx:
            WebhookSecurityConfigModel(
                require_signature=True,
                secret_key=None
            )
        
        self.assertIn("require_signature needs secret_key", str(ctx.exception))
    
    def test_require_secret_needs_secret_key(self):
        """Test that require_secret needs secret_key."""
        with self.assertRaises(ValidationError) as ctx:
            WebhookSecurityConfigModel(
                require_secret=True,
                secret_key=None
            )
        
        self.assertIn("require_secret needs secret_key", str(ctx.exception))


class TestAPIKeyConfigModel(unittest.TestCase):
    """Test cases for API key configuration."""
    
    def test_valid_config(self):
        """Test valid API key configuration."""
        config = APIKeyConfigModel(
            enabled=True,
            default_expiry_days=90,
            grace_period_seconds=86400,
            storage_backend="memory"
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.default_expiry_days, 90)
        self.assertEqual(config.storage_backend, "memory")
    
    def test_positive_expiry_days(self):
        """Test that expiry days must be positive."""
        with self.assertRaises(ValidationError):
            APIKeyConfigModel(default_expiry_days=0)
        
        with self.assertRaises(ValidationError):
            APIKeyConfigModel(default_expiry_days=-1)
    
    def test_positive_grace_period(self):
        """Test that grace period must be positive."""
        with self.assertRaises(ValidationError):
            APIKeyConfigModel(grace_period_seconds=0)
    
    def test_file_backend_needs_storage_path(self):
        """Test that file backend requires storage_path."""
        with self.assertRaises(ValidationError) as ctx:
            APIKeyConfigModel(
                storage_backend="file",
                storage_path=None
            )
        
        self.assertIn("storage_path must be provided", str(ctx.exception))
    
    def test_memory_backend_no_path_needed(self):
        """Test that memory backend doesn't need storage_path."""
        config = APIKeyConfigModel(
            storage_backend="memory",
            storage_path=None
        )
        
        self.assertEqual(config.storage_backend, "memory")


class TestFeatureFlagsConfig(unittest.TestCase):
    """Test cases for main feature flags configuration."""
    
    def test_default_config(self):
        """Test default feature flags configuration."""
        config = FeatureFlagsConfig()
        
        self.assertFalse(config.rate_limit.enabled)
        self.assertFalse(config.maintenance_mode.enabled)
        self.assertTrue(config.webhook_security.enabled)
        self.assertFalse(config.api_keys.enabled)
        self.assertTrue(config.metrics.enabled)
    
    def test_get_active_restrictions_empty(self):
        """Test getting active restrictions when none are active."""
        config = FeatureFlagsConfig()
        
        restrictions = config.get_active_restrictions()
        self.assertEqual(len(restrictions), 0)
    
    def test_get_active_restrictions_rate_limit(self):
        """Test getting active restrictions with rate limit."""
        config = FeatureFlagsConfig(
            rate_limit=RateLimitConfig(enabled=True)
        )
        
        restrictions = config.get_active_restrictions()
        self.assertIn("rate_limit", restrictions)
    
    def test_maintenance_mode_priority(self):
        """Test that maintenance mode has highest priority."""
        config = FeatureFlagsConfig(
            maintenance_mode=MaintenanceModeConfig(
                enabled=True,
                message="Under maintenance"
            ),
            rate_limit=RateLimitConfig(enabled=True)
        )
        
        restrictions = config.get_active_restrictions()
        
        # Should only contain maintenance mode (bypasses everything else)
        self.assertEqual(restrictions, ["maintenance_mode"])
    
    def test_is_maintenance_mode(self):
        """Test maintenance mode check."""
        config = FeatureFlagsConfig(
            maintenance_mode=MaintenanceModeConfig(
                enabled=True,
                message="Under maintenance"
            )
        )
        
        self.assertTrue(config.is_maintenance_mode())
    
    def test_is_rate_limited(self):
        """Test rate limit check."""
        config = FeatureFlagsConfig(
            rate_limit=RateLimitConfig(enabled=True)
        )
        
        self.assertTrue(config.is_rate_limited())
    
    def test_rate_limit_bypassed_in_maintenance(self):
        """Test that rate limit is bypassed during maintenance."""
        config = FeatureFlagsConfig(
            maintenance_mode=MaintenanceModeConfig(
                enabled=True,
                message="Under maintenance"
            ),
            rate_limit=RateLimitConfig(enabled=True)
        )
        
        # Rate limit should be bypassed
        self.assertFalse(config.is_rate_limited())
    
    def test_nested_config_validation(self):
        """Test that nested config validation works."""
        with self.assertRaises(ValidationError):
            FeatureFlagsConfig(
                api_keys=APIKeyConfigModel(
                    storage_backend="file",
                    storage_path=None  # Should fail validation
                )
            )


if __name__ == '__main__':
    unittest.main()
