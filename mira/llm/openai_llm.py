"""OpenAI LLM backend for Mira."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError

from mira.llm.base import BaseLLM

logger = logging.getLogger("mira.llm.openai")

_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class OpenAILLM(BaseLLM):
    """LLM backend that calls OpenAI via the AsyncOpenAI client."""

    def __init__(self, api_key: str, model: str = "gpt-4.1-mini") -> None:
        self.model = model or "gpt-4.1-mini"
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        schema: Optional[Type] = None,
        complexity: str = "auto",
        offline_ok: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if schema is not None:
            return await self._generate_structured(messages, schema)
        return await self._call_with_retry(
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            ),
            context="plain text generation",
        )

    async def _generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type,
    ) -> Dict[str, Any]:
        return await self._call_with_retry(
            lambda: self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=schema,
            ),
            context="structured generation",
            structured=True,
        )

    async def _call_with_retry(
        self, api_fn, context: str = "", structured: bool = False
    ) -> Dict[str, Any]:
        """Call an API coroutine with exponential backoff retry on transient errors."""
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(_MAX_RETRIES):
            try:
                completion = await api_fn()
                if structured:
                    parsed = completion.choices[0].message.parsed
                    return {"text": parsed, "raw": completion}
                text = completion.choices[0].message.content
                return {"text": text, "raw": completion}
            except RateLimitError as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "OpenAI rate limit hit (%s), attempt %d/%d. Retrying in %.1fs.",
                    context, attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except APIConnectionError as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "OpenAI connection error (%s), attempt %d/%d. Retrying in %.1fs.",
                    context, attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "OpenAI server error %d (%s), attempt %d/%d. Retrying in %.1fs.",
                        exc.status_code, context, attempt + 1, _MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("OpenAI API error %d (%s): %s", exc.status_code, context, exc)
                    raise
        logger.error("OpenAI API failed after %d attempts (%s): %s", _MAX_RETRIES, context, last_exc)
        raise last_exc
