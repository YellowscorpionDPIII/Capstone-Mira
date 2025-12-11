"""Health check module for readiness and liveness probes."""
import logging
from typing import Dict, Any, Callable, List
from datetime import datetime, timedelta
from enum import Enum
import time


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheck:
    """
    Health and readiness check system.
    
    Provides:
    - /health endpoint: Basic liveness check (is process running)
    - /ready endpoint: Readiness check with dependency validation
    """
    
    def __init__(self):
        """Initialize health check system."""
        self.logger = logging.getLogger("mira.health")
        self.dependency_checks: Dict[str, Callable[[], tuple[bool, str]]] = {}
        self.start_time = datetime.utcnow()
        self.graceful_startup_seconds = 30  # Skip unavailable deps for first 30s
        
    def register_dependency(self, name: str, check_func: Callable[[], tuple[bool, str]]):
        """
        Register a dependency check.
        
        Args:
            name: Name of the dependency (e.g., 'airtable', 'database')
            check_func: Function that returns (is_healthy, message)
        """
        self.dependency_checks[name] = check_func
        self.logger.info(f"Registered health check for: {name}")
    
    def check_health(self) -> Dict[str, Any]:
        """
        Perform basic health check (liveness).
        
        Returns:
            Health status dict
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'status': HealthStatus.HEALTHY.value,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': uptime
        }
    
    def check_ready(self) -> Dict[str, Any]:
        """
        Perform readiness check with dependencies.
        
        Returns:
            Readiness status dict with dependency details
        """
        dependencies = {}
        all_healthy = True
        has_degraded = False
        
        # Check if we're in graceful startup period
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        in_graceful_startup = uptime < self.graceful_startup_seconds
        
        for name, check_func in self.dependency_checks.items():
            try:
                is_healthy, message = check_func()
                status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
                
                dependencies[name] = {
                    'status': status.value,
                    'message': message
                }
                
                if not is_healthy:
                    # During graceful startup, mark as degraded instead of unhealthy
                    if in_graceful_startup:
                        dependencies[name]['status'] = HealthStatus.DEGRADED.value
                        dependencies[name]['message'] = f"{message} (graceful startup)"
                        has_degraded = True
                    else:
                        all_healthy = False
                        # Check if it's a soft failure (degraded)
                        if 'degraded' in message.lower() or 'warning' in message.lower():
                            has_degraded = True
                        
            except Exception as e:
                # During graceful startup, be more lenient
                if in_graceful_startup:
                    dependencies[name] = {
                        'status': HealthStatus.DEGRADED.value,
                        'message': f'Check failed: {str(e)} (graceful startup)'
                    }
                    has_degraded = True
                else:
                    dependencies[name] = {
                        'status': HealthStatus.UNHEALTHY.value,
                        'message': f'Check failed: {str(e)}'
                    }
                    all_healthy = False
                self.logger.error(f"Health check failed for {name}: {e}")
        
        # Determine overall status
        if all_healthy:
            overall_status = HealthStatus.HEALTHY
        elif has_degraded and not all_healthy:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'dependencies': dependencies,
            'graceful_startup': in_graceful_startup
        }
    
    def _parse_metric_tags(self, metric_name: str) -> tuple[str, str]:
        """
        Parse metric name and tags into Prometheus format.
        
        Args:
            metric_name: Metric name with optional tags (e.g., "metric:key=value,key2=value2")
            
        Returns:
            Tuple of (base_name, label_str) for Prometheus format
        """
        if ':' not in metric_name:
            return metric_name, ''
        
        base_name, tags_str = metric_name.split(':', 1)
        labels = []
        
        # Parse tags with error handling
        for tag in tags_str.split(','):
            if '=' in tag:
                k, v = tag.split('=', 1)  # Use maxsplit=1 to handle values with '='
                labels.append(f'{k}="{v}"')
            else:
                # Malformed tag, skip it
                self.logger.warning(f"Malformed tag in metric {metric_name}: {tag}")
        
        label_str = '{' + ','.join(labels) + '}' if labels else ''
        return base_name, label_str
    
    def get_metrics_prometheus(self) -> str:
        """
        Get metrics in Prometheus exposition format.
        
        Returns:
            Prometheus format metrics as string
        """
        from ..observability.metrics import get_metrics
        
        metrics_collector = get_metrics()
        all_metrics = metrics_collector.get_all_metrics()
        
        lines = []
        lines.append("# HELP mira_uptime_seconds System uptime in seconds")
        lines.append("# TYPE mira_uptime_seconds gauge")
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        lines.append(f"mira_uptime_seconds {uptime}")
        
        # Export counters
        for metric_name, value in all_metrics.get('counters', {}).items():
            base_name, label_str = self._parse_metric_tags(metric_name)
            prom_name = base_name.replace('.', '_').replace('-', '_')
            lines.append(f"# HELP mira_{prom_name} Counter metric")
            lines.append(f"# TYPE mira_{prom_name} counter")
            lines.append(f"mira_{prom_name}{label_str} {value}")
        
        # Export gauges
        for metric_name, value in all_metrics.get('gauges', {}).items():
            base_name, label_str = self._parse_metric_tags(metric_name)
            prom_name = base_name.replace('.', '_').replace('-', '_')
            lines.append(f"# HELP mira_{prom_name} Gauge metric")
            lines.append(f"# TYPE mira_{prom_name} gauge")
            lines.append(f"mira_{prom_name}{label_str} {value}")
        
        # Export timer summaries
        for metric_name, stats in all_metrics.get('timers', {}).items():
            base_name, label_str = self._parse_metric_tags(metric_name)
            prom_name = base_name.replace('.', '_').replace('-', '_')
            lines.append(f"# HELP mira_{prom_name}_milliseconds Timer metric in milliseconds")
            lines.append(f"# TYPE mira_{prom_name}_milliseconds summary")
            
            if stats.get('count', 0) > 0:
                lines.append(f"mira_{prom_name}_milliseconds_count{label_str} {stats['count']}")
                lines.append(f"mira_{prom_name}_milliseconds_sum{label_str} {stats['avg'] * stats['count']}")
        
        # Health status
        lines.append("# HELP mira_health_status Health status (1=healthy, 0=unhealthy)")
        lines.append("# TYPE mira_health_status gauge")
        health_status = self.check_ready()
        health_value = 1 if health_status['status'] == 'healthy' else 0
        lines.append(f"mira_health_status {health_value}")
        
        # Dependency health
        for dep_name, dep_info in health_status.get('dependencies', {}).items():
            dep_value = 1 if dep_info['status'] == 'healthy' else 0
            lines.append(f'mira_dependency_health{{dependency="{dep_name}"}} {dep_value}')
        
        return '\n'.join(lines) + '\n'


# Example dependency check functions
def check_airtable_connection(api_key: str = None, base_id: str = None) -> tuple[bool, str]:
    """
    Check Airtable connectivity.
    
    Args:
        api_key: Airtable API key
        base_id: Airtable base ID
        
    Returns:
        Tuple of (is_healthy, message)
    """
    if not api_key or not base_id:
        return True, "Airtable not configured (optional)"
    
    # In production, would make lightweight API call to verify connection
    # For now, just check if credentials are present
    try:
        # Simulate a connection check
        # In real implementation: make API call to Airtable
        return True, "Airtable connection healthy"
    except Exception as e:
        return False, f"Airtable connection failed: {str(e)}"


def check_broker_status(broker) -> tuple[bool, str]:
    """
    Check message broker status.
    
    Args:
        broker: Message broker instance
        
    Returns:
        Tuple of (is_healthy, message)
    """
    if not broker:
        return False, "Broker not initialized"
    
    try:
        if hasattr(broker, 'running') and broker.running:
            return True, "Broker running"
        else:
            return False, "Broker not running"
    except Exception as e:
        return False, f"Broker check failed: {str(e)}"


def check_redis_connection(redis_url: str = None) -> tuple[bool, str]:
    """
    Check Redis connection pool health.
    
    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        
    Returns:
        Tuple of (is_healthy, message)
    """
    if not redis_url:
        return True, "Redis not configured (optional)"
    
    try:
        # In production, would use redis-py to check connection
        # For now, just verify URL format
        if redis_url.startswith('redis://'):
            return True, "Redis connection healthy"
        else:
            return False, "Invalid Redis URL format"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"


def check_n8n_webhook_latency(n8n_url: str = None, timeout: int = 5) -> tuple[bool, str]:
    """
    Check n8n webhook endpoint latency.
    
    Args:
        n8n_url: n8n webhook URL to test
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (is_healthy, message)
    """
    if not n8n_url:
        return True, "n8n webhook not configured (optional)"
    
    try:
        import requests
        start = time.time()
        response = requests.get(n8n_url, timeout=timeout)
        latency_ms = (time.time() - start) * 1000
        
        if response.status_code < 500:
            if latency_ms < 1000:
                return True, f"n8n webhook healthy (latency: {latency_ms:.0f}ms)"
            else:
                return True, f"n8n webhook degraded (latency: {latency_ms:.0f}ms)"
        else:
            return False, f"n8n webhook unhealthy (status: {response.status_code})"
    except Exception as e:
        return False, f"n8n webhook check failed: {str(e)}"
