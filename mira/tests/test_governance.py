"""Tests for GovernanceAgent and governance orchestration integration."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mira.llm.base import BaseLLM
from mira.llm.schemas import GovernanceAssessmentOutput
from mira.agents.governance_agent import GovernanceAgent, _build_governance_system_prompt
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.llm.schemas import (
    ProjectPlanOutput, Milestone, Task,
    RiskAssessmentOutput, Risk, StatusReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_llm(return_value=None):
    mock = MagicMock(spec=BaseLLM)
    mock.generate = AsyncMock(return_value={"text": return_value, "raw": MagicMock()})
    return mock


def gov_out(risk="low", requires=False, reasons=None, actions=None):
    return GovernanceAssessmentOutput(
        risk_level=risk,
        requires_human_validation=requires,
        reasons=reasons or [],
        recommended_actions=actions or ["Proceed"],
    )


def plan_out():
    return ProjectPlanOutput(
        project_name="Test",
        milestones=[Milestone(name="M1", description="d", due_date="2026-06-01",
                              tasks=[Task(name="T1", priority="high", estimated_hours=4)])],
        total_duration_weeks=6,
    )


def risk_out():
    return RiskAssessmentOutput(
        project_id="proj-1",
        risks=[Risk(category="schedule", description="tight", severity="low",
                    probability="low", mitigation="buffer", impact_score=0.2)],
        overall_risk_score=0.2,
        summary="Low risk",
    )


def report_out():
    return StatusReport(
        week_ending="2026-03-01",
        completion_pct=40.0,
        accomplished=["Done"],
        blockers=[],
        upcoming_milestones=["Launch"],
        risks_summary="None",
    )


# ---------------------------------------------------------------------------
# GovernanceAgent unit tests (LLM-backed)
# ---------------------------------------------------------------------------

class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_low_risk_assessment(self):
        llm = make_llm(gov_out(risk="low", requires=False))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 5000, "compliance_level": "low",
                     "explainability_score": 0.9},
        })
        assert result["agent"] == "governance_agent"
        assert isinstance(result["result"], GovernanceAssessmentOutput)
        assert result["result"].risk_level == "low"
        assert result["result"].requires_human_validation is False

    @pytest.mark.asyncio
    async def test_high_financial_impact(self):
        llm = make_llm(gov_out(risk="high", requires=True,
                               reasons=["Financial impact $50,000 exceeds threshold"]))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 50000, "compliance_level": "low",
                     "explainability_score": 0.9},
        })
        assert result["result"].risk_level == "high"
        assert result["result"].requires_human_validation is True
        assert len(result["result"].reasons) > 0

    @pytest.mark.asyncio
    async def test_high_compliance_requirement(self):
        llm = make_llm(gov_out(risk="medium", requires=True,
                               reasons=["Compliance level 'high' requires review"]))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 5000, "compliance_level": "high",
                     "explainability_score": 0.9},
        })
        assert result["result"].risk_level in ("medium", "high")
        assert result["result"].requires_human_validation is True

    @pytest.mark.asyncio
    async def test_critical_compliance_requirement(self):
        llm = make_llm(gov_out(risk="high", requires=True,
                               reasons=["Critical compliance level"]))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 5000, "compliance_level": "critical",
                     "explainability_score": 0.9},
        })
        assert result["result"].requires_human_validation is True

    @pytest.mark.asyncio
    async def test_low_explainability_score(self):
        llm = make_llm(gov_out(risk="medium", requires=True,
                               reasons=["Explainability score 0.50 below threshold"]))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 5000, "compliance_level": "low",
                     "explainability_score": 0.5},
        })
        assert result["result"].risk_level in ("medium", "high")
        assert result["result"].requires_human_validation is True
        assert any("Explainability" in r or "explainability" in r
                   for r in result["result"].reasons)

    @pytest.mark.asyncio
    async def test_multiple_risk_factors(self):
        llm = make_llm(gov_out(risk="high", requires=True,
                               reasons=["Financial impact", "Compliance", "Explainability"]))
        agent = GovernanceAgent(llm=llm)
        result = await agent.process({
            "type": "assess_governance",
            "data": {"financial_impact": 50000, "compliance_level": "high",
                     "explainability_score": 0.5},
        })
        assert result["result"].risk_level == "high"
        assert len(result["result"].reasons) == 3

    def test_yaml_config_loading_thresholds(self):
        """GovernanceAgent loads default thresholds from YAML at init."""
        llm = make_llm()
        agent = GovernanceAgent(llm=llm)
        assert agent.financial_threshold == 10000
        assert agent.compliance_threshold == "medium"
        assert agent.explainability_threshold == 0.7

    def test_update_thresholds(self):
        """update_thresholds changes values and regenerates system prompt."""
        llm = make_llm()
        agent = GovernanceAgent(llm=llm)
        agent.update_thresholds({
            "financial_threshold": 25000,
            "explainability_threshold": 0.6,
        })
        assert agent.financial_threshold == 25000
        assert agent.explainability_threshold == 0.6
        assert "25,000" in agent.system_prompt

    def test_system_prompt_includes_thresholds(self):
        """System prompt embeds the configured threshold values."""
        prompt = _build_governance_system_prompt({
            "financial_threshold": 99000,
            "compliance_threshold": "critical",
            "explainability_threshold": 0.5,
        })
        assert "99,000" in prompt
        assert "critical" in prompt
        assert "0.5" in prompt

    def test_output_schema_is_governance_output(self):
        llm = make_llm()
        agent = GovernanceAgent(llm=llm)
        assert agent.output_schema() is GovernanceAssessmentOutput

    def test_validate_message_works(self):
        llm = make_llm()
        agent = GovernanceAgent(llm=llm)
        assert agent.validate_message({"type": "assess_governance", "data": {}})
        assert not agent.validate_message({"type": "assess_governance"})

    def test_build_user_prompt_includes_metrics(self):
        llm = make_llm()
        agent = GovernanceAgent(llm=llm)
        prompt = agent.build_user_prompt({
            "type": "assess_governance",
            "data": {
                "financial_impact": 50000,
                "compliance_level": "high",
                "explainability_score": 0.4,
            },
        })
        assert "50,000" in prompt
        assert "high" in prompt
        assert "0.4" in prompt


# ---------------------------------------------------------------------------
# OrchestratorAgent + GovernanceAgent integration tests (async)
# ---------------------------------------------------------------------------

class TestOrchestratorGovernanceIntegration:
    def _build_orch(self, gov_fixture, plan_fixture=None, risk_fixture=None,
                   report_fixture=None):
        """Build an orchestrator with mocked agents registered."""
        gov_llm = make_llm(gov_fixture)
        plan_llm = make_llm(plan_fixture or plan_out())
        risk_llm = make_llm(risk_fixture or risk_out())
        report_llm = make_llm(report_fixture or report_out())

        orch = OrchestratorAgent()
        orch.register_agent(GovernanceAgent(llm=gov_llm))
        orch.register_agent(ProjectPlanAgent(llm=plan_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))
        return orch

    def test_governance_routing_rules_exist(self):
        orch = OrchestratorAgent()
        assert orch.routing_rules["assess_governance"] == "governance_agent"
        assert orch.routing_rules["check_human_validation"] == "governance_agent"

    def test_governance_agent_registered(self):
        orch = OrchestratorAgent()
        gov_llm = make_llm(gov_out())
        orch.register_agent(GovernanceAgent(llm=gov_llm))
        assert "governance_agent" in orch.agent_registry
        assert isinstance(orch.agent_registry["governance_agent"], GovernanceAgent)

    @pytest.mark.asyncio
    async def test_route_to_governance_agent(self):
        orch = self._build_orch(gov_out(risk="high", requires=True))
        result = await orch.process({
            "type": "assess_governance",
            "data": {"financial_impact": 50000, "compliance_level": "high",
                     "explainability_score": 0.6},
        })
        assert result["agent"] == "governance_agent"
        assert isinstance(result["result"], GovernanceAssessmentOutput)

    @pytest.mark.asyncio
    async def test_workflow_with_governance_low_risk(self):
        orch = self._build_orch(gov_out(risk="low", requires=False))
        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Low Risk Project", "goals": ["G1"], "duration_weeks": 10},
                "governance_data": {"financial_impact": 5000, "compliance_level": "low",
                                    "explainability_score": 0.9},
            },
        })
        assert result["workflow_type"] == "project_initialization"
        assert result["governance"] is not None
        assert result["governance"]["risk_level"] == "low"
        assert result["governance"]["requires_human_validation"] is False
        assert "status" not in result or result.get("status") != "pending_approval"

    @pytest.mark.asyncio
    async def test_workflow_with_governance_high_risk(self):
        orch = self._build_orch(gov_out(risk="high", requires=True))
        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "High Risk Project", "goals": ["G1"], "duration_weeks": 10},
                "governance_data": {"financial_impact": 100000, "compliance_level": "critical",
                                    "explainability_score": 0.4},
            },
        })
        assert result["governance"]["risk_level"] == "high"
        assert result["governance"]["requires_human_validation"] is True
        assert result.get("status") == "pending_approval"

    @pytest.mark.asyncio
    async def test_workflow_without_governance_data(self):
        """Backward compatibility: workflow without governance_data still runs."""
        orch = self._build_orch(gov_out())
        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Regular Project", "goals": ["G1"], "duration_weeks": 10},
            },
        })
        assert result["workflow_type"] == "project_initialization"
        assert result["governance"] is None
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_governance_error_fallback(self):
        """If governance agent raises, workflow falls back to low risk."""
        failing_llm = MagicMock(spec=BaseLLM)
        failing_llm.generate = AsyncMock(side_effect=RuntimeError("gov broken"))

        plan_llm = make_llm(plan_out())
        risk_llm = make_llm(risk_out())
        report_llm = make_llm(report_out())

        orch = OrchestratorAgent()
        orch.register_agent(GovernanceAgent(llm=failing_llm))
        orch.register_agent(ProjectPlanAgent(llm=plan_llm))
        orch.register_agent(RiskAssessmentAgent(llm=risk_llm))
        orch.register_agent(StatusReporterAgent(llm=report_llm))

        result = await orch.process({
            "type": "workflow",
            "data": {
                "workflow_type": "project_initialization",
                "data": {"name": "Test", "goals": [], "duration_weeks": 4},
                "governance_data": {"financial_impact": 100000, "compliance_level": "critical",
                                    "explainability_score": 0.3},
            },
        })
        # Should fall back gracefully instead of raising
        assert result["risk_level"] == "low"
        assert result["governance"]["requires_human_validation"] is False
        assert len(result["steps"]) == 3
