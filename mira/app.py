"""Main application entry point for Mira platform."""
import asyncio
from typing import Optional

from mira.core.message_broker import get_broker
from mira.core.webhook_handler import WebhookHandler
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.governance_agent import GovernanceAgent
from mira.agents.roadmapping_agent import RoadmappingAgent
from mira.agents.tool_recommender_agent import ToolRecommenderAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.config.settings import get_config
from mira.utils.logging import setup_logging
from mira.utils.secrets_manager import get_secret
from mira.llm import BaseLLM, ClaudeLLM, OpenAILLM, OllamaLLM, LLMRouter


def _build_llm(config) -> BaseLLM:
    """Instantiate the correct LLM backend(s) from config."""
    mode = config.get("llm.mode", "router")

    claude = ClaudeLLM(
        api_key=get_secret("ANTHROPIC_API_KEY") or config.get("llm.anthropic_api_key", ""),
        model=config.get("llm.claude_model"),
    )
    cheap = OpenAILLM(
        api_key=get_secret("OPENAI_API_KEY") or config.get("llm.openai_api_key", ""),
        model=config.get("llm.cheap_model"),
    )
    local = OllamaLLM(model=config.get("llm.local_model"))

    if mode == "claude-only":
        return claude
    if mode == "local-only":
        return local
    return LLMRouter(claude_llm=claude, cheap_llm=cheap, local_llm=local)


class MiraApplication:
    """
    Main application class for the Mira platform.

    Initialises and coordinates all agents, integrations, and services.
    """

    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        self.config = get_config(config_path)

        # Setup logging
        log_level = self.config.get("logging.level", "INFO")
        setup_logging(level=log_level)

        # Build LLM backend
        self.llm = _build_llm(self.config)

        # Initialise message broker
        self.broker = get_broker()

        # Initialise agents
        self.agents = {}
        self._initialize_agents()

        # Initialise webhook handler if enabled
        self.webhook_handler = None
        if self.config.get("webhook.enabled", False):
            self._initialize_webhook_handler()

    def _initialize_agents(self):
        """Initialise all agents and register them with the orchestrator."""
        llm = self.llm

        # Create orchestrator (no LLM needed)
        self.orchestrator = OrchestratorAgent()
        self.agents["orchestrator"] = self.orchestrator

        # Governance agent (always registered so routing works)
        governance_agent = GovernanceAgent(llm=llm)
        self.agents["governance"] = governance_agent
        self.orchestrator.register_agent(governance_agent)

        if self.config.get("agents.project_plan_agent.enabled", True):
            plan_agent = ProjectPlanAgent(llm=llm)
            self.agents["project_plan"] = plan_agent
            self.orchestrator.register_agent(plan_agent)

        if self.config.get("agents.risk_assessment_agent.enabled", True):
            risk_agent = RiskAssessmentAgent(llm=llm)
            self.agents["risk_assessment"] = risk_agent
            self.orchestrator.register_agent(risk_agent)

        if self.config.get("agents.status_reporter_agent.enabled", True):
            status_agent = StatusReporterAgent(llm=llm)
            self.agents["status_reporter"] = status_agent
            self.orchestrator.register_agent(status_agent)

        if self.config.get("agents.roadmapping_agent.enabled", True):
            roadmap_agent = RoadmappingAgent(llm=llm)
            self.agents["roadmapping"] = roadmap_agent
            self.orchestrator.register_agent(roadmap_agent)

        if self.config.get("agents.tool_recommender_agent.enabled", True):
            tool_rec_agent = ToolRecommenderAgent(llm=llm)
            self.agents["tool_recommender"] = tool_rec_agent
            self.orchestrator.register_agent(tool_rec_agent)

    def _initialize_webhook_handler(self):
        """Initialise webhook handler for external integrations."""
        secret_key = self.config.get("webhook.secret_key")
        self.webhook_handler = WebhookHandler(secret_key=secret_key)

        self.webhook_handler.register_handler("github", self._handle_github_webhook)
        self.webhook_handler.register_handler("trello", self._handle_trello_webhook)
        self.webhook_handler.register_handler("jira", self._handle_jira_webhook)

        self._setup_health_check()

    def _handle_github_webhook(self, data: dict) -> dict:
        return asyncio.run(self._dispatch_async(data))

    def _handle_trello_webhook(self, data: dict) -> dict:
        return asyncio.run(self._dispatch_async(data))

    def _handle_jira_webhook(self, data: dict) -> dict:
        return asyncio.run(self._dispatch_async(data))

    async def _dispatch_async(self, data: dict) -> dict:
        """Async dispatch helper for webhook handlers."""
        return await self.orchestrator.process(data)

    def _setup_health_check(self):
        """Set up health check endpoint for Kubernetes probes."""
        from flask import jsonify

        @self.webhook_handler.app.route("/healthz", methods=["GET"])
        def health_check():
            health_status = {"status": "healthy", "checks": {}}

            try:
                health_status["checks"]["configuration"] = "ok" if self.config else "failed"
                if not self.config:
                    health_status["status"] = "unhealthy"
            except Exception as exc:
                health_status["checks"]["configuration"] = f"error: {exc}"
                health_status["status"] = "unhealthy"

            try:
                if self.agents:
                    health_status["checks"]["agents"] = "ok"
                    health_status["checks"]["agent_count"] = len(self.agents)
                else:
                    health_status["checks"]["agents"] = "no agents initialized"
                    health_status["status"] = "unhealthy"
            except Exception as exc:
                health_status["checks"]["agents"] = f"error: {exc}"
                health_status["status"] = "unhealthy"

            if self.config.get("broker.enabled", True):
                try:
                    if self.broker:
                        if hasattr(self.broker, "running"):
                            broker_status = "running" if self.broker.running else "stopped"
                            health_status["checks"]["broker"] = broker_status
                            if not self.broker.running:
                                health_status["status"] = "degraded"
                        else:
                            health_status["checks"]["broker"] = "status unavailable"
                    else:
                        health_status["checks"]["broker"] = "not initialized"
                        health_status["status"] = "unhealthy"
                except Exception as exc:
                    health_status["checks"]["broker"] = f"error: {exc}"
                    health_status["status"] = "unhealthy"
            else:
                health_status["checks"]["broker"] = "disabled"

            if health_status["status"] in ("healthy", "degraded"):
                return jsonify(health_status), 200
            return jsonify(health_status), 503

    def start(self):
        """Start the Mira application."""
        if self.config.get("broker.enabled", True):
            self.broker.start()

        if self.webhook_handler and self.config.get("webhook.enabled", False):
            host = self.config.get("webhook.host", "0.0.0.0")
            port = self.config.get("webhook.port", 5000)
            self.webhook_handler.run(host=host, port=port)

    def stop(self):
        """Stop the Mira application."""
        if self.broker:
            self.broker.stop()

    async def process_message(self, message: dict) -> dict:
        """
        Process a message through the orchestrator asynchronously.

        Args:
            message: Message to process.

        Returns:
            Processing result.
        """
        return await self.orchestrator.process(message)


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


if __name__ == "__main__":
    main()
