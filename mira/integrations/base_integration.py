"""Base integration adapter class."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


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
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the external service.
        
        Returns:
            True if connection successful
        """
        pass
        
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
        
    def validate_config(self, required_fields: list) -> bool:
        """
        Validate that configuration has required fields.
        
        Args:
            required_fields: List of required configuration keys
            
        Returns:
            True if all required fields present
        """
        return all(field in self.config for field in required_fields)
