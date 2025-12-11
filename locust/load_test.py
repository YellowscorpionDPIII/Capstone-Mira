"""
Locust load test for Mira webhook API.
Simulates n8n webhook traffic at 1000 req/min (16.67 req/sec).

Usage:
    # Run with web UI
    locust -f load_test.py --host=http://localhost:5000

    # Headless mode (1000 req/min = 16.67 req/sec with 10 users)
    locust -f load_test.py --host=http://localhost:5000 \
           --users 10 --spawn-rate 2 --run-time 5m --headless

    # Specific target: 1000 requests per minute
    locust -f load_test.py --host=http://localhost:5000 \
           --users 17 --spawn-rate 5 --run-time 10m --headless
"""

import json
import hmac
import hashlib
import random
import os
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class MiraWebhookUser(HttpUser):
    """
    Simulates n8n webhook requests to Mira API.
    
    Load profile:
    - Wait time: 3.5-4 seconds between requests per user
    - With 17 users: ~16.67 req/sec = 1000 req/min
    """
    
    wait_time = between(3.5, 4)  # Wait 3.5-4 seconds between tasks
    
    def on_start(self):
        """Initialize test user with configuration."""
        self.webhook_secret = os.getenv("MIRA_WEBHOOK_SECRET", "test-secret-key")
        self.service_name = "n8n"
        self.project_names = [
            "Project Alpha", "Project Beta", "Project Gamma",
            "Project Delta", "Project Epsilon", "Project Zeta"
        ]
        self.goals_templates = [
            ["Complete feature X", "Deploy to production", "Get user feedback"],
            ["Improve performance", "Fix critical bugs", "Update documentation"],
            ["Add new integration", "Refactor codebase", "Write tests"],
            ["Design UI", "Implement backend", "Deploy infrastructure"]
        ]
    
    def _generate_signature(self, payload: dict) -> str:
        """Generate HMAC-SHA256 signature for webhook authentication."""
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self, payload: dict) -> dict:
        """Get headers including signature for authenticated request."""
        return {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": self._generate_signature(payload),
            "User-Agent": "n8n-webhook-client/1.0"
        }
    
    @task(5)
    def generate_project_plan(self):
        """
        Simulate n8n workflow triggering project plan generation.
        Weight: 5 (most common operation)
        """
        payload = {
            "type": "generate_plan",
            "data": {
                "name": random.choice(self.project_names),
                "goals": random.choice(self.goals_templates),
                "duration_weeks": random.randint(8, 16)
            }
        }
        
        with self.client.post(
            f"/webhook/{self.service_name}",
            json=payload,
            headers=self._get_headers(payload),
            catch_response=True,
            name="/webhook/n8n [generate_plan]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 403:
                response.failure("Authentication failed")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(3)
    def assess_project_risks(self):
        """
        Simulate n8n workflow triggering risk assessment.
        Weight: 3 (common operation)
        """
        payload = {
            "type": "assess_risks",
            "data": {
                "project_id": f"proj_{random.randint(1000, 9999)}",
                "tasks": [
                    f"Task {i}: " + random.choice([
                        "Database migration",
                        "API integration",
                        "Security audit",
                        "Performance optimization"
                    ])
                    for i in range(random.randint(3, 8))
                ]
            }
        }
        
        with self.client.post(
            f"/webhook/{self.service_name}",
            json=payload,
            headers=self._get_headers(payload),
            catch_response=True,
            name="/webhook/n8n [assess_risks]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def generate_status_report(self):
        """
        Simulate n8n workflow triggering status report generation.
        Weight: 2 (less frequent operation)
        """
        payload = {
            "type": "generate_status",
            "data": {
                "project_id": f"proj_{random.randint(1000, 9999)}",
                "week_number": random.randint(1, 12),
                "completed_tasks": random.randint(5, 20),
                "total_tasks": random.randint(20, 50),
                "blockers": random.randint(0, 3)
            }
        }
        
        with self.client.post(
            f"/webhook/{self.service_name}",
            json=payload,
            headers=self._get_headers(payload),
            catch_response=True,
            name="/webhook/n8n [generate_status]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def orchestrate_workflow(self):
        """
        Simulate n8n workflow triggering multi-agent orchestration.
        Weight: 1 (least frequent but most complex)
        """
        payload = {
            "type": "orchestrate",
            "data": {
                "workflow_type": "full_project_initialization",
                "project_name": random.choice(self.project_names),
                "goals": random.choice(self.goals_templates),
                "duration_weeks": random.randint(8, 16),
                "integrations": random.sample(
                    ["trello", "jira", "github", "airtable"],
                    k=random.randint(1, 3)
                )
            }
        }
        
        with self.client.post(
            f"/webhook/{self.service_name}",
            json=payload,
            headers=self._get_headers(payload),
            catch_response=True,
            name="/webhook/n8n [orchestrate]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """
        Periodic health check to ensure service is responsive.
        Weight: 1 (monitoring)
        """
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Service unhealthy")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Health check failed: {response.status_code}")


class StressTestUser(MiraWebhookUser):
    """
    Stress test user with higher load and more aggressive timing.
    Use this for stress testing beyond normal load.
    """
    wait_time = between(1, 2)  # Faster requests for stress testing


# Event handlers for test reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    print(f"\n{'='*60}")
    print("Starting Mira Webhook Load Test")
    print(f"Target: 1000 req/min (16.67 req/sec)")
    print(f"Host: {environment.host}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test results summary."""
    print(f"\n{'='*60}")
    print("Mira Webhook Load Test Complete")
    print(f"{'='*60}")
    
    # Print statistics if available
    if hasattr(environment, 'stats'):
        stats = environment.stats.total
        print(f"\nTotal Requests: {stats.num_requests}")
        print(f"Total Failures: {stats.num_failures}")
        print(f"Average Response Time: {stats.avg_response_time:.2f}ms")
        print(f"Min Response Time: {stats.min_response_time:.2f}ms")
        print(f"Max Response Time: {stats.max_response_time:.2f}ms")
        print(f"Requests/sec: {stats.total_rps:.2f}")
        
        if stats.num_requests > 0:
            failure_rate = (stats.num_failures / stats.num_requests) * 100
            print(f"Failure Rate: {failure_rate:.2f}%")
            
            # Performance assertions
            if failure_rate > 1.0:
                print("\n⚠️  WARNING: Failure rate exceeds 1%")
            if stats.avg_response_time > 1000:
                print("\n⚠️  WARNING: Average response time exceeds 1000ms")
            if stats.total_rps < 15:
                print("\n⚠️  WARNING: Request rate below target (15 req/sec)")
    
    print(f"{'='*60}\n")


# Custom load shape for specific test scenarios
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    Step load shape to gradually increase load to 1000 req/min.
    
    Steps:
    1. 0-60s: Ramp up to 5 users
    2. 60-120s: Ramp up to 10 users
    3. 120-180s: Ramp up to 17 users (target: 1000 req/min)
    4. 180-480s: Maintain 17 users (5 min sustained load)
    5. 480-540s: Ramp down to 5 users
    """
    
    step_time = 60
    step_load = 5
    spawn_rate = 2
    time_limit = 540  # 9 minutes total
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < self.step_time:
            return (self.step_load, self.spawn_rate)
        elif run_time < self.step_time * 2:
            return (self.step_load * 2, self.spawn_rate)
        elif run_time < self.step_time * 3:
            return (17, self.spawn_rate)  # Target load: 1000 req/min
        elif run_time < self.step_time * 8:
            return (17, self.spawn_rate)  # Sustain target load
        elif run_time < self.time_limit:
            return (self.step_load, self.spawn_rate)  # Ramp down
        
        return None  # Test complete


if __name__ == "__main__":
    """
    Run standalone test with default configuration.
    """
    import subprocess
    import sys
    
    # Default test parameters
    host = os.getenv("MIRA_HOST", "http://localhost:5000")
    users = int(os.getenv("MIRA_LOAD_TEST_USERS", "17"))
    spawn_rate = int(os.getenv("MIRA_LOAD_TEST_SPAWN_RATE", "5"))
    run_time = os.getenv("MIRA_LOAD_TEST_RUNTIME", "5m")
    
    print(f"Running Locust load test:")
    print(f"  Host: {host}")
    print(f"  Users: {users}")
    print(f"  Spawn rate: {spawn_rate}")
    print(f"  Run time: {run_time}")
    print(f"  Target rate: 1000 req/min (16.67 req/sec)\n")
    
    cmd = [
        "locust",
        "-f", __file__,
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
        "--headless"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Load test failed: {e}")
        sys.exit(1)
