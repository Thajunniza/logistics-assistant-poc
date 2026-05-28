"""
FastAPI backend for the Logistics Assistant POC.

This service exposes:
- deterministic risk detection (no LLM) via /risk-check
- agentic diagnosis (LLM) via /diagnosis

In the POC, these endpoints are triggered manually from the Streamlit UI.
In production, the same endpoints could be triggered by a scheduler or Joule/A2A.

Key design principles:
- UI is thin
- All business logic stays in the backend
- Data access goes only through the BDC facade
"""

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Deterministic risk detection logic
from backend.polling.risk_detector import run_risk_check, DetectedRisk

# Agentic diagnosis (Issue Resolution Agent)
from ai.agents.logistics_issue_resolution import run as run_issue_resolution
from ai.agents.schemas import LogisticsIssueResolutionOutput

# Agentic Pattern recognition (Pattern Forecast Agent)
from ai.agents.pattern_forecast import run as run_pattern_forecast
from ai.agents.schemas import PatternForecastOutput, LogisticsIssueResolutionOutput

# Agentic Option generation (Inventory Supervisor Agent)  
from ai.agents.inventory_supervisor import run as run_inventory_supervisor
from ai.agents.schemas import InventorySupervisorOutput

# Agentic Final Action generation (Transport Dispatching Agent)  
from ai.agents.transport_dispatcher import run as run_transport_dispatching
from ai.agents.schemas import TransportDispatchPlanOutput, InventorySupervisorOutput, PatternForecastOutput, LogisticsIssueResolutionOutput

from fastapi import HTTPException

import json
from typing import Any, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter
from ai.llm import call_llm

# -----------------------------------------------------------------------------
# FastAPI application
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Logistics Assistant POC API",
    description="Backend API for risk detection and decision support",
    version="0.2.0",
)

# -----------------------------------------------------------------------------
# CORS configuration (POC ONLY)
# -----------------------------------------------------------------------------
# Streamlit calls backend via Python requests (CORS not strictly required),
# but keeping this is fine for future browser-based calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # POC only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Request schemas
# -----------------------------------------------------------------------------
class DiagnosisRequest(BaseModel):
    po_number: str
    triggering_event_id: str


class PatternForecastRequest(BaseModel):
    po_number: str
    triggering_event_id: str

class InventoryOptionsRequest(BaseModel):
    po_number: str
    triggering_event_id: str

class DispatchPlanRequest(BaseModel):
    po_number: str
    triggering_event_id: str
    approved_option_id: str  # "OPT-A" / "OPT-B" / "OPT-C"


class RiskQnARequest(BaseModel):
    question: str = Field(min_length=3)
    context: Dict[str, Any]


class RiskQnAResponse(BaseModel):
    answer: str




# -----------------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    """Simple health endpoint for sanity checks."""
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Risk detection endpoint (deterministic)
# -----------------------------------------------------------------------------
@app.post("/risk-check", response_model=List[DetectedRisk])
def risk_check():
    """
    Run one risk-detection pass and return detected risks.

    This endpoint:
    - calls run_risk_check()
    - returns decision-ready risk objects
    - performs no scheduling (manual trigger in POC)
    """
    now = datetime.now(timezone.utc)
    return run_risk_check(now)


# -----------------------------------------------------------------------------
# Diagnosis endpoint (agentic)
# -----------------------------------------------------------------------------
@app.post("/diagnosis", response_model=LogisticsIssueResolutionOutput)
def diagnosis(req: DiagnosisRequest):
    """
    Run the Logistics Issue Resolution Agent for a selected risk.

    Input:
    - po_number
    - triggering_event_id

    Output:
    - typed LogisticsIssueResolutionOutput (validated by Pydantic)
    """
    return run_issue_resolution(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
    )

