"""Tests for structured logging with correlation IDs."""
import unittest
import json
import logging
from io import StringIO
from mira.utils.structured_logging import (
    setup_structured_logging,
    get_structured_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    JSONFormatter,
    CorrelationIDFilter
)


class TestStructuredLogging(unittest.TestCase):
    """Test cases for structured logging."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing handlers
        logger = logging.getLogger('mira')
        logger.handlers.clear()
        clear_correlation_id()
    
    def tearDown(self):
        """Clean up after tests."""
        clear_correlation_id()
    
    def test_correlation_id_management(self):
        """Test correlation ID setting and getting."""
        # Initially should be None
        self.assertIsNone(get_correlation_id())
        
        # Set a custom correlation ID
        corr_id = set_correlation_id('test-123')
        self.assertEqual(corr_id, 'test-123')
        self.assertEqual(get_correlation_id(), 'test-123')
        
        # Clear correlation ID
        clear_correlation_id()
        self.assertIsNone(get_correlation_id())
        
        # Auto-generate correlation ID
        auto_id = set_correlation_id()
        self.assertIsNotNone(auto_id)
        self.assertEqual(get_correlation_id(), auto_id)
    
    def test_json_formatter(self):
        """Test JSON formatting of log records."""
        formatter = JSONFormatter()
        
        # Create a test log record
        logger = logging.getLogger('test')
        record = logger.makeRecord(
            'test', logging.INFO, 'test.py', 10,
            'Test message', (), None
        )
        record.correlation_id = 'test-123'
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify fields
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['message'], 'Test message')
        self.assertEqual(log_data['correlation_id'], 'test-123')
        self.assertIn('timestamp', log_data)
        self.assertIn('logger', log_data)
    
    def test_correlation_id_filter(self):
        """Test correlation ID filter."""
        # Set a correlation ID
        set_correlation_id('filter-test')
        
        # Create filter
        filter_obj = CorrelationIDFilter()
        
        # Create a log record
        logger = logging.getLogger('test')
        record = logger.makeRecord(
            'test', logging.INFO, 'test.py', 10,
            'Test message', (), None
        )
        
        # Apply filter
        filter_obj.filter(record)
        
        # Check that correlation_id was added
        self.assertEqual(record.correlation_id, 'filter-test')
    
    def test_setup_structured_logging(self):
        """Test structured logging setup."""
        # Setup with JSON format
        logger = setup_structured_logging(level='DEBUG', json_format=True)
        
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertTrue(len(logger.handlers) > 0)
        
        # Verify handler has JSON formatter
        handler = logger.handlers[0]
        self.assertIsInstance(handler.formatter, JSONFormatter)
    
    def test_structured_logger_with_correlation(self):
        """Test that structured logger includes correlation ID."""
        # Setup logging with string stream to capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(CorrelationIDFilter())
        
        logger = logging.getLogger('mira.test')
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Set correlation ID
        set_correlation_id('test-corr-id')
        
        # Log a message
        logger.info('Test message')
        
        # Get output and parse JSON
        output = stream.getvalue()
        log_data = json.loads(output)
        
        # Verify correlation ID is present
        self.assertEqual(log_data['correlation_id'], 'test-corr-id')
        self.assertEqual(log_data['message'], 'Test message')
    
    def test_get_structured_logger(self):
        """Test getting a structured logger."""
        logger = get_structured_logger('mymodule')
        
        self.assertEqual(logger.name, 'mira.mymodule')
        self.assertIsInstance(logger, logging.Logger)


if __name__ == '__main__':
    unittest.main()
