"""Anthropic (Claude) LLM backend for Mira."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from anthropic import AsyncAnthropic, APIConnectionError, APIStatusError, RateLimitError
from pydantic import BaseModel

from mira.llm.base import BaseLLM

logger = logging.getLogger("mira.llm.anthropic")

# Default max tokens – exposed as a constant so callers can override via kwargs.
DEFAULT_MAX_TOKENS = 4096
# Retry configuration for transient API failures.
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class ClaudeLLM(BaseLLM):
    """LLM backend that calls Anthropic Claude via the AsyncAnthropic client."""

    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-latest") -> None:
        self.model = model or "claude-3-7-sonnet-latest"
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        schema: Optional[Type] = None,
        complexity: str = "auto",
        offline_ok: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Anthropic requires system prompt as a top-level parameter, not a message role.
        system_content = ""
        user_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)

        if schema is not None:
            if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
                raise TypeError(
                    f"schema must be a Pydantic BaseModel subclass, got {schema!r}"
                )
            return await self._generate_structured(system_content, user_messages, schema, **kwargs)

        return await self._call_with_retry(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
                system=system_content,
                messages=user_messages,
            ),
            context="plain text generation",
        )

    async def _generate_structured(
        self,
        system: str,
        messages: List[Dict[str, str]],
        schema: Type,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Use Anthropic tool-calling to return structured output."""
        json_schema = schema.model_json_schema()
        tool_definition = {
            "name": "output",
            "description": "Return the structured output.",
            "input_schema": json_schema,
        }

        response = await self._call_with_retry(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
                system=system,
                messages=messages,
                tools=[tool_definition],
                tool_choice={"type": "tool", "name": "output"},
            ),
            context="structured generation",
            raw=True,
        )

        # Extract the tool_use block – do not fall back silently.
        for block in response.content:
            if block.type == "tool_use" and block.name == "output":
                parsed = schema(**block.input)
                logger.debug("Structured output parsed successfully via tool-use block.")
                return {"text": parsed, "raw": response}

        raise ValueError(
            "Claude did not return a tool-use block for structured output. "
            f"Response content types: {[b.type for b in response.content]}"
        )

    async def _call_with_retry(self, api_fn, context: str = "", raw: bool = False) -> Any:
        """Call an API coroutine with exponential backoff retry on transient errors."""
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(_MAX_RETRIES):
            try:
                response = await api_fn()
                if raw:
                    return response
                text = response.content[0].text
                return {"text": text, "raw": response}
            except RateLimitError as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Anthropic rate limit hit (%s), attempt %d/%d. Retrying in %.1fs.",
                    context, attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except APIConnectionError as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Anthropic connection error (%s), attempt %d/%d. Retrying in %.1fs.",
                    context, attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except APIStatusError as exc:
                # 5xx errors are retried; 4xx (except 429) are not.
                if exc.status_code >= 500:
                    last_exc = exc
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Anthropic server error %d (%s), attempt %d/%d. Retrying in %.1fs.",
                        exc.status_code, context, attempt + 1, _MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Anthropic API error %d (%s): %s", exc.status_code, context, exc)
                    raise
        logger.error("Anthropic API failed after %d attempts (%s): %s", _MAX_RETRIES, context, last_exc)
        raise last_exc
