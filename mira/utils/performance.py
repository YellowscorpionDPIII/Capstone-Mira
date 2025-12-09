"""Performance benchmarking utilities for Mira platform."""
import time
import statistics
from typing import Callable, Dict, Any, List, Optional
from functools import wraps
import logging


class PerformanceMetrics:
    """Store and analyze performance metrics."""
    
    def __init__(self):
        """Initialize performance metrics storage."""
        self.metrics: Dict[str, List[float]] = {}
        self.logger = logging.getLogger("mira.performance")
    
    def record(self, name: str, duration: float):
        """
        Record a performance measurement.
        
        Args:
            name: Name of the operation
            duration: Duration in seconds
        """
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration)
    
    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a metric.
        
        Args:
            name: Name of the operation
            
        Returns:
            Dictionary with min, max, mean, median, and p95 latency
        """
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = self.metrics[name]
        sorted_values = sorted(values)
        p95_index = int(len(sorted_values) * 0.95)
        p99_index = int(len(sorted_values) * 0.99)
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'p95': sorted_values[p95_index] if sorted_values else 0,
            'p99': sorted_values[p99_index] if sorted_values else 0,
            'stdev': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for all metrics.
        
        Returns:
            Dictionary mapping metric names to their statistics
        """
        return {name: self.get_stats(name) for name in self.metrics.keys()}
    
    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()
    
    def compare(self, name: str, before_stats: Dict[str, float], 
                after_stats: Dict[str, float]) -> Dict[str, Any]:
        """
        Compare before and after performance statistics.
        
        Args:
            name: Name of the operation
            before_stats: Statistics before optimization
            after_stats: Statistics after optimization
            
        Returns:
            Comparison report with improvements
        """
        if not before_stats or not after_stats:
            return {'error': 'Missing statistics for comparison'}
        
        comparison = {
            'operation': name,
            'improvements': {}
        }
        
        for metric in ['mean', 'median', 'p95', 'p99', 'max']:
            if metric in before_stats and metric in after_stats:
                before_val = before_stats[metric]
                after_val = after_stats[metric]
                if before_val > 0:
                    improvement_pct = ((before_val - after_val) / before_val) * 100
                    comparison['improvements'][metric] = {
                        'before': before_val,
                        'after': after_val,
                        'improvement_pct': improvement_pct,
                        'faster': improvement_pct > 0
                    }
        
        return comparison


# Global metrics instance
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get the global performance metrics instance."""
    return _metrics


def benchmark(operation_name: str = None):
    """
    Decorator to benchmark function execution time.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                _metrics.record(name, duration)
        return wrapper
    return decorator


class PerformanceBenchmark:
    """Context manager for benchmarking code blocks."""
    
    def __init__(self, operation_name: str):
        """
        Initialize benchmark context.
        
        Args:
            operation_name: Name of the operation being benchmarked
        """
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record timing."""
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        _metrics.record(self.operation_name, duration)


def run_benchmark(func: Callable, iterations: int = 100, 
                  warmup: int = 10, name: str = None) -> Dict[str, float]:
    """
    Run a benchmark on a function.
    
    Args:
        func: Function to benchmark
        iterations: Number of iterations to run
        warmup: Number of warmup iterations
        name: Name for the operation
        
    Returns:
        Performance statistics
    """
    operation_name = name or func.__name__
    
    # Warmup runs
    for _ in range(warmup):
        func()
    
    # Actual benchmark runs
    durations = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        func()
        end_time = time.perf_counter()
        durations.append(end_time - start_time)
    
    # Record all measurements
    for duration in durations:
        _metrics.record(operation_name, duration)
    
    return _metrics.get_stats(operation_name)
