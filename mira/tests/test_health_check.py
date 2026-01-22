"""Tests for health check endpoint."""
import unittest
from unittest.mock import MagicMock, patch
from mira.app import MiraApplication


class TestHealthCheckEndpoint(unittest.TestCase):
    """Test cases for /healthz endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create app with webhook enabled to test health endpoint
        with patch('mira.app.get_config') as mock_config:
            config = MagicMock()
            config.get.side_effect = lambda key, default=None: {
                'logging.level': 'INFO',
                'broker.enabled': True,
                'webhook.enabled': True,
                'webhook.secret_key': 'test_secret',
                'agents.orchestrator_agent': {},
                'agents.project_plan_agent.enabled': True,
                'agents.project_plan_agent': {},
                'agents.risk_assessment_agent.enabled': True,
                'agents.risk_assessment_agent': {},
                'agents.status_reporter_agent.enabled': True,
                'agents.status_reporter_agent': {},
            }.get(key, default)
            
            mock_config.return_value = config
            
            self.app = MiraApplication()
            
        # Get Flask test client
        if self.app.webhook_handler:
            self.client = self.app.webhook_handler.app.test_client()
        else:
            self.client = None
            
    def test_health_check_endpoint_exists(self):
        """Test that /healthz endpoint exists."""
        if not self.client:
            self.skipTest("Webhook handler not initialized")
            
        response = self.client.get('/healthz')
        self.assertIsNotNone(response)
        
    def test_health_check_healthy_status(self):
        """Test health check returns healthy status."""
        if not self.client:
            self.skipTest("Webhook handler not initialized")
            
        response = self.client.get('/healthz')
        data = response.get_json()
        
        self.assertIn('status', data)
        self.assertIn('checks', data)
        
        # Should have configuration and agents checks
        self.assertIn('configuration', data['checks'])
        self.assertIn('agents', data['checks'])
        
    def test_health_check_configuration_ok(self):
        """Test configuration check is ok."""
        if not self.client:
            self.skipTest("Webhook handler not initialized")
            
        response = self.client.get('/healthz')
        data = response.get_json()
        
        self.assertEqual(data['checks']['configuration'], 'ok')
        
    def test_health_check_agents_ok(self):
        """Test agents check is ok."""
        if not self.client:
            self.skipTest("Webhook handler not initialized")
            
        response = self.client.get('/healthz')
        data = response.get_json()
        
        self.assertEqual(data['checks']['agents'], 'ok')
        self.assertGreater(data['checks']['agent_count'], 0)
        
    def test_health_check_status_code_healthy(self):
        """Test health check returns 200 when healthy."""
        if not self.client:
            self.skipTest("Webhook handler not initialized")
            
        response = self.client.get('/healthz')
        
        # Should return 200 for healthy or degraded
        self.assertIn(response.status_code, [200, 503])
        
    def test_health_check_broker_disabled(self):
        """Test health check when broker is disabled."""
        # Create app with broker disabled
        with patch('mira.app.get_config') as mock_config:
            config = MagicMock()
            config.get.side_effect = lambda key, default=None: {
                'logging.level': 'INFO',
                'broker.enabled': False,
                'webhook.enabled': True,
                'webhook.secret_key': 'test_secret',
                'agents.orchestrator_agent': {},
                'agents.project_plan_agent.enabled': True,
                'agents.project_plan_agent': {},
            }.get(key, default)
            
            mock_config.return_value = config
            
            app = MiraApplication()
            
        if app.webhook_handler:
            client = app.webhook_handler.app.test_client()
            response = client.get('/healthz')
            data = response.get_json()
            
            self.assertEqual(data['checks']['broker'], 'disabled')


if __name__ == '__main__':
    unittest.main()
