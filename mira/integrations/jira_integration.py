"""Jira integration adapter."""
from typing import Dict, Any
from mira.integrations.base_integration import BaseIntegration


class JiraIntegration(BaseIntegration):
    """
    Integration adapter for Jira.
    
    Syncs project plans, issues, and risks with Jira.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Jira integration."""
        super().__init__("jira", config)
        self.url = self.config.get('url')
        self.username = self.config.get('username')
        self.api_token = self.config.get('api_token')
        self.project_key = self.config.get('project_key')
        
    def connect(self) -> bool:
        """
        Connect to Jira API.
        
        Returns:
            True if connection successful
        """
        if not self.validate_config(['url', 'username', 'api_token']):
            self.logger.error("Missing required Jira configuration")
            return False
            
        # Simulate connection (in production, would make API call)
        self.connected = True
        self.logger.info(f"Connected to Jira at {self.url}")
        return True
        
    def disconnect(self):
        """Disconnect from Jira."""
        self.connected = False
        self.logger.info("Disconnected from Jira")
        
    def sync_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync data with Jira.
        
        Args:
            data_type: Type of data (issues, risks, etc.)
            data: Data to sync
            
        Returns:
            Sync result
        """
        if not self.connected:
            return {'success': False, 'error': 'Not connected to Jira'}
            
        if data_type == 'issues':
            return self._sync_issues(data)
        elif data_type == 'risks':
            return self._sync_risks(data)
        else:
            return {'success': False, 'error': f'Unknown data type: {data_type}'}
            
    def _sync_issues(self, issues: list) -> Dict[str, Any]:
        """
        Sync issues to Jira.
        
        Args:
            issues: List of issues to sync
            
        Returns:
            Sync result
        """
        # In production, would create/update Jira issues via API
        synced_count = len(issues)
        self.logger.info(f"Synced {synced_count} issues to Jira")
        
        return {
            'success': True,
            'synced_count': synced_count,
            'project_key': self.project_key
        }
        
    def _sync_risks(self, risks: list) -> Dict[str, Any]:
        """
        Sync risks to Jira as issues with risk labels.
        
        Args:
            risks: List of risks to sync
            
        Returns:
            Sync result
        """
        # In production, would create/update Jira issues with risk labels
        synced_count = len(risks)
        self.logger.info(f"Synced {synced_count} risks to Jira")
        
        return {
            'success': True,
            'synced_count': synced_count,
            'project_key': self.project_key
        }
