"""Structured logging with correlation IDs for distributed tracing."""
import logging
import json
import sys
import threading
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime
import uuid

# Context variables for storing correlation ID and context metadata
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_agent_id: ContextVar[Optional[str]] = ContextVar('agent_id', default=None)
_task_id: ContextVar[Optional[str]] = ContextVar('task_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation ID and context metadata to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID, agent_id, and task_id to the log record."""
        record.correlation_id = get_correlation_id() or 'N/A'
        record.agent_id = get_agent_id() or 'N/A'
        record.task_id = get_task_id() or 'N/A'
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
            'agent_id': getattr(record, 'agent_id', 'N/A'),
            'task_id': getattr(record, 'task_id', 'N/A'),
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
                'correlation_id', 'agent_id', 'task_id', 'taskName', 'getMessage', 'asctime'
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


def set_agent_id(agent_id: Optional[str]) -> Optional[str]:
    """
    Set the agent ID for the current context.
    
    Args:
        agent_id: Agent ID to set
        
    Returns:
        The agent ID that was set
    """
    _agent_id.set(agent_id)
    return agent_id


def get_agent_id() -> Optional[str]:
    """
    Get the current agent ID.
    
    Returns:
        Current agent ID or None if not set
    """
    return _agent_id.get()


def clear_agent_id():
    """Clear the agent ID for the current context."""
    _agent_id.set(None)


def set_task_id(task_id: Optional[str]) -> Optional[str]:
    """
    Set the task ID for the current context.
    
    Args:
        task_id: Task ID to set
        
    Returns:
        The task ID that was set
    """
    _task_id.set(task_id)
    return task_id


def get_task_id() -> Optional[str]:
    """
    Get the current task ID.
    
    Returns:
        Current task ID or None if not set
    """
    return _task_id.get()


def clear_task_id():
    """Clear the task ID for the current context."""
    _task_id.set(None)


class CorrelationContext:
    """Context manager for setting correlation ID and metadata for multi-agent tracing."""
    
    def __init__(self, correlation_id: Optional[str] = None,
                 agent_id: Optional[str] = None,
                 task_id: Optional[str] = None):
        """
        Initialize correlation context with multi-agent tracing support.
        
        Args:
            correlation_id: Correlation ID to use, or None to generate a new one
            agent_id: Optional agent ID for multi-agent tracing
            task_id: Optional task ID for multi-agent tracing
        """
        self.correlation_id = correlation_id
        self.agent_id = agent_id
        self.task_id = task_id
        self.previous_id = None
        self.previous_agent_id = None
        self.previous_task_id = None
        
    def __enter__(self) -> str:
        """Enter the context and set correlation ID and metadata."""
        self.previous_id = get_correlation_id()
        self.previous_agent_id = get_agent_id()
        self.previous_task_id = get_task_id()
        
        correlation_id = set_correlation_id(self.correlation_id)
        if self.agent_id is not None:
            set_agent_id(self.agent_id)
        if self.task_id is not None:
            set_task_id(self.task_id)
            
        return correlation_id
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore previous correlation ID and metadata."""
        if self.previous_id is not None:
            _correlation_id.set(self.previous_id)
        else:
            clear_correlation_id()
            
        if self.previous_agent_id is not None:
            _agent_id.set(self.previous_agent_id)
        else:
            clear_agent_id()
            
        if self.previous_task_id is not None:
            _task_id.set(self.previous_task_id)
        else:
            clear_task_id()


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
