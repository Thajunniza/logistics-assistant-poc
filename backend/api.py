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