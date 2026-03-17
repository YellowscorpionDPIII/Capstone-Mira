"""LLM routing logic for Mira – selects the right backend per request."""
from typing import Any, Dict, List, Optional, Type

from mira.llm.base import BaseLLM


class LLMRouter(BaseLLM):
    """
    Routes LLM calls to Claude, a cheap cloud model, or a local model
    based on complexity, token count, and offline preference.
    """

    # Character threshold above which a request is considered 'long'
    LONG_THRESHOLD = 1500

    def __init__(
        self,
        claude_llm: BaseLLM,
        cheap_llm: BaseLLM,
        local_llm: BaseLLM,
    ) -> None:
        self.claude_llm = claude_llm
        self.cheap_llm = cheap_llm
        self.local_llm = local_llm

    def _select_backend(
        self,
        messages: List[Dict[str, str]],
        complexity: str,
        offline_ok: bool,
    ) -> BaseLLM:
        """Choose which LLM backend to use."""
        if offline_ok:
            return self.local_llm

        total_chars = sum(len(m.get("content", "")) for m in messages)
        content_lower = " ".join(m.get("content", "") for m in messages).lower()

        if complexity == "force-claude":
            return self.claude_llm

        if complexity == "high" or total_chars > self.LONG_THRESHOLD:
            return self.claude_llm

        # Route code-heavy requests to Claude
        code_indicators = ["def ", "class ", "import ", "```python", "```js"]
        if any(ind in content_lower for ind in code_indicators):
            return self.claude_llm

        return self.cheap_llm

    async def generate(
        self,
        messages: List[Dict[str, str]],
        schema: Optional[Type] = None,
        complexity: str = "auto",
        offline_ok: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        backend = self._select_backend(messages, complexity, offline_ok)
        return await backend.generate(
            messages,
            schema=schema,
            complexity=complexity,
            offline_ok=offline_ok,
            **kwargs,
        )
