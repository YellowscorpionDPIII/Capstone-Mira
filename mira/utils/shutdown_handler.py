"""Graceful shutdown handler for the Mira application."""
import signal
import logging
import sys
import threading
from typing import Callable, List, Optional
from datetime import datetime


class ShutdownHandler:
    """
    Handles graceful shutdown of the application.
    
    Registers signal handlers for SIGTERM and SIGINT to ensure
    clean shutdown of resources like database connections, message
    brokers, and other services.
    """
    
    def __init__(self):
        """Initialize the shutdown handler."""
        self.logger = logging.getLogger("mira.shutdown")
        self.shutdown_callbacks: List[Callable] = []
        self.shutdown_initiated = False
        self.shutdown_lock = threading.Lock()
        self._original_sigterm = None
        self._original_sigint = None
        
    def register_callback(self, callback: Callable, name: Optional[str] = None):
        """
        Register a callback to be called during shutdown.
        
        Callbacks are called in reverse order of registration (LIFO).
        
        Args:
            callback: Function to call during shutdown
            name: Optional name for the callback (for logging)
        """
        callback_name = name or getattr(callback, '__name__', 'unknown')
        self.shutdown_callbacks.append((callback, callback_name))
        self.logger.debug(f"Registered shutdown callback: {callback_name}")
        
    def unregister_callback(self, callback: Callable):
        """
        Unregister a shutdown callback.
        
        Args:
            callback: Callback function to remove
        """
        self.shutdown_callbacks = [
            (cb, name) for cb, name in self.shutdown_callbacks if cb != callback
        ]
        
    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        try:
            # Store original handlers
            self._original_sigterm = signal.signal(signal.SIGTERM, self._signal_handler)
            self._original_sigint = signal.signal(signal.SIGINT, self._signal_handler)
            self.logger.info("Signal handlers installed for SIGTERM and SIGINT")
        except (ValueError, OSError) as e:
            # This can happen in threads or certain environments
            self.logger.warning(f"Could not install signal handlers: {e}")
            
    def uninstall_signal_handlers(self):
        """Restore original signal handlers."""
        try:
            if self._original_sigterm is not None:
                signal.signal(signal.SIGTERM, self._original_sigterm)
            if self._original_sigint is not None:
                signal.signal(signal.SIGINT, self._original_sigint)
            self.logger.info("Signal handlers restored")
        except (ValueError, OSError) as e:
            self.logger.warning(f"Could not restore signal handlers: {e}")
            
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown")
        self.shutdown()
        
    def shutdown(self, exit_code: int = 0):
        """
        Perform graceful shutdown.
        
        Args:
            exit_code: Exit code to use when exiting the application
        """
        with self.shutdown_lock:
            if self.shutdown_initiated:
                self.logger.warning("Shutdown already in progress")
                return
                
            self.shutdown_initiated = True
            
        self.logger.info("Starting graceful shutdown sequence")
        start_time = datetime.now()
        
        # Execute shutdown callbacks in reverse order (LIFO)
        for callback, name in reversed(self.shutdown_callbacks):
            try:
                self.logger.info(f"Executing shutdown callback: {name}")
                callback()
            except Exception as e:
                self.logger.error(f"Error in shutdown callback {name}: {e}", exc_info=True)
                
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Graceful shutdown completed in {duration:.2f}s")
        
        # Exit if exit_code is provided
        if exit_code is not None:
            sys.exit(exit_code)
            
    def is_shutting_down(self) -> bool:
        """
        Check if shutdown is in progress.
        
        Returns:
            True if shutdown has been initiated
        """
        return self.shutdown_initiated


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


def register_shutdown_callback(callback: Callable, name: Optional[str] = None):
    """
    Register a callback to be called during shutdown.
    
    Args:
        callback: Function to call during shutdown
        name: Optional name for the callback
    """
    handler = get_shutdown_handler()
    handler.register_callback(callback, name)


def install_signal_handlers():
    """Install signal handlers for graceful shutdown."""
    handler = get_shutdown_handler()
    handler.install_signal_handlers()
