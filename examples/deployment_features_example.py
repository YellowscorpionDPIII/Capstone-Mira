#!/usr/bin/env python3
"""
Example demonstrating Mira's deployment-ready features:
- Structured logging with correlation IDs
- Graceful shutdown
- Configuration hot-reload
- Secrets management
"""

import time
import signal
from mira.app import MiraApplication
from mira.utils.structured_logging import set_correlation_id, get_structured_logger


def main():
    """Main function demonstrating deployment features."""
    
    print("=" * 60)
    print("Mira Deployment Features Example")
    print("=" * 60)
    
    # Initialize the application with config file
    # This enables hot-reload if configured
    config_path = 'config.example.json'
    app = MiraApplication(config_path)
    
    # Get a structured logger
    logger = get_structured_logger('example')
    
    print("\n1. Structured Logging with Correlation IDs")
    print("-" * 60)
    
    # Generate a correlation ID for this request
    correlation_id = set_correlation_id()
    logger.info("Starting example with correlation ID", extra={
        'correlation_id': correlation_id,
        'feature': 'structured_logging'
    })
    
    # Process a message - correlation ID will be included in all logs
    response = app.process_message({
        'type': 'generate_plan',
        'data': {
            'name': 'Example Project',
            'goals': ['Goal 1', 'Goal 2'],
            'duration_weeks': 8
        }
    })
    
    logger.info("Message processed successfully", extra={
        'status': response.get('status'),
        'agent': response.get('agent_id')
    })
    
    print("\n2. Graceful Shutdown")
    print("-" * 60)
    print("Graceful shutdown is automatically configured.")
    print("Press Ctrl+C to trigger graceful shutdown...")
    print("The application will:")
    print("  - Stop accepting new requests")
    print("  - Finish processing ongoing requests")
    print("  - Close all connections cleanly")
    print("  - Stop background workers")
    
    print("\n3. Configuration Hot-Reload")
    print("-" * 60)
    if app.hot_reload_config:
        print("✓ Hot-reload is ENABLED")
        print("  Configuration changes will be automatically detected")
        print("  Modify config.example.json to see hot-reload in action")
    else:
        print("○ Hot-reload is DISABLED")
        print("  Enable it in config.example.json:")
        print('  "config": { "hot_reload": true }')
    
    print("\n4. Secrets Management")
    print("-" * 60)
    secrets_backend = app.config.get('secrets.backend', 'env')
    auto_refresh = app.config.get('secrets.auto_refresh', False)
    
    print(f"✓ Secrets backend: {secrets_backend}")
    if auto_refresh:
        refresh_interval = app.config.get('secrets.refresh_interval', 3600)
        print(f"✓ Auto-refresh ENABLED (interval: {refresh_interval}s)")
        print("  Secrets will be automatically rotated")
    else:
        print("○ Auto-refresh DISABLED")
    
    print("\nExample of using secrets in config:")
    print('  "github": { "token": "secret://github-credentials:token" }')
    
    print("\n" + "=" * 60)
    print("Example running. Press Ctrl+C to exit gracefully.")
    print("=" * 60)
    
    # Keep the application running
    try:
        # In a real application, this would be app.start()
        # For this example, we just keep it alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal, shutting down gracefully...")
        app.stop()
        print("Shutdown complete!")


if __name__ == '__main__':
    main()
