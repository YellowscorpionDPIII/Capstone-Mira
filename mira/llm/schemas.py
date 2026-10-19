"""Pydantic v2 output schemas for all Mira agents."""
from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# ProjectPlanAgent schemas
# ---------------------------------------------------------------------------

class Task(BaseModel):
    name: str
    priority: Literal["low", "medium", "high"]
    estimated_hours: int


class Milestone(BaseModel):
    name: str
    description: str
    due_date: str
    tasks: List[Task]


class ProjectPlanOutput(BaseModel):
    project_name: str
    milestones: List[Milestone]
    total_duration_weeks: int


# ---------------------------------------------------------------------------
# RiskAssessmentAgent schemas
# ---------------------------------------------------------------------------

class Risk(BaseModel):
    category: str
    description: str
    severity: Literal["low", "medium", "high"]
    probability: Literal["low", "medium", "high"]
    mitigation: str
    impact_score: float


class RiskAssessmentOutput(BaseModel):
    project_id: str
    risks: List[Risk]
    overall_risk_score: float
    summary: str


# ---------------------------------------------------------------------------
# StatusReporterAgent schema
# ---------------------------------------------------------------------------

class StatusReport(BaseModel):
    week_ending: str
    completion_pct: float
    accomplished: List[str]
    blockers: List[str]
    upcoming_milestones: List[str]
    risks_summary: str


# ---------------------------------------------------------------------------
# GovernanceAgent schema
# ---------------------------------------------------------------------------

class GovernanceAssessmentOutput(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    requires_human_validation: bool
    reasons: List[str]
    recommended_actions: List[str]


# ---------------------------------------------------------------------------
# RoadmappingAgent schemas
# ---------------------------------------------------------------------------

class RoadmapInitiative(BaseModel):
    name: str
    objective: str
    priority: int
    ebit_impact_usd: float
    timeline_weeks: int
    kpis: List[str]


class RoadmapOutput(BaseModel):
    business_context: str
    initiatives: List[RoadmapInitiative]
    total_ebit_projection_usd: float
    generated_at: str
