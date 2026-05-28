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

# -----------------------------------------------------------------------------
# Solution Option endpoint (agentic)
# -----------------------------------------------------------------------------
def get_inventory_options(po_number: str, triggering_event_id: str):
    response = requests.post(
        f"{API_BASE_URL}/inventory-options",
        json={
            "po_number": po_number,
            "triggering_event_id": triggering_event_id,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

# -----------------------------------------------------------------------------
# Transport Dispatcher endpoint (agentic)
# -----------------------------------------------------------------------------

def get_dispatch_plan(po_number: str, triggering_event_id: str, approved_option_id: str):
    response = requests.post(
        f"{API_BASE_URL}/dispatch-plan",
        json={
            "po_number": po_number,
            "triggering_event_id": triggering_event_id,
            "approved_option_id": approved_option_id,
        },
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def ask_risk_qna(question: str, context: dict) -> str:
    """
    Calls backend /risk-qna with strictly JSON-serialisable context.
    Returns plain answer text.
    """
    payload = {
        "question": question,
        "context": context,
    }

    r = requests.post(f"{API_BASE_URL}/risk-qna", json=payload, timeout=60)

    # Helpful debugging if backend returns 422 (schema mismatch)
    if r.status_code == 422:
        raise requests.HTTPError(
            f"422 from /risk-qna. Backend could not validate request body.\n"
            f"Response: {r.text}\n"
            f"Payload keys: {list(payload.keys())}\n"
            f"Context keys: {list(context.keys())}",
            response=r,
        )

    r.raise_for_status()
    return r.json()["answer"]