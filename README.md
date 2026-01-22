# Mira - Multi-Agent Workflow Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Modular multi-agent AI workflow system for technical program management. Automates planning, risk assessment, status reporting, and connects with Trello, Jira, GitHub, Airtable, Google Docs, and PDFs for seamless collaboration.

## 🚀 Features

- **🤖 Four Specialized Agents**
  - ProjectPlanAgent: Generate comprehensive project plans
  - RiskAssessmentAgent: Identify and assess project risks
  - StatusReporterAgent: Create weekly status reports
  - OrchestratorAgent: Coordinate multi-agent workflows

- **🔌 Six Integration Adapters**
  - Trello, Jira, GitHub, Airtable, Google Docs, PDF

- **📡 Event-Driven Architecture**
  - Message broker with publish-subscribe pattern
  - Webhook support for external integrations
  - Asynchronous message processing

- **⚙️ Flexible Configuration**
  - JSON configuration files
  - Environment variable support
  - Modular and extensible design

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/YellowscorpionDPIII/Capstone-Mira.git
cd Capstone-Mira

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## 🏃 Quick Start

```python
from mira.app import MiraApplication

# Initialize the application
app = MiraApplication()

# Generate a project plan
response = app.process_message({
    'type': 'generate_plan',
    'data': {
        'name': 'My Project',
        'goals': ['Goal 1', 'Goal 2'],
        'duration_weeks': 12
    }
})

print(response['data'])
```

Run the example:

```bash
python examples/example_usage.py
```

## 📚 Documentation

See [DOCUMENTATION.md](DOCUMENTATION.md) for comprehensive documentation including:
- Detailed API reference
- Configuration guide
- Usage examples
- Architecture overview
- Extension guide

### Supported Languages

