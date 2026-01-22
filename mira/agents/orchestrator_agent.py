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
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
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
        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        response = target_agent.process(message)
        
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
        
    async def _run_workflow_steps_async(self, workflow_type: str, workflow_data: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute workflow steps asynchronously.
        
        Args:
            workflow_type: Type of workflow to execute
            workflow_data: Data for workflow execution
            results: Results dictionary to populate with step results
            
        Returns:
            Updated results dictionary with workflow execution results
        """
        if workflow_type == 'project_initialization':
            # Step 1: Generate project plan
            loop = asyncio.get_running_loop()
            plan_response = await loop.run_in_executor(
                None,
                lambda: self._route_message({
                    'type': 'generate_plan',
                    'data': workflow_data
                })
            )
            results['steps'].append({
                'step': 'generate_plan',
                'status': plan_response['status'],
                'result': plan_response.get('data')
            })
            
            # Step 2: Assess risks based on plan
            if plan_response['status'] == 'success':
                plan = plan_response['data']
                risk_response = await loop.run_in_executor(
                    None,
                    lambda: self._route_message({
                        'type': 'assess_risks',
                        'data': plan
                    })
                )
                results['steps'].append({
                    'step': 'assess_risks',
                    'status': risk_response['status'],
                    'result': risk_response.get('data')
                })
                
                # Step 3: Generate initial status report
                if risk_response['status'] == 'success':
                    risks = risk_response['data']
                    report_data = {**plan, 'risks': risks.get('risks', [])}
                    report_response = await loop.run_in_executor(
                        None,
                        lambda: self._route_message({
                            'type': 'generate_report',
                            'data': report_data
                        })
                    )
                    results['steps'].append({
                        'step': 'generate_report',
                        'status': report_response['status'],
                        'result': report_response.get('data')
                    })
        
        return results
    
    async def _execute_workflow_async(self, data: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Execute a multi-step workflow asynchronously with timeout protection.
        
        Args:
            data: Workflow definition containing workflow_type and workflow data
            timeout: Timeout in seconds (default: 30.0). Note: Sub-second timeouts (< 1.0s)
                     are supported but may result in immediate timeout for complex workflows.
            
        Returns:
            Dict[str, Any]: Workflow execution results with one of the following structures:
            
            Success Response (no timeout):
                {
                    'workflow_type': str,
                    'steps': [
                        {'step': str, 'status': str, 'result': Any},
                        ...
                    ]
                }
            
            Timeout Response:
                {
                    'workflow_type': str,
                    'status': 'timeout',
                    'error': str,
                    'steps': [...],  # Completed steps only
                    'partial_progress': {
                        'completed_steps': [str],  # List of completed step names
                        'total_steps_completed': int,
                        'timeout_seconds': float
                    }
                }
            
            Error Response (exception occurred):
                {
                    'workflow_type': str,
                    'status': 'error',
                    'error': str,
                    'steps': [...]  # Steps completed before error
                }
        """
        workflow_type = data.get('workflow_type')
        workflow_data = data.get('data', {})
        
        results = {
            'workflow_type': workflow_type,
            'steps': []
        }
        
        # Create a task for the workflow execution
        workflow_task = None
        
        try:
            # Validate timeout value and warn for edge cases
            if timeout < 0:
                raise ValueError(f"Timeout must be non-negative, got {timeout}")
            if timeout < 1.0:
                self.logger.warning(
                    f"Sub-second timeout specified ({timeout}s). "
                    f"Workflow may timeout immediately for complex operations.",
                    extra={
                        'workflow_type': workflow_type,
                        'timeout_seconds': timeout,
                        'warning_type': 'sub_second_timeout'
                    }
                )
            
            # Create and wrap workflow execution in asyncio.wait_for with timeout
            workflow_task = asyncio.create_task(
                self._run_workflow_steps_async(workflow_type, workflow_data, results)
            )
            results = await asyncio.wait_for(workflow_task, timeout=timeout)
            
            self.logger.info(
                f"Workflow completed successfully",
                extra={
                    'workflow_type': workflow_type,
                    'total_steps': len(results.get('steps', [])),
                    'event_type': 'workflow_completed'
                }
            )
            
        except asyncio.TimeoutError:
            # Cancel the workflow task to clean up resources
            if workflow_task and not workflow_task.done():
                workflow_task.cancel()
                try:
                    await workflow_task
                except asyncio.CancelledError:
                    pass  # Expected when we cancel the task
            
            # Extract completed steps with error handling
            completed_steps = []
            try:
                steps_data = results.get('steps', [])
                if not isinstance(steps_data, list):
                    self.logger.error(
                        f"Invalid steps data type: {type(steps_data).__name__}. Expected list.",
                        extra={
                            'workflow_type': workflow_type,
                            'error_type': 'invalid_steps_format'
                        }
                    )
                    steps_data = []
                
                for step in steps_data:
                    if isinstance(step, dict):
                        step_name = step.get('step', 'unknown')
                        completed_steps.append(step_name)
                    else:
                        self.logger.warning(
                            f"Invalid step format: {type(step).__name__}. Expected dict.",
                            extra={
                                'workflow_type': workflow_type,
                                'error_type': 'invalid_step_format'
                            }
                        )
            except Exception as e:
                self.logger.error(
                    f"Error extracting completed steps: {e}",
                    extra={
                        'workflow_type': workflow_type,
                        'error_type': 'step_extraction_failed',
                        'exception': str(e)
                    }
                )
                completed_steps = []  # Fallback to empty list
            
            # Structured logging for timeout events (without sensitive data)
            self.logger.error(
                "Workflow execution timed out",
                extra={
                    'workflow_type': workflow_type,
                    'message_type': 'workflow',
                    'timeout_seconds': timeout,
                    'completed_steps_count': len(completed_steps),
                    'completed_steps': completed_steps,  # Step names only, no data
                    'event_type': 'workflow_timeout'
                }
            )
            
            # Return response indicating timeout with partial progress
            results['status'] = 'timeout'
            results['error'] = f'Workflow execution timed out after {timeout} seconds'
            results['partial_progress'] = {
                'completed_steps': completed_steps,  # Guaranteed to be a list
                'total_steps_completed': len(completed_steps),
                'timeout_seconds': timeout
            }
        
        except Exception as e:
            # Cancel the workflow task to clean up resources
            if workflow_task and not workflow_task.done():
                workflow_task.cancel()
                try:
                    await workflow_task
                except asyncio.CancelledError:
                    pass
            
            # Structured logging for exceptions (without sensitive data)
            self.logger.error(
                "Error in async workflow execution",
                extra={
                    'workflow_type': workflow_type,
                    'message_type': 'workflow',
                    'error_type': type(e).__name__,
                    'exception': str(e),
                    'event_type': 'workflow_error'
                }
            )
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results
    
    async def process_async(self, message: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Process a message asynchronously with timeout protection.
        
        Args:
            message: Message to process containing 'type' and 'data' fields
            timeout: Timeout in seconds for workflow execution (default: 30.0).
                     Applies only to workflow messages. Sub-second timeouts are supported
                     but may cause immediate timeout for complex workflows.
            
        Returns:
            Dict[str, Any]: Response structure depends on message type and execution outcome.
            See _execute_workflow_async() for workflow response structures.
            Non-workflow messages return standard agent responses with 'status' and 'data' fields.
        """
        if not self.validate_message(message):
            return self.create_response('error', None, 'Invalid message format')
            
        try:
            message_type = message['type']
            
            if message_type == 'workflow':
                return await self._execute_workflow_async(message['data'], timeout=timeout)
            else:
                # For non-workflow messages, run synchronously in executor
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self._route_message(message)
                )
                
        except Exception as e:
            self.logger.error(f"Error processing message asynchronously: {e}")
            return self.create_response('error', None, str(e))
    
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")
