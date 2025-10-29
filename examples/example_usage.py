#!/usr/bin/env python3
"""
Example usage script demonstrating the Mira platform capabilities.

This script shows how to:
1. Initialize the Mira application
2. Create a project plan
3. Assess risks
4. Generate status reports
5. Execute multi-agent workflows
"""

from mira.app import MiraApplication
from mira.utils.logging import setup_logging
import json


def main():
    """Run example workflows."""
    # Setup logging
    setup_logging(level='INFO')
    
    print("=" * 60)
    print("Mira Multi-Agent Workflow Platform - Example Usage")
    print("=" * 60)
    
    # Initialize application
    print("\n1. Initializing Mira application...")
    app = MiraApplication()
    
    # Example 1: Generate a project plan
    print("\n2. Generating project plan...")
    plan_message = {
        'type': 'generate_plan',
        'data': {
            'name': 'AI-Powered Mobile App',
            'description': 'Develop a mobile app with new AI features for customer engagement',
            'goals': [
                'Design user interface',
                'Implement AI recommendation engine',
                'Develop backend API',
                'Conduct user testing',
                'Launch to production'
            ],
            'duration_weeks': 16
        }
    }
    
    plan_response = app.process_message(plan_message)
    print(f"Status: {plan_response['status']}")
    if plan_response['status'] == 'success':
        plan = plan_response['data']
        print(f"Project: {plan['name']}")
        print(f"Duration: {plan['duration_weeks']} weeks")
        print(f"Milestones: {len(plan['milestones'])}")
        print(f"Tasks: {len(plan['tasks'])}")
        
    # Example 2: Assess risks
    print("\n3. Assessing project risks...")
    risk_message = {
        'type': 'assess_risks',
        'data': {
            'name': 'AI-Powered Mobile App',
            'description': 'urgent project with new unfamiliar AI technology and limited resources',
            'tasks': plan_response['data']['tasks'] if plan_response['status'] == 'success' else [],
            'duration_weeks': 16
        }
    }
    
    risk_response = app.process_message(risk_message)
    print(f"Status: {risk_response['status']}")
    if risk_response['status'] == 'success':
        assessment = risk_response['data']
        print(f"Risk Score: {assessment['risk_score']:.2f}%")
        print(f"Total Risks: {assessment['total_risks']}")
        print("Identified Risks:")
        for risk in assessment['risks'][:3]:  # Show first 3
            print(f"  - [{risk['severity'].upper()}] {risk['description']}")
            print(f"    Mitigation: {risk['mitigation']}")
            
    # Example 3: Generate status report
    print("\n4. Generating status report...")
    # Simulate some task progress
    if plan_response['status'] == 'success':
        tasks = plan_response['data']['tasks']
        for i, task in enumerate(tasks[:5]):
            task['status'] = 'completed' if i < 3 else 'in_progress'
            
    report_message = {
        'type': 'generate_report',
        'data': {
            'name': 'AI-Powered Mobile App',
            'week_number': 4,
            'tasks': tasks if plan_response['status'] == 'success' else [],
            'milestones': plan_response['data']['milestones'] if plan_response['status'] == 'success' else [],
            'risks': assessment['risks'] if risk_response['status'] == 'success' else []
        }
    }
    
    report_response = app.process_message(report_message)
    print(f"Status: {report_response['status']}")
    if report_response['status'] == 'success':
        report = report_response['data']
        print(f"Week: {report['week_number']}")
        print(f"Completion: {report['summary']['completion_percentage']:.1f}%")
        print(f"Completed Tasks: {report['summary']['completed_tasks']}/{report['summary']['total_tasks']}")
        print("Accomplishments:")
        for item in report['accomplishments'][:3]:
            print(f"  - {item}")
            
    # Example 4: Execute multi-agent workflow
    print("\n5. Executing project initialization workflow...")
    workflow_message = {
        'type': 'workflow',
        'data': {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'E-Commerce Platform Redesign',
                'description': 'Redesign e-commerce platform with modern UI/UX',
                'goals': [
                    'User research and analysis',
                    'Design new interface',
                    'Implement frontend',
                    'Integration testing',
                    'Deployment'
                ],
                'duration_weeks': 12
            }
        }
    }
    
    workflow_response = app.process_message(workflow_message)
    print(f"Workflow Type: {workflow_response.get('workflow_type', 'N/A')}")
    print(f"Workflow Steps: {len(workflow_response.get('steps', []))}")
    for step in workflow_response.get('steps', []):
        print(f"  - {step['step']}: {step['status']}")
        
    # Example 5: Integration demonstration
    print("\n6. Demonstrating integrations...")
    from mira.integrations.trello_integration import TrelloIntegration
    from mira.integrations.github_integration import GitHubIntegration
    
    # Trello integration
    trello = TrelloIntegration({
        'api_key': 'demo_key',
        'api_token': 'demo_token',
        'board_id': 'demo_board'
    })
    if trello.connect():
        result = trello.sync_data('tasks', tasks if plan_response['status'] == 'success' else [])
        print(f"Trello sync: {result.get('synced_count', 0)} tasks synced")
        
    # GitHub integration
    github = GitHubIntegration({
        'token': 'demo_token',
        'repository': 'org/repo'
    })
    if github.connect():
        result = github.sync_data('milestones', 
                                  plan_response['data']['milestones'] if plan_response['status'] == 'success' else [])
        print(f"GitHub sync: {result.get('synced_count', 0)} milestones synced")
        
    print("\n" + "=" * 60)
    print("Example usage completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
