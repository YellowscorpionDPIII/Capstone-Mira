"""OrchestratorAgent for routing messages between agents.

Prometheus Metrics Documentation
=================================

This module exposes the following Prometheus metrics for monitoring orchestrator agent operations:

1. async_timeout_fallbacks_total (Counter)
   - Description: Tracks the total number of asynchronous timeout fallback occurrences.
   - Labels:
     * agent_type: The type/ID of the agent that experienced the timeout (e.g., "plan_generator", "risk_assessor")
   - Purpose: Monitor how often async operations time out and fall back to synchronous mode.
   - Example usage:
     async_timeout_fallbacks_total.labels(agent_type="plan_generator").inc()

2. agent_process_duration_seconds (Histogram)
   - Description: Tracks the duration of agent processing operations in seconds.
   - Labels:
     * agent_type: The type/ID of the agent performing the operation (e.g., "plan_generator", "risk_assessor")
     * fallback_mode: The execution mode used ("sync", "async", "error")
     * success: Whether the operation succeeded ("true") or failed ("false")
   - Purpose: Monitor performance and identify slow operations, compare sync vs async performance,
     and track success/failure rates.
   - Example usage:
     agent_process_duration_seconds.labels(agent_type="plan_generator", fallback_mode="sync", success="true").observe(duration)

3. current_concurrent_agents (Gauge)
   - Description: Tracks the current number of concurrent agent operations in progress.
   - Labels: None
   - Purpose: Monitor system load and concurrent operation capacity.
   - Example usage:
     current_concurrent_agents.inc()  # When starting an operation
     current_concurrent_agents.dec()  # When completing an operation
"""
from typing import Dict, Any, Optional
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker
from config import config
import asyncio
import logging
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
async_timeout_fallbacks_total = Counter(
    'async_timeout_fallbacks_total',
    'Total number of asynchronous timeout fallback occurrences',
    ['agent_type']
)

agent_process_duration_seconds = Histogram(
    'agent_process_duration_seconds',
    'Duration of agent processing operations in seconds',
    ['agent_type', 'fallback_mode', 'success']
)

current_concurrent_agents = Gauge(
    'current_concurrent_agents',
    'Current number of concurrent agent operations'
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
        import time
        start_time = time.time()
        success = False
        fallback_mode = "sync"  # Default mode
        
        # Increment concurrent operations gauge
        current_concurrent_agents.inc()
        
        try:
            if not self.validate_message(message):
                return self.create_response('error', None, 'Invalid message format')
                
            try:
                message_type = message['type']
                
                if message_type == 'workflow':
                    result = self._execute_workflow(message['data'])
                    success = True
                    return result
                else:
                    result = self._route_message(message)
                    success = result.get('status') == 'success'
                    return result
                    
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                fallback_mode = "error"
                return self.create_response('error', None, str(e))
        finally:
            # Decrement concurrent operations gauge
            current_concurrent_agents.dec()
            
            # Record processing duration
            duration = time.time() - start_time
            agent_type = self.agent_id
            success_label = "true" if success else "false"
            agent_process_duration_seconds.labels(
                agent_type=agent_type,
                fallback_mode=fallback_mode,
                success=success_label
            ).observe(duration)
            
    def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: Message to route
            
        Returns:
            Response from target agent
        """
        import time
        message_type = message['type']
        
        # Determine target agent
        target_agent_id = self.routing_rules.get(message_type)
        
        if not target_agent_id:
            return self.create_response('error', None, f'No routing rule for message type: {message_type}')
            
        target_agent = self.agent_registry.get(target_agent_id)
        
        if not target_agent:
            return self.create_response('error', None, f'Agent not found: {target_agent_id}')
            
        # Route message to target agent with metrics tracking
        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        
        start_time = time.time()
        success = False
        fallback_mode = "sync"  # Most agent calls are synchronous
        
        try:
            response = target_agent.process(message)
            success = response.get('status') == 'success'
            return response
        except asyncio.TimeoutError:
            # Track timeout fallbacks
            async_timeout_fallbacks_total.labels(agent_type=target_agent_id).inc()
            fallback_mode = "async"
            raise
        finally:
            # Record agent-specific processing duration
            duration = time.time() - start_time
            success_label = "true" if success else "false"
            agent_process_duration_seconds.labels(
                agent_type=target_agent_id,
                fallback_mode=fallback_mode,
                success=success_label
            ).observe(duration)
        
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
