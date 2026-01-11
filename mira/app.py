"""Main application entry point for Mira platform."""
from typing import Optional
import logging
from datetime import datetime
from mira.core.message_broker import get_broker
from mira.core.webhook_handler import WebhookHandler
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.config.settings import get_config
from mira.utils.logging import setup_logging, setup_structured_logging
from mira.utils.shutdown_handler import get_shutdown_handler, install_signal_handlers
from mira.utils.config_hotreload import HotReloadConfig
from mira.utils.structured_logging import CorrelationContext, set_correlation_id


class MiraApplication:
    """
    Main application class for the Mira platform.
    
    Initializes and coordinates all agents, integrations, and services.
    Supports structured logging, graceful shutdown, config hot-reload, and secrets management.
    """
    
    def __init__(self, config_path: Optional[str] = None, 
                 use_structured_logging: bool = False,
                 enable_hot_reload: bool = False):
        """
        Initialize the Mira application.
        
        Args:
            config_path: Optional path to configuration file
            use_structured_logging: Enable JSON-formatted structured logging with correlation IDs
            enable_hot_reload: Enable configuration hot-reload
        """
        # Load configuration
        self.config = get_config(config_path)
        self.config_path = config_path
        self.logger = None
        self.hot_reload_config = None
        self.shutdown_handler = get_shutdown_handler()
        
        # Setup logging (structured or traditional)
        log_level = self.config.get('logging.level', 'INFO')
        if use_structured_logging:
            log_file = self.config.get('logging.file', None)
            setup_structured_logging(level=log_level, log_file=log_file, use_json=True)
            self.logger = logging.getLogger('mira.app')
            self.logger.info("Initialized with structured logging")
        else:
            setup_logging(level=log_level)
            self.logger = logging.getLogger('mira.app')
            
        # Setup config hot-reload if enabled and config path provided
        if enable_hot_reload and config_path:
            self._setup_hot_reload()
            
        # Install signal handlers for graceful shutdown
        install_signal_handlers()
        
        # Initialize message broker
        self.broker = get_broker()
        
        # Register broker cleanup on shutdown (lower priority = agents should stop first)
        def stop_broker():
            """Stop message broker if running."""
            if self.broker and hasattr(self.broker, 'running') and self.broker.running:
                self.broker.stop()
            elif self.broker and hasattr(self.broker, 'stop'):
                # Try to stop even if we can't check running status
                try:
                    self.broker.stop()
                except:
                    pass
        
        self.shutdown_handler.register_callback(stop_broker, name='message_broker_stop', priority=100)
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize webhook handler if enabled
        self.webhook_handler = None
        if self.config.get('webhook.enabled', False):
            self._initialize_webhook_handler()
            
    def _setup_hot_reload(self):
        """Setup configuration hot-reload."""
        try:
            self.hot_reload_config = HotReloadConfig(self.config, self.config_path)
            
            # Register callback to log config reloads
            def on_config_reload():
                self.logger.info("Configuration reloaded")
                
            self.hot_reload_config.register_reload_callback(on_config_reload, 'log_reload')
            self.hot_reload_config.enable_hot_reload()
            
            # Register hot-reload cleanup on shutdown (higher priority = cleanup tasks)
            self.shutdown_handler.register_callback(
                lambda: self.hot_reload_config.disable_hot_reload() if self.hot_reload_config else None,
                name='config_hotreload_stop',
                priority=150
            )
            
            self.logger.info(f"Config hot-reload enabled for: {self.config_path}")
        except Exception as e:
            self.logger.warning(f"Failed to enable config hot-reload: {e}")
            
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
        
        # Register health check endpoint for K8s liveness/readiness probes
        self.webhook_handler.register_handler('healthz', self._handle_healthz)
        self.webhook_handler.register_handler('readyz', self._handle_readyz)
    
    def _handle_healthz(self, data: dict) -> dict:
        """
        Handle liveness probe for Kubernetes.
        
        Returns 200 OK if the application is alive (can accept traffic).
        """
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'mira'
        }
    
    def _handle_readyz(self, data: dict) -> dict:
        """
        Handle readiness probe for Kubernetes.
        
        Returns 200 OK if the application is ready to handle requests.
        Checks critical components like broker and agents.
        """
        ready = True
        components = {}
        
        # Check message broker
        if self.config.get('broker.enabled', True):
            broker_ready = hasattr(self.broker, 'running') and self.broker.running
            components['message_broker'] = 'ready' if broker_ready else 'not_ready'
            ready = ready and broker_ready
        
        # Check if shutdown is in progress
        shutdown_in_progress = self.shutdown_handler.is_shutting_down()
        components['shutdown_status'] = 'shutting_down' if shutdown_in_progress else 'running'
        ready = ready and not shutdown_in_progress
        
        # Check agents
        components['agents_count'] = len(self.agents)
        components['agents_ready'] = len(self.agents) > 0
        ready = ready and len(self.agents) > 0
        
        return {
            'status': 'ready' if ready else 'not_ready',
            'timestamp': datetime.now().isoformat(),
            'components': components
        }
        
    def _handle_github_webhook(self, data: dict) -> dict:
        """Handle GitHub webhook events."""
        # Process GitHub events and route to appropriate agents
        with CorrelationContext():
            self.logger.info("Processing GitHub webhook", extra={'service': 'github'})
            return {'status': 'processed', 'service': 'github'}
        
    def _handle_trello_webhook(self, data: dict) -> dict:
        """Handle Trello webhook events."""
        # Process Trello events and route to appropriate agents
        with CorrelationContext():
            self.logger.info("Processing Trello webhook", extra={'service': 'trello'})
            return {'status': 'processed', 'service': 'trello'}
        
    def _handle_jira_webhook(self, data: dict) -> dict:
        """Handle Jira webhook events."""
        # Process Jira events and route to appropriate agents
        with CorrelationContext():
            self.logger.info("Processing Jira webhook", extra={'service': 'jira'})
            return {'status': 'processed', 'service': 'jira'}
        
    def start(self):
        """Start the Mira application."""
        self.logger.info("Starting Mira application")
        
        # Start message broker
        if self.config.get('broker.enabled', True):
            self.broker.start()
            self.logger.info("Message broker started")
            
        # Start webhook server if enabled
        if self.webhook_handler and self.config.get('webhook.enabled', False):
            host = self.config.get('webhook.host', '0.0.0.0')
            port = self.config.get('webhook.port', 5000)
            self.logger.info(f"Starting webhook handler on {host}:{port}")
            self.webhook_handler.run(host=host, port=port)
            
    def stop(self):
        """
        Stop the Mira application gracefully.
        
        This method triggers the shutdown handler which will execute all
        registered cleanup callbacks in reverse order.
        """
        self.logger.info("Stopping Mira application")
        self.shutdown_handler.shutdown(exit_code=None)
            
    def process_message(self, message: dict) -> dict:
        """
        Process a message through the orchestrator with correlation tracking.
        
        Args:
            message: Message to process
            
        Returns:
            Processing result
        """
        # Use correlation context for request tracing
        with CorrelationContext() as correlation_id:
            self.logger.info(f"Processing message", 
                           extra={'message_type': message.get('type')})
            result = self.orchestrator.process(message)
            result['correlation_id'] = correlation_id
            return result


def main():
    """Main entry point for the application."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Mira Multi-Agent Workflow Platform')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--structured-logging', action='store_true', 
                       help='Enable JSON-formatted structured logging')
    parser.add_argument('--hot-reload', action='store_true',
                       help='Enable configuration hot-reload')
    
    args = parser.parse_args()
    
    app = MiraApplication(
        config_path=args.config,
        use_structured_logging=args.structured_logging,
        enable_hot_reload=args.hot_reload
    )
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\nShutting down Mira...")
        app.stop()


if __name__ == '__main__':
    main()
