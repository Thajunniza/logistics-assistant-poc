"""Agent output schemas — typed contracts each agent produces."""
from __future__ import annotations

from typing import Literal, List
from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]


## AGENT 1 : Logistics Issue Resolution Agent
class BusinessImpact(BaseModel):
    customers_at_risk: int
    sla_exposure_usd: float
    predicted_delay_days: int
    revenue_at_risk_usd: float

class LogisticsIssueResolutionOutput(BaseModel):
    risk_title: str = Field(description="One-line risk title, ~10 words")
    severity: Severity
    summary: str = Field(description="2-3 sentence briefing for the Supply Chain Head")
    root_causes: List[str] = Field(description="Primary and secondary causes (prefix PRIMARY:/CONTRIB: recommended)")
    business_impact: BusinessImpact
    evidence: List[str] = Field(description="Concrete evidence points from the data")
    affected_order: str = Field(description="Shipment PO number")


## AGENT 2 : Pattern Forecast Agent
from typing import Literal
from pydantic import BaseModel, Field


PatternClassification = Literal["one-off", "recurring", "systemic"]
ConfidenceLevel = Literal["low", "medium", "high"]
ResponsePosture = Literal["tactical", "structural", "hybrid"]


class PatternForecastOutput(BaseModel):
    classification: PatternClassification = Field(
        description="Is this disruption isolated, recurring, or systemic?"
    )

    expected_duration_days: int = Field(
        description="Forecasted duration combining reported event duration and historical recovery"
    )

    confidence: ConfidenceLevel = Field(
        description="Confidence in the classification based on historical evidence"
    )

    pattern_narrative: str = Field(
        description="2–3 sentence explanation of the historical pattern and what to expect"
    )

    recommendation: ResponsePosture = Field(
        description="Recommended response posture: tactical, structural, or hybrid"
    )

    rationale: str = Field(
        description="Short justification explaining why this recommendation fits the pattern"
    )