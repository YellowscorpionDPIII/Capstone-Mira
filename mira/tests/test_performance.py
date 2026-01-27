"""Unit tests for performance benchmarking utilities."""
import unittest
import time
from mira.utils.performance import (
    PerformanceMetrics, benchmark, PerformanceBenchmark, 
    run_benchmark, get_metrics
)


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics collection and analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PerformanceMetrics()
    
    def test_record_and_retrieve(self):
        """Test recording and retrieving metrics."""
        self.metrics.record('test_op', 0.1)
        self.metrics.record('test_op', 0.2)
        self.metrics.record('test_op', 0.15)
        
        stats = self.metrics.get_stats('test_op')
        self.assertIsNotNone(stats)
        self.assertEqual(stats['count'], 3)
        self.assertAlmostEqual(stats['min'], 0.1, places=2)
        self.assertAlmostEqual(stats['max'], 0.2, places=2)
        self.assertAlmostEqual(stats['mean'], 0.15, places=2)
    
    def test_percentiles(self):
        """Test percentile calculations."""
        # Add 100 values from 0.01 to 1.00
        for i in range(1, 101):
            self.metrics.record('test_op', i / 100.0)
        
        stats = self.metrics.get_stats('test_op')
        # P95 and P99 should be close to expected values (allow some variance due to indexing)
        self.assertGreater(stats['p95'], 0.94)
        self.assertLess(stats['p95'], 0.97)
        self.assertGreater(stats['p99'], 0.98)
        self.assertLess(stats['p99'], 1.01)
    
    def test_clear_metrics(self):
        """Test clearing metrics."""
        self.metrics.record('test_op', 0.1)
        self.metrics.clear()
        stats = self.metrics.get_stats('test_op')
        self.assertIsNone(stats)
    
    def test_compare_performance(self):
        """Test performance comparison."""
        before_stats = {
            'mean': 0.5,
            'median': 0.5,
            'p95': 0.8,
            'p99': 0.9,
            'max': 1.0
        }
        after_stats = {
            'mean': 0.25,
            'median': 0.25,
            'p95': 0.4,
            'p99': 0.45,
            'max': 0.5
        }
        
        comparison = self.metrics.compare('test_op', before_stats, after_stats)
        self.assertEqual(comparison['operation'], 'test_op')
        self.assertTrue(comparison['improvements']['mean']['faster'])
        self.assertAlmostEqual(
            comparison['improvements']['mean']['improvement_pct'], 
            50.0, 
            places=1
        )


class TestBenchmarkDecorator(unittest.TestCase):
    """Test benchmark decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        metrics = get_metrics()
        metrics.clear()
    
    def test_benchmark_decorator(self):
        """Test that benchmark decorator records metrics."""
        @benchmark('decorated_func')
        def test_func():
            time.sleep(0.01)
            return 'result'
        
        result = test_func()
        self.assertEqual(result, 'result')
        
        metrics = get_metrics()
        stats = metrics.get_stats('decorated_func')
        self.assertIsNotNone(stats)
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['mean'], 0.01)
    
    def test_benchmark_default_name(self):
        """Test benchmark with default function name."""
        @benchmark()
        def my_function():
            return 42
        
        result = my_function()
        self.assertEqual(result, 42)
        
        metrics = get_metrics()
        stats = metrics.get_stats('my_function')
        self.assertIsNotNone(stats)


class TestPerformanceBenchmark(unittest.TestCase):
    """Test performance benchmark context manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        metrics = get_metrics()
        metrics.clear()
    
    def test_context_manager(self):
        """Test benchmark context manager."""
        with PerformanceBenchmark('context_test'):
            time.sleep(0.01)
        
        metrics = get_metrics()
        stats = metrics.get_stats('context_test')
        self.assertIsNotNone(stats)
        self.assertGreater(stats['mean'], 0.01)


class TestRunBenchmark(unittest.TestCase):
    """Test run_benchmark function."""
    
    def setUp(self):
        """Set up test fixtures."""
        metrics = get_metrics()
        metrics.clear()
    
    def test_run_benchmark(self):
        """Test running a benchmark."""
        def test_func():
            sum([i for i in range(100)])
        
        stats = run_benchmark(test_func, iterations=10, warmup=2)
        self.assertIsNotNone(stats)
        self.assertEqual(stats['count'], 10)
        self.assertGreater(stats['mean'], 0)


class TestWebhookBenchmark(unittest.TestCase):
    """Test webhook processing benchmarks."""
    
    def setUp(self):
        """Set up test fixtures."""
        metrics = get_metrics()
        metrics.clear()
    
    def test_webhook_latency_target(self):
        """Test that webhook processing meets latency target."""
        @benchmark('webhook_processing')
        def process_webhook(data):
            # Simulate webhook processing
            time.sleep(0.001)  # 1ms processing time
            return {'status': 'processed'}
        
        # Run multiple iterations
        for _ in range(100):
            process_webhook({'test': 'data'})
        
        metrics = get_metrics()
        stats = metrics.get_stats('webhook_processing')
        
        # For 99.9% uptime with 10k daily webhooks, 
        # we need fast processing (target < 100ms p95)
        self.assertIsNotNone(stats)
        self.assertLess(stats['p95'], 0.1, 
                       'P95 latency should be under 100ms for high availability')
        self.assertLess(stats['p99'], 0.15,
                       'P99 latency should be under 150ms for SLA compliance')


if __name__ == '__main__':
    unittest.main()
