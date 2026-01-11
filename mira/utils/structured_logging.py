"""Structured logging utilities for Mira platform.

Provides enhanced logging with correlation context, agent metadata, and
structured output for production observability.
"""
import logging
import json
import uuid
from typing import Optional, Dict, Any, List
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps


# Context variables for correlation tracking
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_agent_id: ContextVar[Optional[str]] = ContextVar('agent_id', default=None)
_task_id: ContextVar[Optional[str]] = ContextVar('task_id', default=None)
_workflow_id: ContextVar[Optional[str]] = ContextVar('workflow_id', default=None)


class CorrelationContext:
    """
    Context manager for correlation tracking in multi-agent workflows.
    
    Provides enriched traceability by maintaining correlation ID, agent metadata,
    task information, and workflow context across async operations.
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize correlation context.
        
        Args:
            correlation_id: Unique correlation ID for request tracking
            agent_id: ID of the agent processing the request
            task_id: ID of the current task
            workflow_id: ID of the parent workflow
            metadata: Additional context metadata
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.task_id = task_id
        self.workflow_id = workflow_id
        self.metadata = metadata or {}
        
        # Store previous values for restoration
        self._prev_correlation_id = None
        self._prev_agent_id = None
        self._prev_task_id = None
        self._prev_workflow_id = None
        
    def __enter__(self):
        """Enter context and set correlation values."""
        self._prev_correlation_id = _correlation_id.get()
        self._prev_agent_id = _agent_id.get()
        self._prev_task_id = _task_id.get()
        self._prev_workflow_id = _workflow_id.get()
        
        _correlation_id.set(self.correlation_id)
        _agent_id.set(self.agent_id)
        _task_id.set(self.task_id)
        _workflow_id.set(self.workflow_id)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous values."""
        _correlation_id.set(self._prev_correlation_id)
        _agent_id.set(self._prev_agent_id)
        _task_id.set(self._prev_task_id)
        _workflow_id.set(self._prev_workflow_id)
        
        return False
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for logging.
        
        Returns:
            Dictionary with correlation context
        """
        context = {
            'correlation_id': self.correlation_id,
        }
        
        if self.agent_id:
            context['agent_id'] = self.agent_id
        if self.task_id:
            context['task_id'] = self.task_id
        if self.workflow_id:
            context['workflow_id'] = self.workflow_id
        if self.metadata:
            context['metadata'] = self.metadata
            
        return context
        
    @staticmethod
    def get_current() -> Dict[str, Any]:
        """
        Get current correlation context from context vars.
        
        Returns:
            Dictionary with current context values
        """
        context = {}
        
        correlation_id = _correlation_id.get()
        if correlation_id:
            context['correlation_id'] = correlation_id
            
        agent_id = _agent_id.get()
        if agent_id:
            context['agent_id'] = agent_id
            
        task_id = _task_id.get()
        if task_id:
            context['task_id'] = task_id
            
        workflow_id = _workflow_id.get()
        if workflow_id:
            context['workflow_id'] = workflow_id
            
        return context


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for log records.
    
    Includes correlation context and agent metadata in every log entry.
    """
    
    def __init__(self, include_context: bool = True):
        """
        Initialize formatter.
        
        Args:
            include_context: Whether to include correlation context
        """
        super().__init__()
        self.include_context = include_context
        
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log entry
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add correlation context
        if self.include_context:
            context = CorrelationContext.get_current()
            if context:
                log_data['context'] = context
                
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
            
        return json.dumps(log_data)


class StructuredLogger:
    """
    Enhanced logger with structured logging capabilities.
    
    Provides convenient methods for logging with additional context.
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        
    def _log_with_context(self, level: int, message: str, **kwargs):
        """
        Log message with context.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional fields to include
        """
        # Create a log record with extra fields
        extra_fields = kwargs.copy()
        
        # Get current context
        context = CorrelationContext.get_current()
        if context:
            extra_fields['context'] = context
            
        self.logger.log(level, message, extra={'extra_fields': extra_fields})
        
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)


def setup_structured_logging(
    level: str = 'INFO',
    format_json: bool = False,
    include_context: bool = True
):
    """
    Set up structured logging for the Mira platform.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_json: Whether to use JSON formatting
        include_context: Whether to include correlation context
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger('mira')
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    
    # Set formatter
    if format_json:
        formatter = StructuredFormatter(include_context=include_context)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    root_logger.info(f"Structured logging initialized at {level} level")


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(f"mira.{name}")


def with_correlation_context(
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    workflow_id: Optional[str] = None
):
    """
    Decorator to wrap function with correlation context.
    
    Args:
        agent_id: Agent ID to set in context
        task_id: Task ID to set in context
        workflow_id: Workflow ID to set in context
        
    Returns:
        Decorated function
        
    Note:
        If agent_id is not provided, the decorator will attempt to extract it
        from the first argument (self.agent_id) if the function is a method
        of an object with an 'agent_id' attribute.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract agent_id from self if it's a method
            actual_agent_id = agent_id
            if not actual_agent_id and args and hasattr(args[0], 'agent_id'):
                actual_agent_id = args[0].agent_id
                
            with CorrelationContext(
                agent_id=actual_agent_id,
                task_id=task_id,
                workflow_id=workflow_id
            ):
                return func(*args, **kwargs)
        return wrapper
    return decorator
