"""Tests for graceful shutdown handler."""
import unittest
import signal
import time
import threading
from mira.utils.graceful_shutdown import (
    GracefulShutdown,
    get_shutdown_handler,
    register_shutdown_handler
)


class TestGracefulShutdown(unittest.TestCase):
    """Test cases for graceful shutdown."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.shutdown_handler = GracefulShutdown()
        self.call_count = 0
        self.handlers_called = []
    
    def tearDown(self):
        """Clean up after tests."""
        self.shutdown_handler.restore_signal_handlers()
    
    def test_register_handler(self):
        """Test registering shutdown handlers."""
        def handler1():
            self.handlers_called.append('handler1')
        
        def handler2():
            self.handlers_called.append('handler2')
        
        self.shutdown_handler.register_handler(handler1)
        self.shutdown_handler.register_handler(handler2)
        
        self.assertEqual(len(self.shutdown_handler.shutdown_handlers), 2)
    
    def test_shutdown_executes_handlers(self):
        """Test that shutdown executes all registered handlers."""
        def handler1():
            self.handlers_called.append('handler1')
        
        def handler2():
            self.handlers_called.append('handler2')
        
        self.shutdown_handler.register_handler(handler1)
        self.shutdown_handler.register_handler(handler2)
        
        self.shutdown_handler.shutdown()
        
        # Check that both handlers were called
        self.assertEqual(len(self.handlers_called), 2)
        self.assertIn('handler1', self.handlers_called)
        self.assertIn('handler2', self.handlers_called)
    
    def test_shutdown_handlers_lifo_order(self):
        """Test that handlers are called in LIFO order."""
        call_order = []
        
        def handler1():
            call_order.append(1)
        
        def handler2():
            call_order.append(2)
        
        def handler3():
            call_order.append(3)
        
        self.shutdown_handler.register_handler(handler1)
        self.shutdown_handler.register_handler(handler2)
        self.shutdown_handler.register_handler(handler3)
        
        self.shutdown_handler.shutdown()
        
        # Should be called in reverse order: 3, 2, 1
        self.assertEqual(call_order, [3, 2, 1])
    
    def test_shutdown_handles_exceptions(self):
        """Test that exceptions in handlers don't stop other handlers."""
        def good_handler():
            self.handlers_called.append('good')
        
        def bad_handler():
            raise Exception("Handler error")
        
        def another_good_handler():
            self.handlers_called.append('another_good')
        
        self.shutdown_handler.register_handler(good_handler)
        self.shutdown_handler.register_handler(bad_handler)
        self.shutdown_handler.register_handler(another_good_handler)
        
        # Should not raise exception
        self.shutdown_handler.shutdown()
        
        # Good handlers should still be called
        self.assertIn('good', self.handlers_called)
        self.assertIn('another_good', self.handlers_called)
    
    def test_shutdown_idempotent(self):
        """Test that calling shutdown multiple times is safe."""
        call_count = [0]
        
        def handler():
            call_count[0] += 1
        
        self.shutdown_handler.register_handler(handler)
        
        self.shutdown_handler.shutdown()
        self.shutdown_handler.shutdown()
        
        # Handler should only be called once
        self.assertEqual(call_count[0], 1)
    
    def test_wait_for_shutdown(self):
        """Test waiting for shutdown signal."""
        # Start a thread that signals shutdown after a delay
        def trigger_shutdown():
            time.sleep(0.5)
            self.shutdown_handler.shutdown()
        
        thread = threading.Thread(target=trigger_shutdown)
        thread.start()
        
        # Wait for shutdown
        start = time.time()
        result = self.shutdown_handler.wait_for_shutdown(timeout=2.0)
        elapsed = time.time() - start
        
        self.assertTrue(result)
        self.assertLess(elapsed, 1.0)  # Should complete in less than 1 second
        
        thread.join()
    
    def test_wait_for_shutdown_timeout(self):
        """Test wait_for_shutdown with timeout."""
        start = time.time()
        result = self.shutdown_handler.wait_for_shutdown(timeout=0.5)
        elapsed = time.time() - start
        
        self.assertFalse(result)
        self.assertGreaterEqual(elapsed, 0.5)
    
    def test_global_shutdown_handler(self):
        """Test global shutdown handler singleton."""
        handler1 = get_shutdown_handler()
        handler2 = get_shutdown_handler()
        
        self.assertIs(handler1, handler2)
    
    def test_register_shutdown_handler_global(self):
        """Test registering handler via global function."""
        called = [False]
        
        def my_handler():
            called[0] = True
        
        register_shutdown_handler(my_handler)
        
        # Get the global handler and trigger shutdown
        handler = get_shutdown_handler()
        handler.shutdown()
        
        self.assertTrue(called[0])


if __name__ == '__main__':
    unittest.main()
