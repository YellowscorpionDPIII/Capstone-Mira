"""Logging utilities for Mira platform."""
import logging
import sys
from typing import Optional

# Import structured logging for backward compatibility
from mira.utils.structured_logging import (
    setup_structured_logging,
    get_logger as get_structured_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    CorrelationContext
)


def setup_logging(level: str = 'INFO', log_file: Optional[str] = None, 
                  use_json: bool = False):
    """
    Set up logging for the Mira platform.
    
    This is a wrapper that supports both legacy and structured logging.
    For structured logging with correlation IDs, set use_json=True.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        use_json: Whether to use JSON-formatted structured logging (default: False for backward compatibility)
    """
    if use_json:
        # Use new structured logging
        return setup_structured_logging(level=level, log_file=log_file, use_json=True)
    else:
        # Legacy logging setup for backward compatibility
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Configure root logger
        root_logger = logging.getLogger('mira')
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        root_logger.info(f"Logging initialized at {level} level")
        return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"mira.{name}")


# Export structured logging utilities for convenience
__all__ = [
    'setup_logging',
    'get_logger',
    'setup_structured_logging',
    'set_correlation_id',
    'get_correlation_id',
    'clear_correlation_id',
    'CorrelationContext'
]
