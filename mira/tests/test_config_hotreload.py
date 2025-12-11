"""Tests for configuration hot-reload functionality."""
import unittest
import tempfile
import json
import time
import os
from pathlib import Path
from mira.utils.config_hotreload import (
    ConfigWatcher,
    HotReloadConfig,
    ConfigFileHandler
)


class MockConfig:
    """Mock configuration class for testing."""
    
    def __init__(self, config_path):
        self.config_path = config_path
        self.data = {}
        self._load_from_file(config_path)
        
    def _load_from_file(self, config_path):
        """Load configuration from file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.data = json.load(f)


class TestConfigWatcher(unittest.TestCase):
    """Test cases for ConfigWatcher."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.json'
        self.reload_count = 0
        
        # Create initial config file
        with open(self.config_file, 'w') as f:
            json.dump({'key': 'value1'}, f)
            
    def tearDown(self):
        """Clean up after tests."""
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def reload_callback(self):
        """Test callback for config reload."""
        self.reload_count += 1
        
    def test_watcher_start_stop(self):
        """Test starting and stopping the watcher."""
        watcher = ConfigWatcher(str(self.config_file), self.reload_callback)
        
        self.assertFalse(watcher.is_running())
        
        watcher.start()
        self.assertTrue(watcher.is_running())
        
        watcher.stop()
        self.assertFalse(watcher.is_running())
        
    def test_watcher_detects_changes(self):
        """Test that watcher detects file changes."""
        watcher = ConfigWatcher(str(self.config_file), self.reload_callback)
        watcher.start()
        
        try:
            # Give watcher time to start
            time.sleep(0.5)
            
            # Modify the config file
            with open(self.config_file, 'w') as f:
                json.dump({'key': 'value2'}, f)
                
            # Give watcher time to detect change
            time.sleep(1.5)
            
            # Callback should have been called
            self.assertGreater(self.reload_count, 0)
        finally:
            watcher.stop()
            
    def test_watcher_start_twice(self):
        """Test that starting watcher twice doesn't cause issues."""
        watcher = ConfigWatcher(str(self.config_file), self.reload_callback)
        
        watcher.start()
        watcher.start()  # Should not cause error
        
        self.assertTrue(watcher.is_running())
        
        watcher.stop()
        
    def test_watcher_nonexistent_file(self):
        """Test watcher with non-existent config file."""
        nonexistent = Path(self.temp_dir) / 'nonexistent.json'
        watcher = ConfigWatcher(str(nonexistent), self.reload_callback)
        
        # Should not raise error, but won't start
        watcher.start()
        self.assertFalse(watcher.is_running())


class TestHotReloadConfig(unittest.TestCase):
    """Test cases for HotReloadConfig."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.json'
        
        # Create initial config file
        with open(self.config_file, 'w') as f:
            json.dump({'key': 'initial_value'}, f)
            
        self.mock_config = MockConfig(str(self.config_file))
        self.hot_reload = HotReloadConfig(self.mock_config, str(self.config_file))
        self.callback_count = 0
        
    def tearDown(self):
        """Clean up after tests."""
        self.hot_reload.disable_hot_reload()
        
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def test_callback(self):
        """Test callback for reload."""
        self.callback_count += 1
        
    def test_register_callback(self):
        """Test registering reload callbacks."""
        self.hot_reload.register_reload_callback(self.test_callback, 'test')
        
        self.assertEqual(len(self.hot_reload.reload_callbacks), 1)
        
    def test_unregister_callback(self):
        """Test unregistering reload callbacks."""
        self.hot_reload.register_reload_callback(self.test_callback, 'test')
        self.hot_reload.unregister_reload_callback(self.test_callback)
        
        self.assertEqual(len(self.hot_reload.reload_callbacks), 0)
        
    def test_enable_disable_hot_reload(self):
        """Test enabling and disabling hot reload."""
        self.assertFalse(self.hot_reload.is_hot_reload_enabled())
        
        self.hot_reload.enable_hot_reload()
        self.assertTrue(self.hot_reload.is_hot_reload_enabled())
        
        self.hot_reload.disable_hot_reload()
        self.assertFalse(self.hot_reload.is_hot_reload_enabled())
        
    def test_config_reload(self):
        """Test that configuration is reloaded when file changes."""
        self.hot_reload.enable_hot_reload()
        
        try:
            # Give watcher time to start
            time.sleep(0.5)
            
            # Modify config file
            with open(self.config_file, 'w') as f:
                json.dump({'key': 'updated_value'}, f)
                
            # Give time for reload
            time.sleep(1.5)
            
            # Config should be reloaded
            self.assertEqual(self.mock_config.data['key'], 'updated_value')
        finally:
            self.hot_reload.disable_hot_reload()
            
    def test_reload_callback_execution(self):
        """Test that reload callbacks are executed."""
        callback_executed = []
        
        def callback():
            callback_executed.append(True)
            
        self.hot_reload.register_reload_callback(callback, 'test_callback')
        self.hot_reload.enable_hot_reload()
        
        try:
            # Give watcher time to start
            time.sleep(0.5)
            
            # Modify config file
            with open(self.config_file, 'w') as f:
                json.dump({'key': 'new_value'}, f)
                
            # Give time for reload and callback
            time.sleep(1.5)
            
            # Callback should have been executed
            self.assertGreater(len(callback_executed), 0)
        finally:
            self.hot_reload.disable_hot_reload()


if __name__ == '__main__':
    unittest.main()
