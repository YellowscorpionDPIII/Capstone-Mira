"""OrchestratorAgent for routing messages between agents."""
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker
from config import config
import asyncio
import logging


async def call_llm(prompt: str, model: str = None):
    client = config.llm_client()
    model = model or config.models.orchestrator
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.prompts.max_tokens,
            temperature=config.prompts.temperature
        )
    )
    return response.choices[0].message.content


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
        self.logger.info(f"Routing {message_type} to {target_agent_id}", extra={'message_type': message_type})
        response = self._run_async_with_fallback(target_agent.process, message)
        
        return response
        
    def _execute_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow.
        
        Args:
            data: Workflow definition
            
        Returns:
            Workflow execution results
        """
        workflow_type = data.get('workflow_type')
        workflow_data = data.get('data', {})
        
        results = {
            'workflow_type': workflow_type,
            'steps': []
        }
        
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
        
    def _run_async_with_fallback(self, func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute a function with async timeout and fallback to synchronous execution.
        
        This method attempts to run the given function asynchronously with a timeout
        for production safety. If the async execution times out or fails, it falls
        back to synchronous execution to ensure reliability.
        
        Fallback behavior:
        1. First, attempts to run the function in a thread pool with a 30-second timeout
        2. If timeout occurs (asyncio.TimeoutError), falls back to direct synchronous call
        3. If any other error occurs during async execution, falls back to synchronous call
        4. If synchronous fallback also fails, returns an error response
        
        Args:
            func: The function to execute (typically agent.process)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dict[str, Any]: Response from the function execution or error response
            
        Example:
            response = self._run_async_with_fallback(target_agent.process, message)
        """
        try:
            # Try to get or create an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, just call synchronously
                return func(*args, **kwargs)
            except RuntimeError:
                # No running loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run in thread pool with 30-second timeout
                try:
                    response = loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.to_thread(func, *args, **kwargs),
                            timeout=30.0
                        )
                    )
                    return response
                except asyncio.TimeoutError:
                    func_name = getattr(func, '__name__', str(func))
                    self.logger.warning(
                        f"Async execution of {func_name} timed out after 30s, falling back to synchronous execution"
                    )
                    return func(*args, **kwargs)
                finally:
                    loop.close()
        except Exception as e:
            # Fallback to synchronous execution if async fails
            func_name = getattr(func, '__name__', str(func))
            self.logger.warning(f"Async execution of {func_name} failed ({str(e)}), falling back to synchronous execution")
            try:
                return func(*args, **kwargs)
            except Exception as sync_error:
                self.logger.error(f"Both async and sync execution failed: {sync_error}")
                return self.create_response('error', None, str(sync_error))
    
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")
