"""Unit tests for the mira/llm/ package.

All external API calls are mocked – no API keys needed.
Run with:  pytest mira/tests/test_llm.py -v
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from anthropic import APIConnectionError, APIStatusError, RateLimitError as AnthropicRateLimitError
from openai import APIConnectionError as OpenAIConnectionError, RateLimitError as OpenAIRateLimitError

from mira.llm.base import BaseLLM
from mira.llm.router import LLMRouter
from mira.llm.anthropic_llm import ClaudeLLM
from mira.llm.openai_llm import OpenAILLM
from mira.llm.ollama_llm import OllamaLLM
from mira.llm.schemas import (
    ProjectPlanOutput,
    Milestone,
    Task,
    RiskAssessmentOutput,
    Risk,
    StatusReport,
    GovernanceAssessmentOutput,
    RoadmapOutput,
    RoadmapInitiative,
)
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.governance_agent import GovernanceAgent
from mira.agents.roadmapping_agent import RoadmappingAgent
from mira.agents.tool_recommender_agent import ToolRecommenderAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_llm(return_value):
    """Return a BaseLLM mock whose generate() returns *return_value*."""
    mock = MagicMock(spec=BaseLLM)
    mock.generate = AsyncMock(return_value={"text": return_value, "raw": object()})
    return mock


def fixture_project_plan():
    return ProjectPlanOutput(
        project_name="Test Project",
        milestones=[
            Milestone(
                name="M1",
                description="First milestone",
                due_date="2026-04-01",
                tasks=[Task(name="T1", priority="high", estimated_hours=8)],
            )
        ],
        total_duration_weeks=6,
    )


def fixture_risk_assessment():
    return RiskAssessmentOutput(
        project_id="proj-001",
        risks=[
            Risk(
                category="schedule",
                description="Tight deadline",
                severity="high",
                probability="medium",
                mitigation="Add buffer",
                impact_score=0.8,
            )
        ],
        overall_risk_score=0.6,
        summary="Moderate risk profile",
    )


def fixture_status_report():
    return StatusReport(
        week_ending="2026-03-01",
        completion_pct=42.0,
        accomplished=["Completed API design"],
        blockers=["Waiting for DB access"],
        upcoming_milestones=["API launch"],
        risks_summary="Schedule risk elevated",
    )


def fixture_governance():
    return GovernanceAssessmentOutput(
        risk_level="low",
        requires_human_validation=False,
        reasons=[],
        recommended_actions=["Proceed"],
    )


def fixture_roadmap():
    return RoadmapOutput(
        business_context="Efficiency drive",
        initiatives=[
            RoadmapInitiative(
                name="Automate onboarding",
                objective="efficiency",
                priority=1,
                ebit_impact_usd=500_000.0,
                timeline_weeks=12,
                kpis=["onboarding_time_reduction"],
            )
        ],
        total_ebit_projection_usd=500_000.0,
        generated_at="2026-02-24",
    )


# ---------------------------------------------------------------------------
# ClaudeLLM – happy path tests
# ---------------------------------------------------------------------------

class TestClaudeLLM:
    """Test ClaudeLLM.generate() with mocked AsyncAnthropic."""

    @pytest.mark.asyncio
    async def test_plain_text_generation(self):
        """Plain text call uses messages.create and returns text."""
        mock_content_block = MagicMock()
        mock_content_block.text = "Hello from Claude"
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=mock_response)

            llm = ClaudeLLM(api_key="test-key", model="claude-test")
            result = await llm.generate(
                [{"role": "user", "content": "Say hello"}]
            )

        assert result["text"] == "Hello from Claude"
        assert result["raw"] is mock_response

    @pytest.mark.asyncio
    async def test_structured_tool_call(self):
        """Structured generation uses tool-calling and parses schema."""
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "output"
        mock_tool_block.input = {"name": "Write tests", "priority": "high", "estimated_hours": 4}
        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=mock_response)

            llm = ClaudeLLM(api_key="test-key")
            result = await llm.generate(
                [{"role": "user", "content": "Create a task"}],
                schema=Task,
            )

        assert isinstance(result["text"], Task)
        assert result["text"].name == "Write tests"
        assert result["text"].priority == "high"

    @pytest.mark.asyncio
    async def test_system_message_extracted(self):
        """System messages are passed as top-level param, not in messages list."""
        mock_content_block = MagicMock()
        mock_content_block.text = "ok"
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=mock_response)

            llm = ClaudeLLM(api_key="test-key")
            await llm.generate([
                {"role": "system", "content": "You are helpful"},
                {"role": "user",   "content": "Hi"},
            ])

            call_kwargs = instance.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are helpful"
        assert all(m["role"] != "system" for m in call_kwargs["messages"])

    @pytest.mark.asyncio
    async def test_structured_raises_when_no_tool_block(self):
        """If Claude returns no tool-use block, a ValueError is raised."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "some text"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=mock_response)

            llm = ClaudeLLM(api_key="test-key")
            with pytest.raises(ValueError, match="tool-use block"):
                await llm.generate(
                    [{"role": "user", "content": "Do something"}],
                    schema=Task,
                )

    @pytest.mark.asyncio
    async def test_schema_must_be_pydantic_model(self):
        """Passing a non-Pydantic class as schema raises TypeError."""
        with patch("mira.llm.anthropic_llm.AsyncAnthropic"):
            llm = ClaudeLLM(api_key="test-key")
            with pytest.raises(TypeError, match="Pydantic BaseModel"):
                await llm.generate(
                    [{"role": "user", "content": "Hi"}],
                    schema=dict,  # not a Pydantic model
                )

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_then_succeeds(self):
        """Rate limit errors are retried; success on second attempt is returned."""
        mock_content_block = MagicMock()
        mock_content_block.text = "Success after retry"
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]

        rate_limit_error = AnthropicRateLimitError.__new__(AnthropicRateLimitError)

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            with patch("mira.llm.anthropic_llm.asyncio.sleep", new_callable=AsyncMock):
                instance = MockClient.return_value
                instance.messages.create = AsyncMock(
                    side_effect=[rate_limit_error, mock_response]
                )
                llm = ClaudeLLM(api_key="test-key")
                result = await llm.generate([{"role": "user", "content": "Hi"}])

        assert result["text"] == "Success after retry"

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """If all retries fail, the last exception is raised."""
        error = AnthropicRateLimitError.__new__(AnthropicRateLimitError)

        with patch("mira.llm.anthropic_llm.AsyncAnthropic") as MockClient:
            with patch("mira.llm.anthropic_llm.asyncio.sleep", new_callable=AsyncMock):
                instance = MockClient.return_value
                instance.messages.create = AsyncMock(side_effect=error)
                llm = ClaudeLLM(api_key="test-key")
                with pytest.raises(AnthropicRateLimitError):
                    await llm.generate([{"role": "user", "content": "Hi"}])


