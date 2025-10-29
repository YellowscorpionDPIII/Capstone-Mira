"""Base agent class for all Mira agents."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Mira platform.
    
    All agents must implement the process() method to handle messages.
    """
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = logging.getLogger(f"mira.agent.{agent_id}")
        self.created_at = datetime.utcnow()
        
    @abstractmethod
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message and return a response.
        
        Args:
            message: Message dictionary containing type, data, and metadata
            
        Returns:
            Response dictionary with processing results
        """
        pass
    
    def validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate that a message has required fields.
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['type', 'data']
        return all(field in message for field in required_fields)
    
    def create_response(self, status: str, data: Any, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized response message.
        
        Args:
            status: Status of the operation (success, error, pending)
            data: Response data
            error: Optional error message
            
        Returns:
            Standardized response dictionary
        """
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.utcnow().isoformat(),
            'status': status,
            'data': data,
            'error': error
        }
