"""
Example usage of the Risk Assessment Engine.

This script demonstrates how to use the RiskAssessor class to evaluate
workflows for risk and trigger Human-in-the-Loop (HITL) reviews.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from governance.risk_assessor import RiskAssessor, RiskScore
import json


def example_low_risk_workflow():
    """Example of a low-risk workflow assessment."""
    print("=" * 60)
    print("Example 1: Low-Risk Workflow")
    print("=" * 60)
    
    # Initialize the risk assessor
    assessor = RiskAssessor()
    
    # Define a low-risk workflow
    workflow_data = {
        'financial_amount': 5000,  # Below $10,000 threshold
        'compliance_data': {
            'gdpr': True,
            'sox': True,
            'hipaa': True
        },
        'ai_model_type': 'linear',
        'explainability_score': 0.95
    }
    
    # Assess the workflow
    risk_score = assessor.assess_workflow("WF-LOW-001", workflow_data)
    
    # Display results
    print(f"\nWorkflow ID: {risk_score.workflow_id}")
    print(f"Financial Risk: {risk_score.financial_risk:.3f}")
    print(f"Compliance Risk: {risk_score.compliance_risk:.3f}")
    print(f"Explainability Risk: {risk_score.explainability_risk:.3f}")
    print(f"Composite Score: {risk_score.composite_score:.3f}")
    print(f"Requires HITL: {risk_score.requires_hitl}")
    print(f"\nDetails: {json.dumps(risk_score.details, indent=2)}")


def example_high_risk_workflow():
    """Example of a high-risk workflow assessment."""
    print("\n" + "=" * 60)
    print("Example 2: High-Risk Workflow (Triggers HITL)")
    print("=" * 60)
    
    # Initialize the risk assessor
    assessor = RiskAssessor()
    
    # Define a high-risk workflow
    workflow_data = {
        'financial_amount': 150000,  # Exceeds $10,000 threshold
        'compliance_data': {
            'gdpr': False,  # Compliance failure
            'sox': True,
            'hipaa': False  # Compliance failure
        },
        'ai_model_type': 'deep_learning',
        'explainability_score': 0.3  # Low explainability
    }
    
    # Assess the workflow
    risk_score = assessor.assess_workflow("WF-HIGH-001", workflow_data)
    
    # Display results
    print(f"\nWorkflow ID: {risk_score.workflow_id}")
    print(f"Financial Risk: {risk_score.financial_risk:.3f}")
    print(f"Compliance Risk: {risk_score.compliance_risk:.3f}")
    print(f"Explainability Risk: {risk_score.explainability_risk:.3f}")
    print(f"Composite Score: {risk_score.composite_score:.3f}")
    print(f"Requires HITL: {risk_score.requires_hitl} ⚠️")
    print(f"\nDetails: {json.dumps(risk_score.details, indent=2)}")
    
    if risk_score.requires_hitl:
        print("\n🚨 HITL REVIEW REQUIRED:")
        print("   This workflow has been queued for human review.")
        print("   Reviewers will be notified via the HITL service.")


def example_ai_workflow_without_explainability():
    """Example of an AI workflow without explicit explainability score."""
    print("\n" + "=" * 60)
    print("Example 3: AI Workflow (Model-Based Risk)")
    print("=" * 60)
    
    # Initialize the risk assessor
    assessor = RiskAssessor()
    
    # Define an AI workflow without explicit explainability score
    workflow_data = {
        'financial_amount': 8000,
        'compliance_data': {
            'gdpr': True,
            'sox': True
        },
        'ai_model_type': 'ensemble',  # Model type determines risk
        # No explainability_score provided
    }
    
    # Assess the workflow
    risk_score = assessor.assess_workflow("WF-AI-001", workflow_data)
    
    # Display results
    print(f"\nWorkflow ID: {risk_score.workflow_id}")
    print(f"Financial Risk: {risk_score.financial_risk:.3f}")
    print(f"Compliance Risk: {risk_score.compliance_risk:.3f}")
    print(f"Explainability Risk: {risk_score.explainability_risk:.3f}")
    print(f"  (Based on model type: {workflow_data['ai_model_type']})")
    print(f"Composite Score: {risk_score.composite_score:.3f}")
    print(f"Requires HITL: {risk_score.requires_hitl}")


def example_cached_retrieval():
    """Example of retrieving a cached risk score."""
    print("\n" + "=" * 60)
    print("Example 4: Retrieving Cached Risk Score")
    print("=" * 60)
    
    # Initialize the risk assessor
    assessor = RiskAssessor()
    
    # First, assess a workflow
    workflow_data = {
        'financial_amount': 7500,
        'compliance_data': {'gdpr': True},
        'ai_model_type': 'tree'
    }
    
    risk_score = assessor.assess_workflow("WF-CACHE-001", workflow_data)
    print(f"\nAssessed and cached: {risk_score.workflow_id}")
    
    # Now retrieve from cache
    cached_score = assessor.get_cached_risk_score("WF-CACHE-001")
    
    if cached_score:
        print(f"\nRetrieved from cache: {cached_score.workflow_id}")
        print(f"Composite Score: {cached_score.composite_score:.3f}")
        print("✅ Cache hit!")
    else:
        print("❌ Cache miss - Redis may not be available")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("RISK ASSESSMENT ENGINE - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate the risk assessment engine")
    print("capabilities for Capstone-Mira workflows.\n")
    
    try:
        example_low_risk_workflow()
        example_high_risk_workflow()
        example_ai_workflow_without_explainability()
        example_cached_retrieval()
        
        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
