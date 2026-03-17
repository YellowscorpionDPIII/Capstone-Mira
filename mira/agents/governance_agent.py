"""GovernanceAgent – assesses governance risk and HITL requirements via LLM."""
import json
import os
from typing import Any, Dict, Optional, Type

import yaml

from mira.core.base_agent import BaseAgent
from mira.llm.base import BaseLLM
from mira.llm.schemas import GovernanceAssessmentOutput

# Constants for compliance level mapping defaults
DEFAULT_COMPLIANCE_VALUE = 0
DEFAULT_THRESHOLD_VALUE = 2


def _load_thresholds_from_yaml() -> Dict[str, Any]:
    """Load governance thresholds from YAML configuration file."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    config_path = os.path.join(repo_root, "config", "governance_config.yaml")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
                if data and "thresholds" in data:
                    return data["thresholds"]
    except Exception:
        pass
    return {}


def _build_governance_system_prompt(thresholds: Dict[str, Any]) -> str:
    financial = thresholds.get("financial_threshold", 10000)
    compliance = thresholds.get("compliance_threshold", "medium")
    explainability = thresholds.get("explainability_threshold", 0.7)
    return (
        "You are a governance and compliance expert for AI-driven workflows.\n"
        "Assess the risk level of the provided workflow and determine whether "
        "human validation is required based on these thresholds:\n"
        f"  - Financial impact threshold: ${financial:,}\n"
        f"  - Compliance threshold: {compliance}\n"
        f"  - Explainability score threshold: {explainability}\n"
        "Return a structured governance assessment."
    )


class GovernanceAgent(BaseAgent):
    """Agent responsible for governance assessment and HITL determination."""

    def __init__(self, llm: BaseLLM) -> None:
        thresholds = _load_thresholds_from_yaml()

        self.financial_threshold = thresholds.get("financial_threshold", 10000)
        self.compliance_threshold = thresholds.get("compliance_threshold", "medium")
        self.explainability_threshold = thresholds.get("explainability_threshold", 0.7)
        self.compliance_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        system_prompt = _build_governance_system_prompt(thresholds)
        super().__init__(llm, "governance_agent", system_prompt)

    def build_user_prompt(self, task: Dict[str, Any]) -> str:
        data = task.get("data", {})
        financial_impact = data.get("financial_impact", 0)
        compliance_level = data.get("compliance_level", "low")
        explainability_score = data.get("explainability_score", 1.0)
        return (
            f"Workflow data:\n{json.dumps(data, indent=2)}\n\n"
            f"Key metrics:\n"
            f"  - Financial impact: ${financial_impact:,}\n"
            f"  - Compliance level: {compliance_level}\n"
            f"  - Explainability score: {explainability_score}\n\n"
            "Assess governance risk and whether human validation is required."
        )

    def output_schema(self) -> Optional[Type]:
        return GovernanceAssessmentOutput

    def update_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """Update governance thresholds and regenerate the system prompt."""
        if "financial_threshold" in thresholds:
            self.financial_threshold = thresholds["financial_threshold"]
        if "compliance_threshold" in thresholds:
            self.compliance_threshold = thresholds["compliance_threshold"]
        if "explainability_threshold" in thresholds:
            self.explainability_threshold = thresholds["explainability_threshold"]

        merged = {
            "financial_threshold": self.financial_threshold,
            "compliance_threshold": self.compliance_threshold,
            "explainability_threshold": self.explainability_threshold,
        }
        self.system_prompt = _build_governance_system_prompt(merged)
        self.logger.info("Updated governance thresholds and system prompt.")
