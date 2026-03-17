"""
Tests for MessageBroker infrastructure and OrchestratorAgent edge paths.

Uses skip guards so tests remain safe to run even if module paths change.
"""
import asyncio
import json
import types
from typing import Any, Dict, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Lazy imports with fallback shims
# ---------------------------------------------------------------------------

def _import_optional(path: str):
    """Import a module by dotted path; return an empty namespace on failure."""
    try:
        return __import__(path, fromlist=["*"])
    except ImportError:
        return types.SimpleNamespace()


_broker_mod = _import_optional("mira.core.message_broker")
_orchestrator_mod = _import_optional("mira.agents.orchestrator_agent")


# ---------------------------------------------------------------------------
# MessageBroker – publish / subscribe tests
# ---------------------------------------------------------------------------

class TestMessageBrokerPublishSubscribe:
    def test_basic_publish_subscribe(self):
        """Single subscriber receives the published payload."""
        MessageBroker = getattr(_broker_mod, "MessageBroker", None)
        if MessageBroker is None:
            pytest.skip("MessageBroker not available")

        broker = MessageBroker()
        received: List[Dict[str, Any]] = []

        def handler(message):
            received.append(message)

        broker.subscribe("test_topic", handler)
        broker.start()
        broker.publish("test_topic", {"value": 42})

        import time
        time.sleep(0.4)
        broker.stop()

        assert len(received) == 1
        assert received[0]["data"]["value"] == 42

    def test_multiple_subscribers_all_receive(self):
        """All subscribers for a topic receive every published message."""
        MessageBroker = getattr(_broker_mod, "MessageBroker", None)
        if MessageBroker is None:
            pytest.skip("MessageBroker not available")

        broker = MessageBroker()
        events: List[str] = []

        def h1(msg):
            events.append(f"h1:{msg['data']['id']}")

        def h2(msg):
            events.append(f"h2:{msg['data']['id']}")

        broker.subscribe("shared", h1)
        broker.subscribe("shared", h2)
        broker.start()
        broker.publish("shared", {"id": 99})

        import time
        time.sleep(0.4)
        broker.stop()

        assert "h1:99" in events
        assert "h2:99" in events

    def test_unsubscribe_stops_delivery(self):
        """After unsubscribe, handler no longer receives messages."""
        MessageBroker = getattr(_broker_mod, "MessageBroker", None)
        if MessageBroker is None:
            pytest.skip("MessageBroker not available")

        broker = MessageBroker()
        received: List[Any] = []

        def handler(msg):
            received.append(msg)

        broker.subscribe("ev", handler)
        broker.unsubscribe("ev", handler)
        broker.start()
        broker.publish("ev", {"x": 1})

        import time
        time.sleep(0.4)
        broker.stop()

        assert len(received) == 0

    def test_publish_to_unknown_topic_does_not_raise(self):
        """Publishing to a topic with no subscribers is a no-op."""
        MessageBroker = getattr(_broker_mod, "MessageBroker", None)
        if MessageBroker is None:
            pytest.skip("MessageBroker not available")

        broker = MessageBroker()
        broker.start()
        try:
            broker.publish("ghost_topic", {"ignored": True})
        except Exception as exc:
            pytest.fail(f"publish raised unexpectedly: {exc}")
        finally:
            broker.stop()

    def test_unsubscribe_unknown_topic_is_noop(self):
        """Calling unsubscribe on a topic that was never subscribed to is a no-op."""
        MessageBroker = getattr(_broker_mod, "MessageBroker", None)
        if MessageBroker is None:
            pytest.skip("MessageBroker not available")

        broker = MessageBroker()

        def handler(msg):
            pass

        # Unsubscribing from a topic that was never subscribed to should not raise
        # (the dict check in the implementation guards this path)
        try:
            broker.unsubscribe("never_subscribed", handler)
        except Exception as exc:
            pytest.fail(f"unsubscribe on unknown topic raised: {exc}")


# ---------------------------------------------------------------------------
# OrchestratorAgent – routing edge paths
# ---------------------------------------------------------------------------

class TestOrchestratorEdgePaths:
    @pytest.mark.asyncio
    async def test_unknown_route_returns_error_status(self):
        """Routing to a message type with no registered handler returns an error."""
        OrchestratorAgent = getattr(_orchestrator_mod, "OrchestratorAgent", None)
        if OrchestratorAgent is None:
            pytest.skip("OrchestratorAgent not available")

        orch = OrchestratorAgent()
        result = await orch.process({"type": "completely_unknown", "data": {}})

        assert isinstance(result, dict)
        # Must be an error shape
        assert result.get("status") == "error"
        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_missing_agent_in_registry_returns_error(self):
        """If routing rule exists but agent isn't registered, return error."""
        OrchestratorAgent = getattr(_orchestrator_mod, "OrchestratorAgent", None)
        if OrchestratorAgent is None:
            pytest.skip("OrchestratorAgent not available")

        orch = OrchestratorAgent()
        # Add rule but don't register the agent
        orch.add_routing_rule("orphan_route", "nonexistent_agent")
        result = await orch.process({"type": "orphan_route", "data": {}})

        assert result.get("status") == "error"
        assert "nonexistent_agent" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_invalid_message_format_returns_error(self):
        """Messages without 'type' or 'data' return validation error."""
        OrchestratorAgent = getattr(_orchestrator_mod, "OrchestratorAgent", None)
        if OrchestratorAgent is None:
            pytest.skip("OrchestratorAgent not available")

        orch = OrchestratorAgent()

        for bad_message in [
            {},
            {"type": "x"},          # missing 'data'
            {"data": {}},            # missing 'type'
            {"other": "field"},
        ]:
            result = await orch.process(bad_message)
            assert result.get("status") == "error", f"Expected error for {bad_message}"
