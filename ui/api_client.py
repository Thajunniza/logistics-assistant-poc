# ui/api_client.py
"""
HTTP client for the Logistics Assistant POC UI.
UI talks ONLY to these functions (thin UI).
"""

import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def health_check() -> dict:
    r = requests.get(f"{API_BASE_URL}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def run_risk_check() -> list[dict]:
    """
    Triggers the backend risk detection (manual polling for POC).
    Returns list of detected risks.
    """
    r = requests.post(f"{API_BASE_URL}/risk-check", timeout=30)
    r.raise_for_status()
    return r.json()


# -----------------------------------------------------------------------------
# Diagnosis endpoint (agentic)
# -----------------------------------------------------------------------------
def get_diagnosis(po_number: str, triggering_event_id: str):
    response = requests.post(
        f"{API_BASE_URL}/diagnosis",
        json={
            "po_number": po_number,
            "triggering_event_id": triggering_event_id,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

# -----------------------------------------------------------------------------
# Pattern recognition endpoint (agentic)
# -----------------------------------------------------------------------------
def get_pattern_forecast(po_number: str, triggering_event_id: str):
    response = requests.post(
        f"{API_BASE_URL}/pattern-forecast",
        json={
            "po_number": po_number,
            "triggering_event_id": triggering_event_id,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


