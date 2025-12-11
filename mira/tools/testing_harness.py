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
import time
import os

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


def test_rate_limit(args):
    """Test rate limiting with configurable burst requests."""
    print("=== Rate Limit Testing ===\n")
    
    # Build URL
    url = f"http://{args.host}:{args.port}/webhook/{args.service}"
    
    # Prepare headers
    headers = {'Content-Type': 'application/json'}
    if args.api_key:
        headers['Authorization'] = f'Bearer {args.api_key}'
    
    # Test payload
    payload = {
        'event': 'test',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'data': {'test': True}
    }
    
    # Display test configuration
    print(f"Target: {url}")
    print(f"Requests: {args.requests}")
    print(f"Interval: {args.interval}s")
    print(f"Rate limiting enabled: {os.getenv('MIRA_RATE_LIMITING_ENABLED', 'true')}\n")
    
    # Track results
    results = {
        'success': 0,
        'rate_limited': 0,
        'errors': 0,
        'response_times': []
    }
    
    print("Sending requests...")
    print("-" * 60)
    
    for i in range(args.requests):
        start_time = time.time()
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            duration = (time.time() - start_time) * 1000  # ms
            results['response_times'].append(duration)
            
            if response.status_code == 200:
                results['success'] += 1
                status = "✓ OK"
            elif response.status_code == 429:
                results['rate_limited'] += 1
                status = "⚠ RATE LIMITED"
                # Try to get retry-after header
                retry_after = response.headers.get('Retry-After', 'N/A')
                if retry_after != 'N/A':
                    status += f" (retry after: {retry_after}s)"
            elif response.status_code == 503:
                results['errors'] += 1
                status = "⚠ MAINTENANCE MODE"
            else:
                results['errors'] += 1
                status = f"✗ ERROR ({response.status_code})"
            
            print(f"Request {i+1:3d}: {status} ({duration:.0f}ms)")
            
        except requests.exceptions.RequestException as e:
            results['errors'] += 1
            print(f"Request {i+1:3d}: ✗ FAILED ({str(e)})")
        
        # Wait for interval between requests
        if i < args.requests - 1 and args.interval > 0:
            time.sleep(args.interval)
    
    # Display summary
    print("-" * 60)
    print("\n=== Summary ===\n")
    print(f"Total requests:    {args.requests}")
    print(f"Successful:        {results['success']} ({results['success']/args.requests*100:.1f}%)")
    print(f"Rate limited (429): {results['rate_limited']} ({results['rate_limited']/args.requests*100:.1f}%)")
    print(f"Errors:            {results['errors']} ({results['errors']/args.requests*100:.1f}%)")
    
    if results['response_times']:
        avg_time = sum(results['response_times']) / len(results['response_times'])
        min_time = min(results['response_times'])
        max_time = max(results['response_times'])
        print(f"\nResponse times:")
        print(f"  Average: {avg_time:.0f}ms")
        print(f"  Min:     {min_time:.0f}ms")
        print(f"  Max:     {max_time:.0f}ms")
    
    # Check if rate limiting is working as expected
    print("\n=== Analysis ===\n")
    if os.getenv('MIRA_RATE_LIMITING_ENABLED', 'true').lower() == 'false':
        if results['rate_limited'] == 0:
            print("✓ Rate limiting disabled - no 429 responses (as expected)")
        else:
            print("⚠ Rate limiting disabled but received 429 responses (unexpected)")
    else:
        if results['rate_limited'] > 0:
            print("✓ Rate limiting enabled - 429 responses received (as expected)")
        else:
            print("⚠ Rate limiting enabled but no 429 responses (check threshold)")


