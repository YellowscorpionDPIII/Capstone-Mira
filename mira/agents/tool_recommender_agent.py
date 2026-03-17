"""ToolRecommenderAgent – recommends the best AI tool for a user's task.

Uses an LLM to map a free-form user description to a leaf key in the
decision tree, then resolves the recommendation from the model registry.
"""
import json
import os
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM


# ---------------------------------------------------------------------------
# Decision tree and base recommendations
# (mirrors aiToolGuideConfig.ts so everything stays in one place)
# ---------------------------------------------------------------------------

DECISION_TREE: Dict[str, Any] = {
    "start": {
        "question": "What's your primary use case?",
        "options": [
            {"label": "Coding & Development",    "value": "coding"},
            {"label": "Writing & Content",        "value": "writing"},
            {"label": "Research & Information",   "value": "research"},
            {"label": "Creative & Multimodal",    "value": "multimodal"},
        ],
    },
    "coding": {
        "question": "What type of coding work?",
        "options": [
            {"label": "Complex problem-solving", "value": "complex_coding"},
            {"label": "Code review & debugging",  "value": "review_coding"},
            {"label": "Quick scripts & snippets", "value": "quick_coding"},
            {"label": "Learning to code",         "value": "learning_coding"},
        ],
    },
    "writing": {
        "question": "What type of writing?",
        "options": [
            {"label": "Professional / business", "value": "professional_writing"},
            {"label": "Creative / fiction",       "value": "creative_writing"},
            {"label": "Technical documentation", "value": "technical_writing"},
            {"label": "Social media",             "value": "social_writing"},
        ],
    },
    "research": {
        "question": "What type of research?",
        "options": [
            {"label": "Current events / news",   "value": "current_research"},
            {"label": "Academic / deep-dive",     "value": "academic_research"},
            {"label": "Product comparison",       "value": "product_research"},
            {"label": "General Q&A",              "value": "general_research"},
        ],
    },
    "multimodal": {
        "question": "What kind of multimodal work?",
        "options": [
            {"label": "Image analysis / editing", "value": "image_work"},
            {"label": "Data visualisation",        "value": "data_viz"},
            {"label": "Presentations",             "value": "presentations"},
            {"label": "Mixed media workflow",      "value": "mixed_media"},
        ],
    },
}

BASE_RECOMMENDATIONS: Dict[str, Dict[str, str]] = {
    "complex_coding":      {"toolKey": "claude",      "reasonKey": "complex_coding"},
    "review_coding":       {"toolKey": "claude",      "reasonKey": "review_coding"},
    "quick_coding":        {"toolKey": "chatgpt",     "reasonKey": "quick_coding"},
    "learning_coding":     {"toolKey": "claude",      "reasonKey": "learning_coding"},
    "professional_writing":{"toolKey": "chatgpt",     "reasonKey": "professional_writing"},
    "creative_writing":    {"toolKey": "chatgpt",     "reasonKey": "creative_writing"},
    "technical_writing":   {"toolKey": "claude",      "reasonKey": "technical_writing"},
    "social_writing":      {"toolKey": "chatgpt",     "reasonKey": "social_writing"},
    "current_research":    {"toolKey": "perplexity",  "reasonKey": "current_research"},
    "academic_research":   {"toolKey": "perplexity",  "reasonKey": "academic_research"},
    "product_research":    {"toolKey": "perplexity",  "reasonKey": "product_research"},
    "general_research":    {"toolKey": "perplexity",  "reasonKey": "general_research"},
    "image_work":          {"toolKey": "gemini",      "reasonKey": "image_work"},
    "data_viz":            {"toolKey": "gemini",      "reasonKey": "data_viz"},
    "presentations":       {"toolKey": "gemini",      "reasonKey": "presentations"},
    "mixed_media":         {"toolKey": "gemini",      "reasonKey": "mixed_media"},
}


# ---------------------------------------------------------------------------
# Pydantic schema for LLM classification output
# ---------------------------------------------------------------------------

class LeafClassification(BaseModel):
    leaf_key: str


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

def load_model_registry() -> Dict[str, Any]:
    """Load the model registry from the bundled JSON file."""
    registry_path = os.path.join(os.path.dirname(__file__), "..", "config", "modelRegistry.json")
    registry_path = os.path.abspath(registry_path)
    with open(registry_path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an AI tool selection expert. Given a user's description of their task, "
    "classify it into exactly one of the following leaf keys:\n"
    + "\n".join(f"  - {k}" for k in BASE_RECOMMENDATIONS)
    + "\n\nRespond only with the matching leaf key. No explanation needed."
)


class ToolRecommenderAgent(BaseAgent):
    """
    Recommends the best AI tool for a given user task description.

    Uses an LLM to classify the task into a leaf key, then resolves
    the recommendation from the model registry.
    """

    def __init__(self, llm: BaseLLM) -> None:
        super().__init__(llm, "tool_recommender_agent", SYSTEM_PROMPT)
        self.model_registry = load_model_registry()

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        description = task.get("data", {}).get("description", "")
        return f"User task description: {description}"

    def output_schema(self) -> Optional[Type]:
        return LeafClassification

    def postprocess(self, parsed: Any, raw: Any) -> Dict[str, Any]:
        if isinstance(parsed, LeafClassification):
            leaf_key = parsed.leaf_key.strip().lower()
        else:
            leaf_key = str(parsed).strip().lower()

        recommendation = self.get_recommendation(leaf_key)
        return {
            "agent": self.name,
            "leaf_key": leaf_key,
            "result": recommendation,
            "raw": raw,
        }

    # ------------------------------------------------------------------
    # Core recommendation logic
    # ------------------------------------------------------------------

    def classify_use_case(self, user_description: str) -> str:
        """
        Use the LLM to map a free-form description to a leaf key.

        This is the synchronous wrapper; the async path goes through
        ``process()``.  Useful for interactive / scripted usage.
        """
        import asyncio
        task = {"type": "recommend_tool", "data": {"description": user_description}}
        result = asyncio.run(self.process(task))
        return result.get("leaf_key", "general_research")

    def get_recommendation(self, leaf_key: str) -> Dict[str, Any]:
        """
        Resolve a leaf key to a full tool recommendation.

        Args:
            leaf_key: One of the keys in BASE_RECOMMENDATIONS.

        Returns:
            Dict with tool name, provider, reason, and notes.
        """
        rec_meta = BASE_RECOMMENDATIONS.get(leaf_key)
        if rec_meta is None:
            return {
                "tool": "Unknown",
                "provider": "Unknown",
                "reason": f"No recommendation found for leaf key: {leaf_key!r}",
                "notes": "",
            }

        tool_key = rec_meta["toolKey"]
        reason_key = rec_meta["reasonKey"]

        tool = self.model_registry["tools"].get(tool_key, {})
        reason = self.model_registry["reasons"].get(reason_key, "")

        return {
            "tool": tool.get("displayName", tool_key),
            "provider": tool.get("provider", ""),
            "reason": reason,
            "notes": tool.get("notes", ""),
        }
