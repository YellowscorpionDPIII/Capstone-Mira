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

- **🔒 Enterprise Security**
  - API Key lifecycle management (create, rotate, revoke, validate)
  - Multi-layer webhook authentication (IP, secret, signature)
  - Pluggable storage backends (in-memory, file-based)

- **📊 Observability & Monitoring**
  - Metrics API (counters, gauges, timers)
  - Health and readiness endpoints
  - Dependency health tracking

- **⚙️ Flexible Configuration**
  - Pydantic-based validation
  - Feature flags with priorities
  - JSON and environment variable support
  - Rate limiting and maintenance mode

- **🛠️ Developer Experience**
  - CLI tools for testing and validation
  - Smoke tests for end-to-end verification
  - Comprehensive documentation and examples

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

## 🛠️ CLI Tools

Mira includes developer-friendly CLI tools for testing and validation:

```bash
# Generate test API keys
python -m mira.cli generate-test-key --key-id mykey

# Check application health
python -m mira.cli check-health

# View metrics
python -m mira.cli show-metrics

# Test webhooks
python -m mira.cli test-webhook --url http://localhost:5000 --service github

# Run smoke tests
python -m mira.cli smoke-test
```

See [Quick Start: Security](docs/QUICK_START_SECURITY.md) for more CLI examples.

## 📚 Documentation

### Main Documentation
- [DOCUMENTATION.md](DOCUMENTATION.md) - Complete API reference and architecture
- **[Security & Observability Guide](docs/SECURITY_AND_OBSERVABILITY.md)** - ⭐ NEW! Comprehensive guide for security and monitoring
- **[Quick Start: Security](docs/QUICK_START_SECURITY.md)** - ⭐ NEW! Get started in 5 minutes

### Core Guides
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

# Run specific test modules
python -m unittest mira.tests.test_agents
python -m unittest mira.tests.test_security
python -m unittest mira.tests.test_observability
python -m unittest mira.tests.test_config

# Run smoke tests
python -m mira.cli smoke-test
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
│   │   ├── webhook_handler.py
│   │   ├── api_key_manager.py      # NEW: API key lifecycle
│   │   ├── webhook_security.py     # NEW: Enhanced webhook auth
│   │   ├── metrics.py              # NEW: Metrics collection
│   │   ├── health.py               # NEW: Health checks
│   │   └── feature_flags.py        # NEW: Configuration
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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

- **Translations**: Help make Mira available in more languages - see our [Localization Guide](docs/wiki/Localization.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
