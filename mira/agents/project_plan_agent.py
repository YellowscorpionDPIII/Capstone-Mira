"""ProjectPlanAgent – generates structured project plans via LLM."""
from typing import Any, Dict, Optional, Type

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM
from mira.llm.schemas import ProjectPlanOutput


SYSTEM_PROMPT = (
    "You are a project planning expert. Given a project name, goals, and "
    "duration in weeks, produce a structured project plan with concrete "
    "milestones and tasks."
)


class ProjectPlanAgent(BaseAgent):
    """Agent responsible for generating LLM-backed project plans."""

    def __init__(self, llm: BaseLLM) -> None:
        super().__init__(llm, "project_plan_agent", SYSTEM_PROMPT)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        data = task.get("data", {})
        name = data.get("name", "Unnamed Project")
        goals = data.get("goals", [])
        duration = data.get("duration_weeks", 12)
        goals_str = "\n".join(f"- {g}" for g in goals) if goals else "- (none specified)"
        return (
            f"Project name: {name}\n"
            f"Duration: {duration} weeks\n"
            f"Goals:\n{goals_str}\n\n"
            "Please produce a complete project plan with milestones and tasks."
        )

    def output_schema(self) -> Optional[Type]:
        return ProjectPlanOutput
