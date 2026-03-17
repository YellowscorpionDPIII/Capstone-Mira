"""LLM routing logic for Mira – selects the right backend per request."""
import logging
import re
from typing import Any, Dict, List, Literal, Optional, Type

from mira.llm.base import BaseLLM

logger = logging.getLogger("mira.llm.router")

# Valid complexity values accepted by the router.
Complexity = Literal["auto", "low", "high", "force-claude"]

# Character threshold above which a request is considered 'long' and routed to
# Claude. 1500 chars ≈ ~375 tokens, enough to distinguish simple Q&A from
# longer reasoning tasks. Configurable via settings.
_DEFAULT_LONG_THRESHOLD = 1500

# Regex that matches genuine code patterns (not just the word "defined").
# Anchored to word boundaries / line structure to avoid false positives.
_CODE_PATTERN = re.compile(
    r"(^|\s)(def |class |import |from \S+ import |```python|```js)",
    re.MULTILINE,
)


class LLMRouter(BaseLLM):
    """
    Routes LLM calls to Claude, a cheap cloud model, or a local model
    based on complexity, token count, and offline preference.
    """

    def __init__(
        self,
        claude_llm: BaseLLM,
        cheap_llm: BaseLLM,
        local_llm: Optional[BaseLLM] = None,
        long_threshold: int = _DEFAULT_LONG_THRESHOLD,
    ) -> None:
        self.claude_llm = claude_llm
        self.cheap_llm = cheap_llm
        self.local_llm = local_llm
        self.long_threshold = long_threshold

    def _select_backend(
        self,
        messages: List[Dict[str, str]],
        complexity: str,
        offline_ok: bool,
    ) -> BaseLLM:
        """Choose which LLM backend to use and log the decision."""
        if offline_ok:
            if self.local_llm is None:
                raise ValueError(
                    "offline_ok=True but no local_llm was configured in LLMRouter."
                )
            logger.info("Routing to local LLM (offline_ok=True).")
            return self.local_llm

        if complexity not in ("auto", "low", "high", "force-claude"):
            logger.warning(
                "Unknown complexity value %r; falling back to 'auto'.", complexity
            )
            complexity = "auto"

        if complexity == "force-claude":
            logger.info("Routing to Claude (complexity=force-claude).")
            return self.claude_llm

        total_chars = sum(len(m.get("content", "")) for m in messages)
        if complexity == "high" or total_chars > self.long_threshold:
            logger.info(
                "Routing to Claude (complexity=%r, chars=%d, threshold=%d).",
                complexity, total_chars, self.long_threshold,
            )
            return self.claude_llm

        # Route code-heavy requests to Claude using a precise regex.
        combined = "\n".join(m.get("content", "") for m in messages)
        if _CODE_PATTERN.search(combined):
            logger.info("Routing to Claude (code content detected).")
            return self.claude_llm

        logger.info(
            "Routing to cheap LLM (complexity=%r, chars=%d).", complexity, total_chars
        )
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
