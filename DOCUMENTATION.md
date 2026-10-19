# Mira - Multi-Agent Workflow Platform

A modular multi-agent AI workflow system for technical program management. Automates planning, risk assessment, status reporting, and connects with Trello, Jira, GitHub, Airtable, Google Docs, and more for seamless collaboration.

## Features

### Core Agents

- **ProjectPlanAgent**: Generates structured project plans with milestones and tasks
- **RiskAssessmentAgent**: Identifies and assesses project risks with mitigation strategies
- **StatusReporterAgent**: Creates weekly status reports with accomplishments and metrics
- **OrchestratorAgent**: Routes messages between agents and coordinates multi-agent workflows
- **GovernanceAgent**: Evaluates workflows for risk assessment and human-in-the-loop validation based on financial impact, compliance requirements, and explainability scores

### Integrations

- **Trello**: Sync tasks and milestones with Trello boards
- **Jira**: Sync issues and risks with Jira projects
- **GitHub**: Sync milestones and issues with GitHub repositories
- **Airtable**: Sync project data and reports with Airtable bases
- **Google Docs**: Create formatted documents and reports
- **PDF**: Extract and parse information from PDF documents

### Architecture

- **Event-Driven**: Message broker with publish-subscribe pattern
- **Webhook Support**: Receive events from external services
- **Modular Design**: Easily extend with custom agents and integrations
- **Configuration**: Flexible configuration via files and environment variables

## Installation

```bash
# Clone the repository
git clone https://github.com/YellowscorpionDPIII/Capstone-Mira.git
cd Capstone-Mira

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Quick Start

### Basic Usage

```python
from mira.app import MiraApplication

# Initialize the application
app = MiraApplication()

# Generate a project plan
plan_message = {
    'type': 'generate_plan',
    'data': {
        'name': 'My Project',
        'description': 'Project description',
        'goals': ['Goal 1', 'Goal 2', 'Goal 3'],
        'duration_weeks': 12
    }
}

response = app.process_message(plan_message)
print(response)
```

### Running the Example

```bash
python examples/example_usage.py
```

This will demonstrate:
1. Project plan generation
2. Risk assessment
3. Status report creation
4. Multi-agent workflows
5. Integration with external services

## Configuration

### Configuration File (JSON)

Create a `config.json` file:

```json
{
  "broker": {
    "enabled": true,
    "queue_size": 1000
  },
  "webhook": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 5000,
    "secret_key": "your_secret_key"
  },
  "integrations": {
    "trello": {
      "enabled": true,
      "api_key": "your_api_key",
      "api_token": "your_token",
      "board_id": "your_board_id"
    },
    "jira": {
      "enabled": true,
      "url": "https://your-domain.atlassian.net",
      "username": "your_email",
      "api_token": "your_token",
      "project_key": "YOUR_KEY"
    },
    "github": {
      "enabled": true,
      "token": "your_token",
      "repository": "user/repo"
    }
  }
}
```

### Governance Configuration (YAML)

Governance thresholds can be configured in `config/governance_config.yaml` for runtime tuning without redeployment:

```yaml
thresholds:
  # Financial threshold in dollars - workflows exceeding this amount require human validation
  financial_threshold: 10000
  
  # Compliance threshold level - can be 'low', 'medium', 'high', or 'critical'
  # Workflows at or above this level may require additional review
  compliance_threshold: 'medium'
  
  # Explainability threshold (0.0 to 1.0) - lower scores indicate less explainable decisions
  # Workflows below this threshold require human validation
  explainability_threshold: 0.7
```

Thresholds can also be configured programmatically:

```python
from mira.agents.governance_agent import GovernanceAgent

# Custom thresholds via config parameter
config = {
    'financial_threshold': 50000,
    'compliance_threshold': 'high',
    'explainability_threshold': 0.6
}
agent = GovernanceAgent(config=config)

# Or update thresholds at runtime
agent.update_thresholds({
    'financial_threshold': 75000,
    'explainability_threshold': 0.5
})
```

### Environment Variables

```bash
# Webhook configuration
export MIRA_WEBHOOK_ENABLED=true
export MIRA_WEBHOOK_PORT=5000
export MIRA_WEBHOOK_SECRET=your_secret

# Trello configuration
export MIRA_TRELLO_ENABLED=true
export MIRA_TRELLO_API_KEY=your_key
export MIRA_TRELLO_API_TOKEN=your_token

# Jira configuration
export MIRA_JIRA_ENABLED=true
export MIRA_JIRA_URL=https://your-domain.atlassian.net
```

## Usage Examples

### Generate Project Plan

```python
from mira.agents.project_plan_agent import ProjectPlanAgent

agent = ProjectPlanAgent()
message = {
    'type': 'generate_plan',
    'data': {
        'name': 'Mobile App Development',
        'goals': ['Design', 'Development', 'Testing', 'Launch'],
        'duration_weeks': 16
    }
}

response = agent.process(message)
plan = response['data']
```

### Assess Risks

```python
from mira.agents.risk_assessment_agent import RiskAssessmentAgent

agent = RiskAssessmentAgent()
message = {
    'type': 'assess_risks',
    'data': {
        'name': 'My Project',
        'description': 'urgent project with new technology',
        'tasks': [...],
        'duration_weeks': 8
    }
}

response = agent.process(message)
assessment = response['data']
```

### Generate Status Report

```python
from mira.agents.status_reporter_agent import StatusReporterAgent

agent = StatusReporterAgent()
message = {
    'type': 'generate_report',
    'data': {
        'name': 'My Project',
        'week_number': 5,
        'tasks': [...],
        'milestones': [...],
        'risks': [...]
    }
}

response = agent.process(message)
report = response['data']
```

### Execute Multi-Agent Workflow

```python
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent

# Create and register agents
orchestrator = OrchestratorAgent()
orchestrator.register_agent(ProjectPlanAgent())
orchestrator.register_agent(RiskAssessmentAgent())
orchestrator.register_agent(StatusReporterAgent())

# Execute workflow
workflow_message = {
    'type': 'workflow',
    'data': {
        'workflow_type': 'project_initialization',
        'data': {
            'name': 'New Project',
            'goals': ['Goal 1', 'Goal 2'],
            'duration_weeks': 12
        }
    }
}

result = orchestrator.process(workflow_message)
```

### Governance & Human-in-the-Loop Validation

The GovernanceAgent evaluates workflows for risk assessment and determines when human validation is required:

```python
from mira.agents.governance_agent import GovernanceAgent

agent = GovernanceAgent()

# Assess governance requirements
message = {
    'type': 'assess_governance',
    'data': {
        'workflow_id': 'wf-123',
        'financial_impact': 50000,
        'compliance_level': 'high',
        'explainability_score': 0.6
    }
}

response = agent.process(message)
assessment = response['data']

print(f"Risk Level: {assessment['risk_level']}")
print(f"Requires Human Validation: {assessment['requires_human_validation']}")
print(f"Reasons: {assessment['reasons']}")
```

**Integrate governance checks in workflows:**

```python
from mira.agents.orchestrator_agent import OrchestratorAgent

orchestrator = OrchestratorAgent()

# Workflow with governance data
workflow_message = {
    'type': 'workflow',
    'data': {
        'workflow_type': 'project_initialization',
        'data': {
            'name': 'High-Value Project',
            'goals': ['Design', 'Develop', 'Deploy'],
            'duration_weeks': 16
        },
        'governance_data': {
            'workflow_id': 'proj-456',
            'financial_impact': 250000,
            'compliance_level': 'critical',
            'explainability_score': 0.55
        }
    }
}

result = orchestrator.process(workflow_message)

if result.get('status') == 'pending_approval':
    print("⚠️ Workflow requires human approval")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Reasons: {result['governance']['reasons']}")
