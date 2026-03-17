"""OpenAI LLM backend for Mira."""
from typing import Any, Dict, List, Optional, Type

from openai import AsyncOpenAI

from mira.llm.base import BaseLLM


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

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        text = completion.choices[0].message.content
        return {"text": text, "raw": completion}

    async def _generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type,
    ) -> Dict[str, Any]:
        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        return {"text": parsed, "raw": completion}
