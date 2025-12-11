"""Tests for configuration hot-reload."""
import unittest
import json
import os
import time
import tempfile
from pathlib import Path
from mira.utils.config_hotreload import (
    ConfigWatcher,
    HotReloadableConfig,
    enable_hot_reload
)
from mira.config.settings import Config


class TestConfigWatcher(unittest.TestCase):
    """Test cases for ConfigWatcher."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
        
        self.initial_config = {
            'test_key': 'initial_value',
            'number': 42
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.initial_config, f)
        
        self.callback_called = False
        self.received_config = None
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary files
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_register_callback(self):
        """Test registering reload callbacks."""
        watcher = ConfigWatcher(self.config_path, poll_interval=1)
        
        def callback(config):
            pass
        
        watcher.register_callback(callback)
        
        self.assertEqual(len(watcher.reload_callbacks), 1)
        self.assertIn(callback, watcher.reload_callbacks)
    
    def test_file_change_detection_polling(self):
        """Test file change detection using polling."""
        watcher = ConfigWatcher(self.config_path, poll_interval=1)
        watcher.use_watchdog = False  # Force polling mode
        
        def callback(config):
            self.callback_called = True
            self.received_config = config
        
        watcher.register_callback(callback)
        watcher.start()
        
        # Give it time to start
        time.sleep(0.5)
        
        # Modify the config file
        new_config = {
            'test_key': 'updated_value',
            'number': 100
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(new_config, f)
        
        # Wait for polling cycle to detect change
        time.sleep(2)
        
        # Stop watcher
        watcher.stop()
        
        # Check that callback was called
        self.assertTrue(self.callback_called)
        self.assertEqual(self.received_config['test_key'], 'updated_value')
        self.assertEqual(self.received_config['number'], 100)
    
    def test_stop_watcher(self):
        """Test stopping the watcher."""
        watcher = ConfigWatcher(self.config_path, poll_interval=1)
        watcher.use_watchdog = False
        watcher.start()
        
        self.assertTrue(watcher.running)
        
        watcher.stop()
        
        self.assertFalse(watcher.running)
    
    def test_nonexistent_file(self):
        """Test watcher with non-existent file."""
        nonexistent_path = os.path.join(self.temp_dir, 'nonexistent.json')
        watcher = ConfigWatcher(nonexistent_path, poll_interval=1)
        
        # Should not raise exception
        watcher.start()
        watcher.stop()


class TestHotReloadableConfig(unittest.TestCase):
    """Test cases for HotReloadableConfig."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
        
        self.initial_config = {
            'logging': {
                'level': 'INFO'
            },
            'test_value': 123
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.initial_config, f)
        
        self.config_instance = Config(self.config_path)
        self.reload_callback_called = False
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test hot-reloadable config initialization."""
        hot_config = HotReloadableConfig(
            self.config_instance,
            self.config_path,
            enable_hot_reload=True,
            poll_interval=1
        )
        
        self.assertIsNotNone(hot_config.watcher)
        self.assertTrue(hot_config.watcher.running)
        
        # Cleanup
        hot_config.stop_watching()
    
    def test_config_reload(self):
        """Test configuration reload."""
        hot_config = HotReloadableConfig(
            self.config_instance,
            self.config_path,
            enable_hot_reload=True,
            poll_interval=1
        )
        hot_config.watcher.use_watchdog = False  # Force polling
        
        def reload_callback(config):
            self.reload_callback_called = True
        
        hot_config.register_reload_callback(reload_callback)
        
        # Modify config file
        new_config = {
            'logging': {
                'level': 'DEBUG'
            },
            'test_value': 456
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(new_config, f)
        
        # Wait for reload
        time.sleep(2.5)
        
        # Check that config was updated
        self.assertEqual(hot_config.get('logging.level'), 'DEBUG')
        self.assertEqual(hot_config.get('test_value'), 456)
        self.assertTrue(self.reload_callback_called)
        
        # Cleanup
        hot_config.stop_watching()
    
    def test_get_and_set(self):
        """Test get and set methods."""
        hot_config = HotReloadableConfig(
            self.config_instance,
            self.config_path,
            enable_hot_reload=False
        )
        
        # Test get
        value = hot_config.get('test_value')
        self.assertEqual(value, 123)
        
        # Test set
        hot_config.set('new_key', 'new_value')
        self.assertEqual(hot_config.get('new_key'), 'new_value')
    
    def test_enable_hot_reload_function(self):
        """Test enable_hot_reload helper function."""
        hot_config = enable_hot_reload(
            self.config_instance,
            self.config_path,
            poll_interval=2
        )
        
        self.assertIsInstance(hot_config, HotReloadableConfig)
        self.assertIsNotNone(hot_config.watcher)
        
        # Cleanup
        hot_config.stop_watching()
    
    def test_disabled_hot_reload(self):
        """Test with hot-reload disabled."""
        hot_config = HotReloadableConfig(
            self.config_instance,
            self.config_path,
            enable_hot_reload=False
        )
        
        self.assertIsNone(hot_config.watcher)


if __name__ == '__main__':
    unittest.main()
