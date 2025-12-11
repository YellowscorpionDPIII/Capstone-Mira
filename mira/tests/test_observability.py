"""Tests for observability features: metrics and health checks."""
import unittest
import time
from mira.core.metrics import MetricsCollector, get_metrics_collector
from mira.core.health import HealthRegistry, get_health_registry


class TestMetricsCollector(unittest.TestCase):
    """Test cases for metrics collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()
    
    def test_counter_increment(self):
        """Test counter metric increments."""
        counter = self.collector.counter('test_counter_total')
        
        counter.inc()
        self.assertEqual(counter.value, 1.0)
        
        counter.inc(5)
        self.assertEqual(counter.value, 6.0)
    
    def test_counter_with_labels(self):
        """Test counter with labels."""
        counter1 = self.collector.counter('test_counter', labels={'service': 'api'})
        counter2 = self.collector.counter('test_counter', labels={'service': 'worker'})
        
        counter1.inc()
        counter2.inc(2)
        
        self.assertEqual(counter1.value, 1.0)
        self.assertEqual(counter2.value, 2.0)
    
    def test_gauge_operations(self):
        """Test gauge metric operations."""
        gauge = self.collector.gauge('test_gauge')
        
        gauge.set(10)
        self.assertEqual(gauge.value, 10.0)
        
        gauge.inc(5)
        self.assertEqual(gauge.value, 15.0)
        
        gauge.dec(3)
        self.assertEqual(gauge.value, 12.0)
    
    def test_timer_observe(self):
        """Test timer metric observations."""
        timer = self.collector.timer('test_duration_seconds')
        
        timer.observe(1.5)
        timer.observe(2.5)
        
        self.assertEqual(timer.count, 2)
        self.assertEqual(timer.total_seconds, 4.0)
        self.assertEqual(timer.average_seconds, 2.0)
    
    def test_timer_context_manager(self):
        """Test timer context manager."""
        with self.collector.time('test_duration_seconds'):
            time.sleep(0.01)  # Sleep for 10ms
        
        timer = self.collector.timer('test_duration_seconds')
        self.assertEqual(timer.count, 1)
        self.assertGreater(timer.total_seconds, 0.01)
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.collector.counter('counter1').inc()
        self.collector.gauge('gauge1').set(42)
        self.collector.timer('timer1').observe(1.0)
        
        metrics = self.collector.get_all_metrics()
        
        self.assertIn('counters', metrics)
        self.assertIn('gauges', metrics)
        self.assertIn('timers', metrics)
        
        self.assertEqual(len(metrics['counters']), 1)
        self.assertEqual(len(metrics['gauges']), 1)
        self.assertEqual(len(metrics['timers']), 1)
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        self.collector.counter('test_counter').inc()
        self.collector.gauge('test_gauge').set(10)
        
        self.collector.reset()
        
        metrics = self.collector.get_all_metrics()
        self.assertEqual(len(metrics['counters']), 0)
        self.assertEqual(len(metrics['gauges']), 0)
        self.assertEqual(len(metrics['timers']), 0)
    
    def test_metric_naming_convention(self):
        """Test that metrics follow naming conventions."""
        # Test recommended naming convention: mira_<component>_<metric>_total
        counter = self.collector.counter('mira_auth_attempts_total')
        self.assertEqual(counter.name, 'mira_auth_attempts_total')
        
        timer = self.collector.timer('mira_webhook_duration_seconds')
        self.assertEqual(timer.name, 'mira_webhook_duration_seconds')
    
    def test_metrics_collector_singleton(self):
        """Test metrics collector singleton pattern."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        self.assertIs(collector1, collector2)


