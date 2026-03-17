"""Ollama (local) LLM backend for Mira."""
import json
from typing import Any, Dict, List, Optional, Type

import httpx

from mira.llm.base import BaseLLM


class OllamaLLM(BaseLLM):
    """LLM backend that calls a locally running Ollama server."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model or "llama3.1"
        self.base_url = base_url.rstrip("/")

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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["message"]["content"]

        if schema is not None:
            parsed = schema(**json.loads(content))
            return {"text": parsed, "raw": data}

        return {"text": content, "raw": data}
