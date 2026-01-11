"""Metrics collection for Mira platform using Prometheus."""
from typing import Optional
import logging
import threading

logger = logging.getLogger("mira.metrics")

# Try to import prometheus_client at module level
try:
    from prometheus_client import Counter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None


class PrometheusMetrics:
    """
    Prometheus metrics collector for agent operations.
    
    Provides counters for tracking timeout and fallback events in agent processing.
    If prometheus_client is not installed, metrics are logged instead.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Whether metrics collection is enabled
        """
        self.enabled = enabled
        self._counters = {}
        
        if not enabled:
            logger.info("Metrics collection is disabled")
            return
            
        if not PROMETHEUS_AVAILABLE:
            logger.warning(
                "prometheus_client not installed. Metrics will be logged instead. "
                "Install with: pip install prometheus-client"
            )
            self.enabled = False
            return
            
        # Counter for agent process timeouts
        self._counters['timeout'] = Counter(
            'agent_process_timeout_total',
            'Total number of agent process timeouts',
            ['agent_id', 'function_name']
        )
        
        # Counter for agent process fallbacks
        self._counters['fallback'] = Counter(
            'agent_process_fallback_total',
            'Total number of agent process fallbacks to synchronous execution',
            ['agent_id', 'function_name', 'reason']
        )
        
        logger.info("Prometheus metrics initialized successfully")
    
    def increment_timeout(self, agent_id: str, function_name: str):
        """
        Increment timeout counter.
        
        Args:
            agent_id: ID of the agent that timed out
            function_name: Name of the function that timed out
        """
        if not self.enabled:
            logger.info(
                f"Metrics: agent_process_timeout_total{{agent_id='{agent_id}', "
                f"function_name='{function_name}'}} +1"
            )
            return
            
        if 'timeout' in self._counters:
            self._counters['timeout'].labels(
                agent_id=agent_id,
                function_name=function_name
            ).inc()
    
    def increment_fallback(self, agent_id: str, function_name: str, reason: str):
        """
        Increment fallback counter.
        
        Args:
            agent_id: ID of the agent that fell back
            function_name: Name of the function that fell back
            reason: Reason for fallback (e.g., 'timeout', 'error')
        """
        if not self.enabled:
            logger.info(
                f"Metrics: agent_process_fallback_total{{agent_id='{agent_id}', "
                f"function_name='{function_name}', reason='{reason}'}} +1"
            )
            return
            
        if 'fallback' in self._counters:
            self._counters['fallback'].labels(
                agent_id=agent_id,
                function_name=function_name,
                reason=reason
            ).inc()


# Singleton instance
_metrics_instance: Optional[PrometheusMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics(enabled: bool = True) -> PrometheusMetrics:
    """
    Get the singleton metrics instance (thread-safe).
    
    Args:
        enabled: Whether metrics collection should be enabled
        
    Returns:
        PrometheusMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            # Double-check locking pattern
            if _metrics_instance is None:
                _metrics_instance = PrometheusMetrics(enabled=enabled)
    return _metrics_instance
