"""Unit tests for the mira/llm/ package.

All external API calls are mocked – no API keys needed.
Run with:  pytest mira/tests/test_llm.py -v
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
# ClaudeLLM tests
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
        task_obj = Task(name="Write tests", priority="high", estimated_hours=4)
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
        # system param should be set at top level
        assert call_kwargs["system"] == "You are helpful"
        # messages list should only contain the user message
        assert all(m["role"] != "system" for m in call_kwargs["messages"])


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
        long_content = "x" * (LLMRouter.LONG_THRESHOLD + 1)
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
