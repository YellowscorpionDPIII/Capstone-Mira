"""
Example demonstrating n8n integration with Mira platform.

This example shows how to:
1. Set up the webhook handler with operator keys
2. Register n8n webhook handler
3. Process n8n workflow events
4. Send events to n8n
"""

from mira.app import MiraApplication
from mira.core.webhook_handler import WebhookHandler
import json


def main():
    """Demonstrate n8n integration."""
    print("=== Mira n8n Integration Example ===\n")
    
    # Initialize Mira application
    config = {
        'webhook': {
            'enabled': True,
            'host': '0.0.0.0',
            'port': 5000
        },
        'agents': {
            'project_plan_agent': {'enabled': True},
            'risk_assessment_agent': {'enabled': True},
            'status_reporter_agent': {'enabled': True}
        }
    }
    
    # Create webhook handler
    webhook_handler = WebhookHandler()
    
    # Generate an operator key for n8n authentication
    operator_key = webhook_handler.generate_operator_key()
    print(f"Generated operator key: {operator_key}")
    print("Use this key in your n8n webhook configuration\n")
    
    # Register n8n webhook handler
    def handle_n8n_workflow(data):
        """Handle n8n workflow events."""
        workflow_id = data.get('workflowId', 'unknown')
        execution_id = data.get('executionId', 'unknown')
        event = data.get('data', {}).get('event', 'unknown')
        status = data.get('data', {}).get('status', 'unknown')
        
        print(f"Received n8n event:")
        print(f"  Workflow ID: {workflow_id}")
        print(f"  Execution ID: {execution_id}")
        print(f"  Event: {event}")
        print(f"  Status: {status}")
        
        # Process based on event type
        if event == 'workflow_completed':
            if status == 'success':
                print("  ✓ Workflow completed successfully")
            else:
                print("  ✗ Workflow failed")
        
        return {
            'status': 'processed',
            'service': 'n8n',
            'workflow_id': workflow_id,
            'execution_id': execution_id
        }
    
    webhook_handler.register_handler('n8n', handle_n8n_workflow)
    
    # Simulate n8n webhook call
    print("\n--- Testing n8n webhook ---")
    test_payload = {
        'workflowId': 'wf_123',
        'executionId': 'exec_456',
        'data': {
            'event': 'workflow_completed',
            'status': 'success',
            'timestamp': '2025-12-09T12:00:00Z'
        }
    }
    
    with webhook_handler.app.test_client() as client:
        # Test with valid operator key
        response = client.post(
            '/webhook/n8n',
            json=test_payload,
            headers={
                'Content-Type': 'application/json',
                'X-Operator-Key': operator_key
            }
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Data: {json.dumps(response.json, indent=2)}")
    
    # Show curl command for testing
    print("\n--- n8n Integration Setup ---")
    print("\n1. In n8n, create a new Webhook node")
    print("2. Configure the webhook:")
    print(f"   URL: http://mira-app:5000/webhook/n8n")
    print(f"   Method: POST")
    print(f"   Authentication: Header Auth")
    print(f"   Header Name: X-Operator-Key")
    print(f"   Header Value: {operator_key}")
    
    print("\n3. Test with curl:")
    print(f"""
   curl -X POST http://localhost:5000/webhook/n8n \\
     -H 'Content-Type: application/json' \\
     -H 'X-Operator-Key: {operator_key}' \\
     -d '{{
       "workflowId": "wf_123",
       "executionId": "exec_456",
       "data": {{
         "event": "workflow_completed",
         "status": "success"
       }}
     }}'
    """)
    
    print("\n4. Monitor logs:")
    print("   docker-compose logs -f mira-app")


if __name__ == '__main__':
    main()
