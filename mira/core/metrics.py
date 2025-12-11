"""Minimal metrics API for observability."""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import time
import logging


@dataclass
class Counter:
    """Counter metric that can only increase."""
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment counter by amount."""
        self.value += amount


@dataclass
class Gauge:
    """Gauge metric that can increase or decrease."""
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        """Set gauge to value."""
        self.value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        self.value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class Timer:
    """Timer metric for measuring durations."""
    name: str
    count: int = 0
    total_seconds: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def observe(self, duration_seconds: float) -> None:
        """Record a duration observation."""
        self.count += 1
        self.total_seconds += duration_seconds
    
    @property
    def average_seconds(self) -> float:
        """Get average duration."""
        if self.count == 0:
            return 0.0
        return self.total_seconds / self.count


class MetricsCollector:
    """Collects and manages application metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._timers: Dict[str, Timer] = {}
        self.logger = logging.getLogger("mira.metrics")
    
    def _make_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create unique key for metric with labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """
        Get or create a counter metric.
        
        Args:
            name: Metric name (use convention: mira_<component>_<metric>_total)
            labels: Optional labels for the metric
            
        Returns:
            Counter metric
        """
        key = self._make_metric_key(name, labels)
        if key not in self._counters:
            self._counters[key] = Counter(name=name, labels=labels or {})
        return self._counters[key]
    
    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """
        Get or create a gauge metric.
        
        Args:
            name: Metric name (use convention: mira_<component>_<metric>)
            labels: Optional labels for the metric
            
        Returns:
            Gauge metric
        """
        key = self._make_metric_key(name, labels)
        if key not in self._gauges:
            self._gauges[key] = Gauge(name=name, labels=labels or {})
        return self._gauges[key]
    
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> Timer:
        """
        Get or create a timer metric.
        
        Args:
            name: Metric name (use convention: mira_<component>_duration_seconds)
            labels: Optional labels for the metric
            
        Returns:
            Timer metric
        """
        key = self._make_metric_key(name, labels)
        if key not in self._timers:
            self._timers[key] = Timer(name=name, labels=labels or {})
        return self._timers[key]
    
    @contextmanager
    def time(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        Context manager for timing a block of code.
        
        Args:
            name: Timer metric name
            labels: Optional labels for the metric
            
        Example:
            with metrics.time('mira_webhook_duration_seconds'):
                process_webhook()
        """
        start_time = time.time()
        timer_metric = self.timer(name, labels)
        
        try:
            yield timer_metric
        finally:
            duration = time.time() - start_time
            timer_metric.observe(duration)
    
    def get_all_metrics(self) -> Dict[str, List[Dict]]:
        """
        Get all metrics in a structured format.
        
        Returns:
            Dictionary with counters, gauges, and timers
        """
        return {
            'counters': [
                {
                    'name': c.name,
                    'value': c.value,
                    'labels': c.labels
                }
                for c in self._counters.values()
            ],
            'gauges': [
                {
                    'name': g.name,
                    'value': g.value,
                    'labels': g.labels
                }
                for g in self._gauges.values()
            ],
            'timers': [
                {
                    'name': t.name,
                    'count': t.count,
                    'total_seconds': t.total_seconds,
                    'average_seconds': t.average_seconds,
                    'labels': t.labels
                }
                for t in self._timers.values()
            ]
        }
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