def export_config(args):
    """Export current configuration as example."""
    print("=== Export Configuration ===\n")
    
    # Load current config if exists
    config_dict = {}
    if args.config_path and os.path.exists(args.config_path):
        try:
            with open(args.config_path, 'r') as f:
                config_dict = json.load(f)
            print(f"Loaded configuration from {args.config_path}\n")
        except Exception as e:
            print(f"Error loading config: {e}\n")
    
    # Create example config with all options
    example_config = {
        "webhook": {
            "enabled": config_dict.get('webhook', {}).get('enabled', True),
            "host": config_dict.get('webhook', {}).get('host', '0.0.0.0'),
            "port": config_dict.get('webhook', {}).get('port', 5000),
            "secret_key": "CHANGE_ME"
        },
        "broker": {
            "enabled": config_dict.get('broker', {}).get('enabled', True),
            "queue_size": config_dict.get('broker', {}).get('queue_size', 1000)
        },
        "security": {
            "api_key_enabled": True,
            "api_key_expiry_days": 90,
            "ip_allowlist": ["192.168.1.0/24"],
            "ip_denylist": [],
            "webhook_secrets": {
                "github": "GITHUB_WEBHOOK_SECRET",
                "trello": "TRELLO_WEBHOOK_SECRET"
            }
        },
        "operational": {
            "rate_limiting_enabled": True,
            "rate_limit_per_minute": 60,
            "verbose_logging": False,
            "maintenance_mode": False,
            "maintenance_message": "System is under maintenance"
        },
        "observability": {
            "metrics_enabled": True,
            "health_check_enabled": True
        },
        "integrations": {
            "airtable": {
                "enabled": False,
                "api_key": "AIRTABLE_API_KEY",
                "base_id": "AIRTABLE_BASE_ID"
            }
        }
    }
    
    # Write to output file
    output_path = args.output or 'config.example.json'
    try:
        with open(output_path, 'w') as f:
            json.dump(example_config, f, indent=2)
        print(f"✓ Configuration exported to: {output_path}")
        
        # Also create .env.example
        env_path = '.env.example'
        with open(env_path, 'w') as f:
            f.write("# Mira Platform Environment Variables\n\n")
            f.write("# Required for production\n")
            f.write("AIRTABLE_BASE_ID=your_base_id_here\n")
            f.write("AIRTABLE_API_KEY=your_api_key_here\n")
            f.write("REDIS_URL=redis://localhost:6379/0\n\n")
            f.write("# Webhook configuration\n")
            f.write("MIRA_WEBHOOK_SECRET=change_me_to_random_secret\n\n")
            f.write("# Rate limiting\n")
            f.write("MIRA_RATE_LIMITING_ENABLED=true\n")
            f.write("MIRA_RATE_LIMIT_PER_MINUTE=60\n\n")
            f.write("# Logging\n")
            f.write("MIRA_LOG_LEVEL=INFO\n\n")
            f.write("# Security\n")
            f.write("MIRA_API_KEY_EXPIRY_DAYS=90\n")
        
        print(f"✓ Environment variables template created: {env_path}")
        
    except Exception as e:
        print(f"❌ Error exporting config: {e}")


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
  
  # Test rate limiting
  %(prog)s test-rate-limit --requests 100 --interval 0.01
  
  # Export configuration example
  %(prog)s export-config --output config.example.json
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
    
    # Test rate limit command
    rate_limit = subparsers.add_parser('test-rate-limit', help='Test rate limiting')
    rate_limit.add_argument('--service', default='test', help='Service name (default: test)')
    rate_limit.add_argument('--host', default='localhost', help='Host (default: localhost)')
    rate_limit.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')
    rate_limit.add_argument('--api-key', help='API key for authentication')
    rate_limit.add_argument('--requests', type=int, default=100, help='Number of requests (default: 100)')
    rate_limit.add_argument('--interval', type=float, default=0.01, help='Interval between requests in seconds (default: 0.01)')
    
    # Export config command
    export = subparsers.add_parser('export-config', help='Export configuration example')
    export.add_argument('--config-path', help='Path to existing config file to use as base')
    export.add_argument('--output', help='Output file path (default: config.example.json)')
    
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
        'list-keys': list_api_keys,
        'test-rate-limit': test_rate_limit,
        'export-config': export_config
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
