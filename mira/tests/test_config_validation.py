"""Tests for configuration validation."""
import unittest
from pydantic import ValidationError
from mira.config.validation import (
    MiraConfig,
    validate_config,
    WebhookConfig,
    LoggingConfig,
    SecurityConfig,
    OperationalConfig
)


class TestConfigurationValidation(unittest.TestCase):
    """Test cases for Configuration Validation."""
    
    def test_valid_minimal_config(self):
        """Test validation of minimal valid config."""
        config_dict = {}
        
        config = validate_config(config_dict)
        
        self.assertIsInstance(config, MiraConfig)
        self.assertTrue(config.broker.enabled)
        self.assertFalse(config.webhook.enabled)
        
    def test_valid_full_config(self):
        """Test validation of full valid config."""
        config_dict = {
            'broker': {
                'enabled': True,
                'queue_size': 5000
            },
            'webhook': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8080,
                'secret_key': 'test_secret'
            },
            'logging': {
                'level': 'DEBUG',
                'audit_log_file': '/var/log/audit.log'
            },
            'security': {
                'api_key_enabled': True,
                'api_key_expiry_days': 30,
                'ip_allowlist': ['192.168.1.0/24'],
                'ip_denylist': ['10.0.0.1']
            },
            'operational': {
                'rate_limiting_enabled': True,
                'rate_limit_per_minute': 100,
                'verbose_logging': True,
                'maintenance_mode': False
            }
        }
        
        config = validate_config(config_dict)
        
        self.assertEqual(config.broker.queue_size, 5000)
        self.assertEqual(config.webhook.port, 8080)
        self.assertEqual(config.logging.level, 'DEBUG')
        self.assertEqual(config.security.api_key_expiry_days, 30)
        self.assertTrue(config.operational.rate_limiting_enabled)
        
    def test_invalid_webhook_port(self):
        """Test validation fails with invalid port."""
        config_dict = {
            'webhook': {
                'port': 99999  # Invalid port
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_config(config_dict)
        
        errors = cm.exception.errors()
        self.assertTrue(any('port' in str(e['loc']) for e in errors))
        
    def test_invalid_log_level(self):
        """Test validation fails with invalid log level."""
        config_dict = {
            'logging': {
                'level': 'INVALID'
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_config(config_dict)
        
        errors = cm.exception.errors()
        self.assertTrue(any('level' in str(e['loc']) for e in errors))
        
    def test_invalid_queue_size(self):
        """Test validation fails with invalid queue size."""
        config_dict = {
            'broker': {
                'queue_size': 0  # Too small
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_config(config_dict)
        
        errors = cm.exception.errors()
        self.assertTrue(any('queue_size' in str(e['loc']) for e in errors))
        
    def test_webhook_config_defaults(self):
        """Test webhook config defaults."""
        config = WebhookConfig()
        
        self.assertFalse(config.enabled)
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 5000)
        self.assertIsNone(config.secret_key)
        
    def test_logging_config_validation(self):
        """Test logging config validation."""
        # Valid levels
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            config = LoggingConfig(level=level)
            self.assertEqual(config.level, level)
        
        # Invalid level
        with self.assertRaises(ValidationError):
            LoggingConfig(level='INVALID')
            
    def test_security_config_defaults(self):
        """Test security config defaults."""
        config = SecurityConfig()
        
        self.assertTrue(config.api_key_enabled)
        self.assertIsNone(config.api_key_expiry_days)
        self.assertEqual(config.ip_allowlist, [])
        self.assertEqual(config.ip_denylist, [])
        self.assertEqual(config.webhook_secrets, {})
        
    def test_operational_config_defaults(self):
        """Test operational config defaults."""
        config = OperationalConfig()
        
        self.assertFalse(config.rate_limiting_enabled)
        self.assertEqual(config.rate_limit_per_minute, 60)
        self.assertFalse(config.verbose_logging)
        self.assertFalse(config.maintenance_mode)
        
    def test_config_allows_extra_fields(self):
        """Test that extra fields are allowed for extensibility."""
        config_dict = {
            'custom_field': 'custom_value',
            'nested': {
                'custom': 'value'
            }
        }
        
        # Should not raise exception
        config = validate_config(config_dict)
        self.assertIsInstance(config, MiraConfig)
        
    def test_integration_configs(self):
        """Test integration configuration."""
        config_dict = {
            'integrations': {
                'airtable': {
                    'enabled': True,
                    'api_key': 'test_key',
                    'base_id': 'test_base'
                },
                'github': {
                    'enabled': True,
                    'token': 'gh_token',
                    'repository': 'user/repo'
                }
            }
        }
        
        config = validate_config(config_dict)
        
        self.assertTrue(config.integrations.airtable.enabled)
        self.assertEqual(config.integrations.airtable.api_key, 'test_key')
        self.assertTrue(config.integrations.github.enabled)
        self.assertEqual(config.integrations.github.token, 'gh_token')
        
    def test_agent_configs(self):
        """Test agent configuration."""
        config_dict = {
            'agents': {
                'project_plan_agent': {'enabled': True},
                'risk_assessment_agent': {'enabled': False}
            }
        }
        
        config = validate_config(config_dict)
        
        self.assertTrue(config.agents.project_plan_agent.enabled)
        self.assertFalse(config.agents.risk_assessment_agent.enabled)


if __name__ == '__main__':
    unittest.main()