class TestHealthRegistry(unittest.TestCase):
    """Test cases for health registry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = HealthRegistry()
    
    def test_health_check(self):
        """Test basic health check."""
        health = self.registry.check_health()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertIn('timestamp', health)
        self.assertEqual(health['service'], 'mira')
    
    def test_register_dependency(self):
        """Test registering a dependency."""
        def check_database():
            return True
        
        self.registry.register_dependency('database', check_database)
        
        readiness = self.registry.check_readiness()
        
        self.assertIn('database', readiness['dependencies'])
        self.assertTrue(readiness['dependencies']['database']['healthy'])
    
    def test_readiness_with_healthy_dependencies(self):
        """Test readiness check with all healthy dependencies."""
        def check_api():
            return True
        
        def check_cache():
            return True
        
        self.registry.register_dependency('api', check_api)
        self.registry.register_dependency('cache', check_cache)
        
        readiness = self.registry.check_readiness()
        
        self.assertEqual(readiness['status'], 'ready')
        self.assertEqual(len(readiness['dependencies']), 2)
    
    def test_readiness_with_unhealthy_required_dependency(self):
        """Test readiness check with unhealthy required dependency."""
        def check_database():
            return False
        
        self.registry.register_dependency('database', check_database, required=True)
        
        readiness = self.registry.check_readiness()
        
        self.assertEqual(readiness['status'], 'not_ready')
        self.assertFalse(readiness['dependencies']['database']['healthy'])
    
    def test_readiness_with_unhealthy_optional_dependency(self):
        """Test readiness check with unhealthy optional dependency."""
        def check_cache():
            return False
        
        self.registry.register_dependency('cache', check_cache, required=False)
        
        readiness = self.registry.check_readiness()
        
        # Should still be ready since cache is optional
        self.assertEqual(readiness['status'], 'ready')
        self.assertFalse(readiness['dependencies']['cache']['healthy'])
    
    def test_dependency_check_error_handling(self):
        """Test error handling in dependency checks."""
        def failing_check():
            raise Exception("Connection failed")
        
        self.registry.register_dependency('failing_service', failing_check, required=True)
        
        readiness = self.registry.check_readiness()
        
        self.assertEqual(readiness['status'], 'not_ready')
        self.assertIn('error', readiness['dependencies']['failing_service'])
    
    def test_unregister_dependency(self):
        """Test unregistering a dependency."""
        def check_api():
            return True
        
        self.registry.register_dependency('api', check_api)
        result = self.registry.unregister_dependency('api')
        
        self.assertTrue(result)
        
        readiness = self.registry.check_readiness()
        self.assertNotIn('api', readiness['dependencies'])
    
    def test_get_dependency_status(self):
        """Test getting status of a specific dependency."""
        def check_database():
            return True
        
        self.registry.register_dependency('database', check_database)
        
        status = self.registry.get_dependency_status('database')
        
        self.assertIsNotNone(status)
        self.assertEqual(status['name'], 'database')
        self.assertTrue(status['healthy'])
    
    def test_get_nonexistent_dependency_status(self):
        """Test getting status of non-existent dependency."""
        status = self.registry.get_dependency_status('nonexistent')
        self.assertIsNone(status)
    
    def test_health_registry_singleton(self):
        """Test health registry singleton pattern."""
        registry1 = get_health_registry()
        registry2 = get_health_registry()
        self.assertIs(registry1, registry2)


class TestMetricsInErrorScenarios(unittest.TestCase):
    """Test that metrics are captured in both success and error scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()
    
    def test_metrics_in_try_finally(self):
        """Test metrics captured in try-finally blocks."""
        counter = self.collector.counter('operations_total')
        
        with self.assertRaises(Exception):
            try:
                counter.inc()
                raise Exception("Test error")
            finally:
                # Ensure metric was captured even with exception
                self.assertEqual(counter.value, 1.0)
    
    def test_timer_in_error_scenario(self):
        """Test timer captures duration even when exception occurs."""
        try:
            with self.collector.time('operation_duration_seconds'):
                time.sleep(0.01)
                raise Exception("Test error")
        except Exception:
            pass
        
        timer = self.collector.timer('operation_duration_seconds')
        self.assertEqual(timer.count, 1)
        self.assertGreater(timer.total_seconds, 0)


if __name__ == '__main__':
    unittest.main()
