"""Agent output schemas — typed contracts each agent produces."""
from __future__ import annotations

from typing import Literal, List
from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]

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