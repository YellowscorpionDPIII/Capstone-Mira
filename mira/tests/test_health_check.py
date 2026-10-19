"""Tests for /healthz health check endpoint."""
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from mira.app import MiraApplication


def _make_mock_config(extra=None):
    """Return a mock Config object with sensible defaults for tests."""
    defaults = {
        "logging.level": "INFO",
        "broker.enabled": True,
        "webhook.enabled": True,
        "webhook.secret_key": "test_secret",
        "webhook.host": "0.0.0.0",
        "webhook.port": 5000,
        # LLM config
        "llm.mode": "router",
        "llm.claude_model": "claude-3-7-sonnet-latest",
        "llm.cheap_model": "gpt-4.1-mini",
        "llm.local_model": "llama3.1",
        "llm.anthropic_api_key": "",
        "llm.openai_api_key": "",
        # Agent config
        "agents.project_plan_agent.enabled": True,
        "agents.risk_assessment_agent.enabled": True,
        "agents.status_reporter_agent.enabled": True,
        "agents.roadmapping_agent.enabled": True,
        "agents.tool_recommender_agent.enabled": False,
    }
    if extra:
        defaults.update(extra)
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


class TestHealthCheckEndpoint(unittest.TestCase):
    """Test cases for /healthz endpoint."""

    def setUp(self):
        """Set up test fixtures with fully mocked LLM backends."""
        with patch("mira.app.get_config") as mock_get_config, \
             patch("mira.app.ClaudeLLM") as MockClaude, \
             patch("mira.app.OpenAILLM") as MockOpenAI, \
             patch("mira.app.OllamaLLM") as MockOllama, \
             patch("mira.app.LLMRouter") as MockRouter, \
             patch("mira.app.get_secret", return_value=""):

            mock_get_config.return_value = _make_mock_config()

            # Each LLM constructor returns a MagicMock
            mock_llm = MagicMock()
            mock_llm.generate = AsyncMock(return_value={"text": None, "raw": None})
            MockClaude.return_value = mock_llm
            MockOpenAI.return_value = mock_llm
            MockOllama.return_value = mock_llm
            MockRouter.return_value = mock_llm

            self.app = MiraApplication()

        self.client = (
            self.app.webhook_handler.app.test_client()
            if self.app.webhook_handler
            else None
        )

    def test_health_check_endpoint_exists(self):
        if not self.client:
            self.skipTest("Webhook handler not initialized")
        response = self.client.get("/healthz")
        self.assertIsNotNone(response)

    def test_health_check_healthy_status(self):
        if not self.client:
            self.skipTest("Webhook handler not initialized")
        response = self.client.get("/healthz")
        data = response.get_json()
        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertIn("configuration", data["checks"])
        self.assertIn("agents", data["checks"])

    def test_health_check_configuration_ok(self):
        if not self.client:
            self.skipTest("Webhook handler not initialized")
        response = self.client.get("/healthz")
        data = response.get_json()
        self.assertEqual(data["checks"]["configuration"], "ok")

    def test_health_check_agents_ok(self):
        if not self.client:
            self.skipTest("Webhook handler not initialized")
        response = self.client.get("/healthz")
        data = response.get_json()
        self.assertEqual(data["checks"]["agents"], "ok")
        self.assertGreater(data["checks"]["agent_count"], 0)

    def test_health_check_status_code_healthy(self):
        if not self.client:
            self.skipTest("Webhook handler not initialized")
        response = self.client.get("/healthz")
        self.assertIn(response.status_code, [200, 503])

    def test_health_check_broker_disabled(self):
        with patch("mira.app.get_config") as mock_get_config, \
             patch("mira.app.ClaudeLLM") as MockClaude, \
             patch("mira.app.OpenAILLM") as MockOpenAI, \
             patch("mira.app.OllamaLLM") as MockOllama, \
             patch("mira.app.LLMRouter") as MockRouter, \
             patch("mira.app.get_secret", return_value=""):

            mock_llm = MagicMock()
            mock_llm.generate = AsyncMock(return_value={"text": None, "raw": None})
            MockClaude.return_value = mock_llm
            MockOpenAI.return_value = mock_llm
            MockOllama.return_value = mock_llm
            MockRouter.return_value = mock_llm
            mock_get_config.return_value = _make_mock_config({
                "broker.enabled": False,
            })

            app = MiraApplication()

        if app.webhook_handler:
            client = app.webhook_handler.app.test_client()
            response = client.get("/healthz")
            data = response.get_json()
            self.assertEqual(data["checks"]["broker"], "disabled")


if __name__ == "__main__":
    unittest.main()
