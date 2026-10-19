"""RiskAssessmentAgent – identifies and assesses project risks via LLM."""
import json
from typing import Any, Dict, Optional, Type

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM
from mira.llm.schemas import RiskAssessmentOutput


SYSTEM_PROMPT = (
    "You are a risk management expert. Analyse a project plan and identify "
    "all significant risks, their severity, probability, impact score, and "
    "concrete mitigation strategies."
)


class RiskAssessmentAgent(BaseAgent):
    """Agent responsible for LLM-backed risk assessment."""

    def __init__(self, llm: BaseLLM) -> None:
        super().__init__(llm, "risk_assessment_agent", SYSTEM_PROMPT)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        data = task.get("data", {})
        return (
            "Analyse the following project plan for risks:\n"
            f"{json.dumps(data, indent=2)}"
        )

    def output_schema(self) -> Optional[Type]:
        return RiskAssessmentOutput
