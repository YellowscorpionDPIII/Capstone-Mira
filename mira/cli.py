"""CLI commands for testing and development."""
import argparse
import sys
import json
import logging
from typing import Optional
from mira.core.api_key_manager import APIKeyManager, InMemoryAPIKeyStorage, FileAPIKeyStorage
from mira.core.health import get_health_registry
from mira.core.metrics import get_metrics_collector


def setup_cli_logging(verbose: bool = False):
    """Set up logging for CLI commands."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_generate_test_key(args):
    """Generate a test API key."""
    setup_cli_logging(args.verbose)
    
    # Initialize API key manager
    if args.storage == 'file':
        storage_path = args.storage_path or '/tmp/mira_api_keys.json'
        storage = FileAPIKeyStorage(storage_path)
        print(f"Using file storage: {storage_path}")
    else:
        storage = InMemoryAPIKeyStorage()
        print("Using in-memory storage")
    
    manager = APIKeyManager(storage, default_expiry_days=args.expiry_days)
    
    # Create key
    api_key, record = manager.create(
        key_id=args.key_id,
        expires_in_days=args.expiry_days if args.expiry_days != 90 else None,
        metadata={'created_by': 'cli', 'purpose': args.purpose or 'testing'}
    )
    
    print("\n✓ API Key generated successfully!")
    print(f"Key ID: {record.key_id}")
    print(f"API Key: {api_key}")
    print(f"Created: {record.created_at.isoformat()}")
    if record.expires_at:
        print(f"Expires: {record.expires_at.isoformat()}")
    print("\n⚠ Store this key securely - it cannot be retrieved again!")


def cmd_check_health(args):
    """Check application health status."""
    setup_cli_logging(args.verbose)
    
    registry = get_health_registry()
    
    if args.type == 'health':
        status = registry.check_health()
        print("\n=== Health Check ===")
    else:
        status = registry.check_readiness()
        print("\n=== Readiness Check ===")
    
    print(json.dumps(status, indent=2))
    
    # Exit with error code if not ready
    if args.type == 'ready' and status['status'] != 'ready':
        sys.exit(1)


def cmd_show_metrics(args):
    """Display current metrics."""
    setup_cli_logging(args.verbose)
    
    collector = get_metrics_collector()
    metrics = collector.get_all_metrics()
    
    print("\n=== Metrics ===")
    print(json.dumps(metrics, indent=2))


def cmd_test_webhook(args):
    """Test webhook endpoint."""
    setup_cli_logging(args.verbose)
    
    import requests
    import hmac
    import hashlib
    
    # Prepare payload
    payload = args.payload or '{"test": "data"}'
    payload_bytes = payload.encode('utf-8')
    
    # Calculate signature if secret provided
    headers = {'Content-Type': 'application/json'}
    if args.secret:
        signature = 'sha256=' + hmac.new(
            args.secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        headers['X-Hub-Signature-256'] = signature
        print(f"Using signature: {signature}")
    
    # Make request
    url = f"{args.url}/webhook/{args.service}"
    print(f"\nSending webhook to: {url}")
    
    try:
        response = requests.post(url, data=payload_bytes, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✓ Webhook test successful!")
        else:
            print("\n✗ Webhook test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


def cmd_smoke_test(args):
    """Run end-to-end smoke tests."""
    setup_cli_logging(args.verbose)
    
    print("\n=== Running Smoke Tests ===\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        registry = get_health_registry()
        health = registry.check_health()
        if health['status'] == 'healthy':
            print("   ✓ Health check passed")
            tests_passed += 1
        else:
            print("   ✗ Health check failed")
            tests_failed += 1
    except Exception as e:
        print(f"   ✗ Health check error: {e}")
        tests_failed += 1
    
    # Test 2: Metrics collection
    print("2. Testing metrics collection...")
    try:
        collector = get_metrics_collector()
        counter = collector.counter('mira_smoke_test_total')
        counter.inc()
        metrics = collector.get_all_metrics()
        if len(metrics['counters']) > 0:
            print("   ✓ Metrics collection passed")
            tests_passed += 1
        else:
            print("   ✗ Metrics collection failed")
            tests_failed += 1
    except Exception as e:
        print(f"   ✗ Metrics error: {e}")
        tests_failed += 1
    
    # Test 3: API key generation
    print("3. Testing API key generation...")
    try:
        storage = InMemoryAPIKeyStorage()
        manager = APIKeyManager(storage)
        api_key, record = manager.create()
        is_valid, key_id, status = manager.validate(api_key)
        if is_valid:
            print("   ✓ API key generation passed")
            tests_passed += 1
        else:
            print("   ✗ API key validation failed")
            tests_failed += 1
    except Exception as e:
        print(f"   ✗ API key error: {e}")
        tests_failed += 1
    
    # Summary
    print(f"\n=== Smoke Test Summary ===")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    
    if tests_failed > 0:
        print("\n✗ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Mira Platform CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate a test API key
  python -m mira.cli generate-test-key
  
  # Generate key with specific settings
  python -m mira.cli generate-test-key --key-id mykey --expiry-days 30 --storage file
  
  # Check health
  python -m mira.cli check-health
  
  # Check readiness
  python -m mira.cli check-health --type ready
  
  # Show metrics
  python -m mira.cli show-metrics
  
  # Test webhook
  python -m mira.cli test-webhook --url http://localhost:5000 --service github
  
  # Run smoke tests
  python -m mira.cli smoke-test
        '''
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # generate-test-key command
    key_parser = subparsers.add_parser('generate-test-key', help='Generate a test API key')
    key_parser.add_argument('--key-id', help='Custom key ID')
    key_parser.add_argument('--expiry-days', type=int, default=90, help='Expiration in days')
    key_parser.add_argument('--storage', choices=['memory', 'file'], default='memory', help='Storage backend')
    key_parser.add_argument('--storage-path', help='Path for file storage')
    key_parser.add_argument('--purpose', help='Purpose of the key')
    key_parser.set_defaults(func=cmd_generate_test_key)
    
    # check-health command
    health_parser = subparsers.add_parser('check-health', help='Check application health')
    health_parser.add_argument('--type', choices=['health', 'ready'], default='health', help='Check type')
    health_parser.set_defaults(func=cmd_check_health)
    
    # show-metrics command
    metrics_parser = subparsers.add_parser('show-metrics', help='Display current metrics')
    metrics_parser.set_defaults(func=cmd_show_metrics)
    
    # test-webhook command
    webhook_parser = subparsers.add_parser('test-webhook', help='Test webhook endpoint')
    webhook_parser.add_argument('--url', default='http://localhost:5000', help='Base URL')
    webhook_parser.add_argument('--service', default='github', help='Service name')
    webhook_parser.add_argument('--secret', help='Secret key for signature')
    webhook_parser.add_argument('--payload', help='JSON payload')
    webhook_parser.set_defaults(func=cmd_test_webhook)
    
    # smoke-test command
    smoke_parser = subparsers.add_parser('smoke-test', help='Run end-to-end smoke tests')
    smoke_parser.set_defaults(func=cmd_smoke_test)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
