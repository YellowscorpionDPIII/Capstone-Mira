"""Tests for core framework components."""
import time
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock

from mira.core.message_broker import MessageBroker, get_broker
from mira.core.base_agent import BaseAgent
from mira.core.webhook_handler import WebhookAuthenticator
from mira.llm.base import BaseLLM


# ---------------------------------------------------------------------------
# Minimal concrete agent for testing BaseAgent utilities
# ---------------------------------------------------------------------------

class _SimpleAgent(BaseAgent):
    """Minimal concrete agent that satisfies the abstract interface."""

    def __init__(self, name: str = "simple_agent"):
        mock_llm = MagicMock(spec=BaseLLM)
        super().__init__(llm=mock_llm, name=name)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        return task.get("data", {}).get("prompt", "")


# ---------------------------------------------------------------------------
# MessageBroker tests
# ---------------------------------------------------------------------------

class TestMessageBroker(unittest.TestCase):
    """Test cases for MessageBroker."""

    def setUp(self):
        self.broker = MessageBroker()
        self.received_messages = []

    def tearDown(self):
        if self.broker.running:
            self.broker.stop()

    def test_subscribe_and_publish(self):
        """Test subscribing and publishing messages."""
        def handler(message):
            self.received_messages.append(message)

        self.broker.subscribe("test_event", handler)
        self.broker.start()
        self.broker.publish("test_event", {"value": "test"})
        time.sleep(0.5)

        self.assertEqual(len(self.received_messages), 1)
        self.assertEqual(self.received_messages[0]["type"], "test_event")

    def test_multiple_subscribers(self):
        """Multiple handlers for the same topic all receive the message."""
        received_a = []
        received_b = []

        def handler_a(msg):
            received_a.append(msg)

        def handler_b(msg):
            received_b.append(msg)

        self.broker.subscribe("multi_topic", handler_a)
        self.broker.subscribe("multi_topic", handler_b)
        self.broker.start()
        self.broker.publish("multi_topic", {"value": "shared"})
        time.sleep(0.5)

        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)
        self.assertEqual(received_a[0]["data"]["value"], "shared")
        self.assertEqual(received_b[0]["data"]["value"], "shared")

    def test_unsubscribe(self):
        """Unsubscribed handler does not receive messages."""
        def handler(message):
            self.received_messages.append(message)

        self.broker.subscribe("test_event", handler)
        self.broker.unsubscribe("test_event", handler)
        self.broker.start()
        self.broker.publish("test_event", {"value": "test"})
        time.sleep(0.5)

        self.assertEqual(len(self.received_messages), 0)

    def test_publish_to_nonexistent_topic(self):
        """Publishing to a topic with no subscribers does not raise."""
        self.broker.start()
        try:
            self.broker.publish("nonexistent_topic", {"value": "ignored"})
        except Exception as exc:
            self.fail(f"publish raised unexpectedly: {exc}")

    def test_broker_singleton(self):
        """get_broker() always returns the same instance."""
        broker1 = get_broker()
        broker2 = get_broker()
        self.assertIs(broker1, broker2)


# ---------------------------------------------------------------------------
# BaseAgent utility tests
# ---------------------------------------------------------------------------

class TestBaseAgentUtilities(unittest.TestCase):
    """Test the utility helpers on BaseAgent (validate_message, create_response)."""

    def test_agent_name_and_id(self):
        agent = _SimpleAgent("my_agent")
        self.assertEqual(agent.name, "my_agent")
        self.assertEqual(agent.agent_id, "my_agent")

    def test_validate_message_valid(self):
        agent = _SimpleAgent()
        self.assertTrue(agent.validate_message({"type": "x", "data": {}}))

    def test_validate_message_missing_type(self):
        agent = _SimpleAgent()
        self.assertFalse(agent.validate_message({"data": {}}))

    def test_validate_message_missing_data(self):
        agent = _SimpleAgent()
        self.assertFalse(agent.validate_message({"type": "x"}))

    def test_create_response_success(self):
        agent = _SimpleAgent()
        resp = agent.create_response("success", {"result": "ok"})
        self.assertEqual(resp["status"], "success")
        self.assertEqual(resp["agent_id"], "simple_agent")
        self.assertEqual(resp["data"]["result"], "ok")
        self.assertIsNone(resp["error"])

    def test_create_response_error(self):
        agent = _SimpleAgent()
        resp = agent.create_response("error", None, "Something failed")
        self.assertEqual(resp["status"], "error")
        self.assertEqual(resp["error"], "Something failed")
        self.assertIsNone(resp["data"])


# ---------------------------------------------------------------------------
# WebhookAuthenticator tests (unchanged from original)
# ---------------------------------------------------------------------------

class TestWebhookAuthenticator(unittest.TestCase):
    """Test cases for WebhookAuthenticator."""

    def setUp(self):
        self.authenticator = WebhookAuthenticator()

    def test_valid_timestamp_within_window(self):
        timestamp = (datetime.now() - timedelta(minutes=2)).isoformat()
        self.assertTrue(self.authenticator.validate_signature_timestamp(timestamp))

    def test_valid_timestamp_just_within_window(self):
        timestamp = (datetime.now() - timedelta(seconds=299)).isoformat()
        self.assertTrue(self.authenticator.validate_signature_timestamp(timestamp))

    def test_timestamp_exactly_at_boundary(self):
        timestamp = (datetime.now() - timedelta(seconds=300)).isoformat()
        self.assertFalse(self.authenticator.validate_signature_timestamp(timestamp))

    def test_timestamp_outside_window(self):
        timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
        self.assertFalse(self.authenticator.validate_signature_timestamp(timestamp))

    def test_timestamp_just_outside_window(self):
        timestamp = (datetime.now() - timedelta(seconds=301)).isoformat()
        self.assertFalse(self.authenticator.validate_signature_timestamp(timestamp))

    def test_future_timestamp_within_window(self):
        timestamp = (datetime.now() + timedelta(minutes=2)).isoformat()
        self.assertTrue(self.authenticator.validate_signature_timestamp(timestamp))

    def test_future_timestamp_outside_window(self):
        timestamp = (datetime.now() + timedelta(minutes=10)).isoformat()
        self.assertFalse(self.authenticator.validate_signature_timestamp(timestamp))

    def test_malformed_timestamp_empty_string(self):
        self.assertFalse(self.authenticator.validate_signature_timestamp(""))

    def test_malformed_timestamp_invalid_format(self):
        self.assertFalse(self.authenticator.validate_signature_timestamp("not-a-timestamp"))

    def test_malformed_timestamp_invalid_date(self):
        self.assertFalse(self.authenticator.validate_signature_timestamp("2023-13-45T99:99:99"))

    def test_malformed_timestamp_none(self):
        self.assertFalse(self.authenticator.validate_signature_timestamp(None))

    def test_malformed_timestamp_number(self):
        self.assertFalse(self.authenticator.validate_signature_timestamp(12345))

    def test_timestamp_with_timezone(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        self.assertTrue(self.authenticator.validate_signature_timestamp(timestamp))

    def test_timestamp_with_timezone_old(self):
        timestamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        self.assertFalse(self.authenticator.validate_signature_timestamp(timestamp))


if __name__ == "__main__":
    unittest.main()
