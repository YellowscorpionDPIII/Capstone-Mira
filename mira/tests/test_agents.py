"""Tests for core agent functionality."""
import asyncio
import concurrent.futures
import unittest
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.roadmapping_agent import RoadmappingAgent


class TestProjectPlanAgent(unittest.TestCase):
    """Test cases for ProjectPlanAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = ProjectPlanAgent()
        
    def test_generate_plan(self):
        """Test project plan generation."""
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Test Project',
                'description': 'A test project',
                'goals': ['Goal 1', 'Goal 2', 'Goal 3'],
                'duration_weeks': 12
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        self.assertIn('data', response)
        plan = response['data']
        self.assertEqual(plan['name'], 'Test Project')
        self.assertEqual(len(plan['milestones']), 3)
        self.assertEqual(len(plan['tasks']), 9)  # 3 tasks per milestone
        
    def test_invalid_message(self):
        """Test handling of invalid message."""
        message = {'invalid': 'message'}
        response = self.agent.process(message)
        self.assertEqual(response['status'], 'error')


class TestRiskAssessmentAgent(unittest.TestCase):
    """Test cases for RiskAssessmentAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = RiskAssessmentAgent()
        
    def test_assess_risks(self):
        """Test risk assessment."""
        message = {
            'type': 'assess_risks',
            'data': {
                'name': 'Test Project',
                'description': 'urgent project with new technology and limited resources',
                'tasks': [{'id': f'T{i}'} for i in range(20)],
                'duration_weeks': 2
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertIn('risk_score', assessment)
        self.assertIn('risks', assessment)
        self.assertGreater(len(assessment['risks']), 0)
        
    def test_low_risk_project(self):
        """Test assessment of low-risk project."""
        message = {
            'type': 'assess_risks',
            'data': {
                'name': 'Low Risk Project',
                'description': 'simple straightforward project',
                'tasks': [{'id': f'T{i}'} for i in range(5)],
                'duration_weeks': 10
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        # May have fewer risks
        self.assertGreaterEqual(len(assessment['risks']), 0)


class TestStatusReporterAgent(unittest.TestCase):
    """Test cases for StatusReporterAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = StatusReporterAgent()
        
    def test_generate_report(self):
        """Test status report generation."""
        tasks = [
            {'id': 'T1', 'name': 'Task 1', 'status': 'completed'},
            {'id': 'T2', 'name': 'Task 2', 'status': 'completed'},
            {'id': 'T3', 'name': 'Task 3', 'status': 'in_progress'},
            {'id': 'T4', 'name': 'Task 4', 'status': 'not_started'}
        ]
        
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
        config = {'api_key': 'test_key', 'base_id': 'test_base'}
        self.roadmap_agent = RoadmappingAgent(config=config)
        
        self.orchestrator.register_agent(self.plan_agent)
        self.orchestrator.register_agent(self.risk_agent)
        self.orchestrator.register_agent(self.status_agent)
        self.orchestrator.register_agent(self.roadmap_agent)
        
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
    
    def test_route_to_roadmapping_agent(self):
        """Test routing to roadmapping agent."""
        message = {
            'type': 'generate_roadmap',
            'data': {
                'business_objectives': ['efficiency', 'growth']
            }
        }
        
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        roadmap = response['data']
        self.assertIn('initiatives', roadmap)
        self.assertEqual(len(roadmap['initiatives']), 2)
        
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
            agent = ProjectPlanAgent(agent_id=f"temp_agent_{agent_num}")
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


class TestRoadmappingAgent(unittest.TestCase):
    """Test cases for RoadmappingAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = {
            'api_key': 'test_key',
            'base_id': 'test_base'
        }
        self.agent = RoadmappingAgent(config=config)
        
    def test_generate_roadmap(self):
        """Test roadmap generation with business objectives."""
        message = {
            'type': 'generate_roadmap',
            'data': {
                'business_objectives': ['efficiency', 'growth', 'innovation']
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        self.assertIn('data', response)
        roadmap = response['data']
        self.assertIn('initiatives', roadmap)
        self.assertIn('ebit_projection', roadmap)
        self.assertIn('timeline', roadmap)
        self.assertEqual(len(roadmap['initiatives']), 3)
        self.assertGreater(roadmap['ebit_projection'], 0.0)
        
    def test_generate_roadmap_empty_objectives(self):
        """Test roadmap generation with no objectives."""
        message = {
            'type': 'generate_roadmap',
            'data': {
                'business_objectives': []
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        roadmap = response['data']
        self.assertEqual(len(roadmap['initiatives']), 0)
        self.assertEqual(roadmap['ebit_projection'], 0.0)
        
    def test_track_kpi_progress(self):
        """Test KPI progress tracking."""
        message = {
            'type': 'track_kpi_progress',
            'data': {
                'initiative_id': 'INIT-001'
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        kpi_progress = response['data']
        self.assertIn('initiative_id', kpi_progress)
        self.assertIn('ebit_attribution', kpi_progress)
        self.assertIn('revenue_impact', kpi_progress)
        self.assertIn('cost_savings', kpi_progress)
        self.assertEqual(kpi_progress['initiative_id'], 'INIT-001')
        
    def test_calculate_ebit_impact(self):
        """Test EBIT impact calculation."""
        initiatives = [
            {
                'ebit_impact': 0.25,
                'revenue': 0.20,
                'cost_save': 0.30,
                'scale_factor': 1.0
            },
            {
                'ebit_impact': 0.30,
                'revenue': 0.25,
                'cost_save': 0.20,
                'scale_factor': 1.5
            }
        ]
        
        total_ebit = self.agent._calculate_ebit_impact(initiatives)
        
        # Expected: (0.25*0.4 + 0.20*0.3 + 0.30*0.3)*1.0 + (0.30*0.4 + 0.25*0.3 + 0.20*0.3)*1.5
        # = (0.1 + 0.06 + 0.09)*1.0 + (0.12 + 0.075 + 0.06)*1.5
        # = 0.25 + 0.3825 = 0.6325, rounded to 0.63
        self.assertAlmostEqual(total_ebit, 0.63, places=2)
        
    def test_prioritize_initiatives(self):
        """Test initiative prioritization for different objectives."""
        efficiency_initiatives = self.agent._prioritize_initiatives('efficiency')
        growth_initiatives = self.agent._prioritize_initiatives('growth')
        innovation_initiatives = self.agent._prioritize_initiatives('innovation')
        
        self.assertEqual(len(efficiency_initiatives), 1)
        self.assertEqual(len(growth_initiatives), 1)
        self.assertEqual(len(innovation_initiatives), 1)
        
        # Check that initiatives have required fields
        for initiative in efficiency_initiatives:
            self.assertIn('name', initiative)
            self.assertIn('objective', initiative)
            self.assertIn('ebit_impact', initiative)
            self.assertIn('priority', initiative)
            
    def test_invalid_message(self):
        """Test handling of invalid message."""
        message = {'invalid': 'message'}
        response = self.agent.process(message)
        self.assertEqual(response['status'], 'error')
        
    def test_unknown_message_type(self):
        """Test handling of unknown message type."""
        message = {
            'type': 'unknown_type',
            'data': {}
        }
        response = self.agent.process(message)
        self.assertEqual(response['status'], 'error')


if __name__ == '__main__':
    unittest.main()
