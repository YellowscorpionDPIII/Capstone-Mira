"""Ollama (local) LLM backend for Mira."""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type

import httpx

from mira.llm.base import BaseLLM

logger = logging.getLogger("mira.llm.ollama")

# Default timeout in seconds – can be overridden at construction time.
DEFAULT_TIMEOUT = 120.0
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class OllamaLLM(BaseLLM):
    """LLM backend that calls a locally running Ollama server."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.model = model or "llama3.1"
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generate(
        self,
        messages: List[Dict[str, str]],
        schema: Optional[Type] = None,
        complexity: str = "auto",
        offline_ok: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if schema is not None:
            payload["format"] = "json"

        return await self._call_with_retry(payload, schema)

    async def _call_with_retry(
        self, payload: Dict[str, Any], schema: Optional[Type]
    ) -> Dict[str, Any]:
        """POST to Ollama with exponential backoff retry on transient errors."""
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data.get("message", {}).get("content")
                if content is None:
                    raise ValueError(
                        f"Ollama response missing 'message.content'. "
                        f"Keys present: {list(data.keys())}"
                    )

                if schema is not None:
                    try:
                        parsed = schema(**json.loads(content))
                    except (json.JSONDecodeError, ValueError) as exc:
                        raise ValueError(
                            f"Ollama returned content that could not be parsed as "
                            f"{schema.__name__}: {exc}. Raw content: {content!r}"
                        ) from exc
                    return {"text": parsed, "raw": data}

                return {"text": content, "raw": data}

            except httpx.TimeoutException as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Ollama request timed out, attempt %d/%d. Retrying in %.1fs.",
                    attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except httpx.ConnectError as exc:
                last_exc = exc
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Ollama connection error, attempt %d/%d. Retrying in %.1fs.",
                    attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_exc = exc
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Ollama server error %d, attempt %d/%d. Retrying in %.1fs.",
                        exc.response.status_code, attempt + 1, _MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Ollama HTTP error %d: %s", exc.response.status_code, exc)
                    raise

        logger.error("Ollama failed after %d attempts: %s", _MAX_RETRIES, last_exc)
        raise last_exc
