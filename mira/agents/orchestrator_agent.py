"""OrchestratorAgent for routing messages between agents."""
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker
from config import config
import asyncio
import logging
import time
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
async_timeout_fallbacks_total = Counter(
    'async_timeout_fallbacks_total',
    'Total number of async timeout fallbacks',
    ['agent_type']
)

agent_process_duration_seconds = Histogram(
    'agent_process_duration_seconds',
    'Agent processing duration in seconds',
    ['agent_type', 'fallback_mode']
)

current_concurrent_agents = Gauge(
    'current_concurrent_agents',
    'Current number of agents processing requests concurrently'
)


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
            
        # Route message to target agent with timeout and metrics tracking
        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        
        # Increment concurrent agents gauge
        current_concurrent_agents.inc()
        
        try:
            # Determine agent type for metrics
            agent_type = self._get_agent_type(target_agent_id)
            
            # Try async processing with timeout first
            timeout_seconds = self.config.get('agent_timeout', 30)
            fallback_mode = 'async'
            
            try:
                start_time = time.time()
                
                # Attempt async processing with timeout
                loop = asyncio.get_event_loop()
                response = asyncio.wait_for(
                    loop.run_in_executor(None, target_agent.process, message),
                    timeout=timeout_seconds
                )
                
                # If we get here, async succeeded
                try:
                    response = loop.run_until_complete(response)
                except RuntimeError:
                    # No event loop running, use sync fallback
                    raise asyncio.TimeoutError("No event loop")
                
                duration = time.time() - start_time
                agent_process_duration_seconds.labels(
                    agent_type=agent_type,
                    fallback_mode=fallback_mode
                ).observe(duration)
                
            except (asyncio.TimeoutError, RuntimeError):
                # Timeout occurred, fallback to sync processing
                self.logger.warning(f"Async timeout for {agent_type}, falling back to sync")
                async_timeout_fallbacks_total.labels(agent_type=agent_type).inc()
                
                fallback_mode = 'sync'
                start_time = time.time()
                
                try:
                    response = target_agent.process(message)
                    duration = time.time() - start_time
                    agent_process_duration_seconds.labels(
                        agent_type=agent_type,
                        fallback_mode=fallback_mode
                    ).observe(duration)
                except Exception as e:
                    # Error during sync processing
                    duration = time.time() - start_time
                    fallback_mode = 'error'
                    agent_process_duration_seconds.labels(
                        agent_type=agent_type,
                        fallback_mode=fallback_mode
                    ).observe(duration)
                    raise e
            
            return response
            
        finally:
            # Decrement concurrent agents gauge
            current_concurrent_agents.dec()
        
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
        
    def add_routing_rule(self, message_type: str, agent_id: str):
        """
        Add a custom routing rule.
        
        Args:
            message_type: Message type to route
            agent_id: Target agent ID
        """
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")
    
    def _get_agent_type(self, agent_id: str) -> str:
        """
        Extract agent type from agent_id for metrics labeling.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            Agent type string for metrics
        """
        # Map common agent IDs to metric-friendly names
        agent_type_mapping = {
            'project_plan_agent': 'plan_generator',
            'risk_assessment_agent': 'risk_assessor',
            'status_reporter_agent': 'status_reporter',
            'roadmapping_agent': 'roadmapper'
        }
        return agent_type_mapping.get(agent_id, agent_id)