```

**Monitor pending approvals via pub/sub:**

```python
from mira.core.message_broker import get_broker

broker = get_broker()

def handle_pending_approval(message):
    """Handle workflows requiring human validation"""
    data = message['data']
    print(f"Pending approval for {data['workflow_type']}")
    print(f"Governance: {data['governance']}")
    # Send notification to dashboard, Slack, etc.

# Subscribe to pending approval events
broker.subscribe('governance.pending_approval', handle_pending_approval)
broker.start()
```

**Error handling:** The orchestrator includes automatic fallback to 'low' risk on governance agent failures to prevent workflow halts.

**Structured logging:** High-risk workflows generate warning logs for n8n integration and observability:
```
WARNING - High risk workflow proj-456: risk_level=high, financial_impact=$250000, ...
```

### Use Integrations

```python
from mira.integrations.trello_integration import TrelloIntegration

# Initialize integration
trello = TrelloIntegration({
    'api_key': 'your_key',
    'api_token': 'your_token',
    'board_id': 'your_board'
})

# Connect
trello.connect()

# Sync tasks
tasks = [
    {'id': 'T1', 'name': 'Task 1', 'status': 'in_progress'},
    {'id': 'T2', 'name': 'Task 2', 'status': 'not_started'}
]

result = trello.sync_data('tasks', tasks)
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m unittest discover mira/tests

# Run specific test file
python -m unittest mira.tests.test_agents

# Run with coverage (requires pytest-cov)
pytest --cov=mira mira/tests/
```

## Architecture

### Event-Driven Architecture

```
┌─────────────────┐
│  External APIs  │
│ (Trello, Jira)  │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Webhooks │
    └────┬─────┘
         │
    ┌────▼────────┐
    │   Message   │
    │   Broker    │
    └─┬─────────┬─┘
      │         │
  ┌───▼──┐  ┌──▼───┐
  │Agent1│  │Agent2│
  └──────┘  └──────┘
```

### Agent Communication

Agents communicate through the message broker using a standardized message format:

```python
{
    'type': 'message_type',
    'data': {
        # Message-specific data
    },
    'timestamp': 'ISO-8601 timestamp'
}
```

### Adding Custom Agents

Create a new agent by extending `BaseAgent`:

```python
from mira.core.base_agent import BaseAgent
from typing import Dict, Any

class CustomAgent(BaseAgent):
    def __init__(self, agent_id='custom_agent', config=None):
        super().__init__(agent_id, config)
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message')
            
        # Your custom logic here
        result = self._do_work(message['data'])
        
        return self.create_response('success', result)
        
    def _do_work(self, data):
        # Implementation
        return data
```

### Adding Custom Integrations

Create a new integration by extending `BaseIntegration`:

```python
from mira.integrations.base_integration import BaseIntegration
from typing import Dict, Any

class CustomIntegration(BaseIntegration):
    def __init__(self, config=None):
        super().__init__('custom_service', config)
        
    def connect(self) -> bool:
        # Connection logic
        self.connected = True
        return True
        
    def disconnect(self):
        # Disconnection logic
        self.connected = False
        
    def sync_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # Sync logic
        return {'success': True}
```

## API Reference

### Core Components

- `BaseAgent`: Abstract base class for all agents
- `MessageBroker`: Publish-subscribe message broker
- `WebhookHandler`: HTTP webhook receiver
- `Config`: Configuration management

### Agents

- `ProjectPlanAgent`: Project planning
- `RiskAssessmentAgent`: Risk analysis
- `StatusReporterAgent`: Status reporting
- `OrchestratorAgent`: Message routing and workflow orchestration

### Integrations

- `TrelloIntegration`: Trello API integration
- `JiraIntegration`: Jira API integration
- `GitHubIntegration`: GitHub API integration
- `AirtableIntegration`: Airtable API integration
- `GoogleDocsIntegration`: Google Docs API integration
- `PDFIntegration`: PDF processing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
