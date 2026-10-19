"""Tests for structured logging utilities."""
import unittest
import json
import logging
from io import StringIO
from mira.utils.structured_logging import (
    CorrelationContext,
    StructuredFormatter,
    StructuredLogger,
    get_structured_logger,
    setup_structured_logging,
    with_correlation_context,
    _correlation_id,
    _agent_id,
    _task_id,
    _workflow_id
)


class TestCorrelationContext(unittest.TestCase):
    """Test cases for CorrelationContext."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear context vars
        _correlation_id.set(None)
        _agent_id.set(None)
        _task_id.set(None)
        _workflow_id.set(None)
        
    def test_context_initialization(self):
        """Test context initialization."""
        ctx = CorrelationContext(
            agent_id="test_agent",
            task_id="task_123",
            workflow_id="workflow_456"
        )
        
        self.assertIsNotNone(ctx.correlation_id)
        self.assertEqual(ctx.agent_id, "test_agent")
        self.assertEqual(ctx.task_id, "task_123")
        self.assertEqual(ctx.workflow_id, "workflow_456")
        
    def test_context_manager(self):
        """Test context manager behavior."""
        with CorrelationContext(agent_id="test_agent") as ctx:
            # Inside context, values should be set
            current = CorrelationContext.get_current()
            self.assertEqual(current['agent_id'], "test_agent")
            self.assertIn('correlation_id', current)
            
        # Outside context, values should be cleared
        current = CorrelationContext.get_current()
        self.assertNotIn('agent_id', current)
        
    def test_nested_contexts(self):
        """Test nested context managers."""
        with CorrelationContext(agent_id="agent1", task_id="task1"):
            current = CorrelationContext.get_current()
            self.assertEqual(current['agent_id'], "agent1")
            self.assertEqual(current['task_id'], "task1")
            
            with CorrelationContext(agent_id="agent2", task_id="task2"):
                current = CorrelationContext.get_current()
                self.assertEqual(current['agent_id'], "agent2")
                self.assertEqual(current['task_id'], "task2")
                
            # After inner context, should restore outer context
            current = CorrelationContext.get_current()
            self.assertEqual(current['agent_id'], "agent1")
            self.assertEqual(current['task_id'], "task1")
            
    def test_to_dict(self):
        """Test converting context to dictionary."""
        ctx = CorrelationContext(
            correlation_id="corr_123",
            agent_id="test_agent",
            task_id="task_456",
            metadata={"key": "value"}
        )
        
        ctx_dict = ctx.to_dict()
        
        self.assertEqual(ctx_dict['correlation_id'], "corr_123")
        self.assertEqual(ctx_dict['agent_id'], "test_agent")
        self.assertEqual(ctx_dict['task_id'], "task_456")
        self.assertEqual(ctx_dict['metadata'], {"key": "value"})
        
    def test_get_current_empty(self):
        """Test get_current with no context set."""
        current = CorrelationContext.get_current()
        self.assertEqual(current, {})


class TestStructuredFormatter(unittest.TestCase):
    """Test cases for StructuredFormatter."""
    
    def setUp(self):
        """Set up test fixtures."""
        _correlation_id.set(None)
        _agent_id.set(None)
        
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = StructuredFormatter()
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1,
            "Test message", (), None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['logger'], 'test')
        self.assertEqual(log_data['message'], 'Test message')
        self.assertIn('timestamp', log_data)
        
    def test_format_with_context(self):
        """Test formatting with correlation context."""
        formatter = StructuredFormatter(include_context=True)
        
        with CorrelationContext(agent_id="test_agent", task_id="task_123"):
            logger = logging.getLogger("test")
            record = logger.makeRecord(
                "test", logging.INFO, "test.py", 1,
                "Test message", (), None
            )
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            self.assertIn('context', log_data)
            self.assertEqual(log_data['context']['agent_id'], "test_agent")
            self.assertEqual(log_data['context']['task_id'], "task_123")
            
    def test_format_without_context(self):
        """Test formatting without correlation context."""
        formatter = StructuredFormatter(include_context=False)
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1,
            "Test message", (), None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        self.assertNotIn('context', log_data)


class TestStructuredLogger(unittest.TestCase):
    """Test cases for StructuredLogger."""
    
    def setUp(self):
        """Set up test fixtures."""
        _correlation_id.set(None)
        _agent_id.set(None)
        
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test_module")
        self.assertIsNotNone(logger.logger)
        
    def test_get_structured_logger(self):
        """Test getting a structured logger."""
        logger = get_structured_logger("test_module")
        self.assertIsInstance(logger, StructuredLogger)


class TestLoggingSetup(unittest.TestCase):
    """Test cases for logging setup."""
    
    def test_setup_structured_logging(self):
        """Test setting up structured logging."""
        setup_structured_logging(level='DEBUG', format_json=False)
        
        logger = logging.getLogger('mira')
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertGreater(len(logger.handlers), 0)


class TestWithCorrelationContextDecorator(unittest.TestCase):
    """Test cases for with_correlation_context decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        _correlation_id.set(None)
        _agent_id.set(None)
        _task_id.set(None)
        
    def test_decorator_with_agent_id(self):
        """Test decorator with explicit agent_id."""
        @with_correlation_context(agent_id="decorated_agent")
        def test_function():
            current = CorrelationContext.get_current()
            return current.get('agent_id')
            
        result = test_function()
        self.assertEqual(result, "decorated_agent")
        
        # After function, context should be cleared
        current = CorrelationContext.get_current()
        self.assertNotIn('agent_id', current)
        
    def test_decorator_with_task_id(self):
        """Test decorator with task_id."""
        @with_correlation_context(task_id="task_789")
        def test_function():
            current = CorrelationContext.get_current()
            return current.get('task_id')
            
        result = test_function()
        self.assertEqual(result, "task_789")
        
    def test_decorator_extracts_agent_id_from_self(self):
        """Test decorator extracts agent_id from self."""
        class TestAgent:
            def __init__(self):
                self.agent_id = "self_agent"
                
            @with_correlation_context()
            def process(self):
                current = CorrelationContext.get_current()
                return current.get('agent_id')
                
        agent = TestAgent()
        result = agent.process()
        self.assertEqual(result, "self_agent")


if __name__ == '__main__':
    unittest.main()
