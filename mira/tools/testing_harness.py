#!/usr/bin/env python3
"""Local testing harness for Mira platform.

Provides CLI commands to:
- Generate API keys
- Test webhook endpoints
- Display structured logs
- Validate configuration
"""
import argparse
import json
import sys
import requests
from typing import Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, '/home/runner/work/Capstone-Mira/Capstone-Mira')

from mira.security.api_key_manager import APIKeyManager
from mira.security.audit_logger import AuditLogger
from mira.config.validation import load_and_validate_config, ValidationError


def setup_logging():
    """Setup structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def generate_api_key(args):
    """Generate a new API key."""
    print("=== Generate API Key ===\n")
    
    # Create audit logger
    audit_logger = AuditLogger()
    
    # Create API key manager
    manager = APIKeyManager(audit_logger=audit_logger)
    
    # Generate key
    key_id, raw_key = manager.generate_key(
        name=args.name,
        expires_in_days=args.expires_in_days
    )
    
    print(f"✓ API Key Generated Successfully")
    print(f"\nKey ID: {key_id}")
    print(f"API Key: {raw_key}")
    print(f"Name: {args.name}")
    
    if args.expires_in_days:
        print(f"Expires in: {args.expires_in_days} days")
    else:
        print("Expires: Never")
    
    print("\n⚠️  Save this key securely - it won't be shown again!")
    print(f"\nTo use this key, include it in your requests:")
    print(f"  Authorization: Bearer {raw_key}")


def test_webhook(args):
    """Test a webhook endpoint."""
    print("=== Test Webhook ===\n")
    
    # Build URL
    url = f"http://{args.host}:{args.port}/webhook/{args.service}"
    
    # Prepare headers
    headers = {'Content-Type': 'application/json'}
    
    if args.secret:
        headers['X-Service-Secret'] = args.secret
    
    if args.api_key:
        headers['Authorization'] = f'Bearer {args.api_key}'
    
    # Prepare payload
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON payload: {e}")
            return
    else:
        payload = {
            'event': 'test',
            'timestamp': '2025-12-10T00:00:00Z',
            'data': {'test': True}
        }
    
    print(f"Target: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    # Send request
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code} {response.reason}")
        print(f"\nResponse:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        
        if response.status_code == 200:
            print("\n✓ Webhook test successful")
        else:
            print("\n❌ Webhook test failed")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def check_health(args):
    """Check health endpoints."""
    print("=== Health Check ===\n")
    
    base_url = f"http://{args.host}:{args.port}"
    
    # Check /health
    print("Checking /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        print()
    except Exception as e:
        print(f"❌ Health check failed: {e}\n")
    
    # Check /ready
    print("Checking /ready endpoint...")
    try:
        response = requests.get(f"{base_url}/ready", timeout=5)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✓ All systems ready")
        else:
            print("\n⚠️  Some dependencies are unhealthy")
            
    except Exception as e:
        print(f"❌ Readiness check failed: {e}")


def validate_config_cmd(args):
    """Validate configuration."""
    print("=== Validate Configuration ===\n")
    
    try:
        config = load_and_validate_config(args.config_path)
        print("✓ Configuration is valid\n")
        
        # Print summary
        print("Configuration Summary:")
        print(f"- Webhook enabled: {config.webhook.enabled}")
        print(f"- Broker enabled: {config.broker.enabled}")
        print(f"- Metrics enabled: {config.observability.metrics_enabled}")
        print(f"- Health checks enabled: {config.observability.health_check_enabled}")
        print(f"- Maintenance mode: {config.operational.maintenance_mode}")
        
    except ValidationError as e:
        print("❌ Configuration validation failed:\n")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            print(f"  {loc}: {error['msg']}")
    except Exception as e:
        print(f"❌ Error: {e}")


def list_api_keys(args):
    """List all API keys."""
    print("=== API Keys ===\n")
    
    # Create manager
    manager = APIKeyManager()
    
    # For demo purposes, we need to load keys from somewhere
    # In production, this would load from a database
    print("Note: This is a demo. In production, keys would be loaded from storage.\n")
    
    keys = manager.list_keys(include_revoked=args.include_revoked)
    
    if not keys:
        print("No API keys found")
        return
    
    for i, key in enumerate(keys, 1):
        print(f"{i}. {key['name']}")
        print(f"   ID: {key['key_id']}")
        print(f"   Created: {key['created_at']}")
        print(f"   Expires: {key['expires_at'] or 'Never'}")
        print(f"   Status: {'Revoked' if key['revoked'] else 'Active'}")
        if key['rotated_from']:
            print(f"   Rotated from: {key['rotated_from']}")
        print()


def main():
    """Main entry point."""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Mira Local Testing Harness',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate an API key
  %(prog)s generate-key --name "My API Key" --expires-in-days 30
  
  # Test a webhook
  %(prog)s test-webhook --service github --host localhost --port 5000
  
  # Check health endpoints
  %(prog)s health --host localhost --port 5000
  
  # Validate configuration
  %(prog)s validate-config --config-path config.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate API key command
    gen_key = subparsers.add_parser('generate-key', help='Generate a new API key')
    gen_key.add_argument('--name', required=True, help='Name for the API key')
    gen_key.add_argument('--expires-in-days', type=int, help='Key expiry in days')
    
    # Test webhook command
    test_wh = subparsers.add_parser('test-webhook', help='Test a webhook endpoint')
    test_wh.add_argument('--service', required=True, help='Service name (e.g., github, trello)')
    test_wh.add_argument('--host', default='localhost', help='Host (default: localhost)')
    test_wh.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')
    test_wh.add_argument('--secret', help='Service shared secret')
    test_wh.add_argument('--api-key', help='API key for authentication')
    test_wh.add_argument('--payload', help='JSON payload (optional)')
    
    # Health check command
    health_cmd = subparsers.add_parser('health', help='Check health endpoints')
    health_cmd.add_argument('--host', default='localhost', help='Host (default: localhost)')
    health_cmd.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')
    
    # Validate config command
    val_cfg = subparsers.add_parser('validate-config', help='Validate configuration')
    val_cfg.add_argument('--config-path', help='Path to config file')
    
    # List keys command
    list_keys = subparsers.add_parser('list-keys', help='List API keys')
    list_keys.add_argument('--include-revoked', action='store_true', help='Include revoked keys')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    commands = {
        'generate-key': generate_api_key,
        'test-webhook': test_webhook,
        'health': check_health,
        'validate-config': validate_config_cmd,
        'list-keys': list_api_keys
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
