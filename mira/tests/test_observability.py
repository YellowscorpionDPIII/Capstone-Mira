"""Tests for observability features."""
import unittest
import time
from mira.observability.metrics import MetricsCollector, get_metrics
from mira.observability.health import HealthCheck, check_airtable_connection, check_broker_status


class TestMetricsCollector(unittest.TestCase):
    """Test cases for Metrics Collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = MetricsCollector(enabled=True)
        
    def tearDown(self):
        """Clean up after tests."""
        self.metrics.reset()
        
    def test_increment_counter(self):
        """Test incrementing a counter."""
        self.metrics.increment('test.counter')
        self.metrics.increment('test.counter', value=2)
        
        value = self.metrics.get_counter('test.counter')
        self.assertEqual(value, 3)
        
    def test_increment_counter_with_tags(self):
        """Test counter with tags."""
        self.metrics.increment('test.counter', tags={'service': 'github'})
        self.metrics.increment('test.counter', tags={'service': 'trello'})
        
        github_count = self.metrics.get_counter('test.counter', tags={'service': 'github'})
        trello_count = self.metrics.get_counter('test.counter', tags={'service': 'trello'})
        
        self.assertEqual(github_count, 1)
        self.assertEqual(trello_count, 1)
        
    def test_gauge(self):
        """Test setting a gauge."""
        self.metrics.gauge('test.gauge', 42.5)
        
        value = self.metrics.get_gauge('test.gauge')
        self.assertEqual(value, 42.5)
        
        # Update gauge
        self.metrics.gauge('test.gauge', 50.0)
        value = self.metrics.get_gauge('test.gauge')
        self.assertEqual(value, 50.0)
        
    def test_timing(self):
        """Test recording timing."""
        self.metrics.timing('test.operation', 100.5)
        self.metrics.timing('test.operation', 200.3)
        
        stats = self.metrics.get_timer_stats('test.operation')
        
        self.assertEqual(stats['count'], 2)
        self.assertEqual(stats['min'], 100.5)
        self.assertEqual(stats['max'], 200.3)
        self.assertAlmostEqual(stats['avg'], 150.4, places=1)
        
    def test_timer_context_manager(self):
        """Test timer context manager."""
        with self.metrics.timer('test.operation'):
            time.sleep(0.1)  # Sleep for 100ms
        
        stats = self.metrics.get_timer_stats('test.operation')
        
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 100)  # Should be > 100ms
        self.assertLess(stats['avg'], 200)  # Should be < 200ms
        
    def test_disabled_metrics(self):
        """Test that disabled metrics don't collect."""
        metrics = MetricsCollector(enabled=False)
        
        metrics.increment('test.counter')
        metrics.gauge('test.gauge', 42.0)
        metrics.timing('test.timer', 100.0)
        
        # All metrics should be 0 or None
        self.assertEqual(metrics.get_counter('test.counter'), 0)
        self.assertIsNone(metrics.get_gauge('test.gauge'))
        self.assertEqual(metrics.get_timer_stats('test.timer')['count'], 0)
        
    def test_reset_metrics(self):
        """Test resetting metrics."""
        self.metrics.increment('test.counter')
        self.metrics.gauge('test.gauge', 42.0)
        self.metrics.timing('test.timer', 100.0)
        
        self.metrics.reset()
        
        self.assertEqual(self.metrics.get_counter('test.counter'), 0)
        self.assertIsNone(self.metrics.get_gauge('test.gauge'))
        self.assertEqual(self.metrics.get_timer_stats('test.timer')['count'], 0)
        
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.metrics.increment('test.counter')
        self.metrics.gauge('test.gauge', 42.0)
        self.metrics.timing('test.timer', 100.0)
        
        all_metrics = self.metrics.get_all_metrics()
        
        self.assertIn('timestamp', all_metrics)
        self.assertIn('counters', all_metrics)
        self.assertIn('gauges', all_metrics)
        self.assertIn('timers', all_metrics)
        
        self.assertEqual(all_metrics['counters']['test.counter'], 1)
        self.assertEqual(all_metrics['gauges']['test.gauge'], 42.0)


