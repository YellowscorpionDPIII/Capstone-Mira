"""RoadmappingAgent – generates AI roadmaps and KPI projections via LLM."""
import json
from typing import Any, Dict, Optional, Type

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM
from mira.llm.schemas import RoadmapOutput


SYSTEM_PROMPT = (
    "You are a strategic AI transformation consultant. Given a set of "
    "business objectives and KPI context, produce a prioritised AI roadmap "
    "with concrete initiatives, EBIT impact projections in USD, timelines, "
    "and measurable KPIs for each initiative."
)


class RoadmappingAgent(BaseAgent):
    """Agent responsible for LLM-backed AI roadmap generation."""

    def __init__(self, llm: BaseLLM) -> None:
        super().__init__(llm, "roadmapping_agent", SYSTEM_PROMPT)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        data = task.get("data", {})
        objectives = data.get("business_objectives", [])
        kpi_context = data.get("kpi_context", {})
        objectives_str = "\n".join(f"- {o}" for o in objectives) if objectives else "- (none specified)"
        prompt = (
            f"Business objectives:\n{objectives_str}\n"
        )
        if kpi_context:
            prompt += f"\nKPI context:\n{json.dumps(kpi_context, indent=2)}\n"
        prompt += "\nPlease produce a complete AI roadmap with prioritised initiatives."
        return prompt

    def output_schema(self) -> Optional[Type]:
        return RoadmapOutput
