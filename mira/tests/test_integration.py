"""Test integration of production features."""
import unittest
import tempfile
import json
import time
import os
from pathlib import Path


class TestProductionFeatures(unittest.TestCase):
    """Integration tests for production features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def test_structured_logging_integration(self):
        """Test structured logging with correlation IDs."""
        from mira.utils.structured_logging import (
            setup_structured_logging,
            CorrelationContext,
            get_logger
        )
        
        # Setup structured logging
        setup_structured_logging(level='INFO', use_json=True)
        
        logger = get_logger('test')
        
        # Use correlation context
        with CorrelationContext() as correlation_id:
            logger.info("Test message with correlation")
            self.assertIsNotNone(correlation_id)
            
    def test_graceful_shutdown_integration(self):
        """Test graceful shutdown handler."""
        from mira.utils.shutdown_handler import ShutdownHandler
        
        handler = ShutdownHandler()
        callback_executed = []
        
        def cleanup():
            callback_executed.append(True)
            
        handler.register_callback(cleanup, 'test_cleanup')
        handler.shutdown(exit_code=None)
        
        self.assertEqual(len(callback_executed), 1)
        self.assertTrue(handler.is_shutting_down())
        
    def test_config_hotreload_integration(self):
        """Test config hot-reload functionality."""
        from mira.utils.config_hotreload import HotReloadConfig
        
        # Create test config file
        config_file = Path(self.temp_dir) / 'config.json'
        with open(config_file, 'w') as f:
            json.dump({'test': 'value1'}, f)
            
        # Mock config object
        class MockConfig:
            def __init__(self, path):
                self.data = {}
                self._load_from_file(path)
                
            def _load_from_file(self, path):
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self.data = json.load(f)
        
        config = MockConfig(str(config_file))
        hot_reload = HotReloadConfig(config, str(config_file))
        
        # Enable hot-reload
        hot_reload.enable_hot_reload()
        self.assertTrue(hot_reload.is_hot_reload_enabled())
        
        # Modify config
        time.sleep(0.5)
        with open(config_file, 'w') as f:
            json.dump({'test': 'value2'}, f)
            
        # Wait for reload
        time.sleep(1.5)
        
        # Verify config was reloaded
        self.assertEqual(config.data['test'], 'value2')
        
        # Cleanup
        hot_reload.disable_hot_reload()
        
    def test_secrets_manager_integration(self):
        """Test secrets manager with auto-refresh."""
        from mira.utils.secrets_manager import SecretsManager, SecretsBackend
        
        # Mock backend
        class MockBackend(SecretsBackend):
            def __init__(self):
                self.secrets = {'app/key': {'value': 'secret1'}}
                
            def get_secret(self, path, key=None):
                data = self.secrets[path]
                return data.get(key) if key else data
                
            def list_secrets(self, path):
                return list(self.secrets.keys())
        
        backend = MockBackend()
        manager = SecretsManager(backend)
        
        # Get secret
        value = manager.get_secret('app/key', 'value')
        self.assertEqual(value, 'secret1')
        
        # Register callback
        callback_values = []
        
        def on_refresh(new_value):
            callback_values.append(new_value)
            
        manager.register_refresh_callback('app/key', on_refresh, 'value')
        
        # Start auto-refresh
        manager.start_auto_refresh(interval=1)
        
        # Change secret
        time.sleep(0.5)
        backend.secrets['app/key']['value'] = 'secret2'
        
        # Wait for refresh
        time.sleep(1.5)
        
        # Verify callback was called
        self.assertGreater(len(callback_values), 0)
        self.assertEqual(callback_values[-1], 'secret2')
        
        # Cleanup
        manager.stop_auto_refresh()
        
    def test_full_integration(self):
        """Test all features working together."""
        from mira.utils.structured_logging import setup_structured_logging, CorrelationContext
        from mira.utils.shutdown_handler import ShutdownHandler
        from mira.utils.config_hotreload import ConfigWatcher
        from mira.utils.secrets_manager import SecretsManager, SecretsBackend
        
        # Setup all components
        setup_structured_logging(level='INFO')
        
        shutdown = ShutdownHandler()
        executed = []
        
        shutdown.register_callback(lambda: executed.append('shutdown'))
        
        # Mock secrets
        class MockBackend(SecretsBackend):
            def get_secret(self, path, key=None):
                return 'secret_value'
            def list_secrets(self, path):
                return ['secret1']
        
        secrets = SecretsManager(MockBackend())
        
        # Verify all components work
        with CorrelationContext():
            secret = secrets.get_secret('app/key')
            self.assertEqual(secret, 'secret_value')
            
        shutdown.shutdown(exit_code=None)
        self.assertIn('shutdown', executed)


if __name__ == '__main__':
    unittest.main()
