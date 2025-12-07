"""Tests for core agent functionality."""
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
