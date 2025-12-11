# Mira - Multi-Agent Workflow Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Modular multi-agent AI workflow system for technical program management. Automates planning, risk assessment, status reporting, and connects with Trello, Jira, GitHub, Airtable, Google Docs, and PDFs for seamless collaboration.

## 🚀 Features

- **🤖 Five Specialized Agents**
  - ProjectPlanAgent: Generate comprehensive project plans
  - RiskAssessmentAgent: Identify and assess project risks
  - StatusReporterAgent: Create weekly status reports
  - OrchestratorAgent: Coordinate multi-agent workflows
  - GovernanceAgent: Risk assessment and human-in-the-loop validation

- **🔌 Six Integration Adapters**
  - Trello, Jira, GitHub, Airtable, Google Docs, PDF

- **📡 Event-Driven Architecture**
  - Message broker with publish-subscribe pattern
  - Webhook support for external integrations
  - Asynchronous message processing

- **⚙️ Flexible Configuration**
  - JSON configuration files
  - YAML governance thresholds for runtime tuning
  - Environment variable support
  - Modular and extensible design

- **🛡️ Governance & Compliance**
  - Configurable financial impact thresholds
  - Compliance level assessment (low, medium, high, critical)
  - Explainability score validation
  - Human-in-the-loop validation for high-risk workflows
  - Pub/sub notifications for pending approvals
  - Structured logging for observability

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
│   │   ├── orchestrator_agent.py
│   │   └── governance_agent.py
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
├── config/                    # Configuration files
│   └── governance_config.yaml # Governance thresholds
├── examples/                  # Example scripts
│   ├── example_usage.py
│   └── governance_example.py
├── requirements.txt
├── setup.py
├── DOCUMENTATION.md
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
