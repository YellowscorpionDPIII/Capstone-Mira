"""StatusReporterAgent – generates weekly status reports via LLM."""
import json
from typing import Any, Dict, Optional, Type

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM
from mira.llm.schemas import StatusReport


SYSTEM_PROMPT = (
    "You are a technical program manager. Given a project plan and current "
    "task list, produce a concise weekly status report that summarises "
    "accomplishments, blockers, upcoming milestones, and risk highlights."
)


class StatusReporterAgent(BaseAgent):
    """Agent responsible for LLM-backed weekly status reports."""

    def __init__(self, llm: BaseLLM) -> None:
        super().__init__(llm, "status_reporter_agent", SYSTEM_PROMPT)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        data = task.get("data", {})
        return (
            "Generate a status report for the following project data:\n"
            f"{json.dumps(data, indent=2)}"
        )

    def output_schema(self) -> Optional[Type]:
        return StatusReport
