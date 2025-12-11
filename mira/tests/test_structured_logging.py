"""Tests for structured logging functionality."""
import unittest
import json
import logging
import sys
from io import StringIO
from mira.utils.structured_logging import (
    setup_structured_logging,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    CorrelationContext,
    JSONFormatter,
    CorrelationIdFilter
)


class TestStructuredLogging(unittest.TestCase):
    """Test cases for structured logging."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing correlation ID
        clear_correlation_id()
        # Clear existing handlers
        logging.getLogger('mira').handlers.clear()
        
    def tearDown(self):
        """Clean up after tests."""
        clear_correlation_id()
        logging.getLogger('mira').handlers.clear()
        
    def test_correlation_id_set_and_get(self):
        """Test setting and getting correlation ID."""
        correlation_id = set_correlation_id("test-123")
        self.assertEqual(correlation_id, "test-123")
        self.assertEqual(get_correlation_id(), "test-123")
        
    def test_correlation_id_auto_generate(self):
        """Test auto-generation of correlation ID."""
        correlation_id = set_correlation_id()
        self.assertIsNotNone(correlation_id)
        self.assertEqual(get_correlation_id(), correlation_id)
        # Should be a valid UUID format
        self.assertEqual(len(correlation_id), 36)
        
    def test_correlation_id_clear(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        clear_correlation_id()
        self.assertIsNone(get_correlation_id())
        
    def test_correlation_context_manager(self):
        """Test correlation context manager."""
        # Set initial correlation ID
        set_correlation_id("initial-id")
        
        # Use context manager with new ID
        with CorrelationContext("context-id") as ctx_id:
            self.assertEqual(ctx_id, "context-id")
            self.assertEqual(get_correlation_id(), "context-id")
            
        # Should restore previous ID
        self.assertEqual(get_correlation_id(), "initial-id")
        
    def test_correlation_context_manager_auto_generate(self):
        """Test correlation context manager with auto-generated ID."""
        with CorrelationContext() as ctx_id:
            self.assertIsNotNone(ctx_id)
            self.assertEqual(get_correlation_id(), ctx_id)
            
        # Should clear ID after context
        self.assertIsNone(get_correlation_id())
        
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='mira.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.correlation_id = 'test-123'
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['logger'], 'mira.test')
        self.assertEqual(log_data['message'], 'Test message')
        self.assertEqual(log_data['correlation_id'], 'test-123')
        self.assertIn('timestamp', log_data)
        
    def test_correlation_id_filter(self):
        """Test correlation ID filter."""
        set_correlation_id("filter-test")
        
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name='mira.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        self.assertEqual(record.correlation_id, "filter-test")
        
    def test_correlation_id_filter_no_id(self):
        """Test correlation ID filter when no ID is set."""
        clear_correlation_id()
        
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name='mira.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        self.assertEqual(record.correlation_id, "N/A")
        
    def test_setup_structured_logging_json(self):
        """Test structured logging setup with JSON format."""
        # Capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = setup_structured_logging(level='INFO', use_json=True, include_console=False)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        from mira.utils.structured_logging import CorrelationIdFilter, JSONFormatter
        handler.addFilter(CorrelationIdFilter())
        handler.setFormatter(JSONFormatter())
        
        set_correlation_id("test-json")
        test_logger = get_logger('test')
        test_logger.info("Test JSON message")
        
        output = stream.getvalue()
        log_data = json.loads(output.strip())
        
        self.assertEqual(log_data['message'], 'Test JSON message')
        self.assertEqual(log_data['correlation_id'], 'test-json')
        
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger('test_module')
        self.assertEqual(logger.name, 'mira.test_module')
        
    def test_nested_correlation_contexts(self):
        """Test nested correlation contexts."""
        with CorrelationContext("outer") as outer_id:
            self.assertEqual(get_correlation_id(), "outer")
            
            with CorrelationContext("inner") as inner_id:
                self.assertEqual(get_correlation_id(), "inner")
                
            # Should restore outer context
            self.assertEqual(get_correlation_id(), "outer")
            
        # Should clear after both contexts
        self.assertIsNone(get_correlation_id())


if __name__ == '__main__':
    unittest.main()
