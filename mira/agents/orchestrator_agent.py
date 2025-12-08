"""OrchestratorAgent for routing messages between agents."""
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker


def _run_async_with_fallback(coro):
    """
    Run an async coroutine, handling nested event loops gracefully.
    
    Args:
        coro: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        raise


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
            'generate_roadmap': 'roadmapping_agent',
            'track_kpi_progress': 'roadmapping_agent'
        }
        
    def register_agent(self, agent: BaseAgent):
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: Agent to register
        """
        if agent is None:
            self.logger.error(
                f"Cannot register None agent. "
                f"Agent state: agent_id={self.agent_id}, registered_agents={list(self.agent_registry.keys())}"
            )
            raise ValueError("Cannot register None agent")
        
        if not hasattr(agent, 'agent_id'):
            self.logger.error(
                f"Invalid agent: missing agent_id attribute. "
                f"Agent state: agent_id={self.agent_id}"
            )
            raise ValueError("Agent must have an agent_id attribute")
        
        self.agent_registry[agent.agent_id] = agent
        self.logger.info(
            f"Registered agent: {agent.agent_id}. "
            f"Total registered agents: {len(self.agent_registry)}. "
            f"Orchestrator: {self.agent_id}"
        )
        
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and route a message to the appropriate agent (synchronous wrapper).
        
        Args:
            message: Message to route
            
        Returns:
            Response from the target agent
        """
        return _run_async_with_fallback(self.process_async(message))
    
    async def process_async(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and route a message to the appropriate agent asynchronously.
        
        Args:
            message: Message to route
            
        Returns:
            Response from the target agent
        """
        if not isinstance(message, dict):
            self.logger.error(
                f"Invalid message type received: expected dict, got {type(message).__name__}. "
                f"Agent state: agent_id={self.agent_id}, registered_agents={list(self.agent_registry.keys())}"
            )
            return self.create_response('error', None, 'Message must be a dictionary')
        
        if not self.validate_message(message):
            self.logger.warning(
                f"Invalid message format: missing required fields. "
                f"Received keys: {list(message.keys())}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            message_type = message.get('type')
            self.logger.debug(
                f"Processing message: type={message_type}, "
                f"agent_id={self.agent_id}, registered_agents={list(self.agent_registry.keys())}"
            )
            
            if message_type == 'workflow':
                return await self._execute_workflow_async(message['data'])
            else:
                return await self._route_message_async(message)
                
        except KeyError as e:
            self.logger.error(
                f"Missing required field in message: {e}. "
                f"Message type: {message.get('type', 'unknown')}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return self.create_response('error', None, f'Missing required field: {e}')
        except Exception as e:
            self.logger.error(
                f"Error processing message: {e}. "
                f"Message type: {message.get('type', 'unknown')}. "
                f"Agent state: agent_id={self.agent_id}, registered_agents={list(self.agent_registry.keys())}"
            )
            return self.create_response('error', None, str(e))
            
    def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate agent (synchronous wrapper).
        
        Args:
            message: Message to route
            
        Returns:
            Response from target agent
        """
        return _run_async_with_fallback(self._route_message_async(message))
    
    async def _route_message_async(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate agent asynchronously.
        
        Args:
            message: Message to route
            
        Returns:
            Response from target agent
        """
        message_type = message.get('type')
        
        if not message_type:
            self.logger.error(
                f"Message type is missing or empty. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return self.create_response('error', None, 'Message type is required')
        
        # Determine target agent
        target_agent_id = self.routing_rules.get(message_type)
        
        if not target_agent_id:
            self.logger.warning(
                f"No routing rule found for message type: {message_type}. "
                f"Available routing rules: {list(self.routing_rules.keys())}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return self.create_response('error', None, f'No routing rule for message type: {message_type}')
            
        target_agent = self.agent_registry.get(target_agent_id)
        
        if not target_agent:
            self.logger.error(
                f"Target agent not found: {target_agent_id}. "
                f"Registered agents: {list(self.agent_registry.keys())}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return self.create_response('error', None, f'Agent not found: {target_agent_id}')
        
        # Route message to target agent
        self.logger.info(
            f"Routing message: type={message_type}, target={target_agent_id}, "
            f"orchestrator={self.agent_id}"
        )
        
        # Check if target agent has async process method
        if hasattr(target_agent, 'process_async'):
            response = await target_agent.process_async(message)
        else:
            # Use asyncio.to_thread to prevent blocking the event loop
            response = await asyncio.to_thread(target_agent.process, message)
        
        return response
        
    def _execute_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow (synchronous wrapper).
        
        Args:
            data: Workflow definition
            
        Returns:
            Workflow execution results
        """
        return _run_async_with_fallback(self._execute_workflow_async(data))
    
    async def _execute_workflow_async(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow asynchronously.
        
        Args:
            data: Workflow definition
            
        Returns:
            Workflow execution results
        """
        if not isinstance(data, dict):
            self.logger.error(
                f"Invalid workflow data type: expected dict, got {type(data).__name__}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            return {
                'workflow_type': None,
                'steps': [],
                'error': 'Workflow data must be a dictionary'
            }
        
        workflow_type = data.get('workflow_type')
        workflow_data = data.get('data', {})
        
        self.logger.info(
            f"Starting workflow execution: type={workflow_type}, "
            f"agent_id={self.agent_id}"
        )
        
        results = {
            'workflow_type': workflow_type,
            'steps': []
        }
        
        if workflow_type == 'project_initialization':
            # Step 1: Generate project plan
            self.logger.debug(f"Workflow step 1: generate_plan for workflow={workflow_type}")
            plan_response = await self._route_message_async({
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
                self.logger.debug(f"Workflow step 2: assess_risks for workflow={workflow_type}")
                risk_response = await self._route_message_async({
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
                    self.logger.debug(f"Workflow step 3: generate_report for workflow={workflow_type}")
                    report_response = await self._route_message_async({
                        'type': 'generate_report',
                        'data': report_data
                    })
                    results['steps'].append({
                        'step': 'generate_report',
                        'status': report_response['status'],
                        'result': report_response.get('data')
                    })
        else:
            self.logger.warning(
                f"Unknown workflow type: {workflow_type}. "
                f"Agent state: agent_id={self.agent_id}"
            )
                    
        self.logger.info(
            f"Completed workflow: type={workflow_type}, "
            f"steps_completed={len(results['steps'])}, "
            f"agent_id={self.agent_id}"
        )
        return results
        
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        if not message_type or not isinstance(message_type, str):
            self.logger.error(
                f"Invalid message_type for routing rule: {message_type}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            raise ValueError("message_type must be a non-empty string")
        
        if not agent_id or not isinstance(agent_id, str):
            self.logger.error(
                f"Invalid agent_id for routing rule: {agent_id}. "
                f"Agent state: agent_id={self.agent_id}"
            )
            raise ValueError("agent_id must be a non-empty string")
        
        self.routing_rules[message_type] = agent_id
        self.logger.info(
            f"Added routing rule: {message_type} -> {agent_id}. "
            f"Total routing rules: {len(self.routing_rules)}. "
            f"Orchestrator: {self.agent_id}"
        )
