"""Structured logging with correlation IDs for Mira platform."""
import logging
import json
import uuid
import threading
from typing import Optional, Any, Dict
from contextvars import ContextVar
from datetime import datetime, timezone

# Context variable to store correlation ID per request/thread
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""
    
    def filter(self, record):
        """Add correlation_id to the log record."""
        record.correlation_id = get_correlation_id()
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_extra: Whether to include extra fields in JSON output
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', None),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if requested
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                              'levelname', 'levelno', 'lineno', 'module', 'msecs',
                              'message', 'pathname', 'process', 'processName',
                              'relativeCreated', 'thread', 'threadName', 'exc_info',
                              'exc_text', 'stack_info', 'correlation_id']:
                    try:
                        # Only include JSON-serializable values
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for the current context.
    
    Args:
        correlation_id: Optional correlation ID. If not provided, generates a new one.
        
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_context.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get the correlation ID for the current context.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_context.get()


def clear_correlation_id():
    """Clear the correlation ID for the current context."""
    correlation_id_context.set(None)


def setup_structured_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    json_format: bool = True,
    include_console: bool = True
) -> logging.Logger:
    """
    Set up structured logging with correlation IDs.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        json_format: Whether to use JSON formatting (default: True)
        include_console: Whether to include console handler (default: True)
        
    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get or create root logger for mira
    root_logger = logging.getLogger('mira')
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create correlation ID filter
    correlation_filter = CorrelationIDFilter()
    
    # Create appropriate formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Add console handler if requested
    if include_console:
        console_handler = logging.StreamHandler()
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
    
    root_logger.info("Structured logging initialized", extra={'log_level': level})
    return root_logger


def get_structured_logger(name: str) -> logging.Logger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'mira.')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"mira.{name}")
