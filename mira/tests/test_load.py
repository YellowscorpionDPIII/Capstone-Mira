"""Load testing for Mira platform."""
import time
import unittest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent


class LoadTestCase(unittest.TestCase):
    """Load testing test cases for Mira platform."""
    
    # Load testing thresholds
    MAX_RESPONSE_TIME_MS = 1000  # Maximum acceptable response time in milliseconds
    MAX_ERROR_RATE = 0.05  # Maximum acceptable error rate (5%)
    CONCURRENT_USERS = 10  # Number of concurrent users to simulate
    REQUESTS_PER_USER = 5  # Number of requests per user
    
    def setUp(self):
        """Set up test environment."""
        self.project_agent = ProjectPlanAgent()
        self.risk_agent = RiskAssessmentAgent()
        
    def test_concurrent_message_processing(self):
        """Test system stability under concurrent message processing load."""
        total_requests = self.CONCURRENT_USERS * self.REQUESTS_PER_USER
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        def process_single_request(user_id, request_id):
            """Process a single request and measure response time."""
            start_time = time.time()
            try:
                response = self.project_agent.process({
                    'type': 'generate_plan',
                    'data': {
                        'name': f'Load Test Project {user_id}-{request_id}',
                        'goals': ['Goal 1', 'Goal 2'],
                        'duration_weeks': 4
                    }
                })
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                # Verify response structure
                self.assertIn('status', response)
                self.assertIn('data', response)
                
                return {
                    'success': True,
                    'response_time': response_time_ms,
                    'user_id': user_id,
                    'request_id': request_id
                }
            except Exception as e:
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                return {
                    'success': False,
                    'response_time': response_time_ms,
                    'error': str(e),
                    'user_id': user_id,
                    'request_id': request_id
                }
        
        # Execute load test with concurrent users
        with ThreadPoolExecutor(max_workers=self.CONCURRENT_USERS) as executor:
            futures = []
            for user_id in range(self.CONCURRENT_USERS):
                for request_id in range(self.REQUESTS_PER_USER):
                    future = executor.submit(process_single_request, user_id, request_id)
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                response_times.append(result['response_time'])
                
                if result['success']:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    print(f"Failed request - User: {result['user_id']}, "
                          f"Request: {result['request_id']}, "
                          f"Error: {result.get('error', 'Unknown')}")
        
        # Calculate metrics
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        # Print load test results
        print(f"\n{'='*60}")
        print(f"LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        print(f"Error Rate: {error_rate:.2%}")
        print(f"Avg Response Time: {avg_response_time:.2f}ms")
        print(f"Min Response Time: {min_response_time:.2f}ms")
        print(f"Max Response Time: {max_response_time:.2f}ms")
        print(f"{'='*60}")
        
        # Assert thresholds
        self.assertLessEqual(
            error_rate,
            self.MAX_ERROR_RATE,
            f"Error rate {error_rate:.2%} exceeds threshold {self.MAX_ERROR_RATE:.2%}"
        )
        
        self.assertLessEqual(
            max_response_time,
            self.MAX_RESPONSE_TIME_MS,
            f"Max response time {max_response_time:.2f}ms exceeds threshold {self.MAX_RESPONSE_TIME_MS}ms"
        )
        
    def test_sustained_load(self):
        """Test system stability under sustained load."""
        duration_seconds = 5  # Run for 5 seconds
        start_time = time.time()
        request_count = 0
        error_count = 0
        response_times = []
        
        while time.time() - start_time < duration_seconds:
            request_start = time.time()
            try:
                response = self.risk_agent.process({
                    'type': 'assess_risks',
                    'data': {
                        'project_plan': {
                            'name': f'Sustained Load Test {request_count}',
                            'tasks': ['Task 1', 'Task 2']
                        }
                    }
                })
                request_end = time.time()
                response_times.append((request_end - request_start) * 1000)
                request_count += 1
                
                # Verify response
                self.assertIn('status', response)
                self.assertIn('data', response)
                
            except Exception as e:
                error_count += 1
                print(f"Error in sustained load test: {str(e)}")
        
        # Calculate metrics
        error_rate = error_count / request_count if request_count > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        print(f"\n{'='*60}")
        print(f"SUSTAINED LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"Duration: {duration_seconds}s")
        print(f"Total Requests: {request_count}")
        print(f"Errors: {error_count}")
        print(f"Error Rate: {error_rate:.2%}")
        print(f"Avg Response Time: {avg_response_time:.2f}ms")
        print(f"Requests per Second: {request_count / duration_seconds:.2f}")
        print(f"{'='*60}")
        
        # Assert thresholds
        self.assertLessEqual(
            error_rate,
            self.MAX_ERROR_RATE,
            f"Error rate {error_rate:.2%} exceeds threshold {self.MAX_ERROR_RATE:.2%}"
        )
        
        self.assertGreater(
            request_count,
            0,
            "No requests were processed during sustained load test"
        )


if __name__ == '__main__':
    unittest.main()
