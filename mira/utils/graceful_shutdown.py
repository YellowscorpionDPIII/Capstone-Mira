"""Graceful shutdown handler for Mira platform."""
import signal
import logging
import threading
import atexit
from typing import List, Callable, Optional


class GracefulShutdown:
    """
    Handles graceful shutdown of the application.
    
    Captures SIGTERM and SIGINT signals and executes cleanup handlers.
    """
    
    def __init__(self):
        """Initialize graceful shutdown handler."""
        self.logger = logging.getLogger("mira.shutdown")
        self.shutdown_handlers: List[Callable] = []
        self.is_shutting_down = False
        self.shutdown_event = threading.Event()
        self._original_sigterm = None
        self._original_sigint = None
    
    def register_handler(self, handler: Callable):
        """
        Register a shutdown handler.
        
        Handlers are called in reverse order of registration (LIFO).
        
        Args:
            handler: Callable to execute during shutdown
        """
        self.shutdown_handlers.insert(0, handler)
        self.logger.debug(f"Registered shutdown handler: {handler.__name__}")
    
    def setup(self):
        """Set up signal handlers for graceful shutdown."""
        # Store original handlers
        self._original_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        
        # Also register atexit handler as fallback
        atexit.register(self._cleanup)
        
        self.logger.info("Graceful shutdown handlers registered for SIGTERM and SIGINT")
    
    def _handle_signal(self, signum, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.shutdown()
    
    def shutdown(self, timeout: Optional[int] = 30):
        """
        Perform graceful shutdown.
        
        Args:
            timeout: Maximum time in seconds to wait for shutdown (default: 30)
        """
        if self.is_shutting_down:
            self.logger.warning("Shutdown already in progress")
            return
        
        self.is_shutting_down = True
        self.shutdown_event.set()
        
        self.logger.info(f"Starting graceful shutdown (timeout: {timeout}s)...")
        
        # Execute all registered handlers
        for i, handler in enumerate(self.shutdown_handlers):
            try:
                self.logger.info(f"Executing shutdown handler {i+1}/{len(self.shutdown_handlers)}: {handler.__name__}")
                handler()
            except Exception as e:
                self.logger.error(f"Error in shutdown handler {handler.__name__}: {e}", exc_info=True)
        
        self.logger.info("Graceful shutdown completed")
    
    def _cleanup(self):
        """Cleanup method called by atexit."""
        if not self.is_shutting_down:
            self.logger.info("Cleanup called via atexit")
            self.shutdown()
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown signal.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            True if shutdown was signaled, False if timeout occurred
        """
        return self.shutdown_event.wait(timeout)
    
    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        self.logger.debug("Original signal handlers restored")


# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    """
    Get the global shutdown handler instance.
    
    Returns:
        GracefulShutdown instance
    """
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdown()
    return _shutdown_handler


def register_shutdown_handler(handler: Callable):
    """
    Register a shutdown handler with the global shutdown handler.
    
    Args:
        handler: Callable to execute during shutdown
    """
    get_shutdown_handler().register_handler(handler)
