"""
Locust performance testing file for Mira platform.

This file benchmarks the system to handle traffic scenarios targeting:
- $50k-$5M revenue-range targets
- 1,000+ requests/min capacity

Usage:
    locust -f locustfile.py --host=http://localhost:5000
    
    Or with web UI:
    locust -f locustfile.py --host=http://localhost:5000 --web-host=0.0.0.0

    Headless mode for CI:
    locust -f locustfile.py --host=http://localhost:5000 --headless \
           --users 100 --spawn-rate 10 --run-time 5m
"""

from locust import HttpUser, task, between, events
import random
import time
from datetime import datetime


class MiraUser(HttpUser):
    """Simulates a user interacting with the Mira platform."""
    
    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a user starts. Used for setup/login."""
        self.project_id = None
        self.agent_id = None
        
    @task(5)
    def generate_project_plan(self):
        """Generate a project plan - High frequency task."""
        payload = {
            "type": "generate_plan",
            "data": {
                "name": f"Project-{random.randint(1000, 9999)}",
                "goals": [
                    f"Goal {i}" for i in range(random.randint(2, 5))
                ],
                "duration_weeks": random.randint(8, 24)
            }
        }
        
        with self.client.post(
            "/api/message",
            json=payload,
            catch_response=True,
            name="Generate Project Plan"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "data" in data:
                        self.project_id = data.get("data", {}).get("id")
                        response.success()
                    else:
                        response.failure("No data in response")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(4)
    def assess_risks(self):
        """Assess project risks - Medium-high frequency task."""
        # Randomize project descriptions for more realistic testing
        descriptions = [
            "Project with tight deadline and new technology",
            "Complex integration with multiple external dependencies",
            "Limited resources and aggressive schedule",
            "High-priority initiative with executive visibility",
            "Experimental technology with learning curve",
            "Cross-functional team coordination required"
        ]
        
        payload = {
            "type": "assess_risks",
            "data": {
                "name": f"Risk-Assessment-{random.randint(1000, 9999)}",
                "description": random.choice(descriptions),
                "tasks": [f"Task {i}" for i in range(random.randint(10, 30))],
                "duration_weeks": random.randint(8, 16)
            }
        }
        
        with self.client.post(
            "/api/message",
            json=payload,
            catch_response=True,
            name="Assess Risks"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def generate_status_report(self):
        """Generate weekly status report - Medium frequency task."""
        payload = {
            "type": "generate_status",
            "data": {
                "project_id": self.project_id or f"project-{random.randint(1000, 9999)}",
                "completed_tasks": random.randint(5, 20),
                "total_tasks": random.randint(20, 50),
                "blockers": []
            }
        }
        
        with self.client.post(
            "/api/message",
            json=payload,
            catch_response=True,
            name="Generate Status Report"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def orchestrate_workflow(self):
        """Execute orchestrated workflow - Lower frequency task."""
        payload = {
            "type": "orchestrate",
            "data": {
                "workflow": "project_initialization",
                "project_name": f"Orchestrated-{random.randint(1000, 9999)}",
                "goals": ["Complete planning", "Assess risks"],
                "duration_weeks": 12
            }
        }
        
        with self.client.post(
            "/api/message",
            json=payload,
            catch_response=True,
            name="Orchestrate Workflow"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Health check endpoint - Low frequency monitoring."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class HighVolumeUser(HttpUser):
    """Simulates high-volume API usage for revenue stress testing."""
    
    wait_time = between(0.1, 0.5)  # Much faster requests
    
    @task(10)
    def rapid_fire_requests(self):
        """Rapid API requests simulating high revenue traffic."""
        # Randomize project names and data for more realistic testing
        project_names = ["QuickPlan", "FastTrack", "RapidDeploy", "ExpressProject", "SpeedRun"]
        risk_names = ["QuickRisk", "FastAssess", "RapidCheck", "SpeedAnalysis", "ExpressRisk"]
        
        endpoints = [
            ("/api/message", {
                "type": "generate_plan", 
                "data": {
                    "name": f"{random.choice(project_names)}-{random.randint(100, 999)}", 
                    "goals": [f"Goal{i}" for i in range(random.randint(1, 3))], 
                    "duration_weeks": random.choice([4, 8, 12])
                }
            }),
            ("/api/message", {
                "type": "assess_risks", 
                "data": {
                    "name": f"{random.choice(risk_names)}-{random.randint(100, 999)}", 
                    "description": random.choice(["urgent", "critical", "high-priority"]), 
                    "tasks": [f"T{i}" for i in range(random.randint(5, 15))], 
                    "duration_weeks": random.choice([4, 8])
                }
            }),
            ("/health", None)
        ]
        
        endpoint, payload = random.choice(endpoints)
        
        if payload:
            self.client.post(endpoint, json=payload, name="High Volume Request")
        else:
            self.client.get(endpoint, name="High Volume Request")


# Event handlers for custom metrics and logging
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print(f"\n{'='*60}")
    print(f"Mira Performance Test Started")
    print(f"Target: 1,000+ requests/min capacity")
    print(f"Revenue Range: $50k-$5M simulation")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print(f"\n{'='*60}")
    print(f"Mira Performance Test Completed")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats = environment.stats
    print(f"\nSummary Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Failed Requests: {stats.total.num_failures}")
    print(f"  Median Response Time: {stats.total.median_response_time}ms")
    print(f"  95th Percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    
    # Calculate if target was met (1000 req/min = 16.67 req/sec)
    target_rps = 16.67
    if stats.total.total_rps >= target_rps:
        print(f"\n✓ Target achieved: {stats.total.total_rps:.2f} req/s >= {target_rps} req/s")
    else:
        print(f"\n✗ Target not met: {stats.total.total_rps:.2f} req/s < {target_rps} req/s")
    
    print(f"{'='*60}\n")


# Custom shape for revenue-based load testing
from locust import LoadTestShape

class RevenueTargetShape(LoadTestShape):
    """
    Custom load shape to simulate revenue-based traffic patterns.
    
    Simulates traffic growth from $50k to $5M revenue targets:
    - Low tier ($50k): 10 users, 50 req/min
    - Mid tier ($500k): 50 users, 250 req/min
    - High tier ($2M): 200 users, 1000 req/min
    - Peak tier ($5M): 500 users, 2500 req/min
    """
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},    # $50k tier
        {"duration": 120, "users": 50, "spawn_rate": 5},   # $500k tier
        {"duration": 180, "users": 200, "spawn_rate": 10}, # $2M tier
        {"duration": 240, "users": 500, "spawn_rate": 20}, # $5M tier
        {"duration": 300, "users": 200, "spawn_rate": 10}, # Scale down
    ]
    
    def tick(self):
        """Override to define custom load shape."""
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        
        return None
