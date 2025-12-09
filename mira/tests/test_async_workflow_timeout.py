"""Tests for async workflow timeout protection."""
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent
from mira.agents.orchestrator_agent import OrchestratorAgent


class TestAsyncWorkflowTimeout(unittest.TestCase):
    """Test cases for async workflow timeout protection."""
    
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
    
    def test_async_workflow_completes_before_timeout(self):
        """Test that workflow completes successfully before timeout."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Test Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                }
            }
        }
        
        # Run async workflow with generous timeout
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=60.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Verify successful completion
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertGreater(len(response['steps']), 0)
        self.assertNotIn('status', response)  # No timeout status
        
        # Check all steps completed successfully
        for step in response['steps']:
            self.assertEqual(step['status'], 'success')
    
    def test_async_workflow_timeout_occurs(self):
        """Test that timeout is properly handled with partial progress."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Timeout Test Project',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                }
            }
        }
        
        # Mock route_message to simulate slow execution
        original_route = self.orchestrator._route_message
        call_count = [0]
        
        def slow_route(msg):
            call_count[0] += 1
            # First call succeeds quickly, subsequent calls are slow
            if call_count[0] > 1:
                import time
                time.sleep(3)  # Simulate slow operation
            return original_route(msg)
        
        with patch.object(self.orchestrator, '_route_message', side_effect=slow_route):
            # Run async workflow with very short timeout
            async def run_test():
                response = await self.orchestrator.process_async(message, timeout=1.0)
                return response
            
            response = asyncio.run(run_test())
        
        # Verify timeout response
        self.assertEqual(response['workflow_type'], 'project_initialization')
        self.assertEqual(response['status'], 'timeout')
        self.assertIn('error', response)
        self.assertIn('timed out', response['error'].lower())
        
        # Verify partial progress is returned
        self.assertIn('partial_progress', response)
        partial = response['partial_progress']
        self.assertIn('completed_steps', partial)
        self.assertIn('total_steps_completed', partial)
        self.assertIn('timeout_seconds', partial)
        self.assertEqual(partial['timeout_seconds'], 1.0)
        
        # At least one step should have completed before timeout
        self.assertGreaterEqual(len(response['steps']), 1)
    
    def test_async_workflow_very_short_timeout(self):
        """Test workflow with very short timeout (edge case)."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Quick Timeout Test',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        # Run with very short timeout (0.001 seconds)
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=0.001)
            return response
        
        response = asyncio.run(run_test())
        
        # Should timeout immediately or complete very quickly
        # Due to the very short timeout, either outcome is acceptable
        if 'status' in response:
            # If status is present, it should indicate timeout
            self.assertEqual(response['status'], 'timeout')
            self.assertIn('partial_progress', response)
        else:
            # If no status, workflow may have completed before timeout
            # Verify it's a valid workflow response
            self.assertIn('workflow_type', response)
    
    def test_async_workflow_default_timeout(self):
        """Test workflow uses default timeout of 30 seconds."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Default Timeout Test',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        # Run without specifying timeout (should use default 30s)
        async def run_test():
            response = await self.orchestrator.process_async(message)
            return response
        
        response = asyncio.run(run_test())
        
        # Should complete successfully with default timeout
        self.assertNotEqual(response.get('status'), 'timeout')
    
    def test_async_workflow_unknown_workflow_type(self):
        """Test async workflow with unknown workflow type."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'unknown_workflow',
                'data': {'name': 'Test'}
            }
        }
        
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=10.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Should return empty steps for unknown workflow
        self.assertEqual(response['workflow_type'], 'unknown_workflow')
        self.assertEqual(len(response['steps']), 0)
    
    def test_async_non_workflow_message(self):
        """Test async processing of non-workflow messages."""
        message = {
            'type': 'generate_plan',
            'data': {
                'name': 'Async Plan Test',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
        
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=10.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Should route to plan agent successfully
        self.assertEqual(response['status'], 'success')
        self.assertIn('data', response)
    
    def test_async_workflow_invalid_message(self):
        """Test async processing with invalid message format."""
        message = {'invalid': 'message'}
        
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=10.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Should return error for invalid message
        self.assertEqual(response['status'], 'error')
        self.assertIn('Invalid message format', response['error'])
    
    def test_async_workflow_exception_handling(self):
        """Test exception handling in async workflow."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Exception Test',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        # Mock to raise an exception
        with patch.object(self.orchestrator, '_run_workflow_steps_async', 
                         side_effect=Exception('Test exception')):
            async def run_test():
                response = await self.orchestrator.process_async(message, timeout=10.0)
                return response
            
            response = asyncio.run(run_test())
        
        # Should handle exception gracefully
        self.assertEqual(response['status'], 'error')
        self.assertIn('Test exception', response['error'])
    
    def test_async_workflow_large_timeout(self):
        """Test workflow with very large timeout."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Large Timeout Test',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        # Run with very large timeout (1000 seconds)
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=1000.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Should complete successfully
        self.assertNotEqual(response.get('status'), 'timeout')
        self.assertEqual(response['workflow_type'], 'project_initialization')
    
    def test_async_workflow_partial_progress_steps(self):
        """Test that partial progress includes correct step information."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Partial Progress Test',
                    'goals': ['Goal 1', 'Goal 2'],
                    'duration_weeks': 10
                }
            }
        }
        
        # Mock to make second step very slow
        original_route = self.orchestrator._route_message
        call_count = [0]
        
        def selective_slow_route(msg):
            call_count[0] += 1
            # Second call (risk assessment) is slow
            if call_count[0] == 2:
                import time
                time.sleep(5)
            return original_route(msg)
        
        with patch.object(self.orchestrator, '_route_message', side_effect=selective_slow_route):
            async def run_test():
                response = await self.orchestrator.process_async(message, timeout=2.0)
                return response
            
            response = asyncio.run(run_test())
        
        # Verify partial progress details
        if response.get('status') == 'timeout':
            self.assertIn('partial_progress', response)
            completed_steps = response['partial_progress']['completed_steps']
            # First step (generate_plan) should be completed
            self.assertIn('generate_plan', completed_steps)
    
    def test_async_workflow_concurrent_execution(self):
        """Test multiple concurrent async workflow executions."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {
                    'name': 'Concurrent Test',
                    'goals': ['Goal 1'],
                    'duration_weeks': 8
                }
            }
        }
        
        async def run_multiple():
            # Run 5 concurrent workflows
            tasks = [
                self.orchestrator.process_async(message, timeout=30.0)
                for _ in range(5)
            ]
            responses = await asyncio.gather(*tasks)
            return responses
        
        responses = asyncio.run(run_multiple())
        
        # All should complete successfully
        self.assertEqual(len(responses), 5)
        for response in responses:
            self.assertNotEqual(response.get('status'), 'timeout')
    
    def test_async_workflow_empty_workflow_data(self):
        """Test async workflow with empty workflow data."""
        message = {
            'type': 'workflow',
            'data': {
                'workflow_type': 'project_initialization',
                'data': {}
            }
        }
        
        async def run_test():
            response = await self.orchestrator.process_async(message, timeout=10.0)
            return response
        
        response = asyncio.run(run_test())
        
        # Should handle gracefully
        self.assertIn('workflow_type', response)
        self.assertEqual(response['workflow_type'], 'project_initialization')


class TestAsyncWorkflowStepExecution(unittest.TestCase):
    """Test cases for async workflow step execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorAgent()
        self.orchestrator.register_agent(ProjectPlanAgent())
        self.orchestrator.register_agent(RiskAssessmentAgent())
        self.orchestrator.register_agent(StatusReporterAgent())
    
    def test_run_workflow_steps_async_project_initialization(self):
        """Test async workflow steps for project initialization."""
        workflow_type = 'project_initialization'
        workflow_data = {
            'name': 'Step Test Project',
            'goals': ['Goal 1', 'Goal 2'],
            'duration_weeks': 8
        }
        results = {
            'workflow_type': workflow_type,
            'steps': []
        }
        
        async def run_test():
            result = await self.orchestrator._run_workflow_steps_async(
                workflow_type, workflow_data, results
            )
            return result
        
        result = asyncio.run(run_test())
        
        # Verify all steps executed
        self.assertEqual(len(result['steps']), 3)
        step_names = [step['step'] for step in result['steps']]
        self.assertIn('generate_plan', step_names)
        self.assertIn('assess_risks', step_names)
        self.assertIn('generate_report', step_names)
    
    def test_run_workflow_steps_async_unknown_type(self):
        """Test async workflow steps with unknown workflow type."""
        workflow_type = 'unknown_type'
        workflow_data = {'name': 'Test'}
        results = {
            'workflow_type': workflow_type,
            'steps': []
        }
        
        async def run_test():
            result = await self.orchestrator._run_workflow_steps_async(
                workflow_type, workflow_data, results
            )
            return result
        
        result = asyncio.run(run_test())
        
        # Should return empty steps
        self.assertEqual(len(result['steps']), 0)
    
    def test_execute_workflow_async_direct_call(self):
        """Test direct call to _execute_workflow_async."""
        data = {
            'workflow_type': 'project_initialization',
            'data': {
                'name': 'Direct Call Test',
                'goals': ['Goal 1'],
                'duration_weeks': 8
            }
        }
        
        async def run_test():
            result = await self.orchestrator._execute_workflow_async(data, timeout=30.0)
            return result
        
        result = asyncio.run(run_test())
        
        # Should complete successfully
        self.assertEqual(result['workflow_type'], 'project_initialization')
        self.assertGreater(len(result['steps']), 0)


if __name__ == '__main__':
    unittest.main()
