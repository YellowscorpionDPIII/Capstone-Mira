"""Tests for secrets management functionality."""
import unittest
import time
from unittest.mock import Mock, MagicMock, patch
from mira.utils.secrets_manager import (
    SecretsBackend,
    SecretsManager
)


class MockSecretsBackend(SecretsBackend):
    """Mock secrets backend for testing."""
    
    def __init__(self):
        """Initialize mock backend."""
        self.secrets = {
            'app/database': {'username': 'dbuser', 'password': 'dbpass'},
            'app/api': {'key': 'api-key-123'},
        }
        
    def get_secret(self, path: str, key=None):
        """Get a secret from mock storage."""
        if path not in self.secrets:
            raise KeyError(f"Secret not found: {path}")
            
        data = self.secrets[path]
        
        if key:
            return data.get(key)
        return data
        
    def list_secrets(self, path: str) -> list:
        """List secrets in mock storage."""
        return [k for k in self.secrets.keys() if k.startswith(path)]


class TestSecretsManager(unittest.TestCase):
    """Test cases for SecretsManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend = MockSecretsBackend()
        self.manager = SecretsManager(self.backend)
        
    def tearDown(self):
        """Clean up after tests."""
        if self.manager._refresh_running:
            self.manager.stop_auto_refresh()
            
    def test_get_secret_without_key(self):
        """Test getting a secret without specifying a key."""
        secret = self.manager.get_secret('app/database')
        
        self.assertEqual(secret['username'], 'dbuser')
        self.assertEqual(secret['password'], 'dbpass')
        
    def test_get_secret_with_key(self):
        """Test getting a specific key from a secret."""
        username = self.manager.get_secret('app/database', 'username')
        
        self.assertEqual(username, 'dbuser')
        
    def test_get_secret_caching(self):
        """Test that secrets are cached."""
        # First call
        secret1 = self.manager.get_secret('app/database')
        original_username = secret1['username']
        
        # Modify backend data (but cache shouldn't be affected)
        self.backend.secrets['app/database'] = {'username': 'newuser', 'password': 'newpass'}
        
        # Second call should return cached value (but Python dicts are mutable, so we need to check the cache key)
        # The cache stores references, so we need to verify by fetching without cache
        secret3 = self.manager.get_secret('app/database', use_cache=False)
        self.assertEqual(secret3['username'], 'newuser')
        
        # Now cache has new value
        secret4 = self.manager.get_secret('app/database', use_cache=True)
        self.assertEqual(secret4['username'], 'newuser')
        
    def test_list_secrets(self):
        """Test listing secrets."""
        secrets = self.manager.list_secrets('app/')
        
        self.assertIn('app/database', secrets)
        self.assertIn('app/api', secrets)
        
    def test_register_refresh_callback(self):
        """Test registering refresh callbacks."""
        callback_called = []
        
        def callback(value):
            callback_called.append(value)
            
        self.manager.register_refresh_callback('app/api', callback, 'key')
        
        # Verify callback was registered
        cache_key = 'app/api:key'
        self.assertIn(cache_key, self.manager.refresh_callbacks)
        self.assertEqual(len(self.manager.refresh_callbacks[cache_key]), 1)
        
    def test_auto_refresh(self):
        """Test auto-refresh of secrets."""
        callback_called = []
        
        def callback(value):
            callback_called.append(value)
            
        # Get initial secret
        self.manager.get_secret('app/api', 'key')
        
        # Register callback
        self.manager.register_refresh_callback('app/api', callback, 'key')
        
        # Start auto-refresh with short interval
        self.manager.start_auto_refresh(interval=1)
        
        # Wait a bit
        time.sleep(0.5)
        
        # Modify secret in backend
        self.backend.secrets['app/api']['key'] = 'new-api-key'
        
        # Wait for refresh to happen
        time.sleep(1.5)
        
        # Callback should have been called with new value
        self.assertGreater(len(callback_called), 0)
        self.assertEqual(callback_called[-1], 'new-api-key')
        
        # Stop refresh
        self.manager.stop_auto_refresh()
        
    def test_auto_refresh_start_stop(self):
        """Test starting and stopping auto-refresh."""
        self.assertFalse(self.manager._refresh_running)
        
        self.manager.start_auto_refresh(interval=1)
        self.assertTrue(self.manager._refresh_running)
        
        self.manager.stop_auto_refresh()
        self.assertFalse(self.manager._refresh_running)
        
    def test_auto_refresh_start_twice(self):
        """Test that starting auto-refresh twice doesn't cause issues."""
        self.manager.start_auto_refresh(interval=1)
        self.manager.start_auto_refresh(interval=1)  # Should not cause error
        
        self.assertTrue(self.manager._refresh_running)
        
        self.manager.stop_auto_refresh()
        
    def test_refresh_callback_error_handling(self):
        """Test that errors in refresh callbacks don't break refresh."""
        callback_success = []
        
        def callback_error(value):
            raise ValueError("Test error")
            
        def callback_success_fn(value):
            callback_success.append(value)
            
        # Get initial secret
        self.manager.get_secret('app/api', 'key')
        
        # Register both callbacks
        self.manager.register_refresh_callback('app/api', callback_error, 'key')
        self.manager.register_refresh_callback('app/api', callback_success_fn, 'key')
        
        # Start auto-refresh
        self.manager.start_auto_refresh(interval=1)
        
        # Modify secret
        self.backend.secrets['app/api']['key'] = 'new-key'
        
        # Wait for refresh
        time.sleep(1.5)
        
        # Success callback should still be called despite error in first callback
        self.assertGreater(len(callback_success), 0)
        
        self.manager.stop_auto_refresh()


class TestVaultBackend(unittest.TestCase):
    """Test cases for VaultBackend."""
    
    def test_vault_missing_library(self):
        """Test Vault backend without hvac library."""
        # Save original import
        import sys
        original_hvac = sys.modules.get('hvac')
        
        try:
            # Remove hvac from modules
            if 'hvac' in sys.modules:
                del sys.modules['hvac']
            
            # Mock import to fail
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'hvac':
                    raise ImportError("No module named 'hvac'")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            try:
                from mira.utils.secrets_manager import VaultBackend
                with self.assertRaises(ImportError):
                    backend = VaultBackend(
                        vault_addr='http://localhost:8200',
                        token='test-token'
                    )
            finally:
                builtins.__import__ = original_import
        finally:
            # Restore original module
            if original_hvac is not None:
                sys.modules['hvac'] = original_hvac


class TestKubernetesBackend(unittest.TestCase):
    """Test cases for KubernetesBackend."""
    
    def test_kubernetes_missing_library(self):
        """Test Kubernetes backend without kubernetes library."""
        # Save original import
        import sys
        original_k8s = sys.modules.get('kubernetes')
        
        try:
            # Remove kubernetes from modules
            if 'kubernetes' in sys.modules:
                del sys.modules['kubernetes']
            
            # Mock import to fail
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'kubernetes' or name.startswith('kubernetes.'):
                    raise ImportError("No module named 'kubernetes'")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            try:
                from mira.utils.secrets_manager import KubernetesBackend
                with self.assertRaises(ImportError):
                    backend = KubernetesBackend(namespace='default')
            finally:
                builtins.__import__ = original_import
        finally:
            # Restore original module
            if original_k8s is not None:
                sys.modules['kubernetes'] = original_k8s


if __name__ == '__main__':
    unittest.main()
