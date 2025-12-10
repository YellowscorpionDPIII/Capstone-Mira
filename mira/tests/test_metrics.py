"""Tests for Prometheus metrics integration."""
import unittest
from unittest.mock import patch, MagicMock
import time
from mira.agents.orchestrator_agent import (
    OrchestratorAgent,
    async_timeout_fallbacks_total,
    agent_process_duration_seconds,
    current_concurrent_agents
)
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.core.webhook_handler import WebhookHandler


class TestPrometheusMetrics(unittest.TestCase):
    """Test cases for Prometheus metrics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorAgent()
        
        # Register agents
        self.plan_agent = ProjectPlanAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.status_agent = StatusReporterAgent()
        
        self.orchestrator.register_agent(self.plan_agent)
        self.orchestrator.register_agent(self.risk_agent)
        self.orchestrator.register_agent(self.status_agent)
    
    def test_counter_metric_exists(self):
        """Test that counter metric is properly defined."""
        self.assertIsNotNone(async_timeout_fallbacks_total)
        # Prometheus client automatically strips '_total' suffix from counter names
        self.assertEqual(async_timeout_fallbacks_total._name, 'async_timeout_fallbacks')
    
    def test_histogram_metric_exists(self):
        """Test that histogram metric is properly defined."""
        self.assertIsNotNone(agent_process_duration_seconds)
        self.assertEqual(agent_process_duration_seconds._name, 'agent_process_duration_seconds')
    
    def test_gauge_metric_exists(self):
        """Test that gauge metric is properly defined."""
        self.assertIsNotNone(current_concurrent_agents)
        self.assertEqual(current_concurrent_agents._name, 'current_concurrent_agents')
    
    def test_gauge_increments_and_decrements(self):
        """Test that gauge properly tracks concurrent operations."""
        initial_value = current_concurrent_agents._value._value
        
        # Process multiple messages
        for i in range(3):
            message = {
                'type': 'generate_plan',
                'data': {
                    'name': f'Project {i}',
                    'goals': ['Goal 1'],
                    'duration_weeks': 4
                }
            }
            response = self.orchestrator.process(message)
            self.assertEqual(response['status'], 'success')
        
        # Gauge should return to initial value after all processing
        final_value = current_concurrent_agents._value._value
        self.assertEqual(initial_value, final_value)
    
    def test_histogram_records_duration(self):
        """Test that histogram records processing durations."""
        # Get initial sample count
        metric_before = agent_process_duration_seconds.labels(
            agent_type='plan_generator',
            fallback_mode='sync'
        )
        
        # Collect the metric to get samples before
        samples_before = metric_before.collect()[0].samples
        count_before = next((s.value for s in samples_before if s.name.endswith('_count')), 0)
        
        # Process a message
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Test Project',
                'goals': ['Goal 1', 'Goal 2'],
                'duration_weeks': 8
            }
        }
        
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        
        # Get count after
        metric_after = agent_process_duration_seconds.labels(
            agent_type='plan_generator',
            fallback_mode='sync'
        )
        samples_after = metric_after.collect()[0].samples
        count_after = next((s.value for s in samples_after if s.name.endswith('_count')), 0)
        
        # Count should have increased
        self.assertEqual(count_after, count_before + 1)
    
    def test_histogram_records_different_agent_types(self):
        """Test that histogram records durations for different agent types."""
        messages = [
            {
                'type': 'generate_plan',
                'data': {'name': 'Test', 'goals': ['G1'], 'duration_weeks': 4}
            },
            {
                'type': 'assess_risks',
                'data': {'name': 'Test', 'description': 'test', 'tasks': [], 'duration_weeks': 4}
            },
            {
                'type': 'generate_report',
                'data': {'name': 'Test', 'week_number': 1, 'tasks': [], 'milestones': [], 'risks': []}
            }
        ]
        
        for message in messages:
            response = self.orchestrator.process(message)
            self.assertEqual(response['status'], 'success')
        
        # Verify metrics were recorded for each agent type
        # Check that metrics exist for each agent type
        agent_types = ['plan_generator', 'risk_assessor', 'status_reporter']
        
        for agent_type in agent_types:
            metric = agent_process_duration_seconds.labels(
                agent_type=agent_type,
                fallback_mode='sync'
            )
            samples = metric.collect()[0].samples
            count = next((s.value for s in samples if s.name.endswith('_count')), 0)
            self.assertGreater(count, 0, f"No samples recorded for {agent_type}")
    
    def test_agent_type_mapping(self):
        """Test agent type mapping for metrics labels."""
        orchestrator = OrchestratorAgent()
        
        test_cases = [
            ('project_plan_agent', 'plan_generator'),
            ('risk_assessment_agent', 'risk_assessor'),
            ('status_reporter_agent', 'status_reporter'),
            ('roadmapping_agent', 'roadmapper'),
            ('unknown_agent', 'unknown_agent')
        ]
        
        for agent_id, expected_type in test_cases:
            result = orchestrator._get_agent_type(agent_id)
            self.assertEqual(result, expected_type)
    
    def test_concurrent_gauge_with_errors(self):
        """Test that gauge is properly decremented even when errors occur."""
        initial_value = current_concurrent_agents._value._value
        
        # Create orchestrator without registered agents to force error
        orchestrator = OrchestratorAgent()
        orchestrator.add_routing_rule('test_type', 'nonexistent_agent')
        
        message = {
            'type': 'test_type',
            'data': {'name': 'Test'}
        }
        
        response = orchestrator.process(message)
        self.assertEqual(response['status'], 'error')
        
        # Gauge should still be at initial value (no increment since agent not found before increment)
        final_value = current_concurrent_agents._value._value
        self.assertEqual(initial_value, final_value)


class TestMetricsEndpoint(unittest.TestCase):
    """Test cases for /metrics endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.webhook_handler = WebhookHandler(secret_key='test_secret')
        self.client = self.webhook_handler.app.test_client()
    
    def test_metrics_endpoint_exists(self):
        """Test that /metrics endpoint is accessible."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
    
    def test_metrics_endpoint_content_type(self):
        """Test that /metrics endpoint returns correct content type."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        # Prometheus metrics should use text/plain content type
        self.assertIn('text/plain', response.content_type)
    
    def test_metrics_endpoint_contains_metrics(self):
        """Test that /metrics endpoint returns Prometheus metrics."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        
        data = response.data.decode('utf-8')
        
        # Check for our custom metrics
        self.assertIn('async_timeout_fallbacks_total', data)
        self.assertIn('agent_process_duration_seconds', data)
        self.assertIn('current_concurrent_agents', data)
    
    def test_metrics_endpoint_timeout(self):
        """Test that /metrics endpoint responds within timeout."""
        import time
        
        start_time = time.time()
        response = self.client.get('/metrics')
        duration = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        # Should respond well within 30 seconds
        self.assertLess(duration, 30)
    
    def test_metrics_endpoint_after_operations(self):
        """Test that /metrics reflects actual operations."""
        # Set up orchestrator and process some messages
        orchestrator = OrchestratorAgent()
        orchestrator.register_agent(ProjectPlanAgent())
        
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Test Project',
                'goals': ['Goal 1'],
                'duration_weeks': 4
            }
        }
        
        response = orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        
        # Now check metrics endpoint
        metrics_response = self.client.get('/metrics')
        self.assertEqual(metrics_response.status_code, 200)
        
        data = metrics_response.data.decode('utf-8')
        
        # Should contain metrics about the operation we just performed
        self.assertIn('agent_process_duration_seconds', data)
        self.assertIn('plan_generator', data)


if __name__ == '__main__':
    unittest.main()
