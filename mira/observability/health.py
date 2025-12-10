"""Health check module for readiness and liveness probes."""
import logging
from typing import Dict, Any, Callable, List
from datetime import datetime
from enum import Enum


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
        
        for name, check_func in self.dependency_checks.items():
            try:
                is_healthy, message = check_func()
                status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
                
                dependencies[name] = {
                    'status': status.value,
                    'message': message
                }
                
                if not is_healthy:
                    all_healthy = False
                    # Check if it's a soft failure (degraded)
                    if 'degraded' in message.lower() or 'warning' in message.lower():
                        has_degraded = True
                        
            except Exception as e:
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
            'dependencies': dependencies
        }


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
