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
  - Hot-reload support for configuration changes
  - Modular and extensible design

- **🔐 Production-Ready Deployment Features**
  - **Structured Logging with Correlation IDs**: JSON-formatted logs with automatic correlation ID tracking for request tracing
  - **Graceful Shutdown**: Clean shutdown with SIGTERM/SIGINT handling and proper resource cleanup
  - **Configuration Hot-Reload**: Dynamic configuration updates without application restart
  - **Secrets Management**: Integration with HashiCorp Vault, Kubernetes Secrets, and environment variables

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

# Run deployment feature tests
python -m unittest mira.tests.test_structured_logging
python -m unittest mira.tests.test_graceful_shutdown
python -m unittest mira.tests.test_secrets_manager
python -m unittest mira.tests.test_config_hotreload
```

## 🚀 Deployment Features

### Structured Logging with Correlation IDs

Mira includes built-in structured logging with automatic correlation ID tracking for improved observability:

```python
from mira.utils.structured_logging import setup_structured_logging, set_correlation_id

# Setup JSON-formatted logging
setup_structured_logging(level='INFO', json_format=True)

# Each request gets a unique correlation ID
correlation_id = set_correlation_id()  # Auto-generated UUID
# Or provide your own: set_correlation_id('custom-id-123')
```

**Configuration:**
```json
{
  "logging": {
    "level": "INFO",
    "json_format": true,
    "file": "/var/log/mira/app.log"
  }
}
```

**Environment Variables:**
- `MIRA_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `MIRA_LOG_JSON`: Enable JSON formatting (`true` or `false`)

### Graceful Shutdown

Handles SIGTERM and SIGINT signals to cleanly shutdown the application:

```python
from mira.app import MiraApplication

app = MiraApplication()
app.start()  # Graceful shutdown handlers are automatically registered
```

The application will:
1. Capture shutdown signals (SIGTERM, SIGINT)
2. Stop accepting new requests
3. Drain existing connections
4. Close database connections
5. Stop background workers
6. Exit cleanly

### Configuration Hot-Reload

Automatically reload configuration changes without restarting:

**Configuration:**
```json
{
  "config": {
    "hot_reload": true,
    "poll_interval": 5
  }
}
```

**Environment Variables:**
- `MIRA_CONFIG_HOT_RELOAD`: Enable hot-reload (`true` or `false`)

When enabled, Mira watches the configuration file and applies changes automatically. Uses `watchdog` library when available, falls back to polling otherwise.

### Secrets Management

Secure integration with HashiCorp Vault, Kubernetes Secrets, or environment variables:

**Configuration:**
```json
{
  "secrets": {
    "backend": "vault",
    "auto_refresh": true,
    "refresh_interval": 3600,
    "vault": {
      "url": "https://vault.example.com",
      "token": "secret://vault-credentials:token",
      "mount_point": "secret"
    }
  }
}
```

**Supported Backends:**
- `env`: Environment variables (default, always available)
- `vault`: HashiCorp Vault (requires `hvac` package)
- `kubernetes`: Kubernetes Secrets (requires cluster access)

**Using Secrets in Configuration:**

Reference secrets using the `secret://` prefix:
```json
{
  "integrations": {
    "github": {
      "token": "secret://github-credentials:token"
    }
  }
}
```

**Environment Variables:**
- `MIRA_SECRETS_BACKEND`: Backend type (`env`, `vault`, `kubernetes`)
- `MIRA_SECRETS_AUTO_REFRESH`: Enable automatic secret rotation (`true` or `false`)
- `MIRA_VAULT_URL`: Vault server URL
- `MIRA_VAULT_TOKEN`: Vault authentication token

**Features:**
- Automatic secret caching
- Periodic secret refresh (configurable interval)
- Fallback to cached values on fetch errors
- Callback support for secret rotation events

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
│   │   ├── structured_logging.py
│   │   ├── graceful_shutdown.py
│   │   ├── secrets_manager.py
│   │   └── config_hotreload.py
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
