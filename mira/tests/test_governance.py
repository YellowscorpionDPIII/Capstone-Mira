"""Tests for GovernanceAgent and governance integration."""
import unittest
from mira.agents.governance_agent import GovernanceAgent
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent


class TestGovernanceAgent(unittest.TestCase):
    """Test cases for GovernanceAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = GovernanceAgent()
        
    def test_low_risk_assessment(self):
        """Test governance assessment for low-risk scenario."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 5000,
                'compliance_level': 'low',
                'explainability_score': 0.9
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertEqual(assessment['risk_level'], 'low')
        self.assertFalse(assessment['requires_human_validation'])
        self.assertEqual(len(assessment['reasons']), 0)
        
    def test_high_financial_impact(self):
        """Test governance assessment with high financial impact."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 50000,
                'compliance_level': 'low',
                'explainability_score': 0.9
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertEqual(assessment['risk_level'], 'high')
        self.assertTrue(assessment['requires_human_validation'])
        self.assertGreater(len(assessment['reasons']), 0)
        self.assertIn('Financial impact', assessment['reasons'][0])
        
    def test_high_compliance_requirement(self):
        """Test governance assessment with high compliance requirement."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 5000,
                'compliance_level': 'high',
                'explainability_score': 0.9
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertIn(assessment['risk_level'], ['medium', 'high'])
        self.assertTrue(assessment['requires_human_validation'])
        self.assertGreater(len(assessment['reasons']), 0)
        
    def test_critical_compliance_requirement(self):
        """Test governance assessment with critical compliance requirement."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 5000,
                'compliance_level': 'critical',
                'explainability_score': 0.9
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertTrue(assessment['requires_human_validation'])
        
    def test_low_explainability_score(self):
        """Test governance assessment with low explainability score."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 5000,
                'compliance_level': 'low',
                'explainability_score': 0.5
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertIn(assessment['risk_level'], ['medium', 'high'])
        self.assertTrue(assessment['requires_human_validation'])
        self.assertGreater(len(assessment['reasons']), 0)
        self.assertIn('Explainability', assessment['reasons'][0])
        
    def test_multiple_risk_factors(self):
        """Test governance assessment with multiple risk factors."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 50000,
                'compliance_level': 'high',
                'explainability_score': 0.5
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        self.assertEqual(assessment['risk_level'], 'high')
        self.assertTrue(assessment['requires_human_validation'])
        self.assertEqual(len(assessment['reasons']), 3)
        
    def test_custom_thresholds(self):
        """Test governance agent with custom thresholds."""
        config = {
            'financial_threshold': 20000,
            'compliance_threshold': 'high',
            'explainability_threshold': 0.8
        }
        agent = GovernanceAgent(config=config)
        
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 15000,
                'compliance_level': 'medium',
                'explainability_score': 0.75
            }
        }
        
        response = agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        assessment = response['data']
        # Should be low risk with these custom thresholds
        self.assertIn(assessment['risk_level'], ['low', 'medium'])
        
    def test_check_human_validation(self):
        """Test check_human_validation message type."""
        message = {
            'type': 'check_human_validation',
            'data': {
                'financial_impact': 50000,
                'compliance_level': 'low',
                'explainability_score': 0.9
            }
        }
        
        response = self.agent.process(message)
        
        self.assertEqual(response['status'], 'success')
        result = response['data']
        self.assertIn('requires_validation', result)
        self.assertIn('risk_level', result)
        self.assertTrue(result['requires_validation'])
        
    def test_update_thresholds(self):
        """Test updating governance thresholds."""
        initial_threshold = self.agent.financial_threshold
        
        self.agent.update_thresholds({
            'financial_threshold': 25000,
            'explainability_threshold': 0.6
        })
        
        self.assertEqual(self.agent.financial_threshold, 25000)
        self.assertEqual(self.agent.explainability_threshold, 0.6)
        self.assertNotEqual(self.agent.financial_threshold, initial_threshold)
        
    def test_yaml_config_loading(self):
        """Test that YAML config file is loaded correctly."""
        agent = GovernanceAgent()
        # With YAML config file, should have loaded default thresholds
        self.assertEqual(agent.financial_threshold, 10000)
        self.assertEqual(agent.compliance_threshold, 'medium')
        self.assertEqual(agent.explainability_threshold, 0.7)
        
    def test_config_override_yaml(self):
        """Test that config parameter overrides YAML config."""
        config = {
            'financial_threshold': 30000,
            'explainability_threshold': 0.5
        }
        agent = GovernanceAgent(config=config)
        # Config should override YAML
        self.assertEqual(agent.financial_threshold, 30000)
        self.assertEqual(agent.explainability_threshold, 0.5)
        # compliance_threshold should still come from YAML
        self.assertEqual(agent.compliance_threshold, 'medium')
        
    def test_structured_logging_high_risk(self):
        """Test that structured logging is used for high-risk workflows."""
        import logging
        from io import StringIO
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        
        agent = GovernanceAgent()
        agent.logger.addHandler(handler)
        
        message = {
            'type': 'assess_governance',
            'data': {
                'workflow_id': 'test-workflow-123',
                'financial_impact': 50000,
                'compliance_level': 'high',
                'explainability_score': 0.5
            }
        }
        
        response = agent.process(message)
        
        # Check that warning log was generated
        log_output = log_stream.getvalue()
        self.assertIn('High risk workflow', log_output)
        self.assertIn('test-workflow-123', log_output)
        
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
        self.assertIn('Unknown message type', response['error'])


class TestOrchestratorGovernanceIntegration(unittest.TestCase):
    """Test cases for OrchestratorAgent with governance integration."""
    
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
        
    def test_governance_agent_registered(self):
        """Test that governance agent is automatically registered."""
        self.assertIn('governance_agent', self.orchestrator.agent_registry)
        self.assertIsInstance(
            self.orchestrator.agent_registry['governance_agent'],
            GovernanceAgent
        )
        
    def test_governance_routing_rules(self):
        """Test that governance routing rules are configured."""
        self.assertEqual(
            self.orchestrator.routing_rules['assess_governance'],
            'governance_agent'
        )
        self.assertEqual(
            self.orchestrator.routing_rules['check_human_validation'],
            'governance_agent'
        )
        
    def test_route_to_governance_agent(self):
        """Test routing to governance agent."""
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 50000,
                'compliance_level': 'high',
                'explainability_score': 0.6
            }
        }
        
        response = self.orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        self.assertIn('risk_level', response['data'])
        self.assertIn('requires_human_validation', response['data'])
        
    def test_workflow_with_governance_low_risk(self):
        """Test workflow execution with low-risk governance data."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Low Risk Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                },
                'governance_data': {
                    'financial_impact': 5000,
                    'compliance_level': 'low',
                    'explainability_score': 0.9
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertIn('governance', response)
        self.assertIsNotNone(response['governance'])
        self.assertEqual(response['governance']['risk_level'], 'low')
        self.assertFalse(response['governance']['requires_human_validation'])
        self.assertNotIn('status', response)  # Should not set pending status
        
    def test_workflow_with_governance_high_risk(self):
        """Test workflow execution with high-risk governance data."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'High Risk Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                },
                'governance_data': {
                    'financial_impact': 100000,
                    'compliance_level': 'critical',
                    'explainability_score': 0.4
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertIn('governance', response)
        self.assertIsNotNone(response['governance'])
        self.assertEqual(response['governance']['risk_level'], 'high')
        self.assertTrue(response['governance']['requires_human_validation'])
        self.assertEqual(response['status'], 'pending_approval')
        self.assertIn('risk_level', response)
        self.assertEqual(response['risk_level'], 'high')
        
    def test_workflow_without_governance(self):
        """Test backward compatibility - workflow without governance data."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Regular Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                }
            }
        }
        
        response = self.orchestrator.process(message)
        
        self.assertEqual(response['workflow_type'], 'project_initialization')
        # Governance should be None when not provided
        self.assertIsNone(response['governance'])
        # Should not have governance-related fields
        self.assertNotIn('risk_level', response)
        self.assertNotIn('requires_human_validation', response)
        # Should still execute successfully
        self.assertGreater(len(response['steps']), 0)
        
    def test_backward_compatibility_existing_workflow(self):
        """Test that existing workflows continue to work without governance."""
        # This is the same test from test_agents.py
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
            
    def test_custom_governance_config(self):
        """Test orchestrator with custom governance configuration."""
        config = {
            'governance': {
                'financial_threshold': 15000,
                'compliance_threshold': 'high',
                'explainability_threshold': 0.75
            }
        }
        orchestrator = OrchestratorAgent(config=config)
        
        # Register other agents
        orchestrator.register_agent(ProjectPlanAgent())
        orchestrator.register_agent(RiskAssessmentAgent())
        orchestrator.register_agent(StatusReporterAgent())
        
        message = {
            'type': 'assess_governance',
            'data': {
                'financial_impact': 12000,
                'compliance_level': 'medium',
                'explainability_score': 0.8
            }
        }
        
        response = orchestrator.process(message)
        self.assertEqual(response['status'], 'success')
        # With custom thresholds, this should be low or medium risk
        self.assertIn(response['data']['risk_level'], ['low', 'medium'])
        
    def test_governance_error_handling_fallback(self):
        """Test that governance failures fallback to low risk."""
        # Create orchestrator with broken governance agent
        class BrokenGovernanceAgent:
            agent_id = 'governance_agent'
            
            def process(self, message):
                raise Exception("Governance agent failure")
        
        orchestrator = OrchestratorAgent()
        orchestrator.register_agent(ProjectPlanAgent())
        orchestrator.register_agent(RiskAssessmentAgent())
        orchestrator.register_agent(StatusReporterAgent())
        
        # Replace governance agent with broken one
        orchestrator.agent_registry['governance_agent'] = BrokenGovernanceAgent()
        
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Test Project',
                    'goals': ['Goal 1'],
                    'duration_weeks': 5
                },
                'governance_data': {
                    'financial_impact': 100000,
                    'compliance_level': 'critical',
                    'explainability_score': 0.3
                }
            }
        }
        
        response = orchestrator.process(message)
        
        # Should fallback to low risk instead of halting
        self.assertEqual(response['risk_level'], 'low')
        self.assertFalse(response['governance']['requires_human_validation'])
        self.assertGreater(len(response['steps']), 0)
        
    def test_pending_approval_pubsub(self):
        """Test that pending approval workflows are published to message broker."""
        from mira.core.message_broker import get_broker
        
        broker = get_broker()
        published_messages = []
        
        def capture_message(msg):
            published_messages.append(msg)
        
        # Subscribe to pending approval messages
        broker.subscribe('governance.pending_approval', capture_message)
        broker.start()
        
        try:
            orchestrator = OrchestratorAgent()
            orchestrator.register_agent(ProjectPlanAgent())
            orchestrator.register_agent(RiskAssessmentAgent())
            orchestrator.register_agent(StatusReporterAgent())
            
            message = {
                'type': 'workflow',
                'data': {
                    'workflow_type': 'project_initialization',
                    'data': {
                        'name': 'High Risk Project',
                        'goals': ['Goal 1'],
                        'duration_weeks': 10
                    },
                    'governance_data': {
                        'financial_impact': 100000,
                        'compliance_level': 'critical',
                        'explainability_score': 0.4
                    }
                }
            }
            
            response = orchestrator.process(message)
            
            # Wait a moment for async message processing
            import time
            time.sleep(0.5)
            
            # Should have published a pending approval message
            self.assertEqual(response['status'], 'pending_approval')
            self.assertEqual(len(published_messages), 1)
            
            pub_msg = published_messages[0]
            self.assertEqual(pub_msg['data']['type'], 'pending_approval')
            self.assertEqual(pub_msg['data']['workflow_type'], 'project_initialization')
            self.assertIn('governance', pub_msg['data'])
            
        finally:
            broker.stop()
            broker.unsubscribe('governance.pending_approval', capture_message)


if __name__ == '__main__':
    unittest.main()
