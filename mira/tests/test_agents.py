<<<<<<< HEAD
"""Tests for core agent functionality."""
import asyncio
import concurrent.futures
import unittest
=======
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
>>>>>>> origin/main
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
<<<<<<< HEAD
        
        milestones = [
            {'id': 'M1', 'name': 'Milestone 1', 'week': 5},
            {'id': 'M2', 'name': 'Milestone 2', 'week': 10}
        ]
        
        risks = [
            {'id': 'R1', 'severity': 'high', 'description': 'Critical risk'}
        ]
        
        message = {
            'type': 'generate_report',
            'data': {
                'name': 'Test Project',
                'week_number': 4,
                'tasks': tasks,
                'milestones': milestones,
                'risks': risks
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        report = response['data']
        self.assertEqual(report['week_number'], 4)
        self.assertEqual(report['summary']['total_tasks'], 4)
        self.assertEqual(report['summary']['completed_tasks'], 2)
        self.assertAlmostEqual(report['summary']['completion_percentage'], 50.0)
        
    def test_schedule_report(self):
        """Test report scheduling."""
        message = {
            'type': 'schedule_report',
            'data': {
                'frequency': 'weekly',
                'recipients': ['user1@example.com', 'user2@example.com'],
                'day_of_week': 'Friday'
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        schedule = response['data']
        self.assertEqual(schedule['frequency'], 'weekly')
        self.assertEqual(len(schedule['recipients']), 2)


class TestOrchestratorAgent(unittest.TestCase):
    """Test cases for OrchestratorAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorAgent()
        
        # Register agents
        self.plan_agent = ProjectPlanAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.status_agent = StatusReporterAgent()
        
        self.orchestrator.register_agent(self.plan_agent)
        self.orchestrator.register_agent(self.risk_agent)
        self.orchestrator.register_agent(self.status_agent)
        
    def test_route_to_plan_agent(self):
        """Test routing to project plan agent."""
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Test Project',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
        
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        
    def test_workflow_execution(self):
        """Test multi-agent workflow execution."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Workflow Test',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertGreater(len(response['steps']), 0)
        
        # Check all steps completed successfully
        for step in response['steps']:
            self.assertEqual(step['status'], 'success')
    
    # --- Invalid Input Tests ---
    
    def test_invalid_message_not_dict(self):
        """Test handling of non-dict message."""
        response = self.orchestrator.process("invalid string message")
        self.assertEqual(response['status'], 'error')
        self.assertIn('dictionary', response['error'])
    
    def test_invalid_message_none(self):
        """Test handling of None message."""
        response = self.orchestrator.process(None)
        self.assertEqual(response['status'], 'error')
    
    def test_invalid_message_missing_type(self):
        """Test handling of message missing 'type' field."""
        message = {'data': {'name': 'Test'}}
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'error')
        self.assertIn('Invalid message format', response['error'])
    
    def test_invalid_message_missing_data(self):
        """Test handling of message missing 'data' field."""
        message = {'type': 'generate_plan'}
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'error')
        self.assertIn('Invalid message format', response['error'])
    
    def test_invalid_message_empty_dict(self):
        """Test handling of empty dict message."""
        response = self.orchestrator.process({})
        self.assertEqual(response['status'], 'error')
    
    def test_unknown_message_type(self):
        """Test handling of unknown message type."""
        message = {
            'type': 'unknown_type',
            'data': {'name': 'Test'}
        }
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'error')
        self.assertIn('No routing rule', response['error'])
    
    def test_agent_not_registered(self):
        """Test handling when target agent is not registered."""
        # Create a new orchestrator without registered agents
        orchestrator = OrchestratorAgent()
        message = {
            'type': 'generate_plan',
            'data': {'name': 'Test'}
        }
        response = orchestrator.process(message)
        self.assertEqual(response['status'], 'error')
        self.assertIn('Agent not found', response['error'])
    
    def test_register_agent_none(self):
        """Test that registering None agent raises error."""
        orchestrator = OrchestratorAgent()
        with self.assertRaises(ValueError):
            orchestrator.register_agent(None)
    
    def test_register_agent_invalid(self):
        """Test that registering invalid agent raises error."""
        orchestrator = OrchestratorAgent()
        with self.assertRaises(ValueError):
            orchestrator.register_agent("not an agent")
    
    def test_add_routing_rule_empty_message_type(self):
        """Test that adding routing rule with empty message_type raises error."""
        with self.assertRaises(ValueError):
            self.orchestrator.add_routing_rule("", "some_agent")
    
    def test_add_routing_rule_none_message_type(self):
        """Test that adding routing rule with None message_type raises error."""
        with self.assertRaises(ValueError):
            self.orchestrator.add_routing_rule(None, "some_agent")
    
    def test_add_routing_rule_empty_agent_id(self):
        """Test that adding routing rule with empty agent_id raises error."""
        with self.assertRaises(ValueError):
            self.orchestrator.add_routing_rule("some_type", "")
    
    def test_add_routing_rule_success(self):
        """Test successful addition of routing rule."""
        self.orchestrator.add_routing_rule("custom_type", "custom_agent")
        self.assertEqual(self.orchestrator.routing_rules.get("custom_type"), "custom_agent")
    
    def test_workflow_invalid_data_not_dict(self):
        """Test handling of workflow with invalid data (not a dict)."""
        message = {
            'type': 'workflow',
            'data': "invalid string data"
        }
        response = self.orchestrator.process(message)
        self.assertIn('error', response)
    
    def test_workflow_unknown_type(self):
        """Test handling of unknown workflow type."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'unknown_workflow',
                'data': {'name': 'Test'}
            }
        }
        response = self.orchestrator.process(message)
        self.assertEqual(response['workflow_type'], 'unknown_workflow')
        self.assertEqual(len(response['steps']), 0)


class TestOrchestratorAgentAsync(unittest.TestCase):
    """Test cases for OrchestratorAgent async functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorAgent()
        self.plan_agent = ProjectPlanAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.status_agent = StatusReporterAgent()
        
        self.orchestrator.register_agent(self.plan_agent)
        self.orchestrator.register_agent(self.risk_agent)
        self.orchestrator.register_agent(self.status_agent)
    
    def test_async_process(self):
        """Test async process method."""
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Async Test Project',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
        
        response = asyncio.run(self.orchestrator.process_async(message))
        self.assertEqual(response['status'], 'success')
    
    def test_async_route_message(self):
        """Test async route message method."""
        message = {
            'type': 'assess_risks',
            'data': {
                'name': 'Risk Test',
                'description': 'test',
                'tasks': [],
                'duration_weeks': 4
            }
        }
        
        response = asyncio.run(self.orchestrator._route_message_async(message))
        self.assertEqual(response['status'], 'success')
    
    def test_async_workflow_execution(self):
        """Test async workflow execution."""
        data = {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Async Workflow Test',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
        
        response = asyncio.run(self.orchestrator._execute_workflow_async(data))
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertGreater(len(response['steps']), 0)


class TestOrchestratorAgentConcurrency(unittest.TestCase):
    """Test cases for OrchestratorAgent concurrent access."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorAgent()
        self.plan_agent = ProjectPlanAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.status_agent = StatusReporterAgent()
        
        self.orchestrator.register_agent(self.plan_agent)
        self.orchestrator.register_agent(self.risk_agent)
        self.orchestrator.register_agent(self.status_agent)
    
    def test_concurrent_message_processing(self):
        """Test concurrent message processing with ThreadPoolExecutor."""
        messages = [
            {
                'type': 'generate_plan',
                'data': {
                    'name': f'Project {i}',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
            for i in range(5)
        ]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.orchestrator.process, msg) for msg in messages]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status'], 'success')
    
    def test_concurrent_different_message_types(self):
        """Test concurrent processing of different message types."""
        messages = [
            {
                'type': 'generate_plan',
                'data': {'name': 'Plan Project', 'goals': ['Goal'], 'duration_weeks': 8}
            },
            {
                'type': 'assess_risks',
                'data': {'name': 'Risk Project', 'description': 'test', 'tasks': [], 'duration_weeks': 4}
            },
            {
                'type': 'generate_report',
                'data': {'name': 'Report Project', 'week_number': 1, 'tasks': [], 'milestones': [], 'risks': []}
            }
        ]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.orchestrator.process, msg) for msg in messages]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result['status'], 'success')
    
    def test_concurrent_workflow_and_single_messages(self):
        """Test concurrent workflow and single message processing."""
        workflow_message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Concurrent Workflow',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        single_messages = [
            {
                'type': 'generate_plan',
                'data': {'name': f'Single Project {i}', 'goals': ['Goal'], 'duration_weeks': 4}
            }
            for i in range(3)
        ]
        
        all_messages = [workflow_message] + single_messages
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self.orchestrator.process, msg) for msg in all_messages]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        self.assertEqual(len(results), 4)
        
        # Count successful results
        success_count = sum(1 for r in results if r.get('status') == 'success' or 'workflow_type' in r)
        self.assertEqual(success_count, 4)
    
    def test_agent_registry_thread_safety(self):
        """Test that agent registry access is thread-safe during concurrent operations."""
        def register_and_process(agent_num):
            # Note: In real concurrent scenarios, we'd need synchronization
            # This test validates that operations complete without errors
            message = {
                'type': 'generate_plan',
                'data': {'name': f'Project {agent_num}', 'goals': ['Goal'], 'duration_weeks': 4}
            }
            return self.orchestrator.process(message)
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_and_process, i) for i in range(5)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status'], 'success')


if __name__ == '__main__':
    unittest.main()
=======
>>>>>>> origin/main
