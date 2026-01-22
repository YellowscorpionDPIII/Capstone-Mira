"""Tests for secrets manager utilities."""
import unittest
import os
import time
from unittest.mock import patch, MagicMock
from mira.utils.secrets_manager import (
    SecretsManager,
    SecretNotFoundError,
    SecretsManagerError,
    get_secret,
    initialize_secrets_manager
)


class TestSecretsManager(unittest.TestCase):
    """Test cases for SecretsManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Set test environment variable
        os.environ['TEST_SECRET'] = 'test_value'
        
    def tearDown(self):
        """Clean up after tests."""
        # Clean up environment variable
        if 'TEST_SECRET' in os.environ:
            del os.environ['TEST_SECRET']
            
    def test_env_backend_initialization(self):
        """Test environment variable backend initialization."""
        manager = SecretsManager(backend="env")
        self.assertEqual(manager.backend, "env")
        
    def test_get_secret_from_env(self):
        """Test fetching secret from environment variables."""
        manager = SecretsManager(backend="env")
        value = manager.get_secret("TEST_SECRET")
        self.assertEqual(value, "test_value")
        
    def test_get_secret_not_found(self):
        """Test fetching non-existent secret."""
        manager = SecretsManager(backend="env")
        with self.assertRaises((SecretNotFoundError, SecretsManagerError)):
            manager.get_secret("NONEXISTENT_SECRET", max_retries=1, delay=0.1)
            
    def test_get_secret_with_default(self):
        """Test fetching secret with default value."""
        manager = SecretsManager(backend="env")
        value = manager.get_secret("NONEXISTENT_SECRET", default="default_value", max_retries=1, delay=0.1)
        self.assertEqual(value, "default_value")
        
    def test_fetch_with_retry_success(self):
        """Test retry logic with successful fetch."""
        manager = SecretsManager(backend="env")
        
        fetch_func = MagicMock(return_value="secret_value")
        result = manager._fetch_with_retry(fetch_func, max_retries=3, delay=0.1)
        
        self.assertEqual(result, "secret_value")
        fetch_func.assert_called_once()
        
    def test_fetch_with_retry_eventual_success(self):
        """Test retry logic with eventual success."""
        manager = SecretsManager(backend="env")
        
        # Fail twice, then succeed
        fetch_func = MagicMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "secret_value"
        ])
        
        result = manager._fetch_with_retry(fetch_func, max_retries=3, delay=0.1)
        
        self.assertEqual(result, "secret_value")
        self.assertEqual(fetch_func.call_count, 3)
        
    def test_fetch_with_retry_all_fail(self):
        """Test retry logic when all attempts fail."""
        manager = SecretsManager(backend="env")
        
        fetch_func = MagicMock(side_effect=Exception("Persistent error"))
        
        with self.assertRaises(SecretsManagerError):
            manager._fetch_with_retry(fetch_func, max_retries=2, delay=0.1)
            
        # Should try initial + 2 retries = 3 times
        self.assertEqual(fetch_func.call_count, 3)
        
    def test_fetch_with_retry_backoff(self):
        """Test exponential backoff in retry logic."""
        manager = SecretsManager(backend="env")
        
        call_times = []
        
        def failing_fetch():
            call_times.append(time.time())
            raise Exception("Error")
            
        try:
            manager._fetch_with_retry(
                failing_fetch,
                max_retries=2,
                delay=0.1,
                backoff=2.0
            )
        except SecretsManagerError:
            pass
            
        # Should have 3 calls (initial + 2 retries)
        self.assertEqual(len(call_times), 3)
        
        # Check that delays are increasing (with some tolerance)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be roughly 2x the first (0.1 -> 0.2)
            # Allow for timing variance
            self.assertGreater(delay2, delay1 * 1.5)
            
    @patch('mira.utils.secrets_manager.SecretsManager._initialize_vault')
    def test_vault_backend_initialization(self, mock_init):
        """Test Vault backend initialization."""
        manager = SecretsManager(backend="vault", config={"url": "http://vault:8200"})
        mock_init.assert_called_once()
        
    @patch('mira.utils.secrets_manager.SecretsManager._initialize_k8s')
    def test_k8s_backend_initialization(self, mock_init):
        """Test Kubernetes backend initialization."""
        manager = SecretsManager(backend="k8s")
        mock_init.assert_called_once()


class TestGlobalSecretsManager(unittest.TestCase):
    """Test cases for global secrets manager functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        os.environ['GLOBAL_TEST_SECRET'] = 'global_value'
        
    def tearDown(self):
        """Clean up after tests."""
        if 'GLOBAL_TEST_SECRET' in os.environ:
            del os.environ['GLOBAL_TEST_SECRET']
        
        # Reset global instance
        import mira.utils.secrets_manager as sm
        sm._secrets_manager = None
        
    def test_initialize_global_manager(self):
        """Test initializing global secrets manager."""
        initialize_secrets_manager(backend="env")
        value = get_secret("GLOBAL_TEST_SECRET")
        self.assertEqual(value, "global_value")
        
    def test_get_secret_without_initialization(self):
        """Test get_secret auto-initializes with env backend."""
        value = get_secret("GLOBAL_TEST_SECRET")
        self.assertEqual(value, "global_value")
        
    def test_get_secret_with_retry_params(self):
        """Test get_secret with custom retry parameters."""
        value = get_secret("GLOBAL_TEST_SECRET", max_retries=5, delay=0.05)
        self.assertEqual(value, "global_value")


if __name__ == '__main__':
    unittest.main()
