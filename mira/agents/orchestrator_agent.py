"""OrchestratorAgent – routes messages between agents and manages workflows."""
from datetime import datetime
from typing import Any, Dict, Optional

from mira.core.base_agent import BaseAgent
from mira.core.message_broker import get_broker


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
