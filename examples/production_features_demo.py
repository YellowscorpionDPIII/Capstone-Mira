#!/usr/bin/env python3
"""
Example demonstrating production deployment features:
- Structured logging with correlation IDs
- Graceful shutdown
- Config hot-reload
- Secrets management (mock)

This example shows how to use Mira in a production environment.
"""

import time
import json
import tempfile
import os
from pathlib import Path

from mira.app import MiraApplication
from mira.utils.structured_logging import (
    CorrelationContext,
    set_correlation_id,
    get_logger
)
from mira.utils.shutdown_handler import register_shutdown_callback
from mira.utils.secrets_manager import SecretsManager, SecretsBackend


# Mock secrets backend for demonstration
class MockSecretsBackend(SecretsBackend):
    """Mock secrets backend for demonstration purposes."""
    
    def __init__(self):
        self.secrets = {
            'app/database': {
                'username': 'app_user',
                'password': 'secure_password_123'
            },
            'app/api': {
                'key': 'api_key_xyz789'
            }
        }
    
    def get_secret(self, path: str, key=None):
        if path not in self.secrets:
            raise KeyError(f"Secret not found: {path}")
        data = self.secrets[path]
        if key:
            return data.get(key)
        return data
    
    def list_secrets(self, path: str) -> list:
        return [k for k in self.secrets.keys() if k.startswith(path)]


def main():
    """Run production features demonstration."""
    print("=" * 70)
    print("Mira Production Features Demonstration")
    print("=" * 70)
    
    # Create temporary config file for hot-reload demo
    temp_dir = tempfile.mkdtemp()
    config_file = Path(temp_dir) / 'config.json'
    
    config_data = {
        'logging': {'level': 'INFO'},
        'broker': {'enabled': True},
        'webhook': {'enabled': False},
        'agents': {
            'project_plan_agent': {'enabled': True},
            'risk_assessment_agent': {'enabled': True},
            'status_reporter_agent': {'enabled': True},
            'orchestrator_agent': {'enabled': True}
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"\n1. Created temporary config file: {config_file}")
    
    # Initialize Mira with production features
    print("\n2. Initializing Mira with production features...")
    print("   - Structured logging: ENABLED")
    print("   - Config hot-reload: ENABLED")
    print("   - Graceful shutdown: ENABLED (SIGTERM/SIGINT handlers)")
    
    app = MiraApplication(
        config_path=str(config_file),
        use_structured_logging=True,
        enable_hot_reload=True
    )
    
    # Setup secrets management
    print("\n3. Setting up secrets management...")
    secrets_backend = MockSecretsBackend()
    secrets = SecretsManager(secrets_backend)
    
    # Get secrets
    db_password = secrets.get_secret('app/database', 'password')
    api_key = secrets.get_secret('app/api', 'key')
    
    print(f"   ✓ Retrieved database password: {db_password[:8]}***")
    print(f"   ✓ Retrieved API key: {api_key[:10]}***")
    
    # Register callback for secret rotation
    rotation_count = [0]
    
    def on_secret_rotation(new_value):
        rotation_count[0] += 1
        print(f"   🔄 Secret rotated (callback #{rotation_count[0]}): {new_value[:10]}***")
    
    secrets.register_refresh_callback('app/api', on_secret_rotation, 'key')
    
    # Start auto-refresh
    print("   ✓ Started auto-refresh for rotating secrets")
    secrets.start_auto_refresh(interval=3)
    
    # Register custom shutdown callback
    print("\n4. Registering custom shutdown callbacks...")
    
    def cleanup_resources():
        print("   🧹 Cleaning up application resources...")
        secrets.stop_auto_refresh()
    
    register_shutdown_callback(cleanup_resources, name='app_cleanup')
    print("   ✓ Registered cleanup callback")
    
    # Demonstrate structured logging with correlation IDs
    print("\n5. Demonstrating structured logging with correlation IDs...")
    logger = get_logger('demo')
    
    # Process multiple requests with different correlation IDs
    for i in range(3):
        with CorrelationContext() as correlation_id:
            logger.info(f"Processing request #{i+1}", 
                       extra={'request_id': i+1, 'user': 'demo_user'})
            
            # Simulate processing
            message = {
                'type': 'generate_plan',
                'data': {
                    'name': f'Demo Project {i+1}',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 8
                }
            }
            
            result = app.process_message(message)
            logger.info(f"Request completed", 
                       extra={'status': result.get('status'),
                              'correlation_id': correlation_id})
    
    print("   ✓ Processed 3 requests with unique correlation IDs")
    print("   ✓ Check logs for JSON-formatted output with correlation tracking")
    
    # Demonstrate config hot-reload
    print("\n6. Demonstrating config hot-reload...")
    print("   Modifying config file...")
    
    # Update config
    config_data['logging']['level'] = 'DEBUG'
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print("   ⏳ Waiting for config reload...")
    time.sleep(2)
    print("   ✓ Config should be reloaded automatically (check logs)")
    
    # Simulate secret rotation
    print("\n7. Simulating secret rotation...")
    secrets_backend.secrets['app/api']['key'] = 'rotated_key_abc456'
    print("   ⏳ Waiting for secret refresh...")
    time.sleep(4)
    
    # Demonstrate graceful shutdown
    print("\n8. Graceful shutdown demonstration...")
    print("   To test graceful shutdown, press Ctrl+C")
    print("   The application will:")
    print("   - Execute all registered cleanup callbacks")
    print("   - Stop the message broker")
    print("   - Disable config hot-reload")
    print("   - Stop secrets auto-refresh")
    print("   - Exit cleanly")
    
    print("\n" + "=" * 70)
    print("Production Features Summary:")
    print("=" * 70)
    print("✅ Structured Logging - JSON logs with correlation IDs")
    print("✅ Graceful Shutdown - SIGTERM/SIGINT handlers registered")
    print("✅ Config Hot-Reload - Automatic config reload on file changes")
    print("✅ Secrets Management - Mock backend with auto-refresh")
    print("=" * 70)
    
    # Keep running for a bit
    print("\nApplication running... (Press Ctrl+C to trigger graceful shutdown)")
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n🛑 Graceful shutdown initiated...")
        app.stop()
        print("✅ Application stopped cleanly")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    print(f"\n🧹 Cleaned up temporary files")


if __name__ == '__main__':
    main()
