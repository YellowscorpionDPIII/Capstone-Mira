"""Tests for core agent functionality."""
import unittest
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent


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


if __name__ == '__main__':
    unittest.main()
