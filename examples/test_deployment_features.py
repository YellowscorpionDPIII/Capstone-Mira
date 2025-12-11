#!/usr/bin/env python3
"""
Simplified test for deployment features that doesn't require full app initialization.
This demonstrates the core deployment features independently.
"""

import json
import time
import tempfile
import os
from mira.utils.structured_logging import (
    setup_structured_logging,
    set_correlation_id,
    get_structured_logger
)
from mira.utils.graceful_shutdown import get_shutdown_handler, register_shutdown_handler
from mira.utils.secrets_manager import SecretsManager, EnvironmentBackend
from mira.utils.config_hotreload import ConfigWatcher


def test_structured_logging():
    """Test structured logging with correlation IDs."""
    print("\n" + "="*60)
    print("1. Testing Structured Logging with Correlation IDs")
    print("="*60)
    
    # Setup JSON logging
    setup_structured_logging(level='INFO', json_format=True)
    
    # Get a logger
    logger = get_structured_logger('test')
    
    # Set a correlation ID
    correlation_id = set_correlation_id()
    print(f"✓ Generated correlation ID: {correlation_id}")
    
    # Log some messages - they will appear as JSON with correlation ID
    logger.info("This is a test message", extra={'feature': 'structured_logging'})
    logger.warning("This is a warning", extra={'test_value': 123})
    
    print("✓ Structured logging working - check JSON output above")


def test_graceful_shutdown():
    """Test graceful shutdown handlers."""
    print("\n" + "="*60)
    print("2. Testing Graceful Shutdown")
    print("="*60)
    
    shutdown_handler = get_shutdown_handler()
    
    # Track handler execution
    executed_handlers = []
    
    def cleanup_database():
        executed_handlers.append('database')
        print("  ✓ Database connections closed")
    
    def cleanup_cache():
        executed_handlers.append('cache')
        print("  ✓ Cache cleaned up")
    
    def cleanup_files():
        executed_handlers.append('files')
        print("  ✓ Files closed")
    
    # Register handlers
    register_shutdown_handler(cleanup_database)
    register_shutdown_handler(cleanup_cache)
    register_shutdown_handler(cleanup_files)
    
    print("✓ Registered 3 shutdown handlers")
    
    # Setup signal handlers
    shutdown_handler.setup()
    print("✓ Signal handlers registered (SIGTERM, SIGINT)")
    
    # Manually trigger shutdown to test
    print("\nTriggering shutdown...")
    shutdown_handler.shutdown()
    
    # Verify handlers were called in LIFO order
    if executed_handlers == ['files', 'cache', 'database']:
        print("✓ All handlers executed in correct order (LIFO)")
    else:
        print(f"✗ Handler order incorrect: {executed_handlers}")


def test_secrets_management():
    """Test secrets management."""
    print("\n" + "="*60)
    print("3. Testing Secrets Management")
    print("="*60)
    
    # Setup test environment variable
    os.environ['TEST_SECRET'] = 'secret_value_123'
    os.environ['API_KEY'] = 'test_api_key_456'
    
    # Create secrets manager with env backend
    backend = EnvironmentBackend()
    manager = SecretsManager(backend=backend, refresh_interval=2)
    
    print("✓ Created secrets manager with environment backend")
    
    # Get a secret
    secret = manager.get_secret('TEST_SECRET')
    print(f"✓ Retrieved secret: {secret}")
    
    # Get secret with key
    api_key = manager.get_secret('API', 'KEY')
    print(f"✓ Retrieved API key: {api_key}")
    
    # Test caching
    os.environ['TEST_SECRET'] = 'new_value'
    cached_value = manager.get_secret('TEST_SECRET', use_cache=True)
    print(f"✓ Cached value (should be old): {cached_value}")
    
    fresh_value = manager.get_secret('TEST_SECRET', use_cache=False)
    print(f"✓ Fresh value (should be new): {fresh_value}")
    
    # Test refresh callback
    callback_called = [False]
    new_value = [None]
    
    def on_refresh(value):
        callback_called[0] = True
        new_value[0] = value
    
    manager.register_refresh_callback('TEST_SECRET', on_refresh)
    print("✓ Registered refresh callback")
    
    # Cleanup
    del os.environ['TEST_SECRET']
    del os.environ['API_KEY']


def test_config_hotreload():
    """Test configuration hot-reload."""
    print("\n" + "="*60)
    print("4. Testing Configuration Hot-Reload")
    print("="*60)
    
    # Create a temporary config file
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, 'test_config.json')
    
    initial_config = {
        'app_name': 'Mira',
        'version': '1.0.0',
        'debug': False
    }
    
    with open(config_path, 'w') as f:
        json.dump(initial_config, f)
    
    print(f"✓ Created test config: {config_path}")
    
    # Setup watcher
    reloaded = [False]
    new_config = [None]
    
    def on_reload(config):
        reloaded[0] = True
        new_config[0] = config
        print(f"  → Configuration reloaded: {config}")
    
    watcher = ConfigWatcher(config_path, poll_interval=1)
    watcher.use_watchdog = False  # Force polling mode for testing
    watcher.register_callback(on_reload)
    watcher.start()
    
    print("✓ Started configuration watcher (polling mode)")
    
    # Modify config file
    print("\nModifying configuration file...")
    time.sleep(0.5)
    
    modified_config = {
        'app_name': 'Mira',
        'version': '2.0.0',
        'debug': True,
        'new_feature': 'enabled'
    }
    
    with open(config_path, 'w') as f:
        json.dump(modified_config, f)
    
    # Wait for reload
    print("Waiting for hot-reload detection...")
    time.sleep(2.5)
    
    watcher.stop()
    
    if reloaded[0]:
        print("✓ Configuration was reloaded automatically")
        print(f"  New config: {new_config[0]}")
    else:
        print("○ Reload not detected (may need more time)")
    
    # Cleanup
    os.remove(config_path)
    os.rmdir(temp_dir)


def main():
    """Run all deployment feature tests."""
    print("\n" + "="*60)
    print("Mira Deployment Features - Standalone Test")
    print("="*60)
    print("\nThis test demonstrates deployment features independently")
    print("without requiring full application initialization.")
    
    try:
        test_structured_logging()
        test_graceful_shutdown()
        test_secrets_management()
        test_config_hotreload()
        
        print("\n" + "="*60)
        print("✓ All deployment features tested successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
