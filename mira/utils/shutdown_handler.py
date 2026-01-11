"""Shutdown handler utilities for Mira platform.

Provides priority-based shutdown callback management for graceful application shutdown
in production environments, ensuring high-priority resources are cleaned up first.
"""
import logging
import signal
import heapq
import atexit
from typing import Callable, List, Tuple, Optional
from functools import wraps


logger = logging.getLogger("mira.shutdown_handler")


class ShutdownHandler:
    """
    Priority-based shutdown handler for graceful application termination.
    
    Manages shutdown callbacks with priority levels, ensuring critical resources
    (e.g., agent draining, connection cleanup) are handled first.
    
    Priority levels (lower number = higher priority):
    - 0-9: Critical (agents, message brokers)
    - 10-19: High (database connections, file handles)
    - 20-29: Medium (cache cleanup, temporary files)
    - 30+: Low (logging, metrics)
    """
    
    def __init__(self):
        """Initialize shutdown handler."""
        self._callbacks: List[Tuple[int, int, Callable]] = []
        self._callback_counter = 0
        self._shutting_down = False
        self._signal_handlers_registered = False
        
    def register(
        self,
        callback: Callable,
        priority: int = 20,
        name: Optional[str] = None
    ):
        """
        Register a shutdown callback with priority.
        
        Args:
            callback: Function to call on shutdown (should accept no arguments)
            priority: Priority level (lower = higher priority, 0-100)
            name: Optional name for logging
            
        Returns:
            Callback ID for potential unregistration
        """
        if not callable(callback):
            raise TypeError("Callback must be callable")
            
        if not 0 <= priority <= 100:
            raise ValueError("Priority must be between 0 and 100")
            
        # Use counter for stable ordering of same-priority items
        callback_id = self._callback_counter
        self._callback_counter += 1
        
        callback_name = name or getattr(callback, '__name__', f'callback_{callback_id}')
        
        # Store as (priority, counter, callback, name) - counter ensures FIFO for same priority
        heapq.heappush(self._callbacks, (priority, callback_id, callback, callback_name))
        
        logger.debug(f"Registered shutdown callback '{callback_name}' with priority {priority}")
        
        return callback_id
        
    def unregister(self, callback_id: int) -> bool:
        """
        Unregister a shutdown callback by ID.
        
        Args:
            callback_id: Callback ID returned by register()
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        original_len = len(self._callbacks)
        self._callbacks = [
            item for item in self._callbacks
            if item[1] != callback_id
        ]
        heapq.heapify(self._callbacks)
        
        removed = len(self._callbacks) < original_len
        if removed:
            logger.debug(f"Unregistered shutdown callback ID {callback_id}")
        
        return removed
        
    def execute_shutdown(self):
        """
        Execute all shutdown callbacks in priority order.
        
        Callbacks are executed from highest to lowest priority (lowest number first).
        Errors in callbacks are logged but don't prevent other callbacks from running.
        """
        if self._shutting_down:
            logger.warning("Shutdown already in progress")
            return
            
        self._shutting_down = True
        logger.info("Starting graceful shutdown...")
        
        executed = 0
        failed = 0
        
        # Process callbacks in priority order (heappop returns lowest priority first)
        while self._callbacks:
            priority, callback_id, callback, callback_name = heapq.heappop(self._callbacks)
            
            try:
                logger.info(f"Executing shutdown callback '{callback_name}' (priority {priority})")
                callback()
                executed += 1
            except Exception as e:
                logger.error(f"Error in shutdown callback '{callback_name}': {e}", exc_info=True)
                failed += 1
                
        logger.info(
            f"Shutdown complete: {executed} callbacks executed, {failed} failed"
        )
        
    def register_signal_handlers(self):
        """
        Register signal handlers for graceful shutdown.
        
        Handles SIGTERM and SIGINT (Ctrl+C) signals.
        """
        if self._signal_handlers_registered:
            logger.warning("Signal handlers already registered")
            return
            
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"Received signal {signal_name}, initiating shutdown...")
            self.execute_shutdown()
            # Exit after shutdown
            exit(0)
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Also register with atexit for normal termination
        atexit.register(lambda: self.execute_shutdown() if not self._shutting_down else None)
        
        self._signal_handlers_registered = True
        logger.info("Signal handlers registered for graceful shutdown")
        
    def clear(self):
        """Clear all registered callbacks."""
        self._callbacks.clear()
        logger.debug("All shutdown callbacks cleared")


# Global shutdown handler instance
_shutdown_handler: Optional[ShutdownHandler] = None


def get_shutdown_handler() -> ShutdownHandler:
    """
    Get the global shutdown handler instance.
    
    Returns:
        ShutdownHandler instance
    """
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = ShutdownHandler()
    return _shutdown_handler


def register_shutdown_callback(
    callback: Callable,
    priority: int = 20,
    name: Optional[str] = None
) -> int:
    """
    Register a shutdown callback with the global handler.
    
    Args:
        callback: Function to call on shutdown
        priority: Priority level (0-100, lower = higher priority)
        name: Optional name for logging
        
    Returns:
        Callback ID for potential unregistration
    """
    handler = get_shutdown_handler()
    return handler.register(callback, priority, name)


def on_shutdown(priority: int = 20, name: Optional[str] = None):
    """
    Decorator to register a function as a shutdown callback.
    
    Args:
        priority: Priority level (0-100, lower = higher priority)
        name: Optional name for logging
        
    Returns:
        Decorated function
        
    Example:
        @on_shutdown(priority=5, name="drain_agents")
        def cleanup_agents():
            # Drain agent queues before shutdown
            pass
    """
    def decorator(func):
        callback_name = name or func.__name__
        register_shutdown_callback(func, priority=priority, name=callback_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def initialize_shutdown_handler():
    """
    Initialize and register signal handlers for graceful shutdown.
    
    Call this during application startup to enable automatic shutdown handling.
    """
    handler = get_shutdown_handler()
    handler.register_signal_handlers()
    logger.info("Shutdown handler initialized")
