"""Health and readiness checks for the application."""
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class DependencyCheck:
    """Represents a dependency health check."""
    name: str
    check_func: Callable[[], bool]
    required: bool = True
    timeout_seconds: float = 5.0


class HealthRegistry:
    """Registry for managing health and readiness checks."""
    
    def __init__(self):
        """Initialize health registry."""
        self._dependencies: Dict[str, DependencyCheck] = {}
        self.logger = logging.getLogger("mira.health")
    
    def register_dependency(
        self,
        name: str,
        check_func: Callable[[], bool],
        required: bool = True,
        timeout_seconds: float = 5.0
    ) -> None:
        """
        Register a dependency for health checks.
        
        Args:
            name: Dependency name (e.g., 'airtable', 'database')
            check_func: Function that returns True if dependency is healthy
            required: Whether this dependency is required for readiness
            timeout_seconds: Timeout for the check
        """
        self._dependencies[name] = DependencyCheck(
            name=name,
            check_func=check_func,
            required=required,
            timeout_seconds=timeout_seconds
        )
        self.logger.info(f"Registered dependency check: {name}")
    
    def unregister_dependency(self, name: str) -> bool:
        """
        Unregister a dependency.
        
        Args:
            name: Dependency name
            
        Returns:
            True if dependency was removed
        """
        if name in self._dependencies:
            del self._dependencies[name]
            self.logger.info(f"Unregistered dependency check: {name}")
            return True
        return False
    
    def check_health(self) -> Dict[str, Any]:
        """
        Perform lightweight health check (process-level only).
        
        This endpoint should be fast and not perform I/O operations.
        
        Returns:
            Health status dictionary
        """
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'mira'
        }
    
    def check_readiness(self) -> Dict[str, Any]:
        """
        Perform comprehensive readiness check with dependency validation.
        
        Returns:
            Readiness status dictionary with dependency details
        """
        timestamp = datetime.utcnow().isoformat()
        dependencies_status = {}
        all_ready = True
        
        for dep_name, dep_check in self._dependencies.items():
            try:
                is_healthy = dep_check.check_func()
                dependencies_status[dep_name] = {
                    'healthy': is_healthy,
                    'required': dep_check.required
                }
                
                if dep_check.required and not is_healthy:
                    all_ready = False
                    
            except Exception as e:
                self.logger.error(f"Error checking dependency {dep_name}: {e}")
                dependencies_status[dep_name] = {
                    'healthy': False,
                    'required': dep_check.required,
                    'error': str(e)
                }
                
                if dep_check.required:
                    all_ready = False
        
        return {
            'status': 'ready' if all_ready else 'not_ready',
            'timestamp': timestamp,
            'service': 'mira',
            'dependencies': dependencies_status
        }
    
    def get_dependency_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific dependency.
        
        Args:
            name: Dependency name
            
        Returns:
            Dependency status or None if not found
        """
        if name not in self._dependencies:
            return None
        
        dep_check = self._dependencies[name]
        try:
            is_healthy = dep_check.check_func()
            return {
                'name': name,
                'healthy': is_healthy,
                'required': dep_check.required,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error checking dependency {name}: {e}")
            return {
                'name': name,
                'healthy': False,
                'required': dep_check.required,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global health registry instance
_health_registry = None


def get_health_registry() -> HealthRegistry:
    """
    Get the global health registry instance.
    
    Returns:
        HealthRegistry instance
    """
    global _health_registry
    if _health_registry is None:
        _health_registry = HealthRegistry()
    return _health_registry
