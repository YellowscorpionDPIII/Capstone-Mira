# Quick Start: Security & Observability

Get started with Mira's security and observability features in 5 minutes.

## Prerequisites

```bash
pip install -e .
pip install pydantic requests
```

## 1. Generate an API Key (30 seconds)

```bash
# Generate a test API key
python -m mira.cli generate-test-key --key-id my-app
```

Save the output API key securely. Example output:
```
✓ API Key generated successfully!
Key ID: my-app
API Key: UbNXSsacMxZRTrO0sUFE38XVi6pY90qC8R8YMBGEx50
Created: 2025-12-11T13:49:27.769998
Expires: 2026-03-11T13:49:27.769998

⚠ Store this key securely - it cannot be retrieved again!
```

## 2. Set Up Secure Webhooks (2 minutes)

```python
from mira.core.webhook_handler import WebhookHandler
from mira.core.webhook_security import WebhookSecurityConfig

# Configure security
config = WebhookSecurityConfig(
    secret_key="your-webhook-secret-here",
    allowed_ips=["192.168.1.0/24"],  # Your trusted network
    require_signature=True,
    require_ip_whitelist=True
)

# Create handler
handler = WebhookHandler(security_config=config)

# Register a webhook
def handle_github(data):
    print(f"Received: {data}")
    return {'status': 'ok'}

handler.register_handler('github', handle_github)

# Start server (includes /health, /ready, /metrics endpoints)
handler.run(host='0.0.0.0', port=5000)
```

## 3. Test Your Webhook (1 minute)

In another terminal:

```bash
python -m mira.cli test-webhook \
    --url http://localhost:5000 \
    --service github \
    --secret your-webhook-secret-here
```

## 4. Add Metrics to Your Code (1 minute)

```python
from mira.core.metrics import get_metrics_collector

metrics = get_metrics_collector()

# Track operations
counter = metrics.counter('mira_operations_total')
counter.inc()

# Time operations
with metrics.time('mira_operation_duration_seconds'):
    # Your code here
    process_data()
```

## 5. Set Up Health Checks (30 seconds)

```python
from mira.core.health import get_health_registry

registry = get_health_registry()

# Register dependencies
def check_database():
    return True  # Replace with actual check

registry.register_dependency('database', check_database, required=True)
```

## 6. Run Smoke Tests (30 seconds)

```bash
python -m mira.cli smoke-test
```

Expected output:
```
=== Running Smoke Tests ===

1. Testing health endpoint...
   ✓ Health check passed
2. Testing metrics collection...
   ✓ Metrics collection passed
3. Testing API key generation...
   ✓ API key generation passed

=== Smoke Test Summary ===
Passed: 3
Failed: 0

✓ All tests passed!
```

## Common Commands Cheat Sheet

```bash
# Generate API key
python -m mira.cli generate-test-key --key-id mykey

# Check health
python -m mira.cli check-health

# Check readiness
python -m mira.cli check-health --type ready

# View metrics
python -m mira.cli show-metrics

# Test webhook
python -m mira.cli test-webhook --url http://localhost:5000 --service github

# Run smoke tests
python -m mira.cli smoke-test
```

## Quick Code Examples

### Validate API Key in Flask

```python
from flask import request, jsonify
from mira.core.api_key_manager import APIKeyManager, InMemoryAPIKeyStorage

manager = APIKeyManager(InMemoryAPIKeyStorage())

@app.before_request
def check_api_key():
    key = request.headers.get('X-API-Key')
    if not key:
        return jsonify({'error': 'API key required'}), 401
    
    is_valid, key_id, status = manager.validate(key)
    if not is_valid:
        return jsonify({'error': 'Invalid key'}), 401
```

### Add Metrics to Any Function

```python
from mira.core.metrics import get_metrics_collector

metrics = get_metrics_collector()

def my_function():
    counter = metrics.counter('mira_my_function_calls_total')
    
    try:
        with metrics.time('mira_my_function_duration_seconds'):
            # Your code
            result = do_work()
            counter.inc()
            return result
    except Exception as e:
        error_counter = metrics.counter(
            'mira_my_function_errors_total',
            labels={'error_type': type(e).__name__}
        )
        error_counter.inc()
        raise
```

### Configure Feature Flags

```python
from mira.core.feature_flags import FeatureFlagsConfig, MaintenanceModeConfig

config = FeatureFlagsConfig(
    maintenance_mode=MaintenanceModeConfig(
        enabled=True,
        message="Scheduled maintenance in progress"
    )
)

if config.is_maintenance_mode():
    return "Service unavailable", 503
```

## Next Steps

1. Read the full [Security and Observability Guide](./SECURITY_AND_OBSERVABILITY.md)
2. Check out the [API Documentation](../DOCUMENTATION.md)
3. Review [Best Practices](#best-practices) in the main guide

## Troubleshooting

**Webhook returns 403?**
- Check IP is in allowed_ips list
- Verify signature is being sent correctly
- Test with: `python -m mira.cli test-webhook --secret YOUR_SECRET`

**Metrics not showing?**
- Ensure you're calling counter.inc() or gauge.set()
- Check `/metrics` endpoint: `curl http://localhost:5000/metrics`

**Health check fails?**
- Verify all required dependencies are healthy
- Check individual dependency: `registry.get_dependency_status('name')`

## Support

For more detailed information, see:
- [Security and Observability Guide](./SECURITY_AND_OBSERVABILITY.md)
- [Main Documentation](../DOCUMENTATION.md)
- [GitHub Issues](https://github.com/YellowscorpionDPIII/Capstone-Mira/issues)
