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


from typing import Literal, List
from pydantic import BaseModel, Field


# ----------------------------
# Agent 3 — Inventory Supervisor
# ----------------------------

OptionID = Literal["OPT-A", "OPT-B", "OPT-C"]
Approach = Literal[
    "internal_transfer",
    "alternate_supplier",
    "expedited_freight",
    "hybrid",
    "partial_fulfilment",
    "structural_follow_up",
]
Complexity = Literal["low", "medium", "high"]


class MitigationOption(BaseModel):
    """
    One mitigation option card shown to the Supply Chain Head.
    Agent 3 must return exactly three of these (OPT-A/B/C).
    """

    option_id: OptionID = Field(description="Must be one of OPT-A, OPT-B, OPT-C")
    title: str = Field(description="Short descriptive title (e.g., 'Rotterdam stock transfer to cover Helios')")
    approach: Approach = Field(description="Category of mitigation approach")

    description: str = Field(description="1–2 sentences describing what this option does")

    cost_delta_usd: float = Field(description="Incremental cost vs current plan (use realistic values)")
    sla_recovery_days: int = Field(description="Days until impacted customers are served under this option")

    complexity: Complexity = Field(description="How hard this is to execute operationally")
    customer_impact: str = Field(description="Specific customer impact wording (mention Helios/Triton etc.)")
    trade_off: str = Field(description="One honest sentence describing what this option sacrifices")

    # Architecturally important: Agent 3 NEVER chooses the recommendation.
    recommended: bool = Field(default=False, description="Always false. Orchestrator selects recommendation later.")


class InventorySupervisorOutput(BaseModel):
    """
    Agent 3 output: exactly three options with quantified trade-offs.
    No recommendation is made here.
    """

    options: List[MitigationOption] = Field(description="Exactly three options: OPT-A, OPT-B, OPT-C")
    notes: str = Field(description="1–2 sentence guidance for the Supply Chain Head")
    evidence: List[str] = Field(description="3–5 concrete, data-grounded evidence points (inventory/supplier/commitments)")