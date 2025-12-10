"""Main application entry point for Mira platform."""
from typing import Optional
import logging
from mira.core.message_broker import get_broker
from mira.core.webhook_handler import WebhookHandler
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.config.settings import get_config
from mira.config.validation import load_and_validate_config, ValidationError
from mira.utils.logging import setup_logging
from mira.security.api_key_manager import APIKeyManager
from mira.security.audit_logger import AuditLogger
from mira.security.webhook_security import WebhookSecurity
from mira.observability.metrics import MetricsCollector
from mira.observability.health import HealthCheck, check_airtable_connection, check_broker_status


class MiraApplication:
    """
    Main application class for the Mira platform.
    
    Initializes and coordinates all agents, integrations, and services.
    Enhanced with security, observability, and operational controls.
    """
    
    def __init__(self, config_path: Optional[str] = None, validate_config_on_startup: bool = True):
        """
        Initialize the Mira application.
        
        Args:
            config_path: Optional path to configuration file
            validate_config_on_startup: Whether to validate configuration on startup
        """
        # Validate configuration first if requested
        if validate_config_on_startup:
            try:
                validated_config = load_and_validate_config(config_path)
                logging.info("✓ Configuration validation successful")
            except ValidationError as e:
                logging.error("❌ Configuration validation failed:")
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error['loc'])
                    logging.error(f"  {loc}: {error['msg']}")
                raise
        
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        log_level = self.config.get('logging.level', 'INFO')
        audit_log_file = self.config.get('logging.audit_log_file')
        setup_logging(level=log_level)
        
        # Initialize audit logger
        self.audit_logger = AuditLogger(log_file=audit_log_file)
        logging.info("Audit logger initialized")
        
        # Initialize API key manager
        self.api_key_manager = APIKeyManager(audit_logger=self.audit_logger)
        logging.info("API key manager initialized")
        
        # Initialize webhook security
        self.webhook_security = WebhookSecurity(audit_logger=self.audit_logger)
        self._configure_webhook_security()
        logging.info("Webhook security initialized")
        
        # Initialize metrics collector
        metrics_enabled = self.config.get('observability.metrics_enabled', True)
        self.metrics = MetricsCollector(enabled=metrics_enabled)
        logging.info(f"Metrics collector initialized (enabled={metrics_enabled})")
        
        # Initialize health check
        self.health_check = HealthCheck()
        self._register_health_checks()
        logging.info("Health check system initialized")
        
        # Initialize message broker
        self.broker = get_broker()
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize webhook handler if enabled
        self.webhook_handler = None
        if self.config.get('webhook.enabled', False):
            self._initialize_webhook_handler()
            
        # Check maintenance mode
        self.maintenance_mode = self.config.get('operational.maintenance_mode', False)
        if self.maintenance_mode:
            logging.warning("⚠️  Application started in MAINTENANCE MODE")
            
    def _configure_webhook_security(self):
        """Configure webhook security settings."""
        # Configure IP allowlist
        ip_allowlist = self.config.get('security.ip_allowlist', [])
        for ip in ip_allowlist:
            self.webhook_security.add_ip_to_allowlist(ip)
            
        # Configure IP denylist
        ip_denylist = self.config.get('security.ip_denylist', [])
        for ip in ip_denylist:
            self.webhook_security.add_ip_to_denylist(ip)
            
        # Configure service secrets
        webhook_secrets = self.config.get('security.webhook_secrets', {})
        for service, secret in webhook_secrets.items():
            self.webhook_security.set_service_secret(service, secret)
            
    def _register_health_checks(self):
        """Register health check dependencies."""
        # Register broker health check
        self.health_check.register_dependency(
            'message_broker',
            lambda: check_broker_status(self.broker)
        )
        
        # Register Airtable health check if enabled
        if self.config.get('integrations.airtable.enabled', False):
            api_key = self.config.get('integrations.airtable.api_key')
            base_id = self.config.get('integrations.airtable.base_id')
            self.health_check.register_dependency(
                'airtable',
                lambda: check_airtable_connection(api_key, base_id)
            )
            
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
        maintenance_mode = self.config.get('operational.maintenance_mode', False)
        
        self.webhook_handler = WebhookHandler(
            secret_key=secret_key,
            webhook_security=self.webhook_security,
            metrics_collector=self.metrics,
            health_check=self.health_check,
            maintenance_mode=maintenance_mode
        )
        
        # Register webhook handlers for each integration
        self.webhook_handler.register_handler('github', self._handle_github_webhook)
        self.webhook_handler.register_handler('trello', self._handle_trello_webhook)
        self.webhook_handler.register_handler('jira', self._handle_jira_webhook)
        
    def _handle_github_webhook(self, data: dict) -> dict:
        """Handle GitHub webhook events."""
        # Instrument with metrics
        with self.metrics.timer('webhook.handler.github'):
            # Process GitHub events and route to appropriate agents
            self.metrics.increment('webhook.events.processed', tags={'service': 'github'})
            return {'status': 'processed', 'service': 'github'}
        
    def _handle_trello_webhook(self, data: dict) -> dict:
        """Handle Trello webhook events."""
        # Instrument with metrics
        with self.metrics.timer('webhook.handler.trello'):
            # Process Trello events and route to appropriate agents
            self.metrics.increment('webhook.events.processed', tags={'service': 'trello'})
            return {'status': 'processed', 'service': 'trello'}
        
    def _handle_jira_webhook(self, data: dict) -> dict:
        """Handle Jira webhook events."""
        # Instrument with metrics
        with self.metrics.timer('webhook.handler.jira'):
            # Process Jira events and route to appropriate agents
            self.metrics.increment('webhook.events.processed', tags={'service': 'jira'})
            return {'status': 'processed', 'service': 'jira'}
        
    def start(self):
        """Start the Mira application."""
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
        if self.broker:
            self.broker.stop()
            
    def process_message(self, message: dict) -> dict:
        """
        Process a message through the orchestrator.
        
        Args:
            message: Message to process
            
        Returns:
            Processing result
        """
        # Check maintenance mode
        if self.maintenance_mode:
            return {
                'status': 'error',
                'error': 'System is in maintenance mode',
                'message': self.config.get('operational.maintenance_message', 
                                          'System is currently under maintenance')
            }
        
        # Instrument with metrics
        self.metrics.increment('messages.received')
        
        with self.metrics.timer('message.processing'):
            result = self.orchestrator.process(message)
        
        self.metrics.increment('messages.processed', tags={'status': result.get('status', 'unknown')})
        return result


def main():
    """Main entry point for the application."""
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        app = MiraApplication(config_path, validate_config_on_startup=True)
        logging.info("✓ Mira application initialized successfully")
        app.start()
    except ValidationError as e:
        logging.error("Configuration validation failed. Please check your configuration.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down Mira...")
        app.stop()
    except Exception as e:
        logging.error(f"Failed to start Mira: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
