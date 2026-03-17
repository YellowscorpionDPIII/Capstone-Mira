"""Base agent class for all Mira agents."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Type

import logging

from mira.llm.base import BaseLLM


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Mira platform.

    Subclasses must implement ``build_user_prompt`` and may override
    ``output_schema`` and ``postprocess``.
    """

    def __init__(
        self,
        llm: Optional[BaseLLM],
        name: str,
        system_prompt: str = "",
    ) -> None:
        self.llm = llm
        self.name = name
        self.agent_id = name          # kept for backwards-compat with broker/registry
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f"mira.agent.{name}")
        self.created_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Public async contract
    # ------------------------------------------------------------------

    async def process(self, task: Dict[str, Any], complexity: str = "auto") -> Dict[str, Any]:
        """
        Process a task dict and return a result dict.

        Args:
            task:       Message/task dictionary (must contain at least 'type' and 'data').
            complexity: Routing hint forwarded to the LLM router.

        Returns:
            Result dict produced by ``postprocess``.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": self.build_user_prompt(task)},
        ]
        if self.llm is None:
            raise RuntimeError(
                f"Agent '{self.name}' has no LLM configured. "
                "Override process() or pass an LLM at construction time."
            )
        resp = await self.llm.generate(
            messages,
            schema=self.output_schema(),
            complexity=complexity,
        )
        return self.postprocess(resp["text"], raw=resp["raw"])

    @abstractmethod
    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        """Build the user-facing prompt from the task dict."""

    def output_schema(self) -> Optional[Type]:
        """Return the Pydantic model class for structured output, or None."""
        return None

    def postprocess(self, parsed: Any, raw: Any) -> Dict[str, Any]:
        """Convert the parsed LLM response into the final result dict."""
        return {"agent": self.name, "result": parsed, "raw": raw}

    # ------------------------------------------------------------------
    # Utility helpers (kept from original BaseAgent)
    # ------------------------------------------------------------------

    def validate_message(self, message: Dict[str, Any]) -> bool:
        """Return True if the message contains required 'type' and 'data' fields."""
        return all(field in message for field in ("type", "data"))

    def create_response(
        self,
        status: str,
        data: Any,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standardised synchronous response dict."""
        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "data": data,
            "error": error,
        }
