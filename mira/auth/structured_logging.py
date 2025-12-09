"""Structured logging configuration for Mira API key management."""
import logging
import sys
from typing import Any, Dict, Optional
import time
import uuid

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

class StructuredLogger:
    """Structured logging with correlation IDs and context."""
    
    def __init__(
        self,
        service_name: str = "mira-api-key-manager",
        log_level: str = "INFO",
        json_format: bool = True
    ):
        """
        Initialize structured logger.
        
        Args:
            service_name: Name of the service for log identification
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_format: Whether to output logs in JSON format
        """
        self.service_name = service_name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.json_format = json_format and STRUCTLOG_AVAILABLE
        
        if STRUCTLOG_AVAILABLE and json_format:
            self._configure_structlog()
        else:
            self._configure_standard_logging()
    
    def _configure_structlog(self):
        """Configure structlog for structured JSON logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _configure_standard_logging(self):
        """Configure standard Python logging with structured format."""
        logging.basicConfig(
            level=self.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if STRUCTLOG_AVAILABLE and self.json_format:
            logger = structlog.get_logger(name)
            return logger.bind(service=self.service_name)
        else:
            logger = logging.getLogger(name)
            logger.setLevel(self.log_level)
            return logger


class RequestLogger:
    """Request-specific logger with correlation ID tracking."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize request logger.
        
        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.correlation_id: Optional[str] = None
        self.request_start: Optional[float] = None
    
    def start_request(self, correlation_id: Optional[str] = None) -> str:
        """
        Start tracking a new request.
        
        Args:
            correlation_id: Optional correlation ID (generated if not provided)
            
        Returns:
            Correlation ID for this request
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.request_start = time.time()
        return self.correlation_id
    
    def log(
        self,
        level: str,
        message: str,
        **context: Any
    ):
        """
        Log a message with correlation ID and context.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **context: Additional context to include in log
        """
        log_data = {
            'message': message,
            'correlation_id': self.correlation_id,
            **context
        }
        
        if self.request_start:
            log_data['request_duration_ms'] = round(
                (time.time() - self.request_start) * 1000, 2
            )
        
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        
        if STRUCTLOG_AVAILABLE and hasattr(self.logger, 'bind'):
            # Structlog logger
            log_method(message, **log_data)
        else:
            # Standard logger
            context_str = ', '.join(f"{k}={v}" for k, v in log_data.items() if k != 'message')
            log_method(f"{message} [{context_str}]")
    
    def debug(self, message: str, **context: Any):
        """Log debug message."""
        self.log('debug', message, **context)
    
    def info(self, message: str, **context: Any):
        """Log info message."""
        self.log('info', message, **context)
    
    def warning(self, message: str, **context: Any):
        """Log warning message."""
        self.log('warning', message, **context)
    
    def error(self, message: str, **context: Any):
        """Log error message."""
        self.log('error', message, **context)
    
    def critical(self, message: str, **context: Any):
        """Log critical message."""
        self.log('critical', message, **context)
    
    def finish_request(self, status_code: int, **context: Any):
        """
        Log request completion.
        
        Args:
            status_code: HTTP status code
            **context: Additional context
        """
        if self.request_start:
            duration_ms = round((time.time() - self.request_start) * 1000, 2)
            self.info(
                "Request completed",
                status_code=status_code,
                duration_ms=duration_ms,
                **context
            )


class AuditLogger:
    """Specialized logger for security audit events."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize audit logger.
        
        Args:
            logger: Base logger instance
        """
        self.logger = logger
    
    def log_key_generation(
        self,
        key_id: str,
        role: str,
        created_by: Optional[str] = None,
        **context: Any
    ):
        """Log API key generation event."""
        self._log_audit_event(
            event_type="key_generated",
            key_id=key_id,
            role=role,
            created_by=created_by,
            **context
        )
    
    def log_key_validation(
        self,
        key_id: str,
        success: bool,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        **context: Any
    ):
        """Log API key validation event."""
        self._log_audit_event(
            event_type="key_validated",
            key_id=key_id,
            success=success,
            reason=reason,
            ip_address=ip_address,
            **context
        )
    
    def log_key_revocation(
        self,
        key_id: str,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None,
        **context: Any
    ):
        """Log API key revocation event."""
        self._log_audit_event(
            event_type="key_revoked",
            key_id=key_id,
            revoked_by=revoked_by,
            reason=reason,
            **context
        )
    
    def log_key_rotation(
        self,
        old_key_id: str,
        new_key_id: str,
        rotated_by: Optional[str] = None,
        **context: Any
    ):
        """Log API key rotation event."""
        self._log_audit_event(
            event_type="key_rotated",
            old_key_id=old_key_id,
            new_key_id=new_key_id,
            rotated_by=rotated_by,
            **context
        )
    
    def log_permission_denied(
        self,
        key_id: str,
        required_permission: str,
        ip_address: Optional[str] = None,
        **context: Any
    ):
        """Log permission denied event."""
        self._log_audit_event(
            event_type="permission_denied",
            key_id=key_id,
            required_permission=required_permission,
            ip_address=ip_address,
            severity="warning",
            **context
        )
    
    def _log_audit_event(
        self,
        event_type: str,
        **context: Any
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            **context: Event context
        """
        audit_data = {
            'audit_event': event_type,
            'timestamp': time.time(),
            **context
        }
        
        if STRUCTLOG_AVAILABLE and hasattr(self.logger, 'bind'):
            self.logger.info(f"Audit: {event_type}", **audit_data)
        else:
            context_str = ', '.join(f"{k}={v}" for k, v in audit_data.items())
            self.logger.info(f"Audit: {event_type} [{context_str}]")


# Global logger instances
_structured_logger: Optional[StructuredLogger] = None


def setup_logging(
    service_name: str = "mira-api-key-manager",
    log_level: str = "INFO",
    json_format: bool = True
) -> StructuredLogger:
    """
    Setup structured logging for the application.
    
    Args:
        service_name: Name of the service
        log_level: Logging level
        json_format: Whether to use JSON format
        
    Returns:
        StructuredLogger instance
    """
    global _structured_logger
    _structured_logger = StructuredLogger(
        service_name=service_name,
        log_level=log_level,
        json_format=json_format
    )
    return _structured_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger.get_logger(name)
