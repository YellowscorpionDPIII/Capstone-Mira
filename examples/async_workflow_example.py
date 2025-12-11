"""
Example demonstrating async workflow execution with timeout protection.

This example shows how to use the new async workflow execution capabilities
of the OrchestratorAgent with configurable timeout protection.
"""
import asyncio
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent


async def main():
    """Demonstrate async workflow execution with timeout protection."""
    
    # Initialize orchestrator and register agents
    orchestrator = OrchestratorAgent()
    orchestrator.register_agent(ProjectPlanAgent())
    orchestrator.register_agent(RiskAssessmentAgent())
    orchestrator.register_agent(StatusReporterAgent())
    
    # Example 1: Normal workflow execution with default 30-second timeout
    print("=" * 60)
    print("Example 1: Normal workflow execution with default timeout")
    print("=" * 60)
    
    message = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Demo Project',
                'description': 'A demonstration project for async workflow execution',
                'goals': ['Design System', 'Implement Features', 'Deploy to Production'],
                'duration_weeks': 12
            }
        }
    }
    
    response = await orchestrator.process_async(message)
    
    print(f"\nWorkflow Type: {response['workflow_type']}")
    print(f"Completed Steps: {len(response['steps'])}")
    
    for step in response['steps']:
        print(f"\n  Step: {step['step']}")
        print(f"  Status: {step['status']}")
    
    # Example 2: Workflow execution with custom timeout
    print("\n" + "=" * 60)
    print("Example 2: Workflow execution with custom 60-second timeout")
    print("=" * 60)
    
    message2 = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Large Project',
                'description': 'A large project requiring more processing time',
                'goals': ['Goal ' + str(i) for i in range(1, 6)],
                'duration_weeks': 24
            }
        }
    }
    
    response2 = await orchestrator.process_async(message2, timeout=60.0)
    
    print(f"\nWorkflow Type: {response2['workflow_type']}")
    print(f"Completed Steps: {len(response2['steps'])}")
    
    # Example 3: Demonstrating timeout scenario (very short timeout)
    print("\n" + "=" * 60)
    print("Example 3: Timeout scenario with very short timeout (0.001s)")
    print("=" * 60)
    
    message3 = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Quick Timeout Test',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
    }
    
    response3 = await orchestrator.process_async(message3, timeout=0.001)
    
    if response3.get('status') == 'timeout':
        print(f"\n⚠️  Workflow timed out as expected!")
        print(f"Error: {response3.get('error')}")
        print(f"\nPartial Progress:")
        partial = response3.get('partial_progress', {})
        print(f"  Completed Steps: {partial.get('completed_steps', [])}")
        print(f"  Total Completed: {partial.get('total_steps_completed', 0)}")
        print(f"  Timeout: {partial.get('timeout_seconds', 0)}s")
    else:
        print(f"\nWorkflow completed before timeout (this is rare with 0.001s)")
    
    # Example 4: Non-workflow async message processing
    print("\n" + "=" * 60)
    print("Example 4: Non-workflow async message processing")
    print("=" * 60)
    
    plan_message = {
        'type': 'generate_plan',
        'data': {
            'name': 'Async Plan Test',
            'description': 'Testing async plan generation',
            'goals': ['Goal 1', 'Goal 2'],
            'duration_weeks': 8
        }
    }
    
    plan_response = await orchestrator.process_async(plan_message, timeout=30.0)
    
    print(f"\nAgent ID: {plan_response['agent_id']}")
    print(f"Status: {plan_response['status']}")
    print(f"Project Name: {plan_response['data']['name']}")
    print(f"Milestones: {len(plan_response['data']['milestones'])}")
    print(f"Tasks: {len(plan_response['data']['tasks'])}")
    
    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    # Run the async examples
    asyncio.run(main())
