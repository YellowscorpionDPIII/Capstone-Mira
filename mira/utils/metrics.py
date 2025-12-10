"""Metrics collection utilities for latency and error tracking.

This module provides a pluggable metrics system that can be easily extended
with Prometheus or other monitoring systems in the future.
"""
import time
import logging
from typing import Dict, Any, Callable, Optional
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict
from threading import Lock


class MetricsCollector:
    """
    Central metrics collector for tracking latencies and errors.
    
    This class provides a pluggable interface for collecting metrics
    that can be extended with Prometheus or other monitoring systems.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._latencies: Dict[str, list] = defaultdict(list)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = Lock()
        self.logger = logging.getLogger("mira.metrics")
        
    def record_latency(self, metric_name: str, duration_seconds: float):
        """
        Record a latency measurement.
        
        Args:
            metric_name: Name of the metric (e.g., 'agent.process')
            duration_seconds: Duration in seconds
        """
        with self._lock:
            self._latencies[metric_name].append(duration_seconds)
            self.logger.debug(f"Recorded latency for {metric_name}: {duration_seconds:.4f}s")
            
    def increment_error_counter(self, counter_name: str, increment: int = 1):
        """
        Increment an error counter.
        
        Args:
            counter_name: Name of the counter (e.g., 'agent.errors')
            increment: Amount to increment by (default: 1)
        """
        with self._lock:
            self._error_counts[counter_name] += increment
            self.logger.debug(f"Incremented error counter {counter_name} by {increment}")
            
    def get_latency_stats(self, metric_name: str) -> Dict[str, float]:
        """
        Get statistics for a latency metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary with min, max, avg, count statistics
        """
        with self._lock:
            return self._get_latency_stats_unsafe(metric_name)
    
    def _get_latency_stats_unsafe(self, metric_name: str) -> Dict[str, float]:
        """
        Internal method to get latency stats without acquiring lock.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary with min, max, avg, count statistics
        """
        latencies = self._latencies.get(metric_name, [])
        
        if not latencies:
            return {
                'count': 0,
                'min': 0.0,
                'max': 0.0,
                'avg': 0.0,
                'sum': 0.0
            }
            
        return {
            'count': len(latencies),
            'min': min(latencies),
            'max': max(latencies),
            'avg': sum(latencies) / len(latencies),
            'sum': sum(latencies)
        }
            
    def get_error_count(self, counter_name: str) -> int:
        """
        Get the current value of an error counter.
        
        Args:
            counter_name: Name of the counter
            
        Returns:
            Current counter value
        """
        with self._lock:
            return self._error_counts.get(counter_name, 0)
            
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary with all latency stats and error counts
        """
        with self._lock:
            metrics = {
                'latencies': {},
                'errors': dict(self._error_counts)
            }
            
            for metric_name in self._latencies.keys():
                metrics['latencies'][metric_name] = self._get_latency_stats_unsafe(metric_name)
                
            return metrics
            
    def reset_metrics(self):
        """Reset all collected metrics."""
        with self._lock:
            self._latencies.clear()
            self._error_counts.clear()
            self.logger.info("All metrics reset")
            
    @contextmanager
    def timer(self, metric_name: str):
        """
        Context manager for measuring latency.
        
        Usage:
            with metrics.timer('my_operation'):
                # code to measure
                pass
                
        Args:
            metric_name: Name of the metric to record
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_latency(metric_name, duration)
            
    def timed(self, metric_name: Optional[str] = None):
        """
        Decorator for measuring function latency.
        
        Usage:
            @metrics.timed('my_function')
            def my_function():
                pass
                
        Args:
            metric_name: Optional metric name (defaults to function name)
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            # Determine metric name at decoration time
            final_metric_name = metric_name
            if final_metric_name is None:
                final_metric_name = f"{func.__module__}.{func.__name__}"
                
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.timer(final_metric_name):
                    return func(*args, **kwargs)
                    
            return wrapper
        return decorator


# Singleton instance
_metrics_instance = None
_metrics_lock = Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the singleton metrics collector instance.
    
    Returns:
        Global MetricsCollector instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = MetricsCollector()
    return _metrics_instance


# Convenience functions for direct access
def record_latency(metric_name: str, duration_seconds: float):
    """Record a latency measurement."""
    get_metrics_collector().record_latency(metric_name, duration_seconds)


def increment_error_counter(counter_name: str, increment: int = 1):
    """Increment an error counter."""
    get_metrics_collector().increment_error_counter(counter_name, increment)


def get_latency_stats(metric_name: str) -> Dict[str, float]:
    """Get statistics for a latency metric."""
    return get_metrics_collector().get_latency_stats(metric_name)


def get_error_count(counter_name: str) -> int:
    """Get the current value of an error counter."""
    return get_metrics_collector().get_error_count(counter_name)


def get_all_metrics() -> Dict[str, Any]:
    """Get all collected metrics."""
    return get_metrics_collector().get_all_metrics()


def reset_metrics():
    """Reset all collected metrics."""
    get_metrics_collector().reset_metrics()


@contextmanager
def timer(metric_name: str):
    """Context manager for measuring latency."""
    collector = get_metrics_collector()
    with collector.timer(metric_name):
        yield


def timed(metric_name: Optional[str] = None):
    """Decorator for measuring function latency."""
    return get_metrics_collector().timed(metric_name)
