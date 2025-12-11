# Security and Observability Guide

This guide covers the security, observability, and operational control features introduced in the Mira platform.

## Table of Contents

1. [API Key Management](#api-key-management)
2. [Webhook Security](#webhook-security)
3. [Metrics and Monitoring](#metrics-and-monitoring)
4. [Health and Readiness Checks](#health-and-readiness-checks)
5. [Feature Flags and Configuration](#feature-flags-and-configuration)
6. [CLI Tools](#cli-tools)
7. [Examples](#examples)

## API Key Management

The API Key Manager provides a complete lifecycle for managing API keys with support for creation, rotation, revocation, and validation.

### Features

- **Lifecycle Management**: Create, rotate, revoke, and validate API keys
- **Expiration & Grace Period**: Configure expiration dates and grace periods
- **Pluggable Storage**: Abstract storage interface with in-memory and file-based implementations
- **Secure Hashing**: Keys are hashed using SHA-256 before storage

### Basic Usage

```python
from mira.core.api_key_manager import APIKeyManager, InMemoryAPIKeyStorage

# Initialize with in-memory storage
storage = InMemoryAPIKeyStorage()
manager = APIKeyManager(storage, default_expiry_days=90)

# Create a new API key
api_key, record = manager.create(
    key_id="my-app-key",
    expires_in_days=30,
    metadata={"app": "my-app", "env": "production"}
)

print(f"API Key: {api_key}")
print(f"Key ID: {record.key_id}")
print(f"Expires: {record.expires_at}")
```

### File-based Storage

```python
from mira.core.api_key_manager import APIKeyManager, FileAPIKeyStorage

# Use file-based storage for persistence
storage = FileAPIKeyStorage("/var/lib/mira/api_keys.json")
manager = APIKeyManager(storage)

# Keys are now persisted to disk
api_key, record = manager.create()
```

### Key Rotation

```python
# Rotate an existing key
new_key, record = manager.rotate("my-app-key")
print(f"New API Key: {new_key}")
```

### Key Validation

```python
# Validate an API key
is_valid, key_id, status = manager.validate(api_key)

if is_valid:
    print(f"Valid key: {key_id}, Status: {status.value}")
else:
    print("Invalid or expired key")
```

### Key Revocation

```python
# Revoke a key
manager.revoke("my-app-key")
```

## Webhook Security

Enhanced webhook security with multi-layer authentication pipeline.

### Features

- **IP Whitelisting**: CIDR-based IP filtering validated at startup
- **Secret Header**: Optional secret header authentication
- **HMAC Signature**: GitHub-compatible signature verification
- **Pipeline Authentication**: Layered checks with short-circuiting
- **Clear Failure Reasons**: Enum-based error reporting

### Configuration

```python
from mira.core.webhook_security import WebhookSecurityConfig, WebhookAuthenticator

config = WebhookSecurityConfig(
    secret_key="your-webhook-secret",
    allowed_ips=["192.168.1.0/24", "10.0.0.1"],
    require_signature=True,
    require_secret=False,
    require_ip_whitelist=True
)

authenticator = WebhookAuthenticator(config)
```

### Authentication Pipeline

The authentication follows this order:
1. **IP Check** → Validates client IP against whitelist
2. **Secret Check** → Validates secret header (if required)
3. **Signature Check** → Validates HMAC signature (if required)

If any check fails, the request is rejected with a specific failure reason.

### Integration with Webhook Handler

```python
from mira.core.webhook_handler import WebhookHandler
from mira.core.webhook_security import WebhookSecurityConfig

# Configure security
security_config = WebhookSecurityConfig(
    secret_key="your-secret",
    allowed_ips=["192.168.1.0/24"],
    require_ip_whitelist=True,
    require_signature=True
)

# Create webhook handler with security
handler = WebhookHandler(security_config=security_config)
```

## Metrics and Monitoring

Minimal metrics API for tracking application performance and health.

### Features

- **Three Metric Types**: Counters, Gauges, and Timers
- **Labels Support**: Organize metrics by dimensions
- **Context Managers**: Easy timing of code blocks
- **Standardized Naming**: Follow `mira_<component>_<metric>_<unit>` convention

### Basic Usage

```python
from mira.core.metrics import get_metrics_collector

metrics = get_metrics_collector()

# Counter - for counting events
counter = metrics.counter('mira_auth_attempts_total', labels={'service': 'api'})
counter.inc()

# Gauge - for current values
gauge = metrics.gauge('mira_active_connections', labels={'service': 'api'})
gauge.set(42)
gauge.inc(5)
gauge.dec(2)

# Timer - for durations
timer = metrics.timer('mira_request_duration_seconds', labels={'endpoint': '/webhook'})
timer.observe(0.25)  # Record a 250ms duration
```

### Context Manager for Timing

```python
# Automatically time a block of code
with metrics.time('mira_webhook_duration_seconds', labels={'service': 'github'}):
    process_webhook_data()
    # Duration is automatically recorded when block exits
```

### Metrics in Error Scenarios

Always use try-finally to ensure metrics are captured even during errors:

```python
counter = metrics.counter('mira_operations_total', labels={'status': 'error'})

try:
    risky_operation()
except Exception as e:
    counter.inc()
    raise
finally:
    # Metrics are always recorded
    pass
```

### Viewing Metrics

```python
# Get all metrics
all_metrics = metrics.get_all_metrics()
print(all_metrics)
```

## Health and Readiness Checks

Separate health and readiness endpoints for monitoring application state.

### Health Check

Lightweight check that doesn't perform I/O operations. Use for process-level monitoring.

```python
from mira.core.health import get_health_registry

registry = get_health_registry()
health = registry.check_health()
# Returns: {'status': 'healthy', 'timestamp': '...', 'service': 'mira'}
```

### Readiness Check

Comprehensive check that validates all dependencies. Use for load balancer health checks.

```python
# Register dependencies
def check_database():
    # Return True if database is accessible
    try:
        db.ping()
        return True
    except:
        return False

def check_cache():
    try:
        cache.ping()
        return True
    except:
        return False

# Register checks
registry.register_dependency('database', check_database, required=True)
registry.register_dependency('cache', check_cache, required=False)

# Check readiness
readiness = registry.check_readiness()
# Returns detailed status of all dependencies
```

### Dependency Configuration

```python
registry.register_dependency(
    name='airtable',
    check_func=lambda: airtable.is_connected(),
    required=True,      # Affects overall readiness
    timeout_seconds=5.0 # Max time for check
)
```

## Feature Flags and Configuration

Pydantic-based configuration with validation and feature flag priorities.

### Rate Limiting Configuration

```python
from mira.core.feature_flags import RateLimitConfig

rate_limit = RateLimitConfig(
    enabled=True,
    requests_per_minute=100,
    burst_size=20  # Must be <= requests_per_minute
)
```

### Maintenance Mode Configuration

```python
from mira.core.feature_flags import MaintenanceModeConfig

maintenance = MaintenanceModeConfig(
    enabled=True,
    message="System under maintenance until 3 PM UTC",  # Required when enabled
    allowed_ips=["10.0.0.1"]  # Optional whitelist
)
```

### Complete Configuration

```python
from mira.core.feature_flags import FeatureFlagsConfig

config = FeatureFlagsConfig(
    rate_limit=RateLimitConfig(enabled=True, requests_per_minute=60),
    maintenance_mode=MaintenanceModeConfig(
        enabled=False,
        message=None
    ),
    api_keys=APIKeyConfigModel(
        enabled=True,
        storage_backend="file",
        storage_path="/var/lib/mira/keys.json"
    ),
    metrics=MetricsConfig(enabled=True)
)

# Check active restrictions with priority
restrictions = config.get_active_restrictions()
# Maintenance mode has highest priority and bypasses all other restrictions
```

### Feature Flag Priorities

1. **Maintenance Mode** (Priority 1) - Bypasses everything else
2. **Rate Limiting** (Priority 2) - Only applies if not in maintenance
3. **Normal Operation** (Priority 3)

## CLI Tools

Developer-friendly CLI for testing and validation.

### Generate Test API Key

```bash
# Basic key generation
python -m mira.cli generate-test-key

# With custom settings
python -m mira.cli generate-test-key \
    --key-id my-test-key \
    --expiry-days 30 \
    --storage file \
    --storage-path /tmp/keys.json \
    --purpose "Integration testing"
```

### Check Health

```bash
# Check health status
python -m mira.cli check-health

# Check readiness status
python -m mira.cli check-health --type ready
```

### View Metrics

```bash
# Display all metrics
python -m mira.cli show-metrics
```

### Test Webhooks

```bash
# Test webhook endpoint
python -m mira.cli test-webhook \
    --url http://localhost:5000 \
    --service github \
    --secret your-webhook-secret \
    --payload '{"test": "data"}'
```

### Run Smoke Tests

```bash
# Run end-to-end smoke tests
python -m mira.cli smoke-test
```

## Examples

### Complete Webhook Setup with Security and Metrics

```python
from mira.core.webhook_handler import WebhookHandler
from mira.core.webhook_security import WebhookSecurityConfig
from mira.core.health import get_health_registry

# Configure security
security_config = WebhookSecurityConfig(
    secret_key="your-webhook-secret",
    allowed_ips=["192.168.1.0/24"],
    require_ip_whitelist=True,
    require_signature=True
)

# Create webhook handler
handler = WebhookHandler(security_config=security_config)

# Register health check for airtable dependency
def check_airtable():
    # Your check logic
    return True

registry = get_health_registry()
registry.register_dependency('airtable', check_airtable, required=True)

# Register webhook handlers
def handle_github(data):
    # Process GitHub webhook
    return {'status': 'processed'}

handler.register_handler('github', handle_github)

# Start server (includes /health, /ready, /metrics, /webhook endpoints)
handler.run(host='0.0.0.0', port=5000)
```

### API Key Validation Middleware

```python
from flask import Flask, request, jsonify
from mira.core.api_key_manager import APIKeyManager, FileAPIKeyStorage

app = Flask(__name__)

# Initialize API key manager
storage = FileAPIKeyStorage('/var/lib/mira/api_keys.json')
key_manager = APIKeyManager(storage)

@app.before_request
def validate_api_key():
    """Validate API key on every request."""
    if request.path.startswith('/api/'):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        is_valid, key_id, status = key_manager.validate(api_key)
        
        if not is_valid:
            return jsonify({
                'error': 'Invalid or expired API key',
                'status': status.value if status else 'invalid'
            }), 401
        
        # Store key_id in request context for logging
        request.key_id = key_id

@app.route('/api/data')
def get_data():
    return jsonify({'data': 'sensitive information'})
```

### Comprehensive Metrics Collection

```python
from mira.core.metrics import get_metrics_collector

metrics = get_metrics_collector()

def process_request(request):
    """Example function with comprehensive metrics."""
    # Track total requests
    request_counter = metrics.counter(
        'mira_requests_total',
        labels={'endpoint': request.path, 'method': request.method}
    )
    request_counter.inc()
    
    # Track active requests
    active_gauge = metrics.gauge('mira_active_requests')
    active_gauge.inc()
    
    try:
        # Time the operation
        with metrics.time('mira_request_duration_seconds', 
                         labels={'endpoint': request.path}):
            # Process request
            result = do_processing(request)
            
            # Track success
            success_counter = metrics.counter(
                'mira_requests_total',
                labels={'endpoint': request.path, 'status': 'success'}
            )
            success_counter.inc()
            
            return result
            
    except Exception as e:
        # Track errors
        error_counter = metrics.counter(
            'mira_requests_total',
            labels={'endpoint': request.path, 'status': 'error'}
        )
        error_counter.inc()
        raise
        
    finally:
        # Always decrement active requests
        active_gauge.dec()
```

### Feature Flag Decision Logic

```python
from mira.core.feature_flags import FeatureFlagsConfig

config = FeatureFlagsConfig()

def handle_request(request):
    """Example request handler with feature flag checks."""
    
    # Check maintenance mode first (highest priority)
    if config.is_maintenance_mode():
        # Check if IP is whitelisted
        if request.remote_addr not in config.maintenance_mode.allowed_ips:
            return {
                'error': config.maintenance_mode.message,
                'status': 'maintenance'
            }, 503
    
    # Check rate limiting (only if not in maintenance)
    if config.is_rate_limited():
        # Apply rate limiting logic
        if is_rate_limited(request.remote_addr):
            return {'error': 'Rate limit exceeded'}, 429
    
    # Normal request processing
    return process_request(request)
```

## Best Practices

### Security

1. **Always validate CIDR at startup** to catch configuration errors early
2. **Use file-based storage** for API keys in production
3. **Rotate keys regularly** using the rotation mechanism
4. **Enable all authentication layers** for production webhooks
5. **Log security events** for audit trails

### Observability

1. **Follow naming conventions**: `mira_<component>_<metric>_<unit>`
2. **Use labels wisely**: Don't create too many unique label combinations
3. **Wrap critical paths** in try-finally for reliable metrics
4. **Set appropriate timeouts** for dependency checks
5. **Mark dependencies as optional** when they're not critical

### Configuration

1. **Validate at startup** using Pydantic models
2. **Use environment variables** for sensitive values
3. **Group related configs** for better organization
4. **Document constraints** in field descriptions
5. **Test configuration changes** in staging first

### Developer Experience

1. **Use CLI tools** for local testing
2. **Run smoke tests** before deploying
3. **Test with realistic payloads** using test-webhook
4. **Generate test keys** for development environments
5. **Check logs** with verbose mode when debugging

## Troubleshooting

### API Key Issues

**Problem**: Key validation fails immediately
- Check if key was copied correctly (no whitespace)
- Verify key hasn't been revoked
- Check expiration date

**Problem**: Cannot rotate key
- Ensure key_id exists in storage
- Check file permissions if using file storage

### Webhook Security Issues

**Problem**: All webhooks rejected with IP blocked
- Verify CIDR configuration is correct
- Check that client IP is in allowed ranges
- Test with `python -m mira.cli test-webhook`

**Problem**: Signature validation fails
- Ensure secret_key matches on both sides
- Check signature header format (should be `sha256=<hex>`)
- Verify payload is not modified before signature check

### Metrics Issues

**Problem**: Metrics not appearing
- Ensure metrics collector is initialized
- Check that counter/gauge/timer is being called
- Verify metrics endpoint is accessible

**Problem**: Timer shows zero duration
- Ensure code block completes
- Check for exceptions breaking the context manager
- Use try-finally to guarantee timer completion

### Health Check Issues

**Problem**: Readiness check always fails
- Check dependency check functions return boolean
- Verify all required dependencies are registered
- Test individual dependencies with `get_dependency_status()`
- Check timeout settings for slow dependencies

## Migration Guide

### From Legacy Webhook Handler

```python
# Before
handler = WebhookHandler(secret_key="secret")

# After
from mira.core.webhook_security import WebhookSecurityConfig

security_config = WebhookSecurityConfig(
    secret_key="secret",
    require_signature=True
)
handler = WebhookHandler(security_config=security_config)
```

### Adding Metrics to Existing Code

```python
# Before
def process_data():
    return do_work()

# After
from mira.core.metrics import get_metrics_collector

metrics = get_metrics_collector()

def process_data():
    counter = metrics.counter('mira_data_processed_total')
    
    with metrics.time('mira_data_processing_seconds'):
        result = do_work()
        counter.inc()
        return result
```

## Additional Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [GitHub Webhook Security](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
