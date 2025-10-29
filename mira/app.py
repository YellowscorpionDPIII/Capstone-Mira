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
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        log_level = self.config.get('logging.level', 'INFO')
        setup_logging(level=log_level)
        
        # Initialize message broker
        self.broker = get_broker()
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize webhook handler if enabled
        self.webhook_handler = None
        if self.config.get('webhook.enabled', False):
            self._initialize_webhook_handler()
            
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


if __name__ == '__main__':
    main()
