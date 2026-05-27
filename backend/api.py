"""
FastAPI backend for the Logistics Assistant POC.

This service exposes the risk-detection logic as a REST API.
In the POC, the API is triggered manually (e.g. from a Streamlit button).
In production, the same endpoint could be triggered by a scheduler or Joule/A2A.

Key design principles:
- UI is thin
- All business logic stays in the backend
- Data access goes only through the BDC facade
"""

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import risk detection logic
from backend.polling.risk_detector import run_risk_check, DetectedRisk


# -----------------------------------------------------------------------------
# FastAPI application
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Logistics Assistant POC API",
    description="Backend API for risk detection and decision support",
    version="0.1.0",
)


# -----------------------------------------------------------------------------
# CORS configuration (POC ONLY)
# -----------------------------------------------------------------------------
# This allows Streamlit (running on a different port) to call the API.
# In production, this should be locked down to specific origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # POC only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    """
    Simple health endpoint for sanity checks.
    """
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Risk detection endpoint
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
    risks = run_risk_check(now)
    return risks