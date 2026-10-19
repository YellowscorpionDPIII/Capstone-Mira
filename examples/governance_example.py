#!/usr/bin/env python3
"""
Example demonstrating the Governance & Human-in-the-Loop functionality.

This script shows how to:
1. Use the GovernanceAgent for risk assessment
2. Integrate governance checks in workflows
3. Determine when human validation is required
"""

from mira.agents.governance_agent import GovernanceAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent


def main():
    """Run governance examples."""
    print("=" * 70)
    print("Mira Governance & Human-in-the-Loop - Example")
    print("=" * 70)
    
    # Example 1: Direct governance assessment
    print("\n1. Direct Governance Assessment")
    print("-" * 70)
    
    governance_agent = GovernanceAgent()
    
    # Low-risk scenario
    low_risk_message = {
        'type': 'assess_governance',
        'data': {
            'financial_impact': 5000,
            'compliance_level': 'low',
            'explainability_score': 0.9
        }
    }
    
    response = governance_agent.process(low_risk_message)
    print(f"\nLow-Risk Scenario:")
    print(f"  Financial Impact: $5,000")
    print(f"  Compliance Level: low")
    print(f"  Explainability Score: 0.9")
    print(f"  Result:")
    print(f"    Risk Level: {response['data']['risk_level']}")
    print(f"    Requires Human Validation: {response['data']['requires_human_validation']}")
    
    # High-risk scenario
    high_risk_message = {
        'type': 'assess_governance',
        'data': {
            'financial_impact': 100000,
            'compliance_level': 'critical',
            'explainability_score': 0.4
        }
    }
    
    response = governance_agent.process(high_risk_message)
    print(f"\nHigh-Risk Scenario:")
    print(f"  Financial Impact: $100,000")
    print(f"  Compliance Level: critical")
    print(f"  Explainability Score: 0.4")
    print(f"  Result:")
    print(f"    Risk Level: {response['data']['risk_level']}")
    print(f"    Requires Human Validation: {response['data']['requires_human_validation']}")
    print(f"    Reasons:")
    for reason in response['data']['reasons']:
        print(f"      - {reason}")
    
    # Example 2: Workflow with governance checks
    print("\n2. Workflow Execution with Governance")
    print("-" * 70)
    
    orchestrator = OrchestratorAgent()
    orchestrator.register_agent(ProjectPlanAgent())
    orchestrator.register_agent(RiskAssessmentAgent())
    orchestrator.register_agent(StatusReporterAgent())
    
    # Workflow with low-risk governance data
    workflow_message = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Standard Web Application',
                'goals': ['Design UI', 'Implement backend', 'Test'],
                'duration_weeks': 8
            },
            'governance_data': {
                'financial_impact': 8000,
                'compliance_level': 'low',
                'explainability_score': 0.85
            }
        }
    }
    
    result = orchestrator.process(workflow_message)
    print(f"\nLow-Risk Workflow:")
    print(f"  Workflow Type: {result['workflow_type']}")
    print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"  Requires Validation: {result.get('requires_human_validation', False)}")
    print(f"  Steps Completed: {len(result['steps'])}")
    if result.get('status') == 'pending_approval':
        print(f"  Status: PENDING APPROVAL")
    else:
        print(f"  Status: Workflow can proceed automatically")
    
    # Workflow with high-risk governance data
    workflow_message_high_risk = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Financial Trading Platform',
                'goals': ['Design secure architecture', 'Implement trading engine', 'Compliance review'],
                'duration_weeks': 16
            },
            'governance_data': {
                'financial_impact': 250000,
                'compliance_level': 'critical',
                'explainability_score': 0.55
            }
        }
    }
    
    result = orchestrator.process(workflow_message_high_risk)
    print(f"\nHigh-Risk Workflow:")
    print(f"  Workflow Type: {result['workflow_type']}")
    print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"  Requires Validation: {result.get('requires_human_validation', False)}")
    print(f"  Steps Completed: {len(result['steps'])}")
    if result.get('status') == 'pending_approval':
        print(f"  Status: ⚠️  PENDING HUMAN APPROVAL ⚠️")
        print(f"  Governance Reasons:")
        for reason in result['governance']['reasons']:
            print(f"    - {reason}")
    
    # Example 3: Custom governance thresholds
    print("\n3. Custom Governance Thresholds")
    print("-" * 70)
    
    custom_config = {
        'governance': {
            'financial_threshold': 50000,
            'compliance_threshold': 'high',
            'explainability_threshold': 0.6
        }
    }
    
    custom_orchestrator = OrchestratorAgent(config=custom_config)
    custom_orchestrator.register_agent(ProjectPlanAgent())
    custom_orchestrator.register_agent(RiskAssessmentAgent())
    custom_orchestrator.register_agent(StatusReporterAgent())
    
    custom_message = {
        'type': 'assess_governance',
        'data': {
            'financial_impact': 40000,
            'compliance_level': 'medium',
            'explainability_score': 0.7
        }
    }
    
    response = custom_orchestrator.process(custom_message)
    print(f"\nCustom Thresholds Applied:")
    print(f"  Financial Threshold: $50,000 (vs default $10,000)")
    print(f"  Compliance Threshold: high (vs default medium)")
    print(f"  Explainability Threshold: 0.6 (vs default 0.7)")
    print(f"\nAssessment with $40,000 financial impact:")
    print(f"  Risk Level: {response['data']['risk_level']}")
    print(f"  Requires Validation: {response['data']['requires_human_validation']}")
    
    # Example 4: Backward compatibility (workflow without governance)
    print("\n4. Backward Compatibility Test")
    print("-" * 70)
    
    legacy_workflow = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Legacy Project',
                'goals': ['Goal 1', 'Goal 2'],
                'duration_weeks': 10
            }
            # No governance_data provided
        }
    }
    
    result = orchestrator.process(legacy_workflow)
    print(f"\nLegacy Workflow (no governance data):")
    print(f"  Workflow Type: {result['workflow_type']}")
    print(f"  Governance Assessment: {result.get('governance')}")
    print(f"  Steps Completed: {len(result['steps'])}")
    print(f"  ✓ Workflow executes normally without governance checks")
    
    print("\n" + "=" * 70)
    print("Governance examples completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    main()
