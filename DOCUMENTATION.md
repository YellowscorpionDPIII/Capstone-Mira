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

## LangChain Prompt Optimizations for Governance

### Overview

Mira uses LangChain-optimized prompts for governance-related features to ensure consistent, reliable, and compliant AI-driven decision-making. These optimizations focus on risk assessment, compliance checking, and human-in-the-loop (HITL) approval workflows.

### Governance Prompt Templates

#### Risk Assessment Prompts

The risk assessment agent uses structured prompts that follow LangChain best practices:

```python
# Example: Optimized risk assessment prompt template
risk_assessment_prompt = """
Analyze the following project for potential risks:

Project: {project_name}
Description: {description}
Duration: {duration_weeks} weeks
Task Count: {task_count}

Identify risks in these categories:
1. Schedule risks (timeline, dependencies)
2. Resource risks (team capacity, expertise)
3. Technical risks (technology complexity, integration)
4. Compliance risks (regulatory, security)

For each risk, provide:
- Risk type and severity (low/medium/high/critical)
- Impact description
- Mitigation strategy

Return structured JSON format.
"""
```

**Optimization Techniques Applied:**

1. **Clear Structure**: Prompts use explicit sections and formatting to guide the LLM
2. **Constrained Output**: Requests specific output formats (JSON) for reliable parsing
3. **Few-Shot Learning**: Include examples of well-formed risk assessments when appropriate
4. **Temperature Control**: Lower temperature (0.3-0.5) for consistency in governance decisions
5. **Token Optimization**: Concise prompts that balance context with efficiency

#### Governance Decision Prompts

For governance-related decisions requiring HITL approval:

```python
# Example: Governance decision prompt with chain-of-thought
governance_decision_prompt = """
Evaluate the following action for governance compliance:

Action: {action_type}
Context: {context}
Risk Score: {risk_score}

Step 1: Identify applicable governance policies
Step 2: Assess compliance with each policy
Step 3: Determine if human approval is required
Step 4: Provide recommendation with justification

Governance Thresholds:
- Risk Score > 7: Requires HITL approval
- Compliance Issues: Requires HITL approval
- Budget > $10k: Requires HITL approval

Provide structured analysis and recommendation.
"""
```

**Key Features:**

- **Chain-of-Thought Reasoning**: Breaks down complex governance decisions into steps
- **Explicit Thresholds**: Clearly defines decision boundaries
- **Context Injection**: Includes relevant policies and constraints
- **Audit Trail**: Generates explanations for governance decisions

### Prompt Engineering Best Practices

#### 1. Context Window Management

- **Prioritize Recent Context**: Most relevant governance policies first
- **Summarization**: Use LangChain summarization chains for long documents
- **Sliding Window**: Maintain only essential context for compliance checks

#### 2. Output Parsing

```python
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# Define governance response schema
response_schemas = [
    ResponseSchema(name="risk_level", description="Risk level: low, medium, high, or critical"),
    ResponseSchema(name="requires_approval", description="Boolean: true if HITL approval needed"),
    ResponseSchema(name="justification", description="Explanation for the decision"),
    ResponseSchema(name="mitigation_actions", description="List of recommended mitigation actions")
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
```

#### 3. Prompt Chaining for Complex Governance Workflows

For multi-step governance workflows, use LangChain's sequential chains:

```python
# Example: Governance workflow chain
# Step 1: Risk Assessment
risk_chain = LLMChain(llm=llm, prompt=risk_prompt)

# Step 2: Compliance Check
compliance_chain = LLMChain(llm=llm, prompt=compliance_prompt)

# Step 3: Approval Routing
approval_chain = LLMChain(llm=llm, prompt=approval_routing_prompt)

# Combine into sequential chain
governance_workflow = SequentialChain(
    chains=[risk_chain, compliance_chain, approval_chain],
    input_variables=["project_data"],
    output_variables=["final_decision", "approval_required"]
)
```

#### 4. Governance-Specific Prompt Patterns

**Pattern 1: Constraint-Based Prompting**
```python
constraints_prompt = """
Evaluate against these MANDATORY constraints:
- Regulatory: {regulatory_requirements}
- Security: {security_policies}
- Budget: {budget_limits}

Any violation requires immediate HITL escalation.
"""
```

**Pattern 2: Role-Based Prompting**
```python
role_prompt = """
You are a governance compliance officer responsible for:
- Ensuring regulatory compliance
- Identifying high-risk scenarios
- Escalating issues requiring human oversight

Maintain a conservative, risk-averse approach.
"""
```

**Pattern 3: Evaluation Prompts with Rubrics**
```python
rubric_prompt = """
Evaluate using this rubric:

Risk Score Calculation:
- Low Risk (1-3): Standard automated approval
- Medium Risk (4-6): Enhanced monitoring, auto-approval with notification
- High Risk (7-8): HITL approval required
- Critical Risk (9-10): Immediate escalation to senior governance team

Provide score and detailed justification.
"""
```

### Monitoring and Optimization

#### Prompt Performance Metrics

Track these metrics for governance prompts:

- **Consistency**: Same inputs yield similar outputs (track variance)
- **Latency**: Response time for governance decisions (target: <2s)
- **Accuracy**: Agreement with human governance decisions (target: >90%)
- **Token Usage**: Average tokens per governance decision

#### A/B Testing Governance Prompts

```python
# Example: Test two prompt variants
prompt_variant_a = "Evaluate risks..."  # Control
prompt_variant_b = "Using chain-of-thought, evaluate risks..."  # Test

# Route 50% of requests to each variant
# Measure: accuracy, consistency, latency
# Select winner after statistical significance
```

#### Continuous Improvement

1. **Feedback Loop**: Incorporate HITL corrections back into prompt examples
2. **Prompt Versioning**: Track prompt changes and performance over time
3. **Regular Audits**: Review governance decisions for bias and accuracy
4. **Update Thresholds**: Adjust risk thresholds based on organizational learning

### Integration with Orchestrator

The orchestrator agent uses optimized prompts for routing governance requests:

```python
# Governance routing logic with prompt optimization
async def route_governance_request(request):
    # Use LangChain prompt template
    routing_prompt = PromptTemplate(
        input_variables=["request_type", "risk_score", "context"],
        template="""
        Route this governance request to the appropriate handler:
        
        Request: {request_type}
        Risk Score: {risk_score}
        Context: {context}
        
        Routing Rules:
        - Risk Score < 7: automated_governance_handler
        - Risk Score >= 7: hitl_approval_handler
        - Compliance issues: compliance_review_handler
        
        Return handler name and routing justification.
        """
    )
    
    response = await llm_chain.run(
        request_type=request.type,
        risk_score=request.risk_score,
        context=request.context
    )
    
    return parse_routing_decision(response)
```

### Resources

- **LangChain Documentation**: https://python.langchain.com/docs/
- **Prompt Engineering Guide**: https://www.promptingguide.ai/
- **Governance Patterns**: See `governance/risk_assessor.py` and `governance/hitl_handler.py` for implementation examples

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
