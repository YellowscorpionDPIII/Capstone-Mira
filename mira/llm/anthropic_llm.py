"""Anthropic (Claude) LLM backend for Mira."""
import json
from typing import Any, Dict, List, Optional, Type

from anthropic import AsyncAnthropic

from mira.llm.base import BaseLLM


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
            return await self._generate_structured(system_content, user_messages, schema)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_content,
            messages=user_messages,
        )
        text = response.content[0].text
        return {"text": text, "raw": response}

    async def _generate_structured(
        self,
        system: str,
        messages: List[Dict[str, str]],
        schema: Type,
    ) -> Dict[str, Any]:
        """Use Anthropic tool-calling to return structured output."""
        json_schema = schema.model_json_schema()

        tool_definition = {
            "name": "output",
            "description": "Return the structured output.",
            "input_schema": json_schema,
        }

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=[tool_definition],
            tool_choice={"type": "tool", "name": "output"},
        )

        # Extract the tool_use block
        for block in response.content:
            if block.type == "tool_use" and block.name == "output":
                parsed = schema(**block.input)
                return {"text": parsed, "raw": response}

        # Fallback: attempt JSON parse from text content
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
                break
        parsed = schema(**json.loads(text))
        return {"text": parsed, "raw": response}
