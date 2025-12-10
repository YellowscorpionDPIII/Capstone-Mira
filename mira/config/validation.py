"""Configuration schema validation using Pydantic."""
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, Dict, Any
import os
import logging


class BrokerConfig(BaseModel):
    """Message broker configuration."""
    enabled: bool = True
    queue_size: int = Field(default=1000, ge=1, le=100000)


class WebhookConfig(BaseModel):
    """Webhook server configuration."""
    enabled: bool = False
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5000, ge=1, le=65535)
    secret_key: Optional[str] = None
    
    @validator('host')
    def validate_host(cls, v):
        """Validate host format."""
        if not v:
            raise ValueError("Host cannot be empty")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    audit_log_file: Optional[str] = None
    
    @validator('level')
    def validate_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v_upper


class IntegrationConfig(BaseModel):
    """Base integration configuration."""
    enabled: bool = False
    api_key: Optional[str] = None


class TrelloConfig(IntegrationConfig):
    """Trello integration configuration."""
    api_token: Optional[str] = None
    board_id: Optional[str] = None


class JiraConfig(IntegrationConfig):
    """Jira integration configuration."""
    url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    project_key: Optional[str] = None


class GitHubConfig(IntegrationConfig):
    """GitHub integration configuration."""
    token: Optional[str] = None
    repository: Optional[str] = None


class AirtableConfig(IntegrationConfig):
    """Airtable integration configuration."""
    base_id: Optional[str] = None


class GoogleDocsConfig(IntegrationConfig):
    """Google Docs integration configuration."""
    credentials_path: Optional[str] = None
    folder_id: Optional[str] = None


class IntegrationsConfig(BaseModel):
    """All integrations configuration."""
    trello: TrelloConfig = TrelloConfig()
    jira: JiraConfig = JiraConfig()
    github: GitHubConfig = GitHubConfig()
    airtable: AirtableConfig = AirtableConfig()
    google_docs: GoogleDocsConfig = GoogleDocsConfig()


class AgentConfig(BaseModel):
    """Agent configuration."""
    enabled: bool = True


class AgentsConfig(BaseModel):
    """All agents configuration."""
    project_plan_agent: AgentConfig = AgentConfig()
    risk_assessment_agent: AgentConfig = AgentConfig()
    status_reporter_agent: AgentConfig = AgentConfig()
    orchestrator_agent: AgentConfig = AgentConfig()


class SecurityConfig(BaseModel):
    """Security configuration."""
    api_key_enabled: bool = Field(default=True)
    api_key_expiry_days: Optional[int] = Field(default=None, ge=1)
    ip_allowlist: list[str] = Field(default_factory=list)
    ip_denylist: list[str] = Field(default_factory=list)
    webhook_secrets: Dict[str, str] = Field(default_factory=dict)


class OperationalConfig(BaseModel):
    """Operational controls configuration."""
    rate_limiting_enabled: bool = Field(default=False)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    verbose_logging: bool = Field(default=False)
    maintenance_mode: bool = Field(default=False)
    maintenance_message: str = Field(
        default="System is currently under maintenance"
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    metrics_enabled: bool = Field(default=True)
    health_check_enabled: bool = Field(default=True)


class MiraConfig(BaseModel):
    """Complete Mira platform configuration schema."""
    broker: BrokerConfig = BrokerConfig()
    webhook: WebhookConfig = WebhookConfig()
    logging: LoggingConfig = LoggingConfig()
    integrations: IntegrationsConfig = IntegrationsConfig()
    agents: AgentsConfig = AgentsConfig()
    security: SecurityConfig = SecurityConfig()
    operational: OperationalConfig = OperationalConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields for extensibility


def validate_config(config_dict: Dict[str, Any]) -> MiraConfig:
    """
    Validate configuration dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated MiraConfig instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    logger = logging.getLogger("mira.config.validation")
    
    try:
        config = MiraConfig(**config_dict)
        logger.info("Configuration validation successful")
        return config
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


def validate_env_vars() -> Dict[str, str]:
    """
    Validate required environment variables.
    
    Returns:
        Dict of validated environment variables
        
    Raises:
        ValueError: If required variables are missing or invalid
    """
    env_vars = {}
    logger = logging.getLogger("mira.config.validation")
    
    # Optional but recommended environment variables
    recommended_vars = {
        'MIRA_WEBHOOK_SECRET': 'Webhook secret key',
        'MIRA_LOG_LEVEL': 'Logging level',
    }
    
    for var, description in recommended_vars.items():
        value = os.getenv(var)
        if value:
            env_vars[var] = value
        else:
            logger.warning(f"Recommended environment variable not set: {var} ({description})")
    
    return env_vars


def load_and_validate_config(config_path: Optional[str] = None) -> MiraConfig:
    """
    Load and validate configuration from file and environment.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Validated MiraConfig instance
    """
    import json
    
    logger = logging.getLogger("mira.config.validation")
    config_dict = {}
    
    # Load from file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            raise
    
    # Validate and return
    return validate_config(config_dict)
