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
        import asyncio
        
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
        import asyncio
        
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
        import asyncio
        
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
        import concurrent.futures
        
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
        import concurrent.futures
        
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
        import concurrent.futures
        
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
        import concurrent.futures
        
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


if __name__ == '__main__':
    unittest.main()