# ---------------------------------------------------------------------------
# OllamaLLM – error handling tests
# ---------------------------------------------------------------------------

class TestOllamaLLM:
    @pytest.mark.asyncio
    async def test_plain_text_generation(self):
        mock_data = {"message": {"content": "Hello from Ollama"}}

        with patch("mira.llm.ollama_llm.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            llm = OllamaLLM()
            result = await llm.generate([{"role": "user", "content": "Hi"}])

        assert result["text"] == "Hello from Ollama"

    @pytest.mark.asyncio
    async def test_missing_content_raises_value_error(self):
        """If Ollama response lacks message.content, a ValueError is raised."""
        mock_data = {"message": {}}  # missing "content"

        with patch("mira.llm.ollama_llm.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            llm = OllamaLLM()
            with pytest.raises(ValueError, match="message.content"):
                await llm.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_malformed_json_schema_raises_value_error(self):
        """If schema is requested but Ollama returns invalid JSON, ValueError is raised."""
        mock_data = {"message": {"content": "not valid json {"}}

        with patch("mira.llm.ollama_llm.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            llm = OllamaLLM()
            with pytest.raises(ValueError, match="could not be parsed"):
                await llm.generate(
                    [{"role": "user", "content": "Hi"}],
                    schema=Task,
                )

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        """Timeout errors trigger retries."""
        mock_data = {"message": {"content": "ok"}}

        with patch("mira.llm.ollama_llm.httpx.AsyncClient") as MockClient:
            with patch("mira.llm.ollama_llm.asyncio.sleep", new_callable=AsyncMock):
                mock_resp = MagicMock()
                mock_resp.json.return_value = mock_data
                mock_resp.raise_for_status = MagicMock()
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(
                    side_effect=[httpx.TimeoutException("timeout"), mock_resp]
                )
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                llm = OllamaLLM()
                result = await llm.generate([{"role": "user", "content": "Hi"}])

        assert result["text"] == "ok"

    def test_custom_timeout_is_stored(self):
        llm = OllamaLLM(timeout=30.0)
        assert llm.timeout == 30.0


# ---------------------------------------------------------------------------
# LLMRouter backend selection tests
# ---------------------------------------------------------------------------

class TestLLMRouterSelection:
    """Test LLMRouter._select_backend() routing logic."""

    def _make_router(self):
        claude = MagicMock(spec=BaseLLM)
        cheap = MagicMock(spec=BaseLLM)
        local = MagicMock(spec=BaseLLM)
        router = LLMRouter(claude_llm=claude, cheap_llm=cheap, local_llm=local)
        return router, claude, cheap, local

    def test_short_text_routes_to_cheap(self):
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "Hello"}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=False)
        assert backend is cheap

    def test_long_text_routes_to_claude(self):
        router, claude, cheap, local = self._make_router()
        long_content = "x" * (router.long_threshold + 1)
        messages = [{"role": "user", "content": long_content}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=False)
        assert backend is claude

    def test_offline_ok_routes_to_local(self):
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "Hello"}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=True)
        assert backend is local

    def test_force_claude_complexity(self):
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "Hello"}]
        backend = router._select_backend(
            messages, complexity="force-claude", offline_ok=False
        )
        assert backend is claude

    def test_high_complexity_routes_to_claude(self):
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "Hello"}]
        backend = router._select_backend(messages, complexity="high", offline_ok=False)
        assert backend is claude

    def test_code_content_routes_to_claude(self):
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "def foo(): pass"}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=False)
        assert backend is claude

    def test_false_positive_word_defined_routes_to_cheap(self):
        """'defined' should NOT be treated as code and should route to cheap."""
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "I defined a process for onboarding."}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=False)
        assert backend is cheap

    def test_offline_ok_without_local_llm_raises(self):
        """offline_ok=True with no local_llm configured raises ValueError."""
        claude = MagicMock(spec=BaseLLM)
        cheap = MagicMock(spec=BaseLLM)
        router = LLMRouter(claude_llm=claude, cheap_llm=cheap, local_llm=None)
        with pytest.raises(ValueError, match="no local_llm"):
            router._select_backend([], complexity="auto", offline_ok=True)

    def test_unknown_complexity_falls_back_to_cheap(self):
        """An unrecognised complexity value is treated as 'auto'."""
        router, claude, cheap, local = self._make_router()
        messages = [{"role": "user", "content": "Hello"}]
        backend = router._select_backend(
            messages, complexity="super-intelligent", offline_ok=False
        )
        assert backend is cheap

    def test_empty_messages_routes_to_cheap(self):
        router, claude, cheap, local = self._make_router()
        backend = router._select_backend([], complexity="auto", offline_ok=False)
        assert backend is cheap

    def test_custom_long_threshold_respected(self):
        claude = MagicMock(spec=BaseLLM)
        cheap = MagicMock(spec=BaseLLM)
        router = LLMRouter(claude_llm=claude, cheap_llm=cheap, long_threshold=10)
        messages = [{"role": "user", "content": "x" * 11}]
        backend = router._select_backend(messages, complexity="auto", offline_ok=False)
        assert backend is claude


