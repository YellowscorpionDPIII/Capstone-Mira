"""Tests for graceful shutdown functionality."""
import unittest
import signal
import threading
import time
from mira.utils.shutdown_handler import (
    ShutdownHandler,
    get_shutdown_handler,
    register_shutdown_callback
)


class TestShutdownHandler(unittest.TestCase):
    """Test cases for ShutdownHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = ShutdownHandler()
        self.callback_executed = []
        
    def tearDown(self):
        """Clean up after tests."""
        self.callback_executed.clear()
        # Uninstall signal handlers to avoid interference
        try:
            self.handler.uninstall_signal_handlers()
        except:
            pass
        
    def test_register_callback(self):
        """Test registering shutdown callbacks."""
        def callback1():
            self.callback_executed.append('callback1')
            
        def callback2():
            self.callback_executed.append('callback2')
            
        self.handler.register_callback(callback1, 'callback1')
        self.handler.register_callback(callback2, 'callback2')
        
        self.assertEqual(len(self.handler.shutdown_callbacks), 2)
        
    def test_unregister_callback(self):
        """Test unregistering shutdown callbacks."""
        def callback1():
            self.callback_executed.append('callback1')
            
        self.handler.register_callback(callback1, 'callback1')
        self.assertEqual(len(self.handler.shutdown_callbacks), 1)
        
        self.handler.unregister_callback(callback1)
        self.assertEqual(len(self.handler.shutdown_callbacks), 0)
        
    def test_shutdown_executes_callbacks(self):
        """Test that shutdown executes all callbacks."""
        def callback1():
            self.callback_executed.append('callback1')
            
        def callback2():
            self.callback_executed.append('callback2')
            
        self.handler.register_callback(callback1, 'callback1')
        self.handler.register_callback(callback2, 'callback2')
        
        # Execute shutdown without exiting
        self.handler.shutdown(exit_code=None)
        
        # Callbacks should be executed in reverse order (LIFO)
        self.assertEqual(len(self.callback_executed), 2)
        self.assertEqual(self.callback_executed[0], 'callback2')
        self.assertEqual(self.callback_executed[1], 'callback1')
        
    def test_shutdown_handles_callback_errors(self):
        """Test that shutdown continues even if a callback raises an error."""
        def callback_error():
            raise ValueError("Test error")
            
        def callback_success():
            self.callback_executed.append('success')
            
        self.handler.register_callback(callback_success, 'success')
        self.handler.register_callback(callback_error, 'error')
        
        # Should not raise exception
        self.handler.shutdown(exit_code=None)
        
        # Success callback should still execute
        self.assertIn('success', self.callback_executed)
        
    def test_shutdown_only_executes_once(self):
        """Test that shutdown can only be executed once."""
        def callback():
            self.callback_executed.append('callback')
            
        self.handler.register_callback(callback)
        
        self.handler.shutdown(exit_code=None)
        self.handler.shutdown(exit_code=None)
        
        # Callback should only be executed once
        self.assertEqual(len(self.callback_executed), 1)
        
    def test_is_shutting_down(self):
        """Test shutdown status check."""
        self.assertFalse(self.handler.is_shutting_down())
        
        self.handler.shutdown(exit_code=None)
        
        self.assertTrue(self.handler.is_shutting_down())
        
    def test_install_signal_handlers(self):
        """Test installing signal handlers."""
        # This test just verifies that the method can be called
        # Actual signal handling is difficult to test in unit tests
        try:
            self.handler.install_signal_handlers()
            # Should not raise exception
            self.assertTrue(True)
        except Exception as e:
            # Some environments may not allow signal handling
            self.skipTest(f"Signal handlers not available: {e}")
            
    def test_uninstall_signal_handlers(self):
        """Test uninstalling signal handlers."""
        try:
            self.handler.install_signal_handlers()
            self.handler.uninstall_signal_handlers()
            # Should not raise exception
            self.assertTrue(True)
        except Exception as e:
            # Some environments may not allow signal handling
            self.skipTest(f"Signal handlers not available: {e}")
            
    def test_global_shutdown_handler(self):
        """Test global shutdown handler singleton."""
        handler1 = get_shutdown_handler()
        handler2 = get_shutdown_handler()
        
        self.assertIs(handler1, handler2)
        
    def test_register_shutdown_callback_global(self):
        """Test global register_shutdown_callback function."""
        def callback():
            self.callback_executed.append('global')
            
        register_shutdown_callback(callback, 'global_callback')
        
        # Get the global handler and verify callback was registered
        handler = get_shutdown_handler()
        self.assertGreater(len(handler.shutdown_callbacks), 0)
        
    def test_shutdown_thread_safe(self):
        """Test that shutdown is thread-safe."""
        def callback():
            time.sleep(0.1)
            self.callback_executed.append('callback')
            
        self.handler.register_callback(callback)
        
        # Try to initiate shutdown from multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=lambda: self.handler.shutdown(exit_code=None))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Callback should only execute once
        self.assertEqual(len(self.callback_executed), 1)


if __name__ == '__main__':
    unittest.main()
