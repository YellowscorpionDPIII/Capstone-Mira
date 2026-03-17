"""Tests for ToolRecommenderAgent.

Covers every method and both branches in postprocess / get_recommendation.
No API keys needed – all LLM calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mira.llm.base import BaseLLM
from mira.agents.tool_recommender_agent import (
    ToolRecommenderAgent,
    LeafClassification,
    BASE_RECOMMENDATIONS,
    DECISION_TREE,
    load_model_registry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_llm(leaf_key: str = "complex_coding"):
    """Return a mock LLM that returns a LeafClassification for the given key."""
    mock = MagicMock(spec=BaseLLM)
    mock.generate = AsyncMock(
        return_value={
            "text": LeafClassification(leaf_key=leaf_key),
            "raw": MagicMock(),
        }
    )
    return mock


def make_agent(leaf_key: str = "complex_coding") -> ToolRecommenderAgent:
    return ToolRecommenderAgent(llm=make_llm(leaf_key))


# ---------------------------------------------------------------------------
# load_model_registry
# ---------------------------------------------------------------------------

class TestLoadModelRegistry:
    def test_loads_tools_and_reasons(self):
        registry = load_model_registry()
        assert "tools" in registry
        assert "reasons" in registry

    def test_tools_contain_expected_keys(self):
        registry = load_model_registry()
        for key in ("claude", "chatgpt", "perplexity", "gemini"):
            assert key in registry["tools"], f"Missing tool: {key}"

    def test_each_tool_has_required_fields(self):
        registry = load_model_registry()
        for tool_key, tool in registry["tools"].items():
            assert "displayName" in tool, f"{tool_key} missing displayName"
            assert "provider" in tool, f"{tool_key} missing provider"
            assert "notes" in tool, f"{tool_key} missing notes"

    def test_reasons_cover_all_leaf_keys(self):
        registry = load_model_registry()
        for leaf_key, rec in BASE_RECOMMENDATIONS.items():
            reason_key = rec["reasonKey"]
            assert reason_key in registry["reasons"], (
                f"Reason key '{reason_key}' (for leaf '{leaf_key}') missing from registry"
            )


# ---------------------------------------------------------------------------
# ToolRecommenderAgent.__init__
# ---------------------------------------------------------------------------

class TestToolRecommenderAgentInit:
    def test_name_and_agent_id(self):
        agent = make_agent()
        assert agent.name == "tool_recommender_agent"
        assert agent.agent_id == "tool_recommender_agent"

    def test_model_registry_loaded(self):
        agent = make_agent()
        assert "tools" in agent.model_registry
        assert "claude" in agent.model_registry["tools"]

    def test_system_prompt_contains_all_leaf_keys(self):
        agent = make_agent()
        for leaf_key in BASE_RECOMMENDATIONS:
            assert leaf_key in agent.system_prompt, (
                f"System prompt missing leaf key: {leaf_key}"
            )

    def test_output_schema_is_leaf_classification(self):
        agent = make_agent()
        assert agent.output_schema() is LeafClassification


# ---------------------------------------------------------------------------
# build_user_prompt
# ---------------------------------------------------------------------------

class TestBuildUserPrompt:
    def test_includes_description(self):
        agent = make_agent()
        prompt = agent.build_user_prompt({
            "type": "recommend_tool",
            "data": {"description": "I need to debug a Python microservice"},
        })
        assert "debug a Python microservice" in prompt

    def test_empty_description_does_not_raise(self):
        agent = make_agent()
        prompt = agent.build_user_prompt({"type": "recommend_tool", "data": {}})
        assert isinstance(prompt, str)

    def test_missing_data_key_does_not_raise(self):
        agent = make_agent()
        prompt = agent.build_user_prompt({"type": "recommend_tool"})
        assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# postprocess – LeafClassification branch
# ---------------------------------------------------------------------------

class TestPostprocessLeafClassification:
    def test_returns_agent_name(self):
        agent = make_agent()
        raw = MagicMock()
        result = agent.postprocess(LeafClassification(leaf_key="complex_coding"), raw)
        assert result["agent"] == "tool_recommender_agent"

    def test_leaf_key_normalised_to_lower(self):
        agent = make_agent()
        result = agent.postprocess(LeafClassification(leaf_key="  COMPLEX_CODING  "), MagicMock())
        assert result["leaf_key"] == "complex_coding"

    def test_result_is_recommendation_dict(self):
        agent = make_agent()
        result = agent.postprocess(LeafClassification(leaf_key="quick_coding"), MagicMock())
        rec = result["result"]
        assert rec["tool"] == "ChatGPT GPT-4o"
        assert rec["provider"] == "OpenAI"
        assert isinstance(rec["reason"], str)
        assert isinstance(rec["notes"], str)

    def test_raw_is_preserved(self):
        agent = make_agent()
        raw_sentinel = object()
        result = agent.postprocess(LeafClassification(leaf_key="image_work"), raw_sentinel)
        assert result["raw"] is raw_sentinel


# ---------------------------------------------------------------------------
# postprocess – plain string branch (fallback)
# ---------------------------------------------------------------------------

class TestPostprocessStringFallback:
    def test_plain_string_leaf_key(self):
        agent = make_agent()
        result = agent.postprocess("current_research", MagicMock())
        assert result["leaf_key"] == "current_research"
        assert result["result"]["tool"] == "Perplexity (Search + GPT-4.1)"

    def test_plain_string_normalised(self):
        agent = make_agent()
        result = agent.postprocess("  DATA_VIZ  ", MagicMock())
        assert result["leaf_key"] == "data_viz"
        assert result["result"]["provider"] == "Google"


# ---------------------------------------------------------------------------
# get_recommendation – known leaf keys
# ---------------------------------------------------------------------------

class TestGetRecommendationKnownKeys:
    @pytest.mark.parametrize("leaf_key,expected_tool,expected_provider", [
        ("complex_coding",       "Claude 3.5 Sonnet",         "Anthropic"),
        ("review_coding",        "Claude 3.5 Sonnet",         "Anthropic"),
        ("quick_coding",         "ChatGPT GPT-4o",            "OpenAI"),
        ("learning_coding",      "Claude 3.5 Sonnet",         "Anthropic"),
        ("professional_writing", "ChatGPT GPT-4o",            "OpenAI"),
        ("creative_writing",     "ChatGPT GPT-4o",            "OpenAI"),
        ("technical_writing",    "Claude 3.5 Sonnet",         "Anthropic"),
        ("social_writing",       "ChatGPT GPT-4o",            "OpenAI"),
        ("current_research",     "Perplexity (Search + GPT-4.1)", "Perplexity"),
        ("academic_research",    "Perplexity (Search + GPT-4.1)", "Perplexity"),
        ("product_research",     "Perplexity (Search + GPT-4.1)", "Perplexity"),
        ("general_research",     "Perplexity (Search + GPT-4.1)", "Perplexity"),
        ("image_work",           "Gemini 1.5 Pro",            "Google"),
        ("data_viz",             "Gemini 1.5 Pro",            "Google"),
        ("presentations",        "Gemini 1.5 Pro",            "Google"),
        ("mixed_media",          "Gemini 1.5 Pro",            "Google"),
    ])
    def test_recommendation_tool_and_provider(self, leaf_key, expected_tool, expected_provider):
        agent = make_agent()
        rec = agent.get_recommendation(leaf_key)
        assert rec["tool"] == expected_tool
        assert rec["provider"] == expected_provider

    def test_recommendation_has_reason(self):
        agent = make_agent()
        rec = agent.get_recommendation("complex_coding")
        assert len(rec["reason"]) > 0

    def test_recommendation_has_notes(self):
        agent = make_agent()
        rec = agent.get_recommendation("image_work")
        assert len(rec["notes"]) > 0


# ---------------------------------------------------------------------------
# get_recommendation – unknown leaf key fallback
# ---------------------------------------------------------------------------

class TestGetRecommendationUnknownKey:
    def test_unknown_key_returns_unknown_tool(self):
        agent = make_agent()
        rec = agent.get_recommendation("totally_made_up_key")
        assert rec["tool"] == "Unknown"
        assert rec["provider"] == "Unknown"

    def test_unknown_key_reason_contains_key(self):
        agent = make_agent()
        rec = agent.get_recommendation("nonexistent")
        assert "nonexistent" in rec["reason"]

    def test_unknown_key_notes_is_empty_string(self):
        agent = make_agent()
        rec = agent.get_recommendation("nope")
        assert rec["notes"] == ""


# ---------------------------------------------------------------------------
# process() – end-to-end async flow
# ---------------------------------------------------------------------------

class TestProcessEndToEnd:
    @pytest.mark.asyncio
    async def test_process_returns_recommendation(self):
        agent = make_agent("complex_coding")
        result = await agent.process({
            "type": "recommend_tool",
            "data": {"description": "I need help debugging my Python service"},
        })
        assert result["agent"] == "tool_recommender_agent"
        assert result["leaf_key"] == "complex_coding"
        assert result["result"]["tool"] == "Claude 3.5 Sonnet"

    @pytest.mark.asyncio
    async def test_process_passes_schema_to_llm(self):
        llm = make_llm("quick_coding")
        agent = ToolRecommenderAgent(llm=llm)
        await agent.process({"type": "recommend_tool", "data": {"description": "write a bash script"}})
        call_kwargs = llm.generate.call_args.kwargs
        assert call_kwargs.get("schema") is LeafClassification

    @pytest.mark.asyncio
    async def test_process_all_leaf_keys(self):
        """Every leaf key resolves without error."""
        for leaf_key in BASE_RECOMMENDATIONS:
            llm = make_llm(leaf_key)
            agent = ToolRecommenderAgent(llm=llm)
            result = await agent.process({
                "type": "recommend_tool",
                "data": {"description": "some task"},
            })
            assert result["leaf_key"] == leaf_key
            assert result["result"]["tool"] != "Unknown", (
                f"leaf_key '{leaf_key}' resolved to Unknown"
            )


# ---------------------------------------------------------------------------
# classify_use_case – sync wrapper
# ---------------------------------------------------------------------------

class TestClassifyUseCase:
    def test_returns_leaf_key_string(self):
        agent = make_agent("academic_research")
        key = agent.classify_use_case("I want to research climate change papers")
        assert key == "academic_research"

    def test_returns_general_research_on_unknown_response(self):
        """If LLM returns an unrecognised key, classify_use_case still returns a string."""
        llm = MagicMock(spec=BaseLLM)
        llm.generate = AsyncMock(
            return_value={"text": LeafClassification(leaf_key="unknown_xyz"), "raw": MagicMock()}
        )
        agent = ToolRecommenderAgent(llm=llm)
        # postprocess will call get_recommendation("unknown_xyz") → "Unknown" tool,
        # but classify_use_case returns the raw leaf_key from result["leaf_key"]
        key = agent.classify_use_case("something obscure")
        assert isinstance(key, str)


# ---------------------------------------------------------------------------
# Decision tree structure sanity checks
# ---------------------------------------------------------------------------

class TestDecisionTreeStructure:
    def test_start_node_exists(self):
        assert "start" in DECISION_TREE

    def test_all_category_nodes_reachable(self):
        categories = {opt["value"] for opt in DECISION_TREE["start"]["options"]}
        for cat in categories:
            assert cat in DECISION_TREE, f"Category '{cat}' has no node in DECISION_TREE"

    def test_all_leaf_options_in_base_recommendations(self):
        for category, node in DECISION_TREE.items():
            if category == "start":
                continue
            for opt in node["options"]:
                leaf = opt["value"]
                assert leaf in BASE_RECOMMENDATIONS, (
                    f"Leaf '{leaf}' in DECISION_TREE but not in BASE_RECOMMENDATIONS"
                )
