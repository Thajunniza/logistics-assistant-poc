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
