"""Main application entry point for Mira platform."""
from typing import Optional
from mira.core.message_broker import get_broker
from mira.core.webhook_handler import WebhookHandler
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.config.settings import get_config
from mira.utils.logging import setup_logging
from mira.utils.structured_logging import setup_structured_logging, set_correlation_id
from mira.utils.graceful_shutdown import get_shutdown_handler
from mira.utils.config_hotreload import enable_hot_reload
from mira.utils.secrets_manager import create_secrets_manager, set_secrets_manager


class MiraApplication:
    """
    Main application class for the Mira platform.
    
    Initializes and coordinates all agents, integrations, and services.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Mira application.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Store config path for hot-reload
        self.config_path = config_path
        
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup structured logging with correlation IDs
        log_level = self.config.get('logging.level', 'INFO')
        use_json = self.config.get('logging.json_format', True)
        log_file = self.config.get('logging.file', None)
        
        if use_json:
            setup_structured_logging(level=log_level, log_file=log_file)
        else:
            setup_logging(level=log_level, log_file=log_file)
        
        # Initialize secrets manager
        self.secrets_manager = create_secrets_manager(self.config.config_data)
        set_secrets_manager(self.secrets_manager)
        
        # Start auto-refresh for secrets if enabled
        if self.config.get('secrets.auto_refresh', False):
            self.secrets_manager.start_auto_refresh()
        
        # Enable hot-reload if configured
        self.hot_reload_config = None
        if config_path and self.config.get('config.hot_reload', False):
            self.hot_reload_config = enable_hot_reload(
                self.config, 
                config_path,
                poll_interval=self.config.get('config.poll_interval', 5)
            )
            self.hot_reload_config.register_reload_callback(self._on_config_reload)
        
        # Initialize message broker
        self.broker = get_broker()
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize webhook handler if enabled
        self.webhook_handler = None
        if self.config.get('webhook.enabled', False):
            self._initialize_webhook_handler()
        
        # Setup graceful shutdown handlers
        self._setup_shutdown_handlers()
            
    def _initialize_agents(self):
        """Initialize all agents."""
        # Create orchestrator
        self.orchestrator = OrchestratorAgent(config=self.config.get('agents.orchestrator_agent'))
        self.agents['orchestrator'] = self.orchestrator
        
        # Create specialized agents
        if self.config.get('agents.project_plan_agent.enabled', True):
            plan_agent = ProjectPlanAgent(config=self.config.get('agents.project_plan_agent'))
            self.agents['project_plan'] = plan_agent
            self.orchestrator.register_agent(plan_agent)
            
        if self.config.get('agents.risk_assessment_agent.enabled', True):
            risk_agent = RiskAssessmentAgent(config=self.config.get('agents.risk_assessment_agent'))
            self.agents['risk_assessment'] = risk_agent
            self.orchestrator.register_agent(risk_agent)
            
        if self.config.get('agents.status_reporter_agent.enabled', True):
            status_agent = StatusReporterAgent(config=self.config.get('agents.status_reporter_agent'))
            self.agents['status_reporter'] = status_agent
            self.orchestrator.register_agent(status_agent)
            
    def _initialize_webhook_handler(self):
        """Initialize webhook handler for external integrations."""
        secret_key = self.config.get('webhook.secret_key')
        self.webhook_handler = WebhookHandler(secret_key=secret_key)
        
        # Register webhook handlers for each integration
        self.webhook_handler.register_handler('github', self._handle_github_webhook)
        self.webhook_handler.register_handler('trello', self._handle_trello_webhook)
        self.webhook_handler.register_handler('jira', self._handle_jira_webhook)
        
    def _handle_github_webhook(self, data: dict) -> dict:
        """Handle GitHub webhook events."""
        # Process GitHub events and route to appropriate agents
        return {'status': 'processed', 'service': 'github'}
        
    def _handle_trello_webhook(self, data: dict) -> dict:
        """Handle Trello webhook events."""
        # Process Trello events and route to appropriate agents
        return {'status': 'processed', 'service': 'trello'}
        
    def _handle_jira_webhook(self, data: dict) -> dict:
        """Handle Jira webhook events."""
        # Process Jira events and route to appropriate agents
        return {'status': 'processed', 'service': 'jira'}
    
    def _setup_shutdown_handlers(self):
        """Setup graceful shutdown handlers."""
        shutdown_handler = get_shutdown_handler()
        
        # Register cleanup handlers in order
        shutdown_handler.register_handler(self._cleanup_webhook_handler)
        shutdown_handler.register_handler(self._cleanup_broker)
        shutdown_handler.register_handler(self._cleanup_secrets)
        shutdown_handler.register_handler(self._cleanup_config_watcher)
        
        # Setup signal handlers
        shutdown_handler.setup()
    
    def _cleanup_webhook_handler(self):
        """Cleanup webhook handler."""
        if self.webhook_handler:
            from mira.utils.structured_logging import get_structured_logger
            logger = get_structured_logger('app')
            logger.info("Stopping webhook handler...")
            # Webhook handler cleanup would go here
    
    def _cleanup_broker(self):
        """Cleanup message broker."""
        if self.broker:
            from mira.utils.structured_logging import get_structured_logger
            logger = get_structured_logger('app')
            logger.info("Stopping message broker...")
            self.broker.stop()
    
    def _cleanup_secrets(self):
        """Cleanup secrets manager."""
        if self.secrets_manager:
            from mira.utils.structured_logging import get_structured_logger
            logger = get_structured_logger('app')
            logger.info("Stopping secrets auto-refresh...")
            self.secrets_manager.stop_auto_refresh()
    
    def _cleanup_config_watcher(self):
        """Cleanup config watcher."""
        if self.hot_reload_config:
            from mira.utils.structured_logging import get_structured_logger
            logger = get_structured_logger('app')
            logger.info("Stopping configuration watcher...")
            self.hot_reload_config.stop_watching()
    
    def _on_config_reload(self, new_config: dict):
        """
        Handle configuration reload.
        
        Args:
            new_config: New configuration dictionary
        """
        from mira.utils.structured_logging import get_structured_logger
        logger = get_structured_logger('app')
        logger.info("Configuration reloaded, applying changes...")
        
        # Update logging level if changed
        new_level = self.config.get('logging.level', 'INFO')
        import logging
        logging.getLogger('mira').setLevel(getattr(logging, new_level.upper()))
        
    def start(self):
        """Start the Mira application."""
        # Set correlation ID for startup
        set_correlation_id()
        
        from mira.utils.structured_logging import get_structured_logger
        logger = get_structured_logger('app')
        logger.info("Starting Mira application...")
        
        # Start message broker
        if self.config.get('broker.enabled', True):
            self.broker.start()
            
        # Start webhook server if enabled
        if self.webhook_handler and self.config.get('webhook.enabled', False):
            host = self.config.get('webhook.host', '0.0.0.0')
            port = self.config.get('webhook.port', 5000)
            self.webhook_handler.run(host=host, port=port)
            
    def stop(self):
        """Stop the Mira application."""
        from mira.utils.structured_logging import get_structured_logger
        logger = get_structured_logger('app')
        logger.info("Stopping Mira application...")
        
        # Use graceful shutdown handler
        shutdown_handler = get_shutdown_handler()
        shutdown_handler.shutdown()
            
    def process_message(self, message: dict) -> dict:
        """
        Process a message through the orchestrator.
        
        Args:
            message: Message to process
            
        Returns:
            Processing result
        """
        # Generate correlation ID for this message
        correlation_id = set_correlation_id()
        
        from mira.utils.structured_logging import get_structured_logger
        logger = get_structured_logger('app')
        logger.info("Processing message", extra={
            'message_type': message.get('type'),
            'correlation_id': correlation_id
        })
        
        return self.orchestrator.process(message)


def main():
    """Main entry point for the application."""
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = MiraApplication(config_path)
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\nShutting down Mira...")
        app.stop()
    except Exception as e:
        from mira.utils.structured_logging import get_structured_logger
        logger = get_structured_logger('app')
        logger.error(f"Application error: {e}", exc_info=True)
        app.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
