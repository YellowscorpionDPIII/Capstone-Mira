"""Tests for core agent functionality."""
import unittest
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent, GovernanceAgent


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
    
    def test_workflow_with_governance_check(self):
        """Test workflow execution includes governance check."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Governance Test Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10,
                    'financial_impact': 50000
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        # Check governance results are present
        self.assertIn('governance', response)
        governance_result = response['governance']
        self.assertIn('requires_human_review', governance_result)
        self.assertIn('financial_check', governance_result)
        self.assertIn('compliance_check', governance_result)
        self.assertIn('explainability_check', governance_result)
        self.assertIn('risk_level_check', governance_result)
        
        # Check governance step was added
        governance_steps = [s for s in response['steps'] if s['step'] == 'governance_check']
        self.assertEqual(len(governance_steps), 1)
        
    def test_workflow_with_high_financial_impact(self):
        """Test workflow requiring human review due to high financial impact."""
        config = {
            'governance': {
                'financial_impact_threshold': 50000
            }
        }
        orchestrator = OrchestratorAgent(config=config)
        orchestrator.register_agent(self.plan_agent)
        orchestrator.register_agent(self.risk_agent)
        orchestrator.register_agent(self.status_agent)
        
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'High-Value Project',
                    'goals': ['Goal 1'],
                    'duration_weeks': 10,
                    'financial_impact': 150000
                }
            }
        }
        
        response = orchestrator.process(message)
        
        # Check requires human review
        self.assertTrue(response['governance']['requires_human_review'])
        self.assertEqual(response.get('status'), 'pending_human_review')
        self.assertIn('Financial impact', response.get('human_review_reason', ''))
        
    def test_workflow_with_compliance_requirements(self):
        """Test workflow requiring human review due to compliance."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Compliance Project',
                    'goals': ['Goal 1'],
                    'duration_weeks': 10,
                    'compliance_requirements': ['GDPR', 'HIPAA']
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        # Check compliance check results
        compliance_check = response['governance']['compliance_check']
        self.assertTrue(compliance_check['requires_review'])
        self.assertEqual(len(compliance_check['compliance_requirements']), 2)
        
    def test_backward_compatibility(self):
        """Test that workflows without governance data still work."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Legacy Project',
                    'goals': ['Goal 1'],
                    'duration_weeks': 10
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        # Should complete successfully
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertGreater(len(response['steps']), 0)
        
        # Governance check should still be present but not require review
        self.assertIn('governance', response)
        

class TestGovernanceAgent(unittest.TestCase):
    """Test cases for GovernanceAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.governance_agent = GovernanceAgent()
        
    def test_initialization_with_defaults(self):
        """Test GovernanceAgent initializes with default thresholds."""
        agent = GovernanceAgent()
        thresholds = agent.thresholds
        
        self.assertEqual(thresholds['financial_impact_threshold'], 100000)
        self.assertEqual(thresholds['compliance_risk_threshold'], 70)
        self.assertEqual(thresholds['explainability_threshold'], 0.5)
        self.assertEqual(thresholds['high_risk_score_threshold'], 75)
        
    def test_initialization_with_custom_config(self):
        """Test GovernanceAgent initializes with custom thresholds."""
        config = {
            'governance': {
                'financial_impact_threshold': 50000,
                'high_risk_score_threshold': 80
            }
        }
        agent = GovernanceAgent(config=config)
        thresholds = agent.thresholds
        
        self.assertEqual(thresholds['financial_impact_threshold'], 50000)
        self.assertEqual(thresholds['high_risk_score_threshold'], 80)
        
    def test_financial_impact_check_exceeds_threshold(self):
        """Test financial impact check when exceeding threshold."""
        result = self.governance_agent._check_financial_impact(150000)
        
        self.assertTrue(result['requires_review'])
        self.assertEqual(result['financial_impact'], 150000)
        self.assertIn('exceeds threshold', result['reason'])
        
    def test_financial_impact_check_below_threshold(self):
        """Test financial impact check when below threshold."""
        result = self.governance_agent._check_financial_impact(50000)
        
        self.assertFalse(result['requires_review'])
        self.assertIsNone(result['reason'])
        
    def test_compliance_check_with_requirements(self):
        """Test compliance check with compliance requirements."""
        compliance_requirements = ['GDPR', 'SOX']
        risks = []
        
        result = self.governance_agent._check_compliance(compliance_requirements, risks)
        
        self.assertTrue(result['requires_review'])
        self.assertEqual(len(result['compliance_requirements']), 2)
        self.assertIn('Compliance requirements present', result['reason'])
        
    def test_compliance_check_with_high_severity_risks(self):
        """Test compliance check with high-severity compliance risks."""
        compliance_requirements = []
        risks = [
            {
                'category': 'compliance',
                'severity': 'high',
                'description': 'Data privacy compliance risk'
            }
        ]
        
        result = self.governance_agent._check_compliance(compliance_requirements, risks)
        
        self.assertTrue(result['requires_review'])
        self.assertEqual(result['high_severity_compliance_risks'], 1)
        self.assertIn('High-severity compliance risks', result['reason'])
        
    def test_explainability_check_high_score(self):
        """Test explainability check with complete documentation."""
        plan_data = {
            'description': 'Well documented plan',
            'milestones': [{'id': 'M1'}],
            'tasks': [{'id': 'T1'}]
        }
        risk_data = {
            'risks': [
                {
                    'description': 'Risk 1',
                    'mitigation': 'Mitigation strategy 1'
                }
            ]
        }
        
        result = self.governance_agent._check_explainability(plan_data, risk_data)
        
        self.assertFalse(result['requires_review'])
        self.assertGreaterEqual(result['explainability_score'], 0.5)
        self.assertEqual(len(result['factors_present']), 5)
        
    def test_explainability_check_low_score(self):
        """Test explainability check with incomplete documentation."""
        plan_data = {}
        risk_data = {'risks': []}
        
        result = self.governance_agent._check_explainability(plan_data, risk_data)
        
        self.assertTrue(result['requires_review'])
        self.assertLess(result['explainability_score'], 0.5)
        self.assertIn('below threshold', result['reason'])
        
    def test_risk_level_check_high_risk(self):
        """Test risk level check with high risk score."""
        result = self.governance_agent._check_risk_level(85.0)
        
        self.assertTrue(result['requires_review'])
        self.assertEqual(result['risk_level'], 'high')
        self.assertIn('exceeds high-risk threshold', result['reason'])
        
    def test_risk_level_check_medium_risk(self):
        """Test risk level check with medium risk score."""
        result = self.governance_agent._check_risk_level(60.0)
        
        self.assertFalse(result['requires_review'])
        self.assertEqual(result['risk_level'], 'medium')
        
    def test_risk_level_check_low_risk(self):
        """Test risk level check with low risk score."""
        result = self.governance_agent._check_risk_level(30.0)
        
        self.assertFalse(result['requires_review'])
        self.assertEqual(result['risk_level'], 'low')
        
    def test_perform_governance_check_requires_review(self):
        """Test full governance check requiring human review."""
        workflow_data = {
            'financial_impact': 200000,
            'compliance_requirements': ['GDPR']
        }
        plan_data = {
            'name': 'Test Project',
            'description': 'Test description'
        }
        risk_data = {
            'risk_score': 85.0,
            'risks': []
        }
        
        result = self.governance_agent.perform_governance_check(
            workflow_data, plan_data, risk_data
        )
        
        self.assertTrue(result['requires_human_review'])
        self.assertIsNotNone(result['review_reason'])
        self.assertIn('Financial impact', result['review_reason'])
        
    def test_perform_governance_check_no_review_needed(self):
        """Test full governance check not requiring human review."""
        workflow_data = {
            'financial_impact': 50000,
            'compliance_requirements': []
        }
        plan_data = {
            'name': 'Simple Project',
            'description': 'Simple description',
            'milestones': [{'id': 'M1'}],
            'tasks': [{'id': 'T1'}]
        }
        risk_data = {
            'risk_score': 30.0,
            'risks': [
                {
                    'description': 'Minor risk',
                    'mitigation': 'Simple mitigation'
                }
            ]
        }
        
        result = self.governance_agent.perform_governance_check(
            workflow_data, plan_data, risk_data
        )
        
        self.assertFalse(result['requires_human_review'])
        self.assertIsNone(result['review_reason'])


if __name__ == '__main__':
    unittest.main()
