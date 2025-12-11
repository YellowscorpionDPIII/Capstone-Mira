"""Structured logging with correlation IDs for distributed tracing."""
import logging
import json
import sys
import threading
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime
import uuid

# Context variable for storing correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record."""
        record.correlation_id = get_correlation_id() or 'N/A'
        return True


class JSONFormatter(logging.Formatter):
    """Formatter that outputs log records as JSON."""
    
    def __init__(self, include_extra_fields: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_extra_fields: Whether to include extra fields in log output
        """
        super().__init__()
        self.include_extra_fields = include_extra_fields
        
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'N/A'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if enabled
        if self.include_extra_fields:
            # Standard LogRecord attributes to exclude
            standard_attrs = {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                'correlation_id', 'taskName', 'getMessage', 'asctime'
            }
            
            # Add any extra attributes added to the record
            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith('_'):
                    try:
                        # Try to serialize the value, skip if not serializable
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current context.
    
    Args:
        correlation_id: Correlation ID to set, or None to generate a new one
        
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_id.get()


def clear_correlation_id():
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)


class CorrelationContext:
    """Context manager for setting correlation ID for a block of code."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize correlation context.
        
        Args:
            correlation_id: Correlation ID to use, or None to generate a new one
        """
        self.correlation_id = correlation_id
        self.previous_id = None
        
    def __enter__(self) -> str:
        """Enter the context and set correlation ID."""
        self.previous_id = get_correlation_id()
        return set_correlation_id(self.correlation_id)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore previous correlation ID."""
        if self.previous_id is not None:
            _correlation_id.set(self.previous_id)
        else:
            clear_correlation_id()


def setup_structured_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    use_json: bool = True,
    include_console: bool = True
) -> logging.Logger:
    """
    Set up structured logging with correlation IDs.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        use_json: Whether to use JSON formatting
        include_console: Whether to include console output
        
    Returns:
        Configured root logger
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger('mira')
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Add console handler if requested
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)
    
    root_logger.info(f"Structured logging initialized at {level} level", 
                     extra={'json_enabled': use_json})
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with structured logging support.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"mira.{name}")
