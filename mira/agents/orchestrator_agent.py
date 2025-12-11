"""OrchestratorAgent for routing messages between agents."""
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker
from mira.agents.governance_agent import GovernanceAgent


class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating workflow between other agents.
    
    This agent routes messages to appropriate agents based on message
    type and coordinates multi-agent workflows.
    """
    
    def __init__(self, agent_id: str = "orchestrator_agent", config: Dict[str, Any] = None):
        """Initialize the OrchestratorAgent."""
        super().__init__(agent_id, config)
        self.broker = get_broker()
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.routing_rules = self._initialize_routing_rules()
        
        # Initialize governance agent for risk assessment and human-in-the-loop validation
        self.governance_agent = GovernanceAgent(config=config.get('governance', {}) if config else {})
        self.register_agent(self.governance_agent)
        
    def _initialize_routing_rules(self) -> Dict[str, str]:
        """
        Initialize message routing rules.
        
        Returns:
            Dictionary mapping message types to agent IDs
        """
        return {
            'generate_plan': 'project_plan_agent',
            'update_plan': 'project_plan_agent',
            'assess_risks': 'risk_assessment_agent',
            'update_risk': 'risk_assessment_agent',
            'generate_report': 'status_reporter_agent',
            'schedule_report': 'status_reporter_agent',
            'assess_governance': 'governance_agent',
            'check_human_validation': 'governance_agent'
        }
        
    def register_agent(self, agent: BaseAgent):
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: Agent to register
        """
        self.agent_registry[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.agent_id}")
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and route a message to the appropriate agent.
        
        Args:
            message: Message to route
            
        Returns:
            Response from the target agent
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            message_type = message['type']
            
            if message_type == 'workflow':
                return self._execute_workflow(message['data'])
            else:
                return self._route_message(message)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return self.create_response('error', None, str(e))
            
    def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: Message to route
            
        Returns:
            Response from target agent
        """
        message_type = message['type']
        
        # Determine target agent
        target_agent_id = self.routing_rules.get(message_type)
        
        if not target_agent_id:
            return self.create_response('error', None, f'No routing rule for message type: {message_type}')
            
        target_agent = self.agent_registry.get(target_agent_id)
        
        if not target_agent:
            return self.create_response('error', None, f'Agent not found: {target_agent_id}')
            
        # Route message to target agent
        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        response = target_agent.process(message)
        
        return response
        
    def _execute_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow with governance checks.
        
        Args:
            data: Workflow definition
            
        Returns:
            Workflow execution results with governance assessment
        """
        workflow_type = data.get('workflow_type')
        workflow_data = data.get('data', {})
        
        results = {
            'workflow_type': workflow_type,
            'steps': [],
            'governance': None  # Will be populated if governance data is provided
        }
        
        # Perform governance assessment if governance data is provided
        governance_data = data.get('governance_data')
        if governance_data:
            try:
                governance_response = self._route_message({
                    'type': 'assess_governance',
                    'data': governance_data
                })
                
                if governance_response['status'] == 'success':
                    governance_assessment = governance_response['data']
                    results['governance'] = governance_assessment
                    results['risk_level'] = governance_assessment['risk_level']
                    results['requires_human_validation'] = governance_assessment['requires_human_validation']
                    
                    self.logger.info(
                        f"Governance assessment completed: risk_level={governance_assessment['risk_level']}, "
                        f"requires_validation={governance_assessment['requires_human_validation']}"
                    )
                    
                    # If high risk or requires validation, mark workflow status accordingly
                    if governance_assessment['requires_human_validation']:
                        results['status'] = 'pending_approval'
                        self.logger.warning("Workflow requires human validation before proceeding")
                        
                        # Publish to message broker for HITL dashboard integration
                        self._publish_pending_approval(workflow_type, governance_assessment, workflow_data)
                else:
                    # Governance assessment failed, fallback to 'low' risk
                    self.logger.error(
                        f"Governance assessment failed: {governance_response.get('error', 'Unknown error')}, "
                        f"falling back to 'low' risk level"
                    )
                    results['governance'] = {'risk_level': 'low', 'requires_human_validation': False}
                    results['risk_level'] = 'low'
                    
            except Exception as e:
                # On agent failure, fallback to 'low' risk to prevent workflow halts
                self.logger.error(
                    f"Exception during governance assessment: {e}, "
                    f"falling back to 'low' risk level to prevent workflow halt"
                )
                results['governance'] = {'risk_level': 'low', 'requires_human_validation': False}
                results['risk_level'] = 'low'
        
        if workflow_type == 'project_initialization':
            # Step 1: Generate project plan
            plan_response = self._route_message({
                'type': 'generate_plan',
                'data': workflow_data
            })
            results['steps'].append({
                'step': 'generate_plan',
                'status': plan_response['status'],
                'result': plan_response.get('data')
            })
            
            # Step 2: Assess risks based on plan
            if plan_response['status'] == 'success':
                plan = plan_response['data']
                risk_response = self._route_message({
                    'type': 'assess_risks',
                    'data': plan
                })
                results['steps'].append({
                    'step': 'assess_risks',
                    'status': risk_response['status'],
                    'result': risk_response.get('data')
                })
                
                # Step 3: Generate initial status report
                if risk_response['status'] == 'success':
                    risks = risk_response['data']
                    report_data = {**plan, 'risks': risks.get('risks', [])}
                    report_response = self._route_message({
                        'type': 'generate_report',
                        'data': report_data
                    })
                    results['steps'].append({
                        'step': 'generate_report',
                        'status': report_response['status'],
                        'result': report_response.get('data')
                    })
                    
        self.logger.info(f"Completed workflow: {workflow_type}")
        return results
        
    def _publish_pending_approval(self, workflow_type: str, governance_assessment: Dict[str, Any], workflow_data: Dict[str, Any]) -> None:
        """
        Publish pending approval workflow to message broker for HITL dashboard integration.
        
        This enables the scaling dashboard agent to monitor workflows requiring human validation.
        
        Args:
            workflow_type: Type of workflow pending approval
            governance_assessment: Governance assessment results
            workflow_data: Original workflow data
        """
        try:
            pending_approval_message = {
                'type': 'pending_approval',
                'workflow_type': workflow_type,
                'governance': governance_assessment,
                'workflow_data': workflow_data,
                'timestamp': self.create_response('success', None)['timestamp']
            }
            
            # Publish to broker for consumption by scaling dashboard or other monitoring agents
            self.broker.publish('governance.pending_approval', pending_approval_message)
            
            self.logger.info(
                f"Published pending approval notification for {workflow_type} workflow to message broker"
            )
        except Exception as e:
            self.logger.error(f"Failed to publish pending approval notification: {e}")
        
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")