class TestHealthCheck(unittest.TestCase):
    """Test cases for Health Check."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.health = HealthCheck()
        
    def test_check_health(self):
        """Test basic health check."""
        result = self.health.check_health()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('timestamp', result)
        self.assertIn('uptime_seconds', result)
        self.assertGreaterEqual(result['uptime_seconds'], 0)
        
    def test_check_ready_no_dependencies(self):
        """Test readiness check with no dependencies."""
        result = self.health.check_ready()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('timestamp', result)
        self.assertIn('dependencies', result)
        self.assertEqual(len(result['dependencies']), 0)
        
    def test_check_ready_with_healthy_dependency(self):
        """Test readiness check with healthy dependency."""
        def healthy_check():
            return True, "Service is healthy"
        
        self.health.register_dependency('test_service', healthy_check)
        result = self.health.check_ready()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('test_service', result['dependencies'])
        self.assertEqual(result['dependencies']['test_service']['status'], 'healthy')
        
    def test_check_ready_with_unhealthy_dependency(self):
        """Test readiness check with unhealthy dependency."""
        def unhealthy_check():
            return False, "Service is down"
        
        self.health.register_dependency('test_service', unhealthy_check)
        result = self.health.check_ready()
        
        self.assertEqual(result['status'], 'unhealthy')
        self.assertIn('test_service', result['dependencies'])
        self.assertEqual(result['dependencies']['test_service']['status'], 'unhealthy')
        
    def test_check_ready_with_failing_dependency(self):
        """Test readiness check with failing check function."""
        def failing_check():
            raise Exception("Check failed")
        
        self.health.register_dependency('test_service', failing_check)
        result = self.health.check_ready()
        
        self.assertEqual(result['status'], 'unhealthy')
        self.assertIn('test_service', result['dependencies'])
        self.assertEqual(result['dependencies']['test_service']['status'], 'unhealthy')
        self.assertIn('Check failed', result['dependencies']['test_service']['message'])
        
    def test_check_ready_degraded(self):
        """Test readiness check with degraded service."""
        def degraded_check():
            return False, "Service degraded - running slowly"
        
        self.health.register_dependency('test_service', degraded_check)
        result = self.health.check_ready()
        
        self.assertEqual(result['status'], 'degraded')
        
    def test_check_airtable_connection_not_configured(self):
        """Test Airtable check when not configured."""
        is_healthy, message = check_airtable_connection()
        
        self.assertTrue(is_healthy)
        self.assertIn('not configured', message.lower())
        
    def test_check_airtable_connection_configured(self):
        """Test Airtable check when configured."""
        is_healthy, message = check_airtable_connection(
            api_key='test_key',
            base_id='test_base'
        )
        
        self.assertTrue(is_healthy)
        self.assertIn('healthy', message.lower())
        
    def test_check_broker_status_not_initialized(self):
        """Test broker check when not initialized."""
        is_healthy, message = check_broker_status(None)
        
        self.assertFalse(is_healthy)
        self.assertIn('not initialized', message.lower())
        
    def test_check_broker_status_running(self):
        """Test broker check when running."""
        # Mock broker
        class MockBroker:
            running = True
        
        broker = MockBroker()
        is_healthy, message = check_broker_status(broker)
        
        self.assertTrue(is_healthy)
        self.assertIn('running', message.lower())
        
    def test_check_broker_status_not_running(self):
        """Test broker check when not running."""
        class MockBroker:
            running = False
        
        broker = MockBroker()
        is_healthy, message = check_broker_status(broker)
        
        self.assertFalse(is_healthy)
        self.assertIn('not running', message.lower())


if __name__ == '__main__':
    unittest.main()
