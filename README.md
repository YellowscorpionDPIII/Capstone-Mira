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
  - **Hot-reload support** - detect and reload config changes without restart
  - Modular and extensible design

- **🔒 Production-Ready Deployment Features**
  - **Structured Logging** - JSON-formatted logs with correlation IDs for distributed tracing
  - **Graceful Shutdown** - Clean shutdown with SIGTERM/SIGINT handling
  - **Config Hot-Reload** - Automatic configuration reload on file changes
  - **Secrets Management** - Integration with Vault and Kubernetes Secrets with auto-refresh

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/YellowscorpionDPIII/Capstone-Mira.git
cd Capstone-Mira

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .

# Optional: Install with secrets management support
pip install -e ".[secrets]"  # Both Vault and Kubernetes
pip install -e ".[vault]"     # Vault only
pip install -e ".[kubernetes]" # Kubernetes only
```

## 🏃 Quick Start

### Basic Usage

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

### With Production Features

```python
from mira.app import MiraApplication

# Initialize with structured logging and hot-reload
app = MiraApplication(
    config_path='config.json',
    use_structured_logging=True,  # Enable JSON logs with correlation IDs
    enable_hot_reload=True         # Enable config hot-reload
)

# Process messages with correlation tracking
response = app.process_message({
    'type': 'generate_plan',
    'data': {'name': 'My Project', 'goals': ['Goal 1'], 'duration_weeks': 12}
})
```

### Command Line Usage

```bash
# Basic usage
python -m mira.app

# With structured logging
python -m mira.app --structured-logging

# With config file and hot-reload
python -m mira.app --config config.json --hot-reload

# All features enabled
python -m mira.app --config config.json --structured-logging --hot-reload
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

## 🚀 Deployment Features

### Structured Logging with Correlation IDs

Enable JSON-formatted structured logging for integration with modern observability platforms:

```python
from mira.app import MiraApplication
from mira.utils.structured_logging import CorrelationContext

# Enable structured logging
app = MiraApplication(use_structured_logging=True)

# Use correlation contexts for request tracing
with CorrelationContext() as correlation_id:
    result = app.process_message(message)
    print(f"Request {correlation_id} completed")
```

Logs are emitted in JSON format:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "mira.app",
  "message": "Processing message",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "module": "app",
  "function": "process_message"
}
```

### Graceful Shutdown

The application handles SIGTERM and SIGINT signals for clean shutdown:

```python
from mira.utils.shutdown_handler import register_shutdown_callback

# Register custom cleanup callbacks
def cleanup_database():
    print("Closing database connections...")
    # Your cleanup code here

register_shutdown_callback(cleanup_database, name='database_cleanup')
```

Shutdown sequence:
1. Signal received (SIGTERM/SIGINT)
2. Stops accepting new requests
3. Drains existing connections
4. Executes cleanup callbacks in reverse order
5. Exits cleanly

### Config Hot-Reload

Automatically reload configuration when files change:

```python
app = MiraApplication(
    config_path='config.json',
    enable_hot_reload=True
)

# Register callbacks for config changes
from mira.utils.config_hotreload import HotReloadConfig

hot_reload = HotReloadConfig(config, 'config.json')

def on_config_change():
    print("Configuration reloaded!")
    # React to config changes

hot_reload.register_reload_callback(on_config_change)
hot_reload.enable_hot_reload()
```

### Secrets Management

Integrate with Vault or Kubernetes Secrets for secure credential management:

#### Vault Backend

```python
from mira.utils.secrets_manager import VaultBackend, SecretsManager

# Initialize Vault backend
vault = VaultBackend(
    vault_addr='http://localhost:8200',
    token='vault-token'  # or set VAULT_TOKEN env var
)

# Create secrets manager
secrets = SecretsManager(vault)

# Get secrets
db_password = secrets.get_secret('app/database', 'password')

# Enable auto-refresh for rotating secrets
secrets.start_auto_refresh(interval=300)  # Refresh every 5 minutes

# Register callback for secret changes
def update_db_connection(new_password):
    print(f"Database password rotated: {new_password}")
    # Update your database connection

secrets.register_refresh_callback('app/database', update_db_connection, 'password')
```

#### Kubernetes Secrets Backend

```python
from mira.utils.secrets_manager import KubernetesBackend, SecretsManager

# Initialize Kubernetes backend
k8s = KubernetesBackend(
    namespace='default',
    in_cluster=True  # Set to False for local development
)

# Create secrets manager
secrets = SecretsManager(k8s)

# Get secrets
api_key = secrets.get_secret('app-secrets', 'api-key')
```

### Production Deployment Example

```python
import os
from mira.app import MiraApplication
from mira.utils.secrets_manager import VaultBackend, SecretsManager

# Initialize secrets manager
vault = VaultBackend(
    vault_addr=os.getenv('VAULT_ADDR'),
    token=os.getenv('VAULT_TOKEN')
)
secrets = SecretsManager(vault)

# Start auto-refresh for rotating secrets
secrets.start_auto_refresh(interval=300)

