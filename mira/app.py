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
        rate_limit_enabled = self.config.get('webhook.rate_limit_enabled', True)
        self.webhook_handler = WebhookHandler(
            secret_key=secret_key,
            rate_limit_enabled=rate_limit_enabled
        )
        
        # Register webhook handlers for each integration
        self.webhook_handler.register_handler('github', self._handle_github_webhook)
        self.webhook_handler.register_handler('trello', self._handle_trello_webhook)
        self.webhook_handler.register_handler('jira', self._handle_jira_webhook)
        self.webhook_handler.register_handler('n8n', self._handle_n8n_webhook)
        
        # Register health check endpoint
        self._setup_health_check()
        
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
    
    def _handle_n8n_webhook(self, data: dict) -> dict:
        """
        Handle n8n workflow webhook events.
        
        Processes incoming n8n workflow triggers and routes to appropriate agents.
        """
        # Process n8n events and route to appropriate agents
        workflow_type = data.get('workflow_type', 'unknown')
        self.logger.info(f"Processing n8n workflow: {workflow_type}")
        
        # Route to orchestrator for workflow execution
        if workflow_type == 'project_initialization':
            return self.orchestrator.process({
                'type': 'workflow',
                'data': data
            })
        
        return {'status': 'processed', 'service': 'n8n', 'workflow_type': workflow_type}
        
    def _setup_health_check(self):
        """Set up health check endpoint for Kubernetes probes."""
        from flask import jsonify
        
        @self.webhook_handler.app.route('/healthz', methods=['GET'])
        def health_check():
            """
            Health check endpoint for Kubernetes readiness/liveness probes.
            
            Checks:
            - Configuration validity
            - Agent initialization status
            - Message broker status (if enabled)
            
            Returns:
                200 OK if healthy, 503 Service Unavailable if unhealthy
            """
            health_status = {
                'status': 'healthy',
                'checks': {}
            }
            
            # Check configuration
            try:
                if self.config:
                    health_status['checks']['configuration'] = 'ok'
                else:
                    health_status['checks']['configuration'] = 'failed'
                    health_status['status'] = 'unhealthy'
            except Exception as e:
                health_status['checks']['configuration'] = f'error: {str(e)}'
                health_status['status'] = 'unhealthy'
                
            # Check agents
            try:
                if self.agents and len(self.agents) > 0:
                    health_status['checks']['agents'] = 'ok'
                    health_status['checks']['agent_count'] = len(self.agents)
                else:
                    health_status['checks']['agents'] = 'no agents initialized'
                    health_status['status'] = 'unhealthy'
            except Exception as e:
                health_status['checks']['agents'] = f'error: {str(e)}'
                health_status['status'] = 'unhealthy'
                
            # Check broker if enabled
            if self.config.get('broker.enabled', True):
                try:
                    if self.broker:
                        if hasattr(self.broker, 'running'):
                            broker_status = 'running' if self.broker.running else 'stopped'
                            health_status['checks']['broker'] = broker_status
                            if not self.broker.running:
                                health_status['status'] = 'degraded'
                        else:
                            health_status['checks']['broker'] = 'status unavailable'
                    else:
                        health_status['checks']['broker'] = 'not initialized'
                        health_status['status'] = 'unhealthy'
                except Exception as e:
                    health_status['checks']['broker'] = f'error: {str(e)}'
                    health_status['status'] = 'unhealthy'
            else:
                health_status['checks']['broker'] = 'disabled'
                
            # Return appropriate status code
            if health_status['status'] == 'healthy':
                return jsonify(health_status), 200
            elif health_status['status'] == 'degraded':
                return jsonify(health_status), 200
            else:
                return jsonify(health_status), 503
        
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
