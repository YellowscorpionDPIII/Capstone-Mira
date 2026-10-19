"""Tests for shutdown handler utilities."""
import unittest
import time
from unittest.mock import MagicMock, patch
from mira.utils.shutdown_handler import (
    ShutdownHandler,
    get_shutdown_handler,
    register_shutdown_callback,
    on_shutdown,
    initialize_shutdown_handler
)


class TestShutdownHandler(unittest.TestCase):
    """Test cases for ShutdownHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = ShutdownHandler()
        self.call_order = []
        
    def test_handler_initialization(self):
        """Test handler initialization."""
        self.assertIsNotNone(self.handler)
        self.assertEqual(len(self.handler._callbacks), 0)
        self.assertFalse(self.handler._shutting_down)
        
    def test_register_callback(self):
        """Test registering a shutdown callback."""
        callback = MagicMock()
        callback_id = self.handler.register(callback, priority=20, name="test_callback")
        
        self.assertIsNotNone(callback_id)
        self.assertEqual(len(self.handler._callbacks), 1)
        
    def test_register_invalid_callback(self):
        """Test registering non-callable raises error."""
        with self.assertRaises(TypeError):
            self.handler.register("not_a_function", priority=20)
            
    def test_register_invalid_priority(self):
        """Test registering with invalid priority raises error."""
        callback = MagicMock()
        
        with self.assertRaises(ValueError):
            self.handler.register(callback, priority=-1)
            
        with self.assertRaises(ValueError):
            self.handler.register(callback, priority=101)
            
    def test_unregister_callback(self):
        """Test unregistering a callback."""
        callback = MagicMock()
        callback_id = self.handler.register(callback, priority=20)
        
        result = self.handler.unregister(callback_id)
        self.assertTrue(result)
        self.assertEqual(len(self.handler._callbacks), 0)
        
    def test_unregister_nonexistent_callback(self):
        """Test unregistering non-existent callback."""
        result = self.handler.unregister(999)
        self.assertFalse(result)
        
    def test_execute_shutdown_single_callback(self):
        """Test executing a single shutdown callback."""
        callback = MagicMock()
        self.handler.register(callback, priority=20)
        
        self.handler.execute_shutdown()
        
        callback.assert_called_once()
        self.assertTrue(self.handler._shutting_down)
        
    def test_execute_shutdown_priority_order(self):
        """Test callbacks execute in priority order."""
        def make_callback(name):
            def callback():
                self.call_order.append(name)
            return callback
            
        # Register in random order with different priorities
        self.handler.register(make_callback("medium"), priority=20, name="medium")
        self.handler.register(make_callback("high"), priority=5, name="high")
        self.handler.register(make_callback("low"), priority=30, name="low")
        self.handler.register(make_callback("critical"), priority=1, name="critical")
        
        self.handler.execute_shutdown()
        
        # Should execute in priority order (lowest number first)
        self.assertEqual(self.call_order, ["critical", "high", "medium", "low"])
        
    def test_execute_shutdown_same_priority_fifo(self):
        """Test callbacks with same priority execute in FIFO order."""
        def make_callback(name):
            def callback():
                self.call_order.append(name)
            return callback
            
        # Register multiple callbacks with same priority
        self.handler.register(make_callback("first"), priority=20, name="first")
        self.handler.register(make_callback("second"), priority=20, name="second")
        self.handler.register(make_callback("third"), priority=20, name="third")
        
        self.handler.execute_shutdown()
        
        # Should execute in FIFO order
        self.assertEqual(self.call_order, ["first", "second", "third"])
        
    def test_execute_shutdown_handles_errors(self):
        """Test shutdown continues even if callbacks raise errors."""
        def failing_callback():
            self.call_order.append("failing")
            raise Exception("Test error")
            
        def success_callback():
            self.call_order.append("success")
            
        self.handler.register(failing_callback, priority=10, name="failing")
        self.handler.register(success_callback, priority=20, name="success")
        
        # Should not raise exception
        self.handler.execute_shutdown()
        
        # Both should have been called
        self.assertEqual(self.call_order, ["failing", "success"])
        
    def test_execute_shutdown_idempotent(self):
        """Test execute_shutdown can't run twice simultaneously."""
        callback = MagicMock()
        self.handler.register(callback, priority=20)
        
        self.handler.execute_shutdown()
        self.handler.execute_shutdown()  # Second call
        
        # Callback should only be called once
        callback.assert_called_once()
        
    def test_clear_callbacks(self):
        """Test clearing all callbacks."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        self.handler.register(callback1, priority=10)
        self.handler.register(callback2, priority=20)
        
        self.assertEqual(len(self.handler._callbacks), 2)
        
        self.handler.clear()
        
        self.assertEqual(len(self.handler._callbacks), 0)
        
    @patch('signal.signal')
    @patch('atexit.register')
    def test_register_signal_handlers(self, mock_atexit, mock_signal):
        """Test registering signal handlers."""
        self.handler.register_signal_handlers()
        
        # Should register SIGTERM and SIGINT
        self.assertEqual(mock_signal.call_count, 2)
        mock_atexit.assert_called_once()
        self.assertTrue(self.handler._signal_handlers_registered)


class TestGlobalShutdownHandler(unittest.TestCase):
    """Test cases for global shutdown handler functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global handler
        import mira.utils.shutdown_handler as sh
        sh._shutdown_handler = None
        
    def test_get_shutdown_handler(self):
        """Test getting global shutdown handler."""
        handler1 = get_shutdown_handler()
        handler2 = get_shutdown_handler()
        
        # Should return same instance
        self.assertIs(handler1, handler2)
        
    def test_register_shutdown_callback_global(self):
        """Test registering callback with global handler."""
        callback = MagicMock()
        callback_id = register_shutdown_callback(callback, priority=20, name="test")
        
        self.assertIsNotNone(callback_id)
        
    def test_on_shutdown_decorator(self):
        """Test on_shutdown decorator."""
        call_tracker = []
        
        @on_shutdown(priority=10, name="decorated")
        def cleanup_function():
            call_tracker.append("cleanup")
            
        # Function should still work normally
        cleanup_function()
        self.assertEqual(call_tracker, ["cleanup"])
        
        # Should be registered with handler
        handler = get_shutdown_handler()
        self.assertGreater(len(handler._callbacks), 0)
        
    @patch('mira.utils.shutdown_handler.get_shutdown_handler')
    def test_initialize_shutdown_handler(self, mock_get_handler):
        """Test initializing shutdown handler."""
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler
        
        initialize_shutdown_handler()
        
        mock_handler.register_signal_handlers.assert_called_once()


class TestPriorityLevels(unittest.TestCase):
    """Test different priority level use cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = ShutdownHandler()
        self.call_order = []
        
    def test_critical_priority_agents(self):
        """Test critical priority for agent draining."""
        def drain_agents():
            self.call_order.append("drain_agents")
            
        def close_connections():
            self.call_order.append("close_connections")
            
        def cleanup_temp():
            self.call_order.append("cleanup_temp")
            
        # Register with realistic priorities
        self.handler.register(drain_agents, priority=5, name="drain_agents")
        self.handler.register(close_connections, priority=15, name="close_connections")
        self.handler.register(cleanup_temp, priority=25, name="cleanup_temp")
        
        self.handler.execute_shutdown()
        
        # Agents should drain before connections close
        self.assertEqual(
            self.call_order,
            ["drain_agents", "close_connections", "cleanup_temp"]
        )


if __name__ == '__main__':
    unittest.main()