# ---------------------------------------------------------------------------
# Agent process() tests with mocked LLMRouter
# ---------------------------------------------------------------------------

class TestProjectPlanAgentProcess:
    @pytest.mark.asyncio
    async def test_process_returns_project_plan(self):
        fixture = fixture_project_plan()
        mock_llm = make_mock_llm(fixture)

        agent = ProjectPlanAgent(llm=mock_llm)
        task = {
            "type": "generate_plan",
            "data": {
                "name": "FinTech MVP",
                "goals": ["launch payments"],
                "duration_weeks": 6,
            },
        }
        result = await agent.process(task)

        assert result["agent"] == "project_plan_agent"
        assert isinstance(result["result"], ProjectPlanOutput)
        assert result["result"].project_name == "Test Project"
        mock_llm.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_propagates_llm_error(self):
        """LLM failures bubble up from process()."""
        mock_llm = MagicMock(spec=BaseLLM)
        mock_llm.generate = AsyncMock(side_effect=RuntimeError("API down"))

        agent = ProjectPlanAgent(llm=mock_llm)
        with pytest.raises(RuntimeError, match="API down"):
            await agent.process({"type": "generate_plan", "data": {}})


class TestRiskAssessmentAgentProcess:
    @pytest.mark.asyncio
    async def test_process_returns_risk_assessment(self):
        fixture = fixture_risk_assessment()
        mock_llm = make_mock_llm(fixture)

        agent = RiskAssessmentAgent(llm=mock_llm)
        task = {
            "type": "assess_risks",
            "data": {"name": "FinTech MVP", "duration_weeks": 6},
        }
        result = await agent.process(task)

        assert result["agent"] == "risk_assessment_agent"
        assert isinstance(result["result"], RiskAssessmentOutput)
        assert len(result["result"].risks) == 1


