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
