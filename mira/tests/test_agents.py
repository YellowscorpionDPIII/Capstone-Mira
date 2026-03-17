"""Tests for Mira agent functionality (async LLM-backed API).

All LLM calls are mocked – no API keys required.
Run with:  pytest mira/tests/test_agents.py -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from unittest.mock import AsyncMock
from mira.llm.base import BaseLLM
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
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.core.base_agent import BaseAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_llm(return_value=None):
    """Return a mock LLM whose generate() returns *return_value*."""
    mock = MagicMock(spec=BaseLLM)
    mock.generate = AsyncMock(
        return_value={"text": return_value, "raw": MagicMock()}
    )
    return mock


def make_plan_fixture():
    return ProjectPlanOutput(
        project_name="Test Project",
        milestones=[
            Milestone(
                name="Launch",
                description="Initial launch milestone",
                due_date="2026-06-01",
                tasks=[Task(name="Setup CI", priority="high", estimated_hours=4)],
            )
        ],
        total_duration_weeks=8,
    )


def make_risk_fixture():
    return RiskAssessmentOutput(
        project_id="proj-test",
        risks=[
            Risk(
                category="technical",
                description="New stack",
                severity="medium",
                probability="low",
                mitigation="PoC first",
                impact_score=0.5,
            )
        ],
        overall_risk_score=0.3,
        summary="Low overall risk",
    )


def make_report_fixture():
    return StatusReport(
        week_ending="2026-03-07",
        completion_pct=55.0,
        accomplished=["Completed auth module"],
        blockers=[],
        upcoming_milestones=["Beta release"],
        risks_summary="No critical risks",
    )


def make_governance_fixture(risk="low", requires_validation=False):
    return GovernanceAssessmentOutput(
        risk_level=risk,
        requires_human_validation=requires_validation,
        reasons=[],
        recommended_actions=["Proceed"],
    )


def make_roadmap_fixture():
    return RoadmapOutput(
        business_context="Digital transformation",
        initiatives=[
            RoadmapInitiative(
                name="AI Chatbot",
                objective="growth",
                priority=1,
                ebit_impact_usd=250_000.0,
                timeline_weeks=10,
                kpis=["nps_improvement"],
            )
        ],
        total_ebit_projection_usd=250_000.0,
        generated_at="2026-02-24",
    )


# ---------------------------------------------------------------------------
# BaseAgent contract
# ---------------------------------------------------------------------------

class TestBaseAgentContract:
    def test_validate_message_requires_type_and_data(self):
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        assert agent.validate_message({"type": "x", "data": {}}) is True
        assert agent.validate_message({"type": "x"}) is False
        assert agent.validate_message({"data": {}}) is False
        assert agent.validate_message({}) is False

    def test_create_response_structure(self):
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        resp = agent.create_response("success", {"key": "val"})
        assert resp["status"] == "success"
        assert resp["data"] == {"key": "val"}
        assert resp["error"] is None
        assert "agent_id" in resp
        assert "timestamp" in resp

    def test_create_response_with_error(self):
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        resp = agent.create_response("error", None, "Something failed")
        assert resp["status"] == "error"
        assert resp["error"] == "Something failed"

    def test_agent_id_equals_name(self):
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        assert agent.agent_id == agent.name == "project_plan_agent"


# ---------------------------------------------------------------------------
# ProjectPlanAgent
# ---------------------------------------------------------------------------

class TestProjectPlanAgent:
    @pytest.mark.asyncio
    async def test_process_generate_plan(self):
        fixture = make_plan_fixture()
        llm = make_mock_llm(fixture)
        agent = ProjectPlanAgent(llm=llm)

        result = await agent.process({
            "type": "generate_plan",
            "data": {
                "name": "My Project",
                "goals": ["Build API", "Deploy"],
                "duration_weeks": 8,
            },
        })

        assert result["agent"] == "project_plan_agent"
        assert isinstance(result["result"], ProjectPlanOutput)
        llm.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_build_user_prompt_includes_project_name(self):
        llm = make_mock_llm(make_plan_fixture())
        agent = ProjectPlanAgent(llm=llm)
        prompt = agent.build_user_prompt({
            "type": "generate_plan",
            "data": {"name": "Acme App", "goals": ["ship"], "duration_weeks": 4},
        })
        assert "Acme App" in prompt
        assert "4" in prompt

    @pytest.mark.asyncio
    async def test_output_schema_is_project_plan_output(self):
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        assert agent.output_schema() is ProjectPlanOutput

    @pytest.mark.asyncio
    async def test_process_passes_schema_to_llm(self):
        fixture = make_plan_fixture()
        llm = make_mock_llm(fixture)
        agent = ProjectPlanAgent(llm=llm)

        await agent.process({
            "type": "generate_plan",
            "data": {"name": "X", "goals": [], "duration_weeks": 1},
        })

        call_kwargs = llm.generate.call_args.kwargs
        assert call_kwargs.get("schema") is ProjectPlanOutput


# ---------------------------------------------------------------------------
# RiskAssessmentAgent
# ---------------------------------------------------------------------------

class TestRiskAssessmentAgent:
    @pytest.mark.asyncio
    async def test_process_assess_risks(self):
        fixture = make_risk_fixture()
        llm = make_mock_llm(fixture)
        agent = RiskAssessmentAgent(llm=llm)

        result = await agent.process({
            "type": "assess_risks",
            "data": {"name": "FinTech App", "duration_weeks": 12},
        })

        assert result["agent"] == "risk_assessment_agent"
        assert isinstance(result["result"], RiskAssessmentOutput)

    @pytest.mark.asyncio
    async def test_build_user_prompt_contains_json(self):
        llm = make_mock_llm(make_risk_fixture())
        agent = RiskAssessmentAgent(llm=llm)
        data = {"name": "Project X", "milestones": ["M1"]}
        prompt = agent.build_user_prompt({"type": "assess_risks", "data": data})
        assert "Project X" in prompt
        assert "M1" in prompt

    @pytest.mark.asyncio
    async def test_output_schema_is_risk_assessment_output(self):
        llm = make_mock_llm()
        agent = RiskAssessmentAgent(llm=llm)
        assert agent.output_schema() is RiskAssessmentOutput


# ---------------------------------------------------------------------------
# StatusReporterAgent
# ---------------------------------------------------------------------------

class TestStatusReporterAgent:
    @pytest.mark.asyncio
    async def test_process_generate_report(self):
        fixture = make_report_fixture()
        llm = make_mock_llm(fixture)
        agent = StatusReporterAgent(llm=llm)

        result = await agent.process({
            "type": "generate_report",
            "data": {"name": "Project Y", "tasks": [], "milestones": []},
        })

        assert result["agent"] == "status_reporter_agent"
        assert isinstance(result["result"], StatusReport)
        assert result["result"].completion_pct == 55.0

    @pytest.mark.asyncio
    async def test_output_schema_is_status_report(self):
        llm = make_mock_llm()
        agent = StatusReporterAgent(llm=llm)
        assert agent.output_schema() is StatusReport


# ---------------------------------------------------------------------------
# GovernanceAgent
# ---------------------------------------------------------------------------

class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_process_low_risk(self):
        fixture = make_governance_fixture(risk="low", requires_validation=False)
        llm = make_mock_llm(fixture)
        agent = GovernanceAgent(llm=llm)

        result = await agent.process({
            "type": "assess_governance",
            "data": {
                "financial_impact": 1000,
                "compliance_level": "low",
                "explainability_score": 0.95,
            },
        })

        assert result["agent"] == "governance_agent"
        assert isinstance(result["result"], GovernanceAssessmentOutput)
        assert result["result"].risk_level == "low"
        assert result["result"].requires_human_validation is False

    @pytest.mark.asyncio
    async def test_process_high_risk(self):
        fixture = make_governance_fixture(risk="high", requires_validation=True)
        llm = make_mock_llm(fixture)
        agent = GovernanceAgent(llm=llm)

        result = await agent.process({
            "type": "assess_governance",
            "data": {
                "financial_impact": 500_000,
                "compliance_level": "critical",
                "explainability_score": 0.3,
            },
        })

        assert result["result"].risk_level == "high"
        assert result["result"].requires_human_validation is True

    def test_update_thresholds_changes_system_prompt(self):
        llm = make_mock_llm()
        agent = GovernanceAgent(llm=llm)
        old_prompt = agent.system_prompt
        agent.update_thresholds({"financial_threshold": 99_999})
        assert agent.financial_threshold == 99_999
        assert "99,999" in agent.system_prompt

    @pytest.mark.asyncio
    async def test_output_schema_is_governance_output(self):
        llm = make_mock_llm()
        agent = GovernanceAgent(llm=llm)
        assert agent.output_schema() is GovernanceAssessmentOutput


# ---------------------------------------------------------------------------
# RoadmappingAgent
# ---------------------------------------------------------------------------

class TestRoadmappingAgent:
    @pytest.mark.asyncio
    async def test_process_generate_roadmap(self):
        fixture = make_roadmap_fixture()
        llm = make_mock_llm(fixture)
        agent = RoadmappingAgent(llm=llm)

        result = await agent.process({
            "type": "generate_roadmap",
            "data": {"business_objectives": ["growth", "efficiency"]},
        })

        assert result["agent"] == "roadmapping_agent"
        assert isinstance(result["result"], RoadmapOutput)
        assert len(result["result"].initiatives) == 1

    @pytest.mark.asyncio
    async def test_build_user_prompt_includes_objectives(self):
        llm = make_mock_llm(make_roadmap_fixture())
        agent = RoadmappingAgent(llm=llm)
        prompt = agent.build_user_prompt({
            "type": "generate_roadmap",
            "data": {"business_objectives": ["cost_reduction"]},
        })
        assert "cost_reduction" in prompt

    @pytest.mark.asyncio
    async def test_output_schema_is_roadmap_output(self):
        llm = make_mock_llm()
        agent = RoadmappingAgent(llm=llm)
        assert agent.output_schema() is RoadmapOutput


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------

class TestOrchestratorAgent:
    def _make_orchestrator_with_agents(self):
        """Build an orchestrator with all mock-LLM agents registered."""
        orch = OrchestratorAgent()

        for agent_cls, agent_key in [
            (ProjectPlanAgent, "project_plan_agent"),
            (RiskAssessmentAgent, "risk_assessment_agent"),
            (StatusReporterAgent, "status_reporter_agent"),
            (GovernanceAgent, "governance_agent"),
            (RoadmappingAgent, "roadmapping_agent"),
        ]:
            mock_llm = make_mock_llm(None)
            agent = agent_cls(llm=mock_llm)
            orch.register_agent(agent)

        return orch

    @pytest.mark.asyncio
    async def test_invalid_message_returns_error(self):
        orch = OrchestratorAgent()
        result = await orch.process({"no_type": True})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_unknown_route_returns_error(self):
        orch = OrchestratorAgent()
        result = await orch.process({"type": "unknown_type", "data": {}})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_routing_generate_plan(self):
        fixture = make_plan_fixture()
        llm = make_mock_llm(fixture)
        agent = ProjectPlanAgent(llm=llm)

        orch = OrchestratorAgent()
        orch.register_agent(agent)

        result = await orch.process({
            "type": "generate_plan",
            "data": {"name": "X", "goals": [], "duration_weeks": 4},
        })

        assert result["agent"] == "project_plan_agent"
        llm.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_routing_assess_governance(self):
        fixture = make_governance_fixture()
        llm = make_mock_llm(fixture)
        agent = GovernanceAgent(llm=llm)

        orch = OrchestratorAgent()
        orch.register_agent(agent)

        result = await orch.process({
            "type": "assess_governance",
            "data": {
                "financial_impact": 100,
                "compliance_level": "low",
                "explainability_score": 1.0,
            },
        })

        assert result["agent"] == "governance_agent"

    @pytest.mark.asyncio
    async def test_routing_generate_roadmap(self):
        fixture = make_roadmap_fixture()
        llm = make_mock_llm(fixture)
        agent = RoadmappingAgent(llm=llm)

        orch = OrchestratorAgent()
        orch.register_agent(agent)

        result = await orch.process({
            "type": "generate_roadmap",
            "data": {"business_objectives": ["growth"]},
        })

        assert result["agent"] == "roadmapping_agent"

    def test_add_routing_rule(self):
        orch = OrchestratorAgent()
        orch.add_routing_rule("custom_type", "custom_agent")
        assert orch.routing_rules["custom_type"] == "custom_agent"

    def test_register_agent(self):
        orch = OrchestratorAgent()
        llm = make_mock_llm()
        agent = ProjectPlanAgent(llm=llm)
        orch.register_agent(agent)
        assert "project_plan_agent" in orch.agent_registry

    @pytest.mark.asyncio
    async def test_workflow_project_initialization(self):
        """Full project_initialization workflow runs three steps sequentially."""
        plan_llm = make_mock_llm(make_plan_fixture())
        risk_llm = make_mock_llm(make_risk_fixture())
        report_llm = make_mock_llm(make_report_fixture())

        orch = OrchestratorAgent()
        orch.register_agent(ProjectPlanAgent(llm=plan_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))

        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {
                    "name": "FinTech MVP",
                    "goals": ["launch payments"],
                    "duration_weeks": 6,
                },
            },
        })

        assert len(result["steps"]) == 3
        step_names = [s["step"] for s in result["steps"]]
        assert step_names == ["generate_plan", "assess_risks", "generate_report"]

    @pytest.mark.asyncio
    async def test_workflow_with_governance_check(self):
        """Workflow with governance_data runs a governance pre-check."""
        plan_llm = make_mock_llm(make_plan_fixture())
        risk_llm = make_mock_llm(make_risk_fixture())
        report_llm = make_mock_llm(make_report_fixture())
        gov_llm = make_mock_llm(make_governance_fixture(risk="low"))

        orch = OrchestratorAgent()
        orch.register_agent(ProjectPlanAgent(llm=plan_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))
        orch.register_agent(GovernanceAgent(llm=gov_llm))

        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Test", "goals": [], "duration_weeks": 4},
                "governance_data": {
                    "financial_impact": 500,
                    "compliance_level": "low",
                    "explainability_score": 1.0,
                },
            },
        })

        # Governance check ran and result is stored
        assert result["governance"] is not None
        assert result["risk_level"] == "low"
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_workflow_governance_failure_fallback(self):
        """If governance agent is missing, workflow falls back to 'low' risk."""
        plan_llm = make_mock_llm(make_plan_fixture())
        risk_llm = make_mock_llm(make_risk_fixture())
        report_llm = make_mock_llm(make_report_fixture())

        orch = OrchestratorAgent()
        # Governance agent intentionally NOT registered
        orch.register_agent(ProjectPlanAgent(llm=plan_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))

        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Test", "goals": [], "duration_weeks": 4},
                "governance_data": {
                    "financial_impact": 500,
                    "compliance_level": "low",
                    "explainability_score": 1.0,
                },
            },
        })

        # Should fall back gracefully
        assert result["risk_level"] == "low"
        assert result["governance"]["requires_human_validation"] is False
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_error_recovery_plan_failure_stops_workflow(self):
        """If the plan agent's LLM raises, the orchestrator returns an error response."""
        # LLM raises exception → exception propagates up through the workflow
        failing_llm = MagicMock(spec=BaseLLM)
        failing_llm.generate = AsyncMock(side_effect=RuntimeError("LLM down"))

        risk_llm = make_mock_llm(make_risk_fixture())
        report_llm = make_mock_llm(make_report_fixture())

        orch = OrchestratorAgent()
        orch.register_agent(ProjectPlanAgent(llm=failing_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))

        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Test", "goals": [], "duration_weeks": 4},
            },
        })

        # Orchestrator top-level handler catches the exception and returns error
        assert result["status"] == "error"
        assert "LLM down" in result["error"]
        # Risk and report agents should NOT have been called
        risk_llm.generate.assert_not_awaited()
        report_llm.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multi_agent_delegation_via_routing(self):
        """
        Verify that each agent type is independently reachable through
        the routing table (multi-agent delegation pattern).
        """
        agents_called = []

        for msg_type, agent_cls, fixture in [
            ("generate_plan",   ProjectPlanAgent,    make_plan_fixture()),
            ("assess_risks",    RiskAssessmentAgent, make_risk_fixture()),
            ("generate_report", StatusReporterAgent, make_report_fixture()),
            ("assess_governance", GovernanceAgent,   make_governance_fixture()),
            ("generate_roadmap",  RoadmappingAgent,  make_roadmap_fixture()),
        ]:
            llm = make_mock_llm(fixture)
            orch = OrchestratorAgent()
            orch.register_agent(agent_cls(llm=llm))

            result = await orch.process({"type": msg_type, "data": {}})
            agents_called.append(result.get("agent"))

        assert agents_called == [
            "project_plan_agent",
            "risk_assessment_agent",
            "status_reporter_agent",
            "governance_agent",
            "roadmapping_agent",
        ]
