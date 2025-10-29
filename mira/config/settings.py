"""Configuration management for the Mira platform."""
import os
import json
from typing import Dict, Any, Optional
import logging


class Config:
    """
    Configuration manager for Mira platform.
    
    Loads configuration from environment variables and config files.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration file (JSON)
        """
        self.logger = logging.getLogger("mira.config")
        self.config_data: Dict[str, Any] = {}
        
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        else:
            self._load_defaults()
            
        # Override with environment variables
        self._load_from_env()
        
    def _load_from_file(self, config_path: str):
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to config file
        """
        try:
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)
            self.logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Error loading config file: {e}")
            self._load_defaults()
            
    def _load_defaults(self):
        """Load default configuration."""
        self.config_data = {
            'broker': {
                'enabled': True,
                'queue_size': 1000
            },
            'webhook': {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 5000,
                'secret_key': None
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'integrations': {
                'trello': {
                    'enabled': False,
                    'api_key': None,
                    'api_token': None,
                    'board_id': None
                },
                'jira': {
                    'enabled': False,
                    'url': None,
                    'username': None,
                    'api_token': None,
                    'project_key': None
                },
                'github': {
                    'enabled': False,
                    'token': None,
                    'repository': None
                },
                'airtable': {
                    'enabled': False,
                    'api_key': None,
                    'base_id': None
                },
                'google_docs': {
                    'enabled': False,
                    'credentials_path': None,
                    'folder_id': None
                }
            },
            'agents': {
                'project_plan_agent': {
                    'enabled': True
                },
                'risk_assessment_agent': {
                    'enabled': True
                },
                'status_reporter_agent': {
                    'enabled': True
                },
                'orchestrator_agent': {
                    'enabled': True
                }
            }
        }
        
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Webhook config
        if os.getenv('MIRA_WEBHOOK_ENABLED'):
            self.config_data['webhook']['enabled'] = os.getenv('MIRA_WEBHOOK_ENABLED') == 'true'
        if os.getenv('MIRA_WEBHOOK_PORT'):
            self.config_data['webhook']['port'] = int(os.getenv('MIRA_WEBHOOK_PORT'))
        if os.getenv('MIRA_WEBHOOK_SECRET'):
            self.config_data['webhook']['secret_key'] = os.getenv('MIRA_WEBHOOK_SECRET')
            
        # Integration configs
        integrations = ['trello', 'jira', 'github', 'airtable', 'google_docs']
        for integration in integrations:
            prefix = f'MIRA_{integration.upper()}_'
            if os.getenv(f'{prefix}ENABLED'):
                self.config_data['integrations'][integration]['enabled'] = os.getenv(f'{prefix}ENABLED') == 'true'
                
        self.logger.info("Loaded configuration from environment variables")
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'webhook.port')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def save(self, config_path: str):
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save config file
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            self.logger.info(f"Saved configuration to {config_path}")
        except Exception as e:
            self.logger.error(f"Error saving config file: {e}")


# Singleton instance
_config_instance = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the singleton configuration instance.
    
    Args:
        config_path: Optional path to config file (only used on first call)
        
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