# -----------------------------------------------------------------------------
# Pattern recognition endpoint (agentic)
# -----------------------------------------------------------------------------
@app.post("/pattern-forecast", response_model=PatternForecastOutput)
def pattern_forecast(req: PatternForecastRequest):
    """
    Run Pattern Forecast Agent (Agent 2).

    For now, we call Agent 1 internally to get diagnosis (simple POC wiring).
    Later, orchestrator will pass diagnosis directly.
    """
    diagnosis: LogisticsIssueResolutionOutput = run_issue_resolution(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
    )
    return run_pattern_forecast(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
        diagnosis=diagnosis,
    )

# -----------------------------------------------------------------------------
# Solution Option endpoint (agentic)
# -----------------------------------------------------------------------------
@app.post("/inventory-options", response_model=InventorySupervisorOutput)
def inventory_options(req: InventoryOptionsRequest):
    """
    Generate mitigation options (Agent 3).
    This endpoint is recommendation-only.
    """

    # Agent 1
    diagnosis = run_issue_resolution(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
    )

    # Agent 2
    forecast = run_pattern_forecast(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
        diagnosis=diagnosis,
    )

    # Agent 3
    return run_inventory_supervisor(
        po_number=req.po_number,
        diagnosis=diagnosis,
        pattern_forecast=forecast,
    )

# -----------------------------------------------------------------------------
# Transport Dispatching endpoint (agentic)
# -----------------------------------------------------------------------------
@app.post("/dispatch-plan", response_model=TransportDispatchPlanOutput)
def dispatch_plan(req: DispatchPlanRequest):
    """
    Agent 4 (Transport Dispatching) — simulated execution plan only.

    Input:
    - po_number
    - triggering_event_id
    - approved_option_id (OPT-A/B/C)

    Output:
    - TransportDispatchPlanOutput (ordered steps + notifications + completion ETA)
    """

    # Agent 1: diagnosis
    diagnosis: LogisticsIssueResolutionOutput = run_issue_resolution(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
    )

    # Agent 2: pattern forecast
    forecast: PatternForecastOutput = run_pattern_forecast(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
        diagnosis=diagnosis,
    )

    # Agent 3: inventory options (to retrieve the full approved option object)
    inventory_output: InventorySupervisorOutput = run_inventory_supervisor(
        po_number=req.po_number,
        diagnosis=diagnosis,
        pattern_forecast=forecast,
    )

    # Agent 4: dispatch plan (simulated, approval-gated)
    return run_transport_dispatching(
        po_number=req.po_number,
        triggering_event_id=req.triggering_event_id,
        approved_option_id=req.approved_option_id,
        diagnosis=diagnosis,
        pattern_forecast=forecast,
        inventory_output=inventory_output,
    )


RISK_QNA_SYSTEM_PROMPT = """\
You are a Supply Chain Decision Assistant.

You are answering a follow-up question from the Supply Chain Head about a specific disruption.

You are given structured context (diagnosis, forecast, mitigation options, commitments, and possibly dispatch plan).

STRICT RULES:
- Use ONLY the provided context.
- If the context does not contain an answer, say so explicitly.
- Do NOT approve actions.
- Do NOT execute actions.
- Do NOT suggest running SAP systems.
- If the question is a 'what if', explain implications using existing numbers/trade-offs only.

Return ONLY plain text in the 'answer' field.
Limit to 4–8 sentences.
"""


@app.post("/risk-qna", response_model=RiskQnAResponse)
def risk_qna(req: RiskQnARequest):
    # Basic validation guard: context must be dict
    if not isinstance(req.context, dict):
        raise HTTPException(status_code=400, detail="context must be a JSON object")

    user_message = (
        "CONTEXT (JSON):\n"
        f"{json.dumps(req.context, indent=2, default=str)}\n\n"
        f"QUESTION:\n{req.question}\n"
    )

    # We validate output using a tiny schema for stability
    result = call_llm(
        system_prompt=RISK_QNA_SYSTEM_PROMPT,
        user_message=user_message,
        response_model=RiskQnAResponse,
        temperature=0.2,
        max_tokens=450,
    )

    return result

