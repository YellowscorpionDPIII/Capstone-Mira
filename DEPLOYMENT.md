# Mira Deployment Guide

This guide covers deploying Mira with production-ready features including structured logging, graceful shutdown, configuration hot-reload, and secrets management.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Structured Logging](#structured-logging)
- [Graceful Shutdown](#graceful-shutdown)
- [Configuration Hot-Reload](#configuration-hot-reload)
- [Secrets Management](#secrets-management)
- [Deployment Scenarios](#deployment-scenarios)

## Prerequisites

Install Mira with all dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- `Flask==3.0.0` - Web framework
- `watchdog==3.0.0` - File system monitoring for hot-reload
- `hvac==1.2.1` - HashiCorp Vault client (optional, for Vault secrets)

## Configuration

### Basic Configuration

Create a configuration file (e.g., `config.json`):

```json
{
  "logging": {
    "level": "INFO",
    "json_format": true,
    "file": "/var/log/mira/app.log"
  },
  "config": {
    "hot_reload": true,
    "poll_interval": 5
  },
  "secrets": {
    "backend": "env",
    "auto_refresh": false
  }
}
```

### Environment Variables

Override configuration with environment variables:

```bash
# Logging
export MIRA_LOG_LEVEL=DEBUG
export MIRA_LOG_JSON=true

# Configuration hot-reload
export MIRA_CONFIG_HOT_RELOAD=true

# Secrets management
export MIRA_SECRETS_BACKEND=vault
export MIRA_SECRETS_AUTO_REFRESH=true
export MIRA_VAULT_URL=https://vault.example.com:8200
export MIRA_VAULT_TOKEN=your-vault-token

# Integration credentials
export MIRA_GITHUB_ENABLED=true
export GITHUB_TOKEN=your-github-token
```

## Structured Logging

### Features

- **JSON-formatted logs** for easy parsing by log aggregation tools
- **Correlation IDs** automatically track requests across the system
- **Structured fields** provide rich context for debugging

### Configuration

```json
{
  "logging": {
    "level": "INFO",
    "json_format": true,
    "file": "/var/log/mira/app.log"
  }
}
```

### Log Format

Each log entry includes:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "level": "INFO",
  "logger": "mira.app",
  "message": "Processing message",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "module": "app",
  "function": "process_message",
  "line": 150,
  "message_type": "generate_plan"
}
```

### Integration with Log Aggregation

**ELK Stack (Elasticsearch, Logstash, Kibana):**

Logstash configuration:
```ruby
input {
  file {
    path => "/var/log/mira/app.log"
    codec => json
  }
}

filter {
  # Add additional processing if needed
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "mira-logs-%{+YYYY.MM.dd}"
  }
}
```

**Datadog:**

Configure the Datadog agent to tail the log file:
```yaml
logs:
  - type: file
    path: /var/log/mira/app.log
    service: mira
    source: python
```

**CloudWatch Logs:**

Use the CloudWatch Logs agent or Fluentd to forward logs.

## Graceful Shutdown

### How It Works

Mira automatically handles shutdown signals:

1. Captures `SIGTERM` and `SIGINT` signals
2. Stops accepting new requests
3. Completes ongoing operations
4. Closes all connections (database, message broker, etc.)
5. Exits cleanly

### Kubernetes Deployment

Graceful shutdown works seamlessly with Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mira
spec:
  template:
    spec:
      containers:
      - name: mira
        image: mira:latest
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 5"]
      terminationGracePeriodSeconds: 30
```

### Docker

```bash
# Sends SIGTERM to the container
docker stop mira-container
```

### Manual Testing

```bash
# Start the application
python -m mira.app config.json &
APP_PID=$!

# Send SIGTERM
kill -TERM $APP_PID

# Or use Ctrl+C if running in foreground
```

## Configuration Hot-Reload

### Features

- **No downtime** configuration updates
- **Automatic detection** of file changes
- **Selective updates** - only modified settings are changed

### Setup

Enable in configuration:

```json
{
  "config": {
    "hot_reload": true,
    "poll_interval": 5
  }
}
```

Or via environment variable:
```bash
export MIRA_CONFIG_HOT_RELOAD=true
```

### How to Update Configuration

1. Edit your configuration file (e.g., `config.json`)
2. Save the changes
3. Mira automatically detects and applies the new configuration
4. Check logs for confirmation:

```json
{
  "message": "Configuration reloaded successfully",
  "timestamp": "2024-01-15T10:35:00.000000+00:00"
}
```

### Monitoring Changes

Register a callback to track configuration changes:

```python
from mira.app import MiraApplication

app = MiraApplication('config.json')

def on_config_change(new_config):
    print(f"Configuration updated: {new_config}")

if app.hot_reload_config:
    app.hot_reload_config.register_reload_callback(on_config_change)
```

## Secrets Management

### Supported Backends

#### 1. Environment Variables (Default)

Simplest option, suitable for development:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
export JIRA_API_TOKEN=xxxxxxxxxxxxx
```

Configuration:
```json
{
  "secrets": {
    "backend": "env"
  }
}
```

#### 2. HashiCorp Vault

Recommended for production:

**Prerequisites:**
```bash
pip install hvac
```

**Configuration:**
```json
{
  "secrets": {
    "backend": "vault",
    "auto_refresh": true,
    "refresh_interval": 3600,
    "vault": {
      "url": "https://vault.example.com:8200",
      "token": "s.xxxxxxxxxxxxx",
      "mount_point": "secret"
    }
  }
}
```

**Store secrets in Vault:**
```bash
vault kv put secret/github-credentials token=ghp_xxxxxxxxxxxxx
vault kv put secret/jira-credentials username=user@example.com api_token=xxxxxxxxxxxxx
```

**Reference in configuration:**
```json
{
  "integrations": {
    "github": {
      "token": "secret://github-credentials:token"
    },
    "jira": {
      "username": "secret://jira-credentials:username",
      "api_token": "secret://jira-credentials:api_token"
    }
  }
}
```

#### 3. Kubernetes Secrets

For Kubernetes deployments:

**Create secret:**
```bash
kubectl create secret generic github-credentials \
  --from-literal=token=ghp_xxxxxxxxxxxxx
```

**Configuration:**
```json
{
  "secrets": {
    "backend": "kubernetes",
    "kubernetes": {
      "namespace": "default"
    }
  }
}
```

**Reference in configuration:**
```json
{
  "integrations": {
    "github": {
      "token": "secret://github-credentials:token"
    }
  }
}
```

### Secret Rotation

Enable automatic secret refresh:

```json
{
  "secrets": {
    "auto_refresh": true,
    "refresh_interval": 3600
  }
}
```

Benefits:
- Secrets are automatically updated when rotated
- Minimal downtime during rotation
- Cached values used as fallback if fetch fails

### Handling Secret Changes

Register a callback for secret rotation events:

```python
from mira.utils.secrets_manager import get_secrets_manager

secrets_manager = get_secrets_manager()

def on_secret_rotated(new_value):
    print(f"Secret rotated: {new_value}")
    # Reinitialize connections with new credentials

secrets_manager.register_refresh_callback('github-credentials', on_secret_rotated)
```

## Deployment Scenarios

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create log directory
RUN mkdir -p /var/log/mira

# Run as non-root user
RUN useradd -m mira
USER mira

CMD ["python", "-m", "mira.app", "config.json"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  mira:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - mira-logs:/var/log/mira
    environment:
      - MIRA_LOG_LEVEL=INFO
      - MIRA_CONFIG_HOT_RELOAD=true
    restart: unless-stopped
    
volumes:
  mira-logs:
```

### Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mira
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mira
  template:
    metadata:
      labels:
        app: mira
    spec:
      containers:
      - name: mira
        image: mira:latest
        env:
        - name: MIRA_LOG_LEVEL
          value: "INFO"
        - name: MIRA_LOG_JSON
          value: "true"
        - name: MIRA_SECRETS_BACKEND
          value: "kubernetes"
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
        - name: logs
          mountPath: /var/log/mira
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: mira-config
      - name: logs
        emptyDir: {}
      terminationGracePeriodSeconds: 30
```

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mira-config
data:
  config.json: |
    {
      "logging": {
        "level": "INFO",
        "json_format": true
      },
      "config": {
        "hot_reload": true
      },
      "secrets": {
        "backend": "kubernetes"
      }
    }
```

### Cloud Deployments

#### AWS

Use AWS Secrets Manager:
```python
# Custom secrets backend for AWS
import boto3
from mira.utils.secrets_manager import SecretsBackend

class AWSSecretsBackend(SecretsBackend):
    def __init__(self):
        self.client = boto3.client('secretsmanager')
    
    def get_secret(self, path, key=None):
        response = self.client.get_secret_value(SecretId=path)
        # Parse and return secret
        pass
```

#### Azure

Use Azure Key Vault with the Azure SDK.

#### GCP

Use Google Secret Manager with the Google Cloud SDK.

## Monitoring and Observability

### Health Checks

Implement health check endpoints for load balancers:

```python
from flask import jsonify

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/ready')
def ready():
    # Check if application is ready to serve traffic
    return jsonify({'status': 'ready'})
```

### Metrics

Track application metrics:
- Request count and latency
- Error rates
- Secret refresh success/failure
- Configuration reload events

### Alerting

Set up alerts for:
- Failed secret refreshes
- Configuration reload errors
- Shutdown events
- Error rate spikes

## Troubleshooting

### Logs Not Showing Correlation IDs

Ensure structured logging is enabled:
```json
{
  "logging": {
    "json_format": true
  }
}
```

### Configuration Hot-Reload Not Working

1. Check if hot-reload is enabled
2. Verify file permissions
3. Check logs for errors
4. Try increasing `poll_interval`

### Secrets Not Loading

1. Verify backend configuration
2. Check authentication credentials
3. Ensure secrets exist in the backend
4. Review logs for error messages

### Graceful Shutdown Timing Out

Increase the termination grace period:
```yaml
terminationGracePeriodSeconds: 60
```

## Best Practices

1. **Always use structured logging in production**
2. **Enable graceful shutdown for zero-downtime deployments**
3. **Use secrets management - never hardcode credentials**
4. **Enable auto-refresh for secrets in production**
5. **Monitor configuration reload events**
6. **Set appropriate log levels (INFO in production, DEBUG for troubleshooting)**
7. **Use correlation IDs to trace requests across services**
8. **Implement health checks for load balancers**
9. **Regular test your deployment process**
10. **Keep secrets rotation intervals aligned with security policies**

## Additional Resources

- [DOCUMENTATION.md](DOCUMENTATION.md) - Full API documentation
- [README.md](README.md) - Quick start guide
- [examples/deployment_features_example.py](examples/deployment_features_example.py) - Example implementation
