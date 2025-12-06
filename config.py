# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import Dict, Any
import yaml
import os
from pathlib import Path

class OrchestratorConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    # Core settings
    openai_api_key: str = Field(..., json_schema_extra={"env": "OPENAI_API_KEY"})
    mcp_endpoint: str = Field(default="http://localhost:8000/mcp")
    n8n_webhook_url: str = Field(default="")
    
    # Config file override
    config_path: str = "config/orchestrator_config.yaml"
    
    def __post_init__(self):
        self.load_yaml_config()
    
    def load_yaml_config(self):
        """Load YAML config and merge with settings"""
        config_path = Path(self.config_path)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
                for key, value in yaml_data.items():
                    if not hasattr(self, key):  # Avoid overwriting Pydantic fields
                        setattr(self, key, value)
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or v.startswith('sk-') is False:
            raise ValueError('OPENAI_API_KEY must be valid OpenAI key')
        return v
    
    def llm_client(self):
        """Return configured OpenAI client"""
        from openai import OpenAI
        return OpenAI(
            api_key=self.openai_api_key,
            base_url=getattr(self, 'openai.base_url', None),
            timeout=getattr(self, 'openai.timeout', 60)
        )
    
    def mcp_client(self):
        """Return MCP client"""
        import aiohttp
        return aiohttp.ClientSession(
            base_url=self.mcp_endpoint,
            timeout=self.mcp.timeout if hasattr(self.mcp, 'timeout') else 30,
            headers={'Authorization': f'Bearer {self.mcp.auth_token}'}
        )

# Global config instance
config = OrchestratorConfig()
