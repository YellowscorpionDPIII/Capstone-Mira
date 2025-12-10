"""Tests for metrics collection functionality."""
import unittest
import time
from mira.utils.metrics import (
    MetricsCollector,
    get_metrics_collector,
    record_latency,
    increment_error_counter,
    get_latency_stats,
    get_error_count,
    get_all_metrics,
    reset_metrics,
    timer,
    timed
)


class TestMetricsCollector(unittest.TestCase):
    """Test cases for MetricsCollector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()
        
    def test_record_latency(self):
        """Test recording latency measurements."""
        self.collector.record_latency('test_metric', 0.5)
        self.collector.record_latency('test_metric', 1.0)
        
        stats = self.collector.get_latency_stats('test_metric')
        self.assertEqual(stats['count'], 2)
        self.assertEqual(stats['min'], 0.5)
        self.assertEqual(stats['max'], 1.0)
        self.assertEqual(stats['avg'], 0.75)
        self.assertEqual(stats['sum'], 1.5)
        
    def test_increment_error_counter(self):
        """Test incrementing error counters."""
        self.collector.increment_error_counter('test_errors')
        self.collector.increment_error_counter('test_errors', 2)
        
        count = self.collector.get_error_count('test_errors')
        self.assertEqual(count, 3)
        
    def test_get_latency_stats_empty(self):
        """Test getting stats for non-existent metric."""
        stats = self.collector.get_latency_stats('nonexistent')
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['min'], 0.0)
        self.assertEqual(stats['max'], 0.0)
        self.assertEqual(stats['avg'], 0.0)
        
    def test_get_error_count_empty(self):
        """Test getting count for non-existent counter."""
        count = self.collector.get_error_count('nonexistent')
        self.assertEqual(count, 0)
        
    def test_timer_context_manager(self):
        """Test timer context manager."""
        with self.collector.timer('test_timer'):
            time.sleep(0.1)
            
        stats = self.collector.get_latency_stats('test_timer')
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 0.1)
        self.assertLess(stats['avg'], 0.2)
        
    def test_timed_decorator(self):
        """Test timed decorator."""
        @self.collector.timed('decorated_func')
        def slow_function():
            time.sleep(0.1)
            return 'result'
            
        result = slow_function()
        self.assertEqual(result, 'result')
        
        stats = self.collector.get_latency_stats('decorated_func')
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 0.1)
        
    def test_timed_decorator_no_metric_name(self):
        """Test timed decorator without explicit metric name."""
        @self.collector.timed()
        def my_function():
            time.sleep(0.05)
            return 'done'
            
        result = my_function()
        self.assertEqual(result, 'done')
        
        # Should use module.function_name as metric
        all_metrics = self.collector.get_all_metrics()
        latency_keys = list(all_metrics['latencies'].keys())
        # Check that some metric was recorded
        self.assertGreater(len(latency_keys), 0)
        
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.collector.record_latency('metric1', 0.5)
        self.collector.record_latency('metric2', 1.0)
        self.collector.increment_error_counter('error1')
        self.collector.increment_error_counter('error2', 3)
        
        all_metrics = self.collector.get_all_metrics()
        
        self.assertIn('latencies', all_metrics)
        self.assertIn('errors', all_metrics)
        
        self.assertIn('metric1', all_metrics['latencies'])
        self.assertIn('metric2', all_metrics['latencies'])
        
        self.assertEqual(all_metrics['errors']['error1'], 1)
        self.assertEqual(all_metrics['errors']['error2'], 3)
        
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        self.collector.record_latency('test_metric', 0.5)
        self.collector.increment_error_counter('test_errors')
        
        self.collector.reset_metrics()
        
        stats = self.collector.get_latency_stats('test_metric')
        count = self.collector.get_error_count('test_errors')
        
        self.assertEqual(stats['count'], 0)
        self.assertEqual(count, 0)
        
    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading
        
        def record_metrics():
            for i in range(100):
                self.collector.record_latency('concurrent_metric', 0.01)
                self.collector.increment_error_counter('concurrent_errors')
                
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        stats = self.collector.get_latency_stats('concurrent_metric')
        count = self.collector.get_error_count('concurrent_errors')
        
        self.assertEqual(stats['count'], 500)
        self.assertEqual(count, 500)


class TestGlobalMetricsFunctions(unittest.TestCase):
    """Test cases for global metrics functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        
    def tearDown(self):
        """Clean up after tests."""
        reset_metrics()
        
    def test_record_latency_global(self):
        """Test global record_latency function."""
        record_latency('global_metric', 0.5)
        
        stats = get_latency_stats('global_metric')
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['avg'], 0.5)
        
    def test_increment_error_counter_global(self):
        """Test global increment_error_counter function."""
        increment_error_counter('global_errors', 5)
        
        count = get_error_count('global_errors')
        self.assertEqual(count, 5)
        
    def test_timer_global(self):
        """Test global timer context manager."""
        with timer('global_timer'):
            time.sleep(0.1)
            
        stats = get_latency_stats('global_timer')
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 0.1)
        
    def test_timed_global(self):
        """Test global timed decorator."""
        @timed('global_decorated')
        def test_function():
            time.sleep(0.05)
            return 42
            
        result = test_function()
        self.assertEqual(result, 42)
        
        stats = get_latency_stats('global_decorated')
        self.assertEqual(stats['count'], 1)
        
    def test_get_all_metrics_global(self):
        """Test global get_all_metrics function."""
        record_latency('test1', 0.5)
        increment_error_counter('err1')
        
        all_metrics = get_all_metrics()
        
        self.assertIn('latencies', all_metrics)
        self.assertIn('errors', all_metrics)
        self.assertIn('test1', all_metrics['latencies'])
        self.assertEqual(all_metrics['errors']['err1'], 1)
        
    def test_singleton_behavior(self):
        """Test that get_metrics_collector returns singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        self.assertIs(collector1, collector2)
        
        # Record using one reference
        collector1.record_latency('test', 0.5)
        
        # Should be visible through other reference
        stats = collector2.get_latency_stats('test')
        self.assertEqual(stats['count'], 1)


class TestMetricsIntegration(unittest.TestCase):
    """Integration tests for metrics with agents and broker."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        
    def tearDown(self):
        """Clean up after tests."""
        reset_metrics()
        
    def test_agent_metrics_integration(self):
        """Test metrics collection with BaseAgent."""
        from mira.core.base_agent import BaseAgent
        from typing import Dict, Any
        
        class TestAgent(BaseAgent):
            def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
                time.sleep(0.1)
                return self.create_response('success', {'result': 'ok'})
                
        agent = TestAgent('test_agent')
        message = {'type': 'test', 'data': {}}
        
        # Use process_with_metrics to ensure metrics are collected
        result = agent.process_with_metrics(message)
        
        self.assertEqual(result['status'], 'success')
        
        # Check latency was recorded
        stats = get_latency_stats('agent.test_agent.process')
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 0.1)
        
    def test_agent_error_counter(self):
        """Test error counter with agent errors."""
        from mira.core.base_agent import BaseAgent
        from typing import Dict, Any
        
        class ErrorAgent(BaseAgent):
            def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
                return self.create_response('error', None, 'Test error')
                
        agent = ErrorAgent('error_agent')
        message = {'type': 'test', 'data': {}}
        
        result = agent.process_with_metrics(message)
        
        self.assertEqual(result['status'], 'error')
        
        # Check error counter was incremented
        count = get_error_count('agent.error_agent.errors')
        self.assertEqual(count, 1)
        
    def test_broker_metrics_integration(self):
        """Test metrics collection with MessageBroker."""
        from mira.core.message_broker import MessageBroker
        import time
        
        broker = MessageBroker()
        received = []
        
        def handler(msg):
            received.append(msg)
            
        broker.subscribe('test_event', handler)
        broker.start()
        
        try:
            broker.publish('test_event', {'value': 'test'})
            
            # Give broker time to process
            time.sleep(0.5)
            
            # Check that metrics were recorded
            publish_stats = get_latency_stats('broker.publish')
            process_stats = get_latency_stats('broker.process_message')
            
            self.assertGreater(publish_stats['count'], 0)
            self.assertGreater(process_stats['count'], 0)
        finally:
            broker.stop()


if __name__ == '__main__':
    unittest.main()
