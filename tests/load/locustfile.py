"""Locust load testing for Mira API Key Management System.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:5000

Or with specific users and spawn rate:
    locust -f tests/load/locustfile.py --host=http://localhost:5000 --users 100 --spawn-rate 10

For headless mode:
    locust -f tests/load/locustfile.py --host=http://localhost:5000 --headless --users 100 --spawn-rate 10 --run-time 5m
"""

from locust import HttpUser, task, between, events
import json
import random
import time
from typing import Dict, List


class APIKeyTestData:
    """Test data manager for load testing."""
    
    def __init__(self):
        self.admin_keys: List[str] = []
        self.operator_keys: List[str] = []
        self.viewer_keys: List[str] = []
        self.all_keys: List[Dict] = []
    
    def add_key(self, api_key: str, role: str, key_id: str):
        """Add a test key."""
        self.all_keys.append({'key': api_key, 'role': role, 'id': key_id})
        if role == 'admin':
            self.admin_keys.append(api_key)
        elif role == 'operator':
            self.operator_keys.append(api_key)
        elif role == 'viewer':
            self.viewer_keys.append(api_key)
    
    def get_random_key(self, role: str = None) -> str:
        """Get a random API key, optionally filtered by role."""
        if role == 'admin' and self.admin_keys:
            return random.choice(self.admin_keys)
        elif role == 'operator' and self.operator_keys:
            return random.choice(self.operator_keys)
        elif role == 'viewer' and self.viewer_keys:
            return random.choice(self.viewer_keys)
        elif self.all_keys:
            return random.choice(self.all_keys)['key']
        return None
    
    def get_random_key_id(self) -> str:
        """Get a random key ID."""
        if self.all_keys:
            return random.choice(self.all_keys)['id']
        return None


# Global test data
test_data = APIKeyTestData()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup test data before load test starts."""
    print("Setting up test data...")
    
    # Generate initial API keys for testing
    roles = ['admin', 'operator', 'viewer']
    for i in range(10):  # Generate 10 keys per role
        for role in roles:
            test_key = f"test_{role}_key_{i}_{int(time.time())}"
            test_id = f"test_{role}_id_{i}"
            test_data.add_key(test_key, role, test_id)
    
    print(f"Test data ready: {len(test_data.all_keys)} API keys")


class APIKeyUser(HttpUser):
    """Simulates a user interacting with the API Key Management system."""
    
    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.api_key = test_data.get_random_key()
        if not self.api_key:
            # For simplicity in load testing, just use a pre-generated key
            self.api_key = "test_key_placeholder"
    
    @task(10)
    def validate_key(self):
        """Validate an API key - most common operation."""
        if not self.api_key:
            return
        
        headers = {'Authorization': f'Bearer {self.api_key}'}
        with self.client.post(
            "/webhook/health",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Validation failed: {response.status_code}")
    
    @task(5)
    def list_keys(self):
        """List API keys."""
        admin_key = test_data.get_random_key('admin')
        if not admin_key:
            return
        
        headers = {'Authorization': f'Bearer {admin_key}'}
        with self.client.get(
            "/api/keys",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"List failed: {response.status_code}")
    
    @task(3)
    def health_check(self):
        """Check system health."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
