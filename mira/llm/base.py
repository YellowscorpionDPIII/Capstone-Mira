"""Base LLM interface for Mira."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type


class BaseLLM(ABC):
    """Abstract base class for all LLM backends."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        schema: Optional[Type] = None,
        complexity: str = "auto",
        offline_ok: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            schema: Optional Pydantic model class for structured output.
            complexity: Routing hint – 'low', 'high', or 'auto'.
            offline_ok: If True the router may use a local model.
            **kwargs: Backend-specific extra arguments.

        Returns:
            Dict with at minimum:
                'text'  – str (parsed structured object when schema given)
                'raw'   – the raw backend response object
        """