class TestStatusReporterAgentProcess:
    @pytest.mark.asyncio
    async def test_process_returns_status_report(self):
        fixture = fixture_status_report()
        mock_llm = make_mock_llm(fixture)

        agent = StatusReporterAgent(llm=mock_llm)
        task = {
            "type": "generate_report",
            "data": {"name": "FinTech MVP", "tasks": [], "milestones": []},
        }
        result = await agent.process(task)

        assert result["agent"] == "status_reporter_agent"
        assert isinstance(result["result"], StatusReport)
        assert result["result"].completion_pct == 42.0


class TestGovernanceAgentProcess:
    @pytest.mark.asyncio
    async def test_process_returns_governance_output(self):
        fixture = fixture_governance()
        mock_llm = make_mock_llm(fixture)

        agent = GovernanceAgent(llm=mock_llm)
        task = {
            "type": "assess_governance",
            "data": {
                "financial_impact": 5000,
                "compliance_level": "low",
                "explainability_score": 0.9,
            },
        }
        result = await agent.process(task)

        assert result["agent"] == "governance_agent"
        assert isinstance(result["result"], GovernanceAssessmentOutput)
        assert result["result"].risk_level == "low"

    def test_update_thresholds_validates_negative_financial(self):
        mock_llm = MagicMock(spec=BaseLLM)
        agent = GovernanceAgent(llm=mock_llm)
        with pytest.raises(ValueError, match="financial_threshold"):
            agent.update_thresholds({"financial_threshold": -100})

    def test_update_thresholds_validates_bad_compliance(self):
        mock_llm = MagicMock(spec=BaseLLM)
        agent = GovernanceAgent(llm=mock_llm)
        with pytest.raises(ValueError, match="compliance_threshold"):
            agent.update_thresholds({"compliance_threshold": "extreme"})

    def test_update_thresholds_validates_explainability_out_of_range(self):
        mock_llm = MagicMock(spec=BaseLLM)
        agent = GovernanceAgent(llm=mock_llm)
        with pytest.raises(ValueError, match="explainability_threshold"):
            agent.update_thresholds({"explainability_threshold": 1.5})


class TestRoadmappingAgentProcess:
    @pytest.mark.asyncio
    async def test_process_returns_roadmap(self):
        fixture = fixture_roadmap()
        mock_llm = make_mock_llm(fixture)

        agent = RoadmappingAgent(llm=mock_llm)
        task = {
            "type": "generate_roadmap",
            "data": {"business_objectives": ["efficiency", "growth"]},
        }
        result = await agent.process(task)

        assert result["agent"] == "roadmapping_agent"
        assert isinstance(result["result"], RoadmapOutput)
        assert result["result"].total_ebit_projection_usd == 500_000.0


# ---------------------------------------------------------------------------
# BaseAgent – llm=None guard
# ---------------------------------------------------------------------------

class TestBaseAgentNullLLM:
    @pytest.mark.asyncio
    async def test_process_raises_when_llm_is_none(self):
        """process() must raise RuntimeError when llm=None."""
        from mira.agents.orchestrator_agent import OrchestratorAgent
        agent = OrchestratorAgent()
        # OrchestratorAgent overrides process(), so test via a minimal concrete agent.
        from mira.core.base_agent import BaseAgent

        class MinimalAgent(BaseAgent):
            def build_user_prompt(self, task):
                return "prompt"

        agent = MinimalAgent(llm=None, name="test_agent")
        with pytest.raises(RuntimeError, match="no LLM configured"):
            await agent.process({"type": "test", "data": {}})


# ---------------------------------------------------------------------------
# ToolRecommenderAgent – edge cases
# ---------------------------------------------------------------------------

class TestToolRecommenderAgent:
    @pytest.mark.asyncio
    async def test_empty_description_raises(self):
        from mira.agents.tool_recommender_agent import ToolRecommenderAgent
        mock_llm = MagicMock(spec=BaseLLM)
        mock_llm.generate = AsyncMock()

        with patch("mira.agents.tool_recommender_agent.load_model_registry", return_value={"tools": {}, "reasons": {}}):
            agent = ToolRecommenderAgent(llm=mock_llm)
            with pytest.raises(ValueError, match="non-empty"):
                await agent.process({"type": "recommend_tool", "data": {"description": "  "}})

    @pytest.mark.asyncio
    async def test_classify_use_case_is_awaitable(self):
        """classify_use_case must be async (not use asyncio.run)."""
        from mira.agents.tool_recommender_agent import ToolRecommenderAgent
        import inspect
        mock_llm = MagicMock(spec=BaseLLM)
        mock_llm.generate = AsyncMock(
            return_value={"text": MagicMock(leaf_key="complex_coding"), "raw": None}
        )
        with patch("mira.agents.tool_recommender_agent.load_model_registry", return_value={"tools": {}, "reasons": {}}):
            agent = ToolRecommenderAgent(llm=mock_llm)
            assert inspect.iscoroutinefunction(agent.classify_use_case)
