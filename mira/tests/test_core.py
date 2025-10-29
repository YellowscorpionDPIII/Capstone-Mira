"""Tests for core functionality."""
import unittest
from mira.core.message_broker import MessageBroker, get_broker
from mira.core.base_agent import BaseAgent
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


if __name__ == '__main__':
    unittest.main()
