"""Integration test demonstrating security, observability, and operational features."""
import unittest
import json
from mira.security.api_key_manager import APIKeyManager
from mira.security.audit_logger import AuditLogger
from mira.security.webhook_security import WebhookSecurity
from mira.observability.metrics import MetricsCollector
from mira.observability.health import HealthCheck
from mira.config.validation import validate_config, ValidationError


class TestIntegration(unittest.TestCase):
    """Integration tests for the enhanced Mira platform."""
    
    def test_complete_security_flow(self):
        """Test complete security workflow."""
        # Setup
        audit_logger = AuditLogger()
        api_key_manager = APIKeyManager(audit_logger=audit_logger)
        webhook_security = WebhookSecurity(audit_logger=audit_logger)
        
        # Generate API key
        key_id, raw_key = api_key_manager.generate_key(
            "integration-test",
            expires_in_days=30
        )
        self.assertIsNotNone(key_id)
        self.assertIsNotNone(raw_key)
        
        # Validate key
        is_valid, validated_key_id, reason = api_key_manager.validate_key(raw_key)
        self.assertTrue(is_valid)
        self.assertEqual(validated_key_id, key_id)
        
        # Configure webhook security
        webhook_security.add_ip_to_allowlist("192.168.1.0/24")
        webhook_security.set_service_secret("github", "test_secret")
        
        # Test webhook authentication
        is_auth, auth_reason = webhook_security.authenticate_webhook(
            "github",
            "192.168.1.100",
            "test_secret"
        )
        self.assertTrue(is_auth)
        
        # Rotate key
        new_key_id, new_raw_key = api_key_manager.rotate_key(key_id, grace_period_days=7)
        self.assertIsNotNone(new_key_id)
        self.assertNotEqual(key_id, new_key_id)
        
        # Both old and new keys should work during grace period
        self.assertTrue(api_key_manager.validate_key(raw_key)[0])
        self.assertTrue(api_key_manager.validate_key(new_raw_key)[0])
        
    def test_complete_observability_flow(self):
        """Test complete observability workflow."""
        # Setup
        metrics = MetricsCollector(enabled=True)
        health = HealthCheck()
        
        # Register health check
        def mock_dependency_check():
            return True, "Dependency healthy"
        
        health.register_dependency("test_dep", mock_dependency_check)
        
        # Record metrics
        metrics.increment("requests.total")
        metrics.increment("requests.total", tags={"endpoint": "/api/v1"})
        metrics.gauge("queue.size", 42)
        
        with metrics.timer("operation.duration"):
            # Simulate operation
            import time
            time.sleep(0.01)
        
        # Verify metrics - tags create separate keys
        self.assertEqual(metrics.get_counter("requests.total"), 1)
        self.assertEqual(metrics.get_counter("requests.total", tags={"endpoint": "/api/v1"}), 1)
        self.assertEqual(metrics.get_gauge("queue.size"), 42)
        
        timer_stats = metrics.get_timer_stats("operation.duration")
        self.assertEqual(timer_stats['count'], 1)
        self.assertGreater(timer_stats['avg'], 10)  # Should be > 10ms
        
        # Check health
        health_status = health.check_health()
        self.assertEqual(health_status['status'], 'healthy')
        
        ready_status = health.check_ready()
        self.assertEqual(ready_status['status'], 'healthy')
        self.assertIn('test_dep', ready_status['dependencies'])
        
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid config
        valid_config = {
            "webhook": {
                "port": 5000,
                "enabled": True
            },
            "security": {
                "api_key_enabled": True,
                "api_key_expiry_days": 30
            },
            "operational": {
                "maintenance_mode": False,
                "rate_limiting_enabled": True
            }
        }
        
        config = validate_config(valid_config)
        self.assertEqual(config.webhook.port, 5000)
        self.assertEqual(config.security.api_key_expiry_days, 30)
        self.assertFalse(config.operational.maintenance_mode)
        
        # Invalid config
        invalid_config = {
            "webhook": {
                "port": 99999  # Invalid port
            }
        }
        
        with self.assertRaises(ValidationError):
            validate_config(invalid_config)
            
    def test_integrated_workflow(self):
        """Test integrated workflow with all components."""
        # Initialize all components
        audit_logger = AuditLogger()
        api_key_manager = APIKeyManager(audit_logger=audit_logger)
        webhook_security = WebhookSecurity(audit_logger=audit_logger)
        metrics = MetricsCollector(enabled=True)
        health = HealthCheck()
        
        # Simulate a complete request flow
        
        # 1. Generate API key
        key_id, raw_key = api_key_manager.generate_key("test-client")
        metrics.increment("api_keys.created")
        
        # 2. Configure security
        webhook_security.add_ip_to_allowlist("10.0.0.0/8")
        webhook_security.set_service_secret("github", "secret123")
        
        # 3. Process webhook request
        metrics.increment("webhooks.received", tags={"service": "github"})
        
        # Check IP
        ip_allowed, _ = webhook_security.check_ip_allowed("10.0.0.100")
        self.assertTrue(ip_allowed)
        metrics.increment("webhooks.ip_allowed", tags={"service": "github"})
        
        # Authenticate
        with metrics.timer("webhooks.auth_duration"):
            is_auth, _ = webhook_security.authenticate_webhook(
                "github", "10.0.0.100", "secret123"
            )
        self.assertTrue(is_auth)
        metrics.increment("webhooks.authenticated", tags={"service": "github"})
        
        # Validate API key
        with metrics.timer("api_key.validation_duration"):
            is_valid, _, _ = api_key_manager.validate_key(raw_key)
        self.assertTrue(is_valid)
        metrics.increment("api_key.validations")
        
        # 4. Check system health
        health.register_dependency(
            "api_keys",
            lambda: (True, f"{len(api_key_manager.keys)} keys active")
        )
        
        ready_status = health.check_ready()
        self.assertEqual(ready_status['status'], 'healthy')
        
        # 5. Verify metrics
        all_metrics = metrics.get_all_metrics()
        self.assertIn('counters', all_metrics)
        self.assertIn('timers', all_metrics)
        self.assertEqual(all_metrics['counters']['api_keys.created'], 1)
        self.assertEqual(all_metrics['counters']['api_key.validations'], 1)


if __name__ == '__main__':
    unittest.main()
