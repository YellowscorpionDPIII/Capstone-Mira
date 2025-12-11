"""Tests for core functionality."""
import unittest
from datetime import datetime, timedelta, timezone
from mira.core.message_broker import MessageBroker, get_broker
from mira.core.base_agent import BaseAgent
from mira.core.webhook_handler import WebhookAuthenticator
from typing import Dict, Any


class TestAgent(BaseAgent):
    """Test agent for testing purposes."""
    
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process test message."""
        return self.create_response('success', message['data'])


class TestMessageBroker(unittest.TestCase):
    """Test cases for MessageBroker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.broker = MessageBroker()
        self.received_messages = []
        
    def tearDown(self):
        """Clean up after tests."""
        if self.broker.running:
            self.broker.stop()
            
    def test_subscribe_and_publish(self):
        """Test subscribing and publishing messages."""
        def handler(message):
            self.received_messages.append(message)
            
        self.broker.subscribe('test_event', handler)
        self.broker.start()
        
        self.broker.publish('test_event', {'value': 'test'})
        
        # Give broker time to process
        import time
        time.sleep(0.5)
        
        self.assertEqual(len(self.received_messages), 1)
        self.assertEqual(self.received_messages[0]['type'], 'test_event')
        
    def test_unsubscribe(self):
        """Test unsubscribing from messages."""
        def handler(message):
            self.received_messages.append(message)
            
        self.broker.subscribe('test_event', handler)
        self.broker.unsubscribe('test_event', handler)
        self.broker.start()
        
        self.broker.publish('test_event', {'value': 'test'})
        
        import time
        time.sleep(0.5)
        
        self.assertEqual(len(self.received_messages), 0)
        
    def test_broker_singleton(self):
        """Test broker singleton pattern."""
        broker1 = get_broker()
        broker2 = get_broker()
        self.assertIs(broker1, broker2)


class TestBaseAgent(unittest.TestCase):
    """Test cases for BaseAgent."""
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = TestAgent('test_agent', {'key': 'value'})
        self.assertEqual(agent.agent_id, 'test_agent')
        self.assertEqual(agent.config['key'], 'value')
        
    def test_validate_message(self):
        """Test message validation."""
        agent = TestAgent('test_agent')
        
        valid_message = {'type': 'test', 'data': {}}
        self.assertTrue(agent.validate_message(valid_message))
        
        invalid_message = {'type': 'test'}
        self.assertFalse(agent.validate_message(invalid_message))
        
    def test_create_response(self):
        """Test response creation."""
        agent = TestAgent('test_agent')
        response = agent.create_response('success', {'result': 'ok'})
        
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['agent_id'], 'test_agent')
        self.assertEqual(response['data']['result'], 'ok')
        self.assertIsNone(response['error'])


class TestWebhookAuthenticator(unittest.TestCase):
    """Test cases for WebhookAuthenticator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.authenticator = WebhookAuthenticator()
    
    def test_valid_timestamp_within_window(self):
        """Test validation of a timestamp within the 5-minute window."""
        # Create a timestamp 2 minutes ago
        timestamp = (datetime.now() - timedelta(minutes=2)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertTrue(result)
    
    def test_valid_timestamp_just_within_window(self):
        """Test validation of a timestamp at 299 seconds (just within window)."""
        # Create a timestamp 299 seconds ago
        timestamp = (datetime.now() - timedelta(seconds=299)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertTrue(result)
    
    def test_timestamp_exactly_at_boundary(self):
        """Test validation of a timestamp at exactly 300 seconds."""
        # Create a timestamp exactly 300 seconds ago
        timestamp = (datetime.now() - timedelta(seconds=300)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        # Should be False as it's not less than 300
        self.assertFalse(result)
    
    def test_timestamp_outside_window(self):
        """Test validation of a timestamp outside the 5-minute window."""
        # Create a timestamp 10 minutes ago
        timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertFalse(result)
    
    def test_timestamp_just_outside_window(self):
        """Test validation of a timestamp at 301 seconds (just outside window)."""
        # Create a timestamp 301 seconds ago
        timestamp = (datetime.now() - timedelta(seconds=301)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertFalse(result)
    
    def test_future_timestamp_within_window(self):
        """Test validation of a future timestamp within the window."""
        # Create a timestamp 2 minutes in the future
        timestamp = (datetime.now() + timedelta(minutes=2)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        # Should be True as we use abs() for time difference
        self.assertTrue(result)
    
    def test_future_timestamp_outside_window(self):
        """Test validation of a future timestamp outside the window."""
        # Create a timestamp 10 minutes in the future
        timestamp = (datetime.now() + timedelta(minutes=10)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertFalse(result)
    
    def test_malformed_timestamp_empty_string(self):
        """Test handling of empty string timestamp."""
        result = self.authenticator.validate_signature_timestamp("")
        self.assertFalse(result)
    
    def test_malformed_timestamp_invalid_format(self):
        """Test handling of invalid timestamp format."""
        result = self.authenticator.validate_signature_timestamp("not-a-timestamp")
        self.assertFalse(result)
    
    def test_malformed_timestamp_invalid_date(self):
        """Test handling of invalid date values."""
        result = self.authenticator.validate_signature_timestamp("2023-13-45T99:99:99")
        self.assertFalse(result)
    
    def test_malformed_timestamp_none(self):
        """Test handling of None as timestamp."""
        result = self.authenticator.validate_signature_timestamp(None)
        self.assertFalse(result)
    
    def test_malformed_timestamp_number(self):
        """Test handling of number instead of string."""
        result = self.authenticator.validate_signature_timestamp(12345)
        self.assertFalse(result)
    
    def test_timestamp_with_timezone(self):
        """Test validation of timestamp with timezone information."""
        # Create a timestamp with UTC timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertTrue(result)
    
    def test_timestamp_with_timezone_old(self):
        """Test validation of old timestamp with timezone information."""
        # Create a timestamp 10 minutes ago with UTC timezone
        timestamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        result = self.authenticator.validate_signature_timestamp(timestamp)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
