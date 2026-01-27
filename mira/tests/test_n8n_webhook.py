"""Unit tests for n8n integration and enhanced webhook handler."""
import unittest
import time
from mira.integrations.n8n_integration import N8nIntegration
from mira.core.webhook_handler import WebhookHandler, RateLimiter


class TestN8nIntegration(unittest.TestCase):
    """Test n8n integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        config = {
            'webhook_url': 'https://n8n.example.com/webhook',
            'api_key': 'test_key'
        }
        n8n = N8nIntegration(config)
        self.assertTrue(n8n.connect())
        self.assertTrue(n8n.connected)
    
    def test_connect_without_config(self):
        """Test connection fails without configuration."""
        n8n = N8nIntegration()
        self.assertFalse(n8n.connect())
    
    def test_trigger_workflow(self):
        """Test triggering a workflow."""
        config = {'webhook_url': 'https://n8n.example.com/webhook'}
        n8n = N8nIntegration(config)
        n8n.connect()
        
        result = n8n.trigger_workflow('workflow_123', {'data': 'test'})
        self.assertTrue(result['success'])
        self.assertEqual(result['workflow_id'], 'workflow_123')
    
    def test_get_execution_status(self):
        """Test getting execution status."""
        config = {'webhook_url': 'https://n8n.example.com/webhook'}
        n8n = N8nIntegration(config)
        n8n.connect()
        
        result = n8n.get_execution_status('exec_123')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'success')
    
    def test_sync_project_events(self):
        """Test syncing project events."""
        config = {'webhook_url': 'https://n8n.example.com/webhook'}
        n8n = N8nIntegration(config)
        n8n.connect()
        
        result = n8n.sync_data('project_events', {
            'events': [
                {'type': 'project_created', 'name': 'Test Project'},
                {'type': 'milestone_completed', 'milestone': 'M1'}
            ]
        })
        self.assertTrue(result['success'])
        self.assertEqual(result['synced'], 2)
    
    def test_sync_task_updates(self):
        """Test syncing task updates."""
        config = {'webhook_url': 'https://n8n.example.com/webhook'}
        n8n = N8nIntegration(config)
        n8n.connect()
        
        result = n8n.sync_data('task_updates', {
            'tasks': [
                {'id': 'T1', 'status': 'completed'},
                {'id': 'T2', 'status': 'in_progress'}
            ]
        })
        self.assertTrue(result['success'])
        self.assertEqual(result['synced'], 2)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter."""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        
        # First 5 requests should be allowed
        for i in range(5):
            self.assertTrue(limiter.is_allowed('client1'))
        
        # 6th request should be denied
        self.assertFalse(limiter.is_allowed('client1'))
    
    def test_rate_limit_window_reset(self):
        """Test rate limit window reset."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up the limit
        self.assertTrue(limiter.is_allowed('client1'))
        self.assertTrue(limiter.is_allowed('client1'))
        self.assertFalse(limiter.is_allowed('client1'))
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        self.assertTrue(limiter.is_allowed('client1'))
    
    def test_per_client_limits(self):
        """Test per-client rate limiting."""
        limiter = RateLimiter(max_requests=2, window_seconds=10)
        
        # Client 1 uses up limit
        self.assertTrue(limiter.is_allowed('client1'))
        self.assertTrue(limiter.is_allowed('client1'))
        self.assertFalse(limiter.is_allowed('client1'))
        
        # Client 2 should still be allowed
        self.assertTrue(limiter.is_allowed('client2'))
        self.assertTrue(limiter.is_allowed('client2'))
    
    def test_get_stats(self):
        """Test getting rate limit statistics."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        # Make some requests
        for i in range(3):
            limiter.is_allowed('client1')
        
        stats = limiter.get_stats('client1')
        self.assertEqual(stats['current_count'], 3)
        self.assertEqual(stats['max_requests'], 10)
        self.assertEqual(stats['remaining'], 7)


class TestEnhancedWebhookHandler(unittest.TestCase):
    """Test enhanced webhook handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = WebhookHandler(rate_limit_enabled=True)
        
        def mock_handler(data):
            return {'status': 'ok', 'data': data}
        
        self.handler.register_handler('test', mock_handler)
    
    def test_metrics_initialization(self):
        """Test metrics are initialized."""
        metrics = self.handler.get_metrics()
        self.assertEqual(metrics['total_requests'], 0)
        self.assertEqual(metrics['successful_requests'], 0)
        self.assertEqual(metrics['failed_requests'], 0)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        with self.handler.app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'healthy')
            self.assertEqual(data['service'], 'mira-webhook')
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        with self.handler.app.test_client() as client:
            response = client.get('/metrics')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('total_requests', data)
            self.assertIn('rate_limit', data)
    
    def test_successful_webhook_request(self):
        """Test successful webhook request updates metrics."""
        with self.handler.app.test_client() as client:
            response = client.post('/webhook/test',
                                   json={'test': 'data'},
                                   content_type='application/json')
            self.assertEqual(response.status_code, 200)
        
        metrics = self.handler.get_metrics()
        self.assertEqual(metrics['total_requests'], 1)
        self.assertEqual(metrics['successful_requests'], 1)
    
    def test_rate_limiting(self):
        """Test rate limiting for high volume."""
        # Create handler with low limit for testing
        handler = WebhookHandler(rate_limit_enabled=True)
        handler.rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        def mock_handler(data):
            return {'status': 'ok'}
        
        handler.register_handler('test', mock_handler)
        
        with handler.app.test_client() as client:
            # Make requests up to limit
            for i in range(5):
                response = client.post('/webhook/test',
                                      json={'test': 'data'},
                                      content_type='application/json')
                self.assertEqual(response.status_code, 200)
            
            # Next request should be rate limited
            response = client.post('/webhook/test',
                                  json={'test': 'data'},
                                  content_type='application/json')
            self.assertEqual(response.status_code, 429)
    
    def test_n8n_webhook_handler(self):
        """Test n8n webhook handler registration."""
        def n8n_handler(data):
            return {'status': 'processed', 'service': 'n8n'}
        
        self.handler.register_handler('n8n', n8n_handler)
        
        with self.handler.app.test_client() as client:
            response = client.post('/webhook/n8n',
                                   json={'workflow_type': 'test'},
                                   content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['service'], 'n8n')


class TestWebhookSLA(unittest.TestCase):
    """Test webhook SLA compliance."""
    
    def test_99_9_percent_uptime_simulation(self):
        """Simulate 10k webhooks and verify 99.9% success rate."""
        handler = WebhookHandler(rate_limit_enabled=True)
        handler.rate_limiter = RateLimiter(max_requests=10000, window_seconds=86400)
        
        def mock_handler(data):
            return {'status': 'ok'}
        
        handler.register_handler('n8n', mock_handler)
        
        with handler.app.test_client() as client:
            # Simulate subset of daily load (100 requests for test speed)
            for i in range(100):
                response = client.post('/webhook/n8n',
                                      json={'request': i},
                                      content_type='application/json')
                # Should succeed
                self.assertIn(response.status_code, [200])
        
        metrics = handler.get_metrics()
        # Success rate should be 100% for normal operation
        self.assertGreaterEqual(metrics['success_rate'], 99.9,
                               'Should meet 99.9% SLA target')
        self.assertTrue(metrics['uptime_compliance'],
                       'Should indicate SLA compliance')


if __name__ == '__main__':
    unittest.main()
