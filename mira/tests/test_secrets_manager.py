"""Tests for secrets management."""
import unittest
import os
import time
from unittest.mock import Mock, patch
from mira.utils.secrets_manager import (
    SecretsManager,
    EnvironmentBackend,
    get_secrets_manager,
    set_secrets_manager,
    create_secrets_manager
)


class TestEnvironmentBackend(unittest.TestCase):
    """Test cases for environment backend."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend = EnvironmentBackend()
    
    def test_is_available(self):
        """Test that environment backend is always available."""
        self.assertTrue(self.backend.is_available())
    
    def test_get_secret_simple(self):
        """Test getting a simple secret from environment."""
        os.environ['TEST_SECRET'] = 'secret_value'
        
        value = self.backend.get_secret('TEST_SECRET')
        
        self.assertEqual(value, 'secret_value')
        
        # Cleanup
        del os.environ['TEST_SECRET']
    
    def test_get_secret_with_key(self):
        """Test getting a secret with key suffix."""
        os.environ['TEST_API_KEY'] = 'api_key_value'
        
        value = self.backend.get_secret('TEST_API', 'KEY')
        
        self.assertEqual(value, 'api_key_value')
        
        # Cleanup
        del os.environ['TEST_API_KEY']
    
    def test_get_secret_missing(self):
        """Test getting a non-existent secret."""
        value = self.backend.get_secret('NONEXISTENT_SECRET')
        
        self.assertIsNone(value)


class TestSecretsManager(unittest.TestCase):
    """Test cases for SecretsManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend = EnvironmentBackend()
        self.manager = SecretsManager(backend=self.backend, refresh_interval=1)
    
    def tearDown(self):
        """Clean up after tests."""
        self.manager.stop_auto_refresh()
    
    def test_get_secret(self):
        """Test getting a secret."""
        os.environ['TEST_SECRET'] = 'test_value'
        
        value = self.manager.get_secret('TEST_SECRET')
        
        self.assertEqual(value, 'test_value')
        
        # Cleanup
        del os.environ['TEST_SECRET']
    
    def test_get_secret_with_cache(self):
        """Test that secrets are cached."""
        os.environ['TEST_SECRET'] = 'initial_value'
        
        # First call should fetch and cache
        value1 = self.manager.get_secret('TEST_SECRET')
        self.assertEqual(value1, 'initial_value')
        
        # Change environment variable
        os.environ['TEST_SECRET'] = 'new_value'
        
        # Second call should return cached value
        value2 = self.manager.get_secret('TEST_SECRET', use_cache=True)
        self.assertEqual(value2, 'initial_value')
        
        # Third call without cache should get new value
        value3 = self.manager.get_secret('TEST_SECRET', use_cache=False)
        self.assertEqual(value3, 'new_value')
        
        # Cleanup
        del os.environ['TEST_SECRET']
    
    def test_get_secret_fallback_to_cache(self):
        """Test fallback to cached value on error."""
        os.environ['TEST_SECRET'] = 'cached_value'
        
        # Cache the value
        value = self.manager.get_secret('TEST_SECRET')
        self.assertEqual(value, 'cached_value')
        
        # Mock backend to raise exception
        self.manager.backend.get_secret = Mock(side_effect=Exception("Backend error"))
        
        # Should return cached value as fallback
        fallback_value = self.manager.get_secret('TEST_SECRET')
        self.assertEqual(fallback_value, 'cached_value')
        
        # Cleanup
        del os.environ['TEST_SECRET']
    
    def test_register_refresh_callback(self):
        """Test registering refresh callbacks."""
        callback_called = [False]
        new_value_received = [None]
        
        def callback(value):
            callback_called[0] = True
            new_value_received[0] = value
        
        self.manager.register_refresh_callback('TEST_SECRET', callback)
        
        self.assertIn('TEST_SECRET', self.manager.refresh_callbacks)
        self.assertIn(callback, self.manager.refresh_callbacks['TEST_SECRET'])
    
    def test_auto_refresh(self):
        """Test automatic secret refresh."""
        os.environ['TEST_SECRET'] = 'initial'
        
        # Cache initial value
        value = self.manager.get_secret('TEST_SECRET')
        self.assertEqual(value, 'initial')
        
        # Start auto-refresh with short interval
        self.manager.refresh_interval = 1
        self.manager.start_auto_refresh()
        
        # Change the value
        os.environ['TEST_SECRET'] = 'updated'
        
        # Wait for refresh cycle
        time.sleep(2)
        
        # Check that cache was updated
        cached_value = self.manager.cache.get('TEST_SECRET')
        self.assertEqual(cached_value, 'updated')
        
        # Cleanup
        del os.environ['TEST_SECRET']
    
    def test_stop_auto_refresh(self):
        """Test stopping auto-refresh."""
        self.manager.start_auto_refresh()
        self.assertTrue(self.manager.running)
        
        self.manager.stop_auto_refresh()
        self.assertFalse(self.manager.running)
    
    def test_global_secrets_manager(self):
        """Test global secrets manager singleton."""
        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_set_global_secrets_manager(self):
        """Test setting global secrets manager."""
        custom_manager = SecretsManager()
        set_secrets_manager(custom_manager)
        
        manager = get_secrets_manager()
        self.assertIs(manager, custom_manager)
    
    def test_create_secrets_manager_env_backend(self):
        """Test creating secrets manager with env backend."""
        config = {
            'secrets': {
                'backend': 'env',
                'refresh_interval': 3600
            }
        }
        
        manager = create_secrets_manager(config)
        
        self.assertIsInstance(manager.backend, EnvironmentBackend)
        self.assertEqual(manager.refresh_interval, 3600)
    
    def test_create_secrets_manager_default(self):
        """Test creating secrets manager with default config."""
        config = {}
        
        manager = create_secrets_manager(config)
        
        self.assertIsInstance(manager.backend, EnvironmentBackend)


if __name__ == '__main__':
    unittest.main()