<!-- Badge reflects current translation status from docs/wiki/Localization.md - update counts as languages are completed -->
[![Languages](https://img.shields.io/badge/languages-6_total_(1_complete%2C_1_in_progress%2C_4_planned)-blue.svg)](docs/wiki/Localization.md)

### Wiki

Additional documentation is available in our [Wiki](docs/wiki/Home.md):
- [Localization Guide](docs/wiki/Localization.md) - Setup, contribution guidelines, and adding new languages

## 🧪 Testing

```bash
# Run all tests
python -m unittest discover mira/tests

# Run specific test module
python -m unittest mira.tests.test_agents
```

## 📊 Metrics and Monitoring

Mira includes built-in metrics collection for latency and error tracking, designed to facilitate future integration with Prometheus or other monitoring systems.

### Using Metrics

```python
from mira.utils.metrics import timer, timed, get_all_metrics

# Use timer context manager
with timer('my_operation'):
    # Your code here
    pass

# Use decorator for functions
@timed('my_function')
def my_function():
    # Your code here
    pass

# Get all collected metrics
metrics = get_all_metrics()
print(metrics)
# Output: {
#   'latencies': {
#     'my_operation': {'count': 1, 'min': 0.5, 'max': 0.5, 'avg': 0.5, 'sum': 0.5}
#   },
#   'errors': {
#     'agent.errors': 2
#   }
# }
```

### Automatic Metrics Collection

Metrics are automatically collected for:
- **Agent Processing**: `agent.{agent_id}.process` - latency and errors
- **Message Broker**: `broker.publish`, `broker.process_message` - latency and errors
- **Integrations**: `integration.{service}.connect`, `integration.{service}.sync_data` - latency and errors
- **Webhooks**: `webhook.{service}` - latency and errors
- **Workflows**: `orchestrator.workflow.{workflow_type}` - latency

### Retrieving Metrics

```python
from mira.utils.metrics import (
    get_latency_stats,
    get_error_count,
    get_all_metrics,
    reset_metrics
)

# Get latency statistics for a specific metric
stats = get_latency_stats('agent.orchestrator_agent.process')
# Returns: {'count': 10, 'min': 0.01, 'max': 0.5, 'avg': 0.15, 'sum': 1.5}

# Get error count for a specific counter
errors = get_error_count('broker.handler_errors')

# Get all metrics
all_metrics = get_all_metrics()

# Reset all metrics
reset_metrics()
```

### Future Prometheus Integration

The metrics system is designed with a pluggable architecture. To integrate with Prometheus:

1. Install Prometheus client: `pip install prometheus-client`
2. Create a Prometheus exporter that reads from `get_all_metrics()`
3. Export metrics to Prometheus format
4. Configure Prometheus to scrape the metrics endpoint

Example integration pattern:
```python
from prometheus_client import Counter, Histogram
from mira.utils.metrics import get_metrics_collector

# Create Prometheus metrics
latency_histogram = Histogram('mira_operation_latency', 'Operation latency')
error_counter = Counter('mira_errors', 'Error count')

# Periodically sync from Mira metrics to Prometheus
collector = get_metrics_collector()
# Implement sync logic here
```

## 📁 Project Structure

```
Capstone-Mira/
├── mira/                      # Main package
│   ├── agents/                # Agent implementations
│   │   ├── project_plan_agent.py
│   │   ├── risk_assessment_agent.py
│   │   ├── status_reporter_agent.py
│   │   └── orchestrator_agent.py
│   ├── integrations/          # External service integrations
│   │   ├── trello_integration.py
│   │   ├── jira_integration.py
│   │   ├── github_integration.py
│   │   ├── airtable_integration.py
│   │   ├── google_docs_integration.py
│   │   └── pdf_integration.py
│   ├── core/                  # Core components
│   │   ├── base_agent.py
│   │   ├── message_broker.py
│   │   └── webhook_handler.py
│   ├── config/                # Configuration
│   │   └── settings.py
│   ├── utils/                 # Utilities
│   │   ├── logging.py
│   │   └── metrics.py
│   ├── tests/                 # Test suite
│   └── app.py                 # Main application
├── examples/                  # Example scripts
│   └── example_usage.py
├── requirements.txt
├── setup.py
├── DOCUMENTATION.md
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

- **Translations**: Help make Mira available in more languages - see our [Localization Guide](docs/wiki/Localization.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🚀 Production Deployment

### Overview

Mira is production-ready with built-in support for:
- **Secrets Management**: Vault and Kubernetes secrets integration with retry logic
- **Structured Logging**: JSON logging with correlation IDs for distributed tracing
- **Graceful Shutdown**: Priority-based shutdown handlers for clean termination
- **Health Checks**: Kubernetes-compatible readiness/liveness probes

### Containerization

Build and run Mira in a container:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install optional dependencies as needed
# For Vault: pip install -e ".[vault]"
# For Kubernetes: pip install -e ".[kubernetes]"
# For all optional features: pip install -e ".[all]"

# Expose webhook port
EXPOSE 5000

# Run the application
CMD ["python", "-m", "mira.app"]
```

Build and run:

```bash
docker build -t mira:latest .
docker run -p 5000:5000 mira:latest
```

### Kubernetes Deployment

Example Kubernetes deployment with health checks:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mira-deployment
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
        ports:
        - containerPort: 5000
        env:
        - name: MIRA_WEBHOOK_ENABLED
          value: "true"
        - name: MIRA_WEBHOOK_PORT
          value: "5000"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mira-service
spec:
  selector:
    app: mira
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

### Configuration

#### Secrets Management

Enable Vault or Kubernetes secrets:

```python
from mira.utils.secrets_manager import initialize_secrets_manager

# Use Vault
initialize_secrets_manager(
    backend="vault",
    config={"url": "https://vault.example.com", "token": "..."}
)

# Use Kubernetes secrets
initialize_secrets_manager(backend="k8s", config={"namespace": "default"})

# Fetch secrets with retry
from mira.utils.secrets_manager import get_secret
api_key = get_secret("API_KEY", max_retries=3, delay=1.0)
```

#### Structured Logging

Enable JSON logging with correlation tracking:

```python
from mira.utils.structured_logging import (
    setup_structured_logging,
    CorrelationContext,
    get_structured_logger
)

# Setup JSON logging
setup_structured_logging(level='INFO', format_json=True)

# Use correlation context for traceability
logger = get_structured_logger("my_module")
with CorrelationContext(agent_id="agent_1", task_id="task_123"):
    logger.info("Processing task", extra_field="value")
```

#### Graceful Shutdown

Register shutdown callbacks with priorities:

```python
from mira.utils.shutdown_handler import (
    initialize_shutdown_handler,
    register_shutdown_callback
)

# Initialize shutdown handler
initialize_shutdown_handler()

# Register callbacks (lower priority number = executes first)
def drain_agents():
    # Drain agent queues
    pass

def close_connections():
    # Close database connections
    pass

register_shutdown_callback(drain_agents, priority=5, name="drain_agents")
register_shutdown_callback(close_connections, priority=15, name="close_db")
```

#### Health Checks

The `/healthz` endpoint is automatically available when webhooks are enabled:

```bash
curl http://localhost:5000/healthz
```

Response example:
```json
{
  "status": "healthy",
  "checks": {
    "configuration": "ok",
    "agents": "ok",
    "agent_count": 4,
    "broker": "running"
  }
}
```

### Environment Variables

Configure Mira using environment variables:

```bash
# Webhook configuration
export MIRA_WEBHOOK_ENABLED=true
export MIRA_WEBHOOK_PORT=5000
export MIRA_WEBHOOK_SECRET=your-secret-key

# Integration toggles
export MIRA_GITHUB_ENABLED=true
export MIRA_TRELLO_ENABLED=true

# Logging
export MIRA_LOG_LEVEL=INFO
```

### Dependencies

Core dependencies (always installed):
- Flask >= 3.0.0
- Werkzeug >= 3.0.1

Optional dependencies (install as needed):
```bash
# For Vault secrets
pip install ".[vault]"

# For Kubernetes integration
pip install ".[kubernetes]"

# For file monitoring
pip install ".[monitoring]"

# Install all optional features
pip install ".[all]"
```

### Security Considerations

1. **Secrets**: Never commit secrets to source code. Use environment variables or secret management systems.
2. **Webhook Security**: Always set `MIRA_WEBHOOK_SECRET` for signature verification.
3. **Network**: Use TLS/SSL in production with proper certificates.
4. **Updates**: Regularly update dependencies to patch security vulnerabilities.

For security scanning, use tools like:
```bash
# Dependency scanning
pip install safety
safety check

# Secret scanning
pip install detect-secrets
detect-secrets scan
```
