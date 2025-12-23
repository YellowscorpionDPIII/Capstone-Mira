"""
Load testing for Mira platform using Locust.

Run with: locust -f load_test.py --host=http://localhost:5000
"""
from locust import HttpUser, task, between
import json
import random
import uuid


class MiraUser(HttpUser):
    """Simulated user for Mira platform load testing."""
    
    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.operator_key = self.generate_operator_key()
        
    def generate_operator_key(self):
        """Generate a unique operator key for webhook authentication."""
        return f"op_{uuid.uuid4().hex[:16]}"
    
    @task(3)
    def webhook_github(self):
        """Test GitHub webhook endpoint."""
        payload = {
            "action": "opened",
            "repository": {
                "name": f"test-repo-{random.randint(1, 100)}",
                "owner": {"login": "test-user"}
            },
            "issue": {
                "number": random.randint(1, 1000),
                "title": "Test Issue",
                "body": "This is a test issue"
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Operator-Key": self.operator_key
        }
        self.client.post("/webhook/github", json=payload, headers=headers)
    
    @task(2)
    def webhook_trello(self):
        """Test Trello webhook endpoint."""
        payload = {
            "action": {
                "type": "createCard",
                "data": {
                    "card": {
                        "name": f"Test Card {random.randint(1, 100)}",
                        "desc": "Test description"
                    }
                }
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Operator-Key": self.operator_key
        }
        self.client.post("/webhook/trello", json=payload, headers=headers)
    
    @task(2)
    def webhook_jira(self):
        """Test Jira webhook endpoint."""
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": f"TEST-{random.randint(1, 1000)}",
                "fields": {
                    "summary": "Test issue",
                    "description": "Test description"
                }
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Operator-Key": self.operator_key
        }
        self.client.post("/webhook/jira", json=payload, headers=headers)
    
    @task(1)
    def webhook_n8n(self):
        """Test n8n webhook endpoint."""
        payload = {
            "workflowId": f"wf_{random.randint(1, 100)}",
            "executionId": f"exec_{uuid.uuid4().hex[:8]}",
            "data": {
                "event": "workflow_completed",
                "status": random.choice(["success", "error"]),
                "timestamp": "2025-12-09T12:00:00Z"
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Operator-Key": self.operator_key
        }
        self.client.post("/webhook/n8n", json=payload, headers=headers)
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        self.client.get("/health")


class StressTestUser(HttpUser):
    """High-frequency stress testing user."""
    
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.operator_key = f"op_{uuid.uuid4().hex[:16]}"
    
    @task
    def rapid_webhooks(self):
        """Send rapid webhook requests to test system limits."""
        payload = {
            "test": "data",
            "timestamp": "2025-12-09T12:00:00Z"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Operator-Key": self.operator_key
        }
        service = random.choice(["github", "trello", "jira", "n8n"])
        self.client.post(f"/webhook/{service}", json=payload, headers=headers)