# Initialize application with all production features
app = MiraApplication(
    config_path='/etc/mira/config.json',
    use_structured_logging=True,
    enable_hot_reload=True
)

# Start the application
# Signal handlers are automatically installed
app.start()
```

### Environment Variables

Configure the application using environment variables:

```bash
# Logging
export MIRA_LOG_LEVEL=INFO

# Webhook
export MIRA_WEBHOOK_ENABLED=true
export MIRA_WEBHOOK_PORT=5000
export MIRA_WEBHOOK_SECRET=your-secret-key

# Vault
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-vault-token

# Integrations
export MIRA_GITHUB_ENABLED=true
export MIRA_TRELLO_ENABLED=true
```

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
│   │   └── logging.py
│   ├── tests/                 # Test suite
│   └── app.py                 # Main application
├── examples/                  # Example scripts
│   └── example_usage.py
├── requirements.txt
├── setup.py
├── DOCUMENTATION.md
└── README.md
```

## 🏭 Production Deployment

### Docker Compose with Vault

Deploy Mira with HashiCorp Vault for secrets management:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  vault:
    image: hashicorp/vault:latest
    container_name: mira-vault
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: myroot
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    cap_add:
      - IPC_LOCK
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 10s
      timeout: 5s
      retries: 3

  mira:
    build: .
    container_name: mira-app
    ports:
      - "5000:5000"
    environment:
      VAULT_ADDR: http://vault:8200
      VAULT_TOKEN: myroot
      MIRA_WEBHOOK_ENABLED: "true"
      MIRA_WEBHOOK_PORT: 5000
    volumes:
      - ./config:/etc/mira
    depends_on:
      vault:
        condition: service_healthy
    command: python -m mira.app --config /etc/mira/config.json --structured-logging --hot-reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir hvac

# Copy application
COPY mira ./mira
COPY config.example.json /etc/mira/config.json

# Non-root user for security
RUN useradd -m -u 1000 mira && \
    chown -R mira:mira /app /etc/mira
USER mira

EXPOSE 5000

CMD ["python", "-m", "mira.app", "--config", "/etc/mira/config.json", "--structured-logging"]
```

**Setup Vault secrets:**
```bash
# Start services
docker-compose up -d

# Configure Vault (first time only)
docker exec -it mira-vault sh
vault login myroot
vault secrets enable -path=secret kv-v2
vault kv put secret/mira/database password=secure_password username=mira_user
vault kv put secret/mira/api key=api_key_xyz789
exit

# Restart Mira to use secrets
docker-compose restart mira
```

### Kubernetes Deployment

**mira-deployment.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mira-secrets
type: Opaque
stringData:
  database-password: "secure_password"
  api-key: "api_key_xyz789"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mira-config
data:
  config.json: |
    {
      "logging": {"level": "INFO"},
      "broker": {"enabled": true},
      "webhook": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 5000
      }
    }
---
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
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mira-secrets
              key: database-password
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: mira-secrets
              key: api-key
        volumeMounts:
        - name: config
          mountPath: /etc/mira
        livenessProbe:
          httpGet:
            path: /healthz
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: mira-config
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

**Deploy to Kubernetes:**
```bash
# Apply configuration
kubectl apply -f mira-deployment.yaml

# Check deployment status
kubectl get pods -l app=mira
kubectl get svc mira-service

# View logs
kubectl logs -l app=mira --tail=100 -f

# Check health
kubectl port-forward svc/mira-service 5000:80
curl http://localhost:5000/healthz
curl http://localhost:5000/readyz
```

### Production Configuration Example

**config/production.json:**
```json
{
  "logging": {
    "level": "INFO",
    "file": "/var/log/mira/app.log"
  },
  "broker": {
    "enabled": true,
    "queue_size": 10000
  },
  "webhook": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 5000,
    "secret_key": "${WEBHOOK_SECRET}"
  },
  "agents": {
    "project_plan_agent": {"enabled": true},
    "risk_assessment_agent": {"enabled": true},
    "status_reporter_agent": {"enabled": true},
    "orchestrator_agent": {"enabled": true}
  }
}
```

### Monitoring and Observability

**Integration with ELK Stack:**
```python
from mira.app import MiraApplication
import logging.handlers

app = MiraApplication(
    config_path='config/production.json',
    use_structured_logging=True  # JSON logs to stdout
)

# Logs are JSON-formatted and can be shipped to ELK
# Example log entry:
# {
#   "timestamp": "2024-01-15T10:30:45.123Z",
#   "level": "INFO",
#   "correlation_id": "a1b2c3d4-e5f6-7890",
#   "agent_id": "orchestrator",
#   "task_id": "task-123",
#   "message": "Processing request"
# }
```

**Prometheus Metrics (Future Enhancement):**
```python
# Example of how metrics could be added
from prometheus_client import Counter, Histogram

request_count = Counter('mira_requests_total', 'Total requests')
request_duration = Histogram('mira_request_duration_seconds', 'Request duration')
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

- **Translations**: Help make Mira available in more languages - see our [Localization Guide](docs/wiki/Localization.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
