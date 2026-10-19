<<<<<<< HEAD
"""OrchestratorAgent for routing messages between agents."""
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional
=======
"""OrchestratorAgent – routes messages between agents and manages workflows."""
from datetime import datetime
from typing import Any, Dict, Optional

>>>>>>> origin/main
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
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run
        return asyncio.run(coro)
    else:
        # Already in an event loop, run in a separate thread with a new event loop
        def run_in_new_loop(coro):
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop, coro)
            return future.result()
class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating workflow between other agents.

    Routes messages to the correct agent and coordinates multi-step
    async workflows.  Does not call an LLM directly.
    """

    def __init__(self) -> None:
        super().__init__(llm=None, name="orchestrator_agent")
        self.broker = get_broker()
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.routing_rules = self._initialize_routing_rules()

    # ------------------------------------------------------------------
    # Routing table
    # ------------------------------------------------------------------

    def _initialize_routing_rules(self) -> Dict[str, str]:
        return {
            "generate_plan":          "project_plan_agent",
            "update_plan":            "project_plan_agent",
            "assess_risks":           "risk_assessment_agent",
            "update_risk":            "risk_assessment_agent",
            "generate_report":        "status_reporter_agent",
            "schedule_report":        "status_reporter_agent",
            "assess_governance":      "governance_agent",
            "check_human_validation": "governance_agent",
            "generate_roadmap":       "roadmapping_agent",
            "track_kpi_progress":     "roadmapping_agent",
            "recommend_tool":         "tool_recommender_agent",
        }
<<<<<<< HEAD
        
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
        
        if not isinstance(agent, BaseAgent):
            self.logger.error(
                f"Invalid agent: must be a BaseAgent instance. "
                f"Agent state: agent_id={self.agent_id}"
            )
            raise ValueError("Agent must be a BaseAgent instance")
        
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
            return self.create_response('error', None, 'Workflow data must be a dictionary')
        
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
=======

    def register_agent(self, agent: BaseAgent) -> None:
        self.agent_registry[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.agent_id}")

    def add_routing_rule(self, message_type: str, agent_id: str) -> None:
        self.routing_rules[message_type] = agent_id
        self.logger.info(f"Added routing rule: {message_type} -> {agent_id}")

    # ------------------------------------------------------------------
    # Async process entry-point
    # ------------------------------------------------------------------

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        # Orchestrator does not call an LLM; this satisfies the abstract method.
        return ""

    async def process(self, task: Dict[str, Any], complexity: str = "auto") -> Dict[str, Any]:
        if not self.validate_message(task):
            return self.create_response("error", None, "Invalid message format")

        try:
            if task["type"] == "workflow":
                return await self._execute_workflow(task["data"])
            return await self._route_message(task)
        except Exception as exc:
            self.logger.error(f"Error processing message: {exc}")
            return self.create_response("error", None, str(exc))

    # ------------------------------------------------------------------
    # Internal async helpers
    # ------------------------------------------------------------------

    async def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        message_type = message["type"]
        target_agent_id = self.routing_rules.get(message_type)

        if not target_agent_id:
            return self.create_response(
                "error", None, f"No routing rule for message type: {message_type}"
            )

        target_agent = self.agent_registry.get(target_agent_id)
        if not target_agent:
            return self.create_response(
                "error", None, f"Agent not found: {target_agent_id}"
            )

        self.logger.info(f"Routing {message_type} to {target_agent_id}")
        return await target_agent.process(message)

    @staticmethod
    def _is_ok(response: Dict[str, Any]) -> bool:
        """Return True when a routed response carried no error."""
        # New agent format has 'result'; old create_response format has 'status'.
        if "status" in response:
            return response["status"] == "success"
        return "result" in response and "agent" in response

    @staticmethod
    def _get_result(response: Dict[str, Any]) -> Any:
        """Extract the payload from either response format."""
        if "result" in response:
            result = response["result"]
            # Serialise Pydantic models so they can be passed as plain dicts
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return result
        return response.get("data")

    async def _execute_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a multi-step workflow with optional governance checks."""
        workflow_type = data.get("workflow_type")
        workflow_data = data.get("data", {})

        results: Dict[str, Any] = {
            "workflow_type": workflow_type,
            "steps": [],
            "governance": None,
        }

        # Governance pre-check if governance_data is provided
        governance_data = data.get("governance_data")
        if governance_data:
            try:
                gov_response = await self._route_message(
                    {"type": "assess_governance", "data": governance_data}
                )
                if self._is_ok(gov_response):
                    assessment = self._get_result(gov_response) or {}
                    results["governance"] = assessment
                    results["risk_level"] = assessment.get("risk_level", "low")
                    results["requires_human_validation"] = assessment.get(
                        "requires_human_validation", False
                    )
                    if assessment.get("requires_human_validation"):
                        results["status"] = "pending_approval"
                        self.logger.warning(
                            "Workflow requires human validation before proceeding"
                        )
                        self._publish_pending_approval(
                            workflow_type, assessment, workflow_data
                        )
                else:
                    self.logger.error(
                        "Governance assessment failed, falling back to 'low' risk"
                    )
                    results["governance"] = {
                        "risk_level": "low",
                        "requires_human_validation": False,
                    }
                    results["risk_level"] = "low"
            except Exception as exc:
                self.logger.error(
                    f"Exception during governance assessment: {exc}, "
                    "falling back to 'low' risk level"
                )
                results["governance"] = {
                    "risk_level": "low",
                    "requires_human_validation": False,
                }
                results["risk_level"] = "low"

        if workflow_type == "project_initialization":
            # Step 1 – generate plan
            plan_response = await self._route_message(
                {"type": "generate_plan", "data": workflow_data}
            )
            plan_ok = self._is_ok(plan_response)
            results["steps"].append(
                {
                    "step": "generate_plan",
                    "status": "success" if plan_ok else "error",
                    "result": self._get_result(plan_response),
                }
            )

            # Step 2 – assess risks
            if plan_ok:
                plan = self._get_result(plan_response) or {}
                risk_response = await self._route_message(
                    {"type": "assess_risks", "data": plan}
                )
                risk_ok = self._is_ok(risk_response)
                results["steps"].append(
                    {
                        "step": "assess_risks",
                        "status": "success" if risk_ok else "error",
                        "result": self._get_result(risk_response),
                    }
                )

                # Step 3 – generate initial status report
                if risk_ok:
                    risks_data = self._get_result(risk_response) or {}
                    report_data = {**plan, "risks": risks_data.get("risks", [])}
                    report_response = await self._route_message(
                        {"type": "generate_report", "data": report_data}
                    )
                    results["steps"].append(
                        {
                            "step": "generate_report",
                            "status": "success" if self._is_ok(report_response) else "error",
                            "result": self._get_result(report_response),
                        }
                    )

        self.logger.info(f"Completed workflow: {workflow_type}")
        return results

    def _publish_pending_approval(
        self,
        workflow_type: str,
        governance_assessment: Dict[str, Any],
        workflow_data: Dict[str, Any],
    ) -> None:
        try:
            self.broker.publish(
                "governance.pending_approval",
                {
                    "type": "pending_approval",
                    "workflow_type": workflow_type,
                    "governance": governance_assessment,
                    "workflow_data": workflow_data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            self.logger.info(
                f"Published pending approval notification for {workflow_type}"
            )
        except Exception as exc:
            self.logger.error(f"Failed to publish pending approval notification: {exc}")
>>>>>>> origin/main
