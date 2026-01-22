"""Base integration adapter class."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from mira.utils.metrics import get_metrics_collector


class BaseIntegration(ABC):
    """
    Abstract base class for external service integrations.
    
    All integrations must implement connect, disconnect, and sync methods.
    """
    
    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the integration.
        
        Args:
            service_name: Name of the external service
            config: Configuration dictionary with credentials and settings
        """
        self.service_name = service_name
        self.config = config or {}
        self.logger = logging.getLogger(f"mira.integration.{service_name}")
        self.connected = False
        self.metrics = get_metrics_collector()
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the external service.
        
        Returns:
            True if connection successful
        """
        pass
    
    def connect_with_metrics(self) -> bool:
        """
        Wrap connect() with metrics collection.
        
        Returns:
            True if connection successful
        """
        metric_name = f"integration.{self.service_name}.connect"
        
        try:
            with self.metrics.timer(metric_name):
                result = self.connect()
                
            if not result:
                self.metrics.increment_error_counter(f"integration.{self.service_name}.connect_errors")
                
            return result
        except Exception as e:
            self.metrics.increment_error_counter(f"integration.{self.service_name}.connect_errors")
            self.logger.error(f"Error connecting to {self.service_name}: {e}")
            raise
        
    @abstractmethod
    def disconnect(self):
        """Disconnect from the external service."""
        pass
        
    @abstractmethod
    def sync_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync data with the external service.
        
        Args:
            data_type: Type of data to sync
            data: Data to sync
            
        Returns:
            Sync result
        """
        pass
    
    def sync_data_with_metrics(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap sync_data() with metrics collection.
        
        Args:
            data_type: Type of data to sync
            data: Data to sync
            
        Returns:
            Sync result
        """
        metric_name = f"integration.{self.service_name}.sync_data"
        
        try:
            with self.metrics.timer(metric_name):
                result = self.sync_data(data_type, data)
                
            # Check for errors in result
            if isinstance(result, dict) and result.get('status') == 'error':
                self.metrics.increment_error_counter(f"integration.{self.service_name}.sync_errors")
                
            return result
        except Exception as e:
            self.metrics.increment_error_counter(f"integration.{self.service_name}.sync_errors")
            self.logger.error(f"Error syncing data to {self.service_name}: {e}")
            raise
        
    def validate_config(self, required_fields: list) -> bool:
        """
        Validate that configuration has required fields.
        
        Args:
            required_fields: List of required configuration keys
            
        Returns:
            True if all required fields present
        """
        return all(field in self.config for field in required_fields)
