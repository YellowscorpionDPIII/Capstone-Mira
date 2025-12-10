# Security & Observability

This document explains Mira's security, observability, and operational control features.

## Table of Contents
- [Security Features](#security-features)
- [Observability & Monitoring](#observability--monitoring)
- [Operational Controls](#operational-controls)
- [Developer Tools](#developer-tools)
- [Architecture Overview](#architecture-overview)

---

## Security Features

### API Key Management

Mira includes a comprehensive API key management system with rotation and expiry support.

#### Features
- **Key Generation**: Create API keys with optional expiration dates
- **Key Rotation**: Rotate keys with configurable grace periods
- **Key Validation**: Validate keys and check expiration status
- **Key Revocation**: Revoke compromised or unused keys
- **Audit Trail**: All key operations are logged to the audit log

#### Usage

```python
from mira.security.api_key_manager import APIKeyManager
from mira.security.audit_logger import AuditLogger

# Initialize
audit_logger = AuditLogger()
manager = APIKeyManager(audit_logger=audit_logger)

# Generate a key with 30-day expiry
key_id, raw_key = manager.generate_key("production-api", expires_in_days=30)

# Validate a key
is_valid, key_id, reason = manager.validate_key(raw_key)

# Rotate a key with 7-day grace period
new_key_id, new_raw_key = manager.rotate_key(key_id, grace_period_days=7)

# Revoke a key
manager.revoke_key(key_id)
```

### Webhook Security

Enhanced webhook security with multiple authentication mechanisms:

#### Features
- **IP Allow/Deny Lists**: Control access by IP address or CIDR ranges
- **Per-Service Shared Secrets**: Require shared secrets for specific services
- **Multi-Layer Authentication**: Combine IP filtering with secret verification
- **Audit Logging**: All authentication decisions are logged

#### Configuration

```json
{
  "security": {
    "ip_allowlist": ["192.168.1.0/24", "10.0.0.1"],
    "ip_denylist": ["203.0.113.0/24"],
    "webhook_secrets": {
      "github": "your-github-webhook-secret",
      "trello": "your-trello-webhook-secret"
    }
  }
}
```

#### Usage

```python
from mira.security.webhook_security import WebhookSecurity

security = WebhookSecurity(audit_logger=audit_logger)

# Configure IP filtering
security.add_ip_to_allowlist("192.168.1.0/24")
security.add_ip_to_denylist("10.0.0.1")

# Configure service secrets
security.set_service_secret("github", "secret123")

# Authenticate webhook request
is_auth, reason = security.authenticate_webhook(
    service="github",
    ip_address="192.168.1.100",
    secret="secret123"
)
```

### Audit Logging

All security events are logged to a dedicated audit log sink:

- API key creation, rotation, and revocation
- Authentication successes and failures
- IP blocking/allowing decisions
- Key lifecycle events

Audit logs are structured JSON for easy parsing and analysis.

---

## Observability & Monitoring

### Metrics Collection

Standardized metrics collection for monitoring system health and performance.

#### Metric Types
- **Counters**: Incremental counts (e.g., requests, errors)
- **Gauges**: Point-in-time values (e.g., queue size, active connections)
- **Timers**: Duration measurements (e.g., request latency, operation duration)

#### Key Metrics

**Authentication Metrics**:
- `api_key.validation_attempts`
- `api_key.validation_failures`
- `webhook.auth_success`
- `webhook.auth_failed`

**Webhook Metrics**:
- `webhook.requests` (tagged by service)
- `webhook.success` (tagged by service)
- `webhook.errors` (tagged by service)
- `webhook.handler_duration` (timer, tagged by service)

**Airtable Integration Metrics**:
- `airtable.connection_attempts`
- `airtable.connection_successes`
- `airtable.sync_attempts` (tagged by data_type)
- `airtable.sync_successes` (tagged by data_type)
- `airtable.sync_failures` (tagged by reason)

#### Usage

```python
from mira.observability.metrics import MetricsCollector

metrics = MetricsCollector(enabled=True)

# Increment a counter
metrics.increment('requests.processed', tags={'endpoint': '/api/v1'})

# Set a gauge
metrics.gauge('queue.size', 42)

# Record timing
metrics.timing('operation.duration', 123.45)

# Use timer context manager
with metrics.timer('database.query'):
    # ... perform query ...
    pass

# Get all metrics
all_metrics = metrics.get_all_metrics()
```

### Health Checks

Two endpoints for monitoring system health:

#### `/health` - Liveness Probe
Simple check that the process is running.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-10T13:00:00Z",
  "uptime_seconds": 3600
}
```

#### `/ready` - Readiness Probe
Comprehensive check including dependency health.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-10T13:00:00Z",
  "dependencies": {
    "message_broker": {
      "status": "healthy",
      "message": "Broker running"
    },
    "airtable": {
      "status": "healthy",
      "message": "Airtable connection healthy"
    }
  }
}
```

**Status Values**:
- `healthy`: All systems operational
- `degraded`: Some non-critical issues
- `unhealthy`: Critical systems down

#### Usage

```python
from mira.observability.health import HealthCheck

health = HealthCheck()

# Register custom health check
def check_database():
    # ... perform check ...
    return True, "Database is healthy"

health.register_dependency('database', check_database)

# Perform checks
health_status = health.check_health()
readiness_status = health.check_ready()
```

---

## Operational Controls

### Feature Flags

Configuration-driven feature flags for runtime control:

```json
{
  "operational": {
    "rate_limiting_enabled": true,
    "rate_limit_per_minute": 100,
    "verbose_logging": false,
    "maintenance_mode": false,
    "maintenance_message": "System is under maintenance"
  }
}
```

#### Features

**Rate Limiting**: Control request rates per minute
```json
{
  "rate_limiting_enabled": true,
  "rate_limit_per_minute": 60
}
```

**Verbose Logging**: Enable detailed debug logging
```json
{
  "verbose_logging": true
}
```

**Maintenance Mode**: Reject non-critical traffic with clear status
```json
{
  "maintenance_mode": true,
  "maintenance_message": "Scheduled maintenance in progress"
}
```

When maintenance mode is enabled, the webhook handler returns:
```json
{
  "error": "Service is in maintenance mode",
  "status": "maintenance"
}
```
HTTP Status: `503 Service Unavailable`

### Configuration Validation

Pydantic-based schema validation catches configuration errors on startup:

```python
from mira.config.validation import load_and_validate_config

try:
    config = load_and_validate_config('config.json')
    print("✓ Configuration valid")
except ValidationError as e:
    for error in e.errors():
        print(f"Error: {error}")
```

**Validated Fields**:
- Port numbers (1-65535)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Queue sizes (1-100000)
- IP addresses and CIDR notation
- Required fields for enabled integrations

---

## Developer Tools

### Local Testing Harness

A CLI tool for local development and testing:

```bash
# Generate an API key
python -m mira.tools.testing_harness generate-key \
  --name "Development Key" \
  --expires-in-days 30

# Test a webhook
python -m mira.tools.testing_harness test-webhook \
  --service github \
  --host localhost \
  --port 5000 \
  --secret "my-secret"

# Check health endpoints
python -m mira.tools.testing_harness health \
  --host localhost \
  --port 5000

# Validate configuration
python -m mira.tools.testing_harness validate-config \
  --config-path config.json

# List API keys
python -m mira.tools.testing_harness list-keys
```

#### Features
- Generate and manage API keys locally
- Test webhook endpoints with custom payloads
- Check health and readiness endpoints
- Validate configuration files
- Display structured logs

---

## Architecture Overview

### Request Flow

```
External Service (GitHub, Trello, etc.)
    |
    v
[IP Filter Check]
    |
    v
[Shared Secret Validation]
    |
    v
[Signature Verification]
    |
    v
[Maintenance Mode Check]
    |
    v
[Metrics Recording]
    |
    v
[Webhook Handler]
    |
    v
[Agent Processing]
    |
    v
[Airtable Sync (if enabled)]
    |
    v
[Response + Metrics]
```

### Security Layers

1. **Network Layer**: IP allow/deny lists
2. **Application Layer**: Shared secrets, API keys
3. **Cryptographic Layer**: Signature verification
4. **Audit Layer**: Comprehensive logging

### Component Integration

```
┌─────────────────────────────────────────────────┐
│           Mira Application                      │
│                                                 │
│  ┌──────────────┐        ┌──────────────┐     │
│  │ API Key      │◄───────┤ Audit        │     │
│  │ Manager      │        │ Logger       │     │
│  └──────────────┘        └──────────────┘     │
│         │                        │             │
│         │                        │             │
│  ┌──────▼──────────────────────┐│             │
│  │  Webhook Security           ││             │
│  │  - IP Filtering             ││             │
│  │  - Shared Secrets           ││             │
│  └─────────────────────────────┘│             │
│         │                        │             │
│         │                        │             │
│  ┌──────▼────────────────────────▼─────────┐  │
│  │       Webhook Handler                   │  │
│  │       - /health endpoint                │  │
│  │       - /ready endpoint                 │  │
│  │       - /webhook/<service> endpoint     │  │
│  └─────────────┬───────────────────────────┘  │
│                │                               │
│         ┌──────▼──────┐                        │
│         │  Metrics    │                        │
│         │  Collector  │                        │
│         └─────────────┘                        │
│                │                               │
│         ┌──────▼──────────┐                    │
│         │  Health Check   │                    │
│         │  - Broker       │                    │
│         │  - Airtable     │                    │
│         └─────────────────┘                    │
└─────────────────────────────────────────────────┘
```

### Configuration Hierarchy

```
Environment Variables (highest priority)
    ↓
Config File (config.json)
    ↓
Default Values (lowest priority)
```

### Key Rotation Strategy

When rotating API keys:
1. Generate new key
2. Set expiry on old key (grace period)
3. Both keys valid during grace period
4. Old key expires automatically
5. Clients migrate to new key
6. No service disruption

Recommended grace period: 7-14 days

---

## Best Practices

### Security
- Rotate API keys regularly (30-90 days)
- Use IP allowlists for production webhooks
- Set expiry dates on all API keys
- Enable audit logging in production
- Review audit logs regularly
- Use shared secrets for all webhook services

### Observability
- Monitor key metrics in production
- Set up alerts for authentication failures
- Track sync failures to external services
- Use health checks in orchestration (Kubernetes, etc.)
- Enable verbose logging for debugging only

### Operations
- Validate configuration on startup
- Use maintenance mode for planned downtime
- Test health endpoints in monitoring systems
- Keep grace periods for key rotation
- Document all operational procedures

---

## Troubleshooting

### Authentication Failures

Check audit logs for details:
```bash
grep "authentication_failed" /var/log/mira/audit.log
```

Common reasons:
- Expired API key
- Revoked API key
- IP address not in allowlist
- Invalid shared secret
- Invalid signature

### Health Check Failures

Check the `/ready` endpoint for details on which dependency is failing:
```bash
curl http://localhost:5000/ready
```

Common issues:
- Message broker not running
- Airtable API unreachable
- Network connectivity issues

### Configuration Validation Errors

Use the testing harness to validate:
```bash
python -m mira.tools.testing_harness validate-config --config-path config.json
```

Review error messages for specific fields that need correction.

---

## References

- [API Documentation](DOCUMENTATION.md)
- [Configuration Guide](DOCUMENTATION.md#configuration)
- [Integration Guide](DOCUMENTATION.md#integrations)
- [Main README](README.md)
