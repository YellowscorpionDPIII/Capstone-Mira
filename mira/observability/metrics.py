"""Metrics collection module with standardized hooks."""
import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from contextlib import contextmanager


class MetricsCollector:
    """
    Standardized metrics collection for Mira platform.
    
    Provides hooks for:
    - Counters (incremental counts)
    - Timers (duration measurements)
    - Gauges (point-in-time values)
    
    Initial implementation logs metrics, can be extended to 
    send to metrics backends (Prometheus, StatsD, etc.)
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Whether metrics collection is enabled
        """
        self.enabled = enabled
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, list] = defaultdict(list)
        self.logger = logging.getLogger("mira.metrics")
        
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict] = None):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to increment by (default 1)
            tags: Optional tags/labels for the metric
        """
        if not self.enabled:
            return
        
        key = self._build_key(metric_name, tags)
        self.counters[key] += value
        
        self.logger.debug(
            f"COUNTER {metric_name} +{value}",
            extra={'tags': tags, 'total': self.counters[key]}
        )
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """
        Set a gauge metric.
        
        Args:
            metric_name: Name of the metric
            value: Current value
            tags: Optional tags/labels for the metric
        """
        if not self.enabled:
            return
        
        key = self._build_key(metric_name, tags)
        self.gauges[key] = value
        
        self.logger.debug(
            f"GAUGE {metric_name} = {value}",
            extra={'tags': tags}
        )
    
    def timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict] = None):
        """
        Record a timing metric.
        
        Args:
            metric_name: Name of the metric
            duration_ms: Duration in milliseconds
            tags: Optional tags/labels for the metric
        """
        if not self.enabled:
            return
        
        key = self._build_key(metric_name, tags)
        self.timers[key].append(duration_ms)
        
        self.logger.debug(
            f"TIMER {metric_name} = {duration_ms:.2f}ms",
            extra={'tags': tags}
        )
    
    @contextmanager
    def timer(self, metric_name: str, tags: Optional[Dict] = None):
        """
        Context manager for timing operations.
        
        Args:
            metric_name: Name of the metric
            tags: Optional tags/labels for the metric
            
        Usage:
            with metrics.timer('operation_name'):
                # code to time
                pass
        """
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.timing(metric_name, duration_ms, tags)
    
    def get_counter(self, metric_name: str, tags: Optional[Dict] = None) -> int:
        """Get current counter value."""
        key = self._build_key(metric_name, tags)
        return self.counters.get(key, 0)
    
    def get_gauge(self, metric_name: str, tags: Optional[Dict] = None) -> Optional[float]:
        """Get current gauge value."""
        key = self._build_key(metric_name, tags)
        return self.gauges.get(key)
    
    def get_timer_stats(self, metric_name: str, tags: Optional[Dict] = None) -> Dict[str, float]:
        """
        Get timing statistics.
        
        Returns:
            Dict with min, max, avg, count
        """
        key = self._build_key(metric_name, tags)
        values = self.timers.get(key, [])
        
        if not values:
            return {'count': 0}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values)
        }
    
    def reset(self):
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()
        self.logger.info("Metrics reset")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all current metrics.
        
        Returns:
            Dict with all metrics organized by type
        """
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'timers': {
                key: self.get_timer_stats(key.split(':')[0], self._parse_tags(key))
                for key in self.timers.keys()
            }
        }
    
    @staticmethod
    def _build_key(metric_name: str, tags: Optional[Dict] = None) -> str:
        """Build metric key with tags."""
        if not tags:
            return metric_name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}:{tag_str}"
    
    @staticmethod
    def _parse_tags(key: str) -> Optional[Dict]:
        """Parse tags from metric key."""
        if ':' not in key:
            return None
        
        tag_str = key.split(':', 1)[1]
        tags = {}
        for pair in tag_str.split(','):
            k, v = pair.split('=')
            tags[k] = v
        return tags


# Global metrics collector instance
_metrics_instance = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance
