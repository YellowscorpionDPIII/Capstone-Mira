#!/usr/bin/env python3
"""
Mira HITL Authenticated Webhook Server

This script starts an authenticated webhook server with API key management.
Perfect for n8n, Airtable, and other workflow integrations.
"""
import sys
import argparse
from mira.auth import ApiKeyManager, AuthenticatedWebhookHandler
from mira.integrations.airtable_integration import AirtableIntegration
from mira.config.settings import get_config
import logging


def setup_logging(level='INFO'):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def initialize_api_key_manager(config):
    """Initialize API key manager with optional Airtable storage."""
    storage_backend = None
    
    # Set up Airtable storage if configured
    if config.get('integrations.airtable.enabled'):
        airtable_config = {
            'api_key': config.get('integrations.airtable.api_key'),
            'base_id': config.get('integrations.airtable.base_id')
        }
        airtable = AirtableIntegration(airtable_config)
        if airtable.connect():
            storage_backend = airtable
            logging.info("✓ Connected to Airtable for API key storage")
        else:
            logging.warning("⚠ Could not connect to Airtable, using in-memory storage")
    
    # Initialize API key manager
    default_expiry = config.get('api_keys.default_expiry_days', 90)
    manager = ApiKeyManager(
        storage_backend=storage_backend,
        default_expiry_days=default_expiry
    )
    
    return manager


def create_initial_admin_key(manager):
    """Create an initial admin key if none exist."""
    existing_admins = manager.list_keys(role='admin', status='active')
    
    if not existing_admins:
        raw_key, api_key = manager.generate_key(
            role='admin',
            name='Initial Admin Key',
            expiry_days=365
        )
        
        print("\n" + "=" * 60)
        print("🔑 INITIAL ADMIN KEY CREATED")
        print("=" * 60)
        print(f"\nAPI Key: {raw_key}")
        print(f"Key ID: {api_key.key_id}")
        print(f"Role: {api_key.role}")
        print(f"Expires: {api_key.expires_at}")
        print("\n⚠️  IMPORTANT: Save this key securely!")
        print("This is the only time you'll see this key.")
        print("Use it to create additional keys via the API.")
        print("=" * 60 + "\n")
        
        return raw_key
    else:
        logging.info(f"Found {len(existing_admins)} existing admin key(s)")
        return None


def register_webhook_handlers(handler):
    """Register webhook handlers for different services."""
    
    def handle_n8n_webhook(data):
        """Handle n8n webhook events."""
        auth_info = data.get('_auth', {})
        msg_type = data.get('type', 'unknown')
        
        logging.info(f"Processing n8n webhook: {msg_type} from {auth_info.get('key_id')}")
        
        # Process the webhook data
        # In production, route to appropriate agent based on message type
        return {
            'status': 'success',
            'service': 'n8n',
            'message': f'Processed {msg_type} request',
            'auth': auth_info
        }
    
    def handle_airtable_webhook(data):
        """Handle Airtable webhook events."""
        auth_info = data.get('_auth', {})
        
        logging.info(f"Processing Airtable webhook from {auth_info.get('key_id')}")
        
        return {
            'status': 'success',
            'service': 'airtable',
            'message': 'Processed Airtable webhook',
            'auth': auth_info
        }
    
    def handle_generic_webhook(data):
        """Handle generic webhook events."""
        auth_info = data.get('_auth', {})
        
        logging.info(f"Processing generic webhook from {auth_info.get('key_id')}")
        
        return {
            'status': 'success',
            'service': 'generic',
            'message': 'Processed generic webhook',
            'auth': auth_info
        }
    
    # Register handlers
    handler.register_handler('n8n', handle_n8n_webhook)
    handler.register_handler('airtable', handle_airtable_webhook)
    handler.register_handler('generic', handle_generic_webhook)
    
    logging.info("✓ Registered webhook handlers: n8n, airtable, generic")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Mira HITL Authenticated Webhook Server'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )
    parser.add_argument(
        '--create-admin-key',
        action='store_true',
        help='Create an initial admin key if none exist'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Load configuration
    config = get_config(args.config)
    
    print("\n" + "=" * 60)
    print("🚀 Starting Mira HITL Authenticated Webhook Server")
    print("=" * 60)
    
    # Initialize API key manager
    logging.info("Initializing API key manager...")
    manager = initialize_api_key_manager(config)
    
    # Create initial admin key if requested
    if args.create_admin_key:
        create_initial_admin_key(manager)
    
    # Initialize webhook handler
    secret_key = config.get('webhook.secret_key')
    webhook_handler = AuthenticatedWebhookHandler(
        api_key_manager=manager,
        secret_key=secret_key
    )
    
    # Register webhook handlers
    register_webhook_handlers(webhook_handler)
    
    # Print startup information
    print(f"\n✓ Server configuration:")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  API Key Storage: {'Airtable' if manager.storage else 'In-Memory'}")
    print(f"  Webhook Secret: {'Configured' if secret_key else 'Not Set'}")
    
    print(f"\n✓ Available endpoints:")
    print(f"  POST   http://{args.host}:{args.port}/webhook/<service>")
    print(f"  POST   http://{args.host}:{args.port}/api/keys")
    print(f"  GET    http://{args.host}:{args.port}/api/keys")
    print(f"  DELETE http://{args.host}:{args.port}/api/keys/<key_id>")
    print(f"  POST   http://{args.host}:{args.port}/api/keys/<key_id>/rotate")
    print(f"  GET    http://{args.host}:{args.port}/api/auth/validate")
    print(f"  GET    http://{args.host}:{args.port}/health")
    
    print(f"\n✓ Supported webhook services: n8n, airtable, generic")
    
    print(f"\n📚 Documentation: docs/API_KEY_MANAGEMENT.md")
    print(f"🔧 Examples: examples/api_key_management.py")
    
    print("\n" + "=" * 60)
    print("Server is running... Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Start server
    try:
        webhook_handler.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
