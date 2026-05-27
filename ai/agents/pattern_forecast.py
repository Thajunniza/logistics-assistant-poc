"""
Pattern Forecast Agent (POC)

Purpose:
- Answer: "Is this disruption a one-off, recurring, or systemic?"
- Use BDC DP6 (Historical Disruption Patterns) to provide memory across time
- Produce a typed output that influences downstream options and recommendations

Shape:
- One LLM call
- Typed output validated by Pydantic
- Graceful handling when no historical pattern exists
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from ai.llm import call_llm
from ai.agents.schemas import PatternForecastOutput, LogisticsIssueResolutionOutput

# BDC facade (your project uses backend.bdc.data_products)
from backend.bdc.data_products import (
    get_shipment,
    get_events_for_port,
    get_historical_pattern,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are the Pattern Forecast Agent in PrismCorp's Logistics Assistant.

Your job: decide whether this disruption is a one-off, recurring, or systemic pattern,
using historical disruption patterns (if available).

Inputs:
- Diagnosis output from Issue Resolution (what/why/impact)
- Triggering event (event_type, location_code, expected_duration_days)
- Historical disruption pattern record for (event_type, location_code) from BDC DP6 (may be null)

Rules of thumb:
- If no historical pattern is provided: classification = "one-off", confidence = "low".
- If occurrence_count is high within a short time_window (e.g. >= 3 in last_3_years): "systemic", confidence "high".
- If occurrence_count is moderate (e.g. 2-3) or the window is longer: "recurring", confidence "medium".
- If occurrence_count is 1 in a long window: "one-off", confidence "low".

Expected duration:
- Use the computed_expected_duration_days provided in the context as the best estimate.
- Explain why it differs from the event's reported duration if it is longer (historical recovery).

Recommendation:
- tactical: treat as isolated; optimise for quick fix
- structural: systemic; include long-term mitigation posture
- hybrid: recurring; handle now tactically + flag structural follow-up

Return JSON that matches the schema exactly. Do not invent fields.
"""


def _compute_expected_duration(event_duration_days: int, pattern: Optional[dict]) -> int:
    """
    Deterministic helper:
    - If pattern exists, use max(event_duration, rounded historical avg_recovery_days or avg_duration_days)
    - Else use event_duration
    This keeps numbers stable across runs and makes LLM narrative the only variable.
    """
    if not pattern:
        return int(event_duration_days)

    # Prefer avg_recovery_days, fallback to avg_duration_days
    avg_recovery = pattern.get("avg_recovery_days")
    avg_duration = pattern.get("avg_duration_days")

    hist = None
    if isinstance(avg_recovery, (int, float)):
        hist = avg_recovery
    elif isinstance(avg_duration, (int, float)):
        hist = avg_duration

    if hist is None:
        return int(event_duration_days)

    return int(max(event_duration_days, round(hist)))


def run(
    po_number: str,
    triggering_event_id: str,
    diagnosis: LogisticsIssueResolutionOutput,
) -> PatternForecastOutput:
    """
    Run Pattern Forecast for a selected shipment + triggering event, using diagnosis from Agent 1.

    We fetch:
    - shipment (to locate the port)
    - triggering event (to get event_type + location_code + expected_duration_days)
    - historical pattern record DP6 (may be None)

    Then call the LLM once and validate PatternForecastOutput.
    """

    shipment = get_shipment(po_number)
    if shipment is None:
        raise ValueError(f"Shipment {po_number} not found")

    events = get_events_for_port(shipment.source_port_code)
    event = next((e for e in events if e.event_id == triggering_event_id), None)
    if event is None:
        raise ValueError(
            f"Event {triggering_event_id} not found for port {shipment.source_port_code}"
        )

    # Historical pattern may be None
    pattern_obj = get_historical_pattern(event.event_type, event.location_code)
    pattern_dict = pattern_obj.model_dump(mode="json") if pattern_obj else None

    computed_expected_duration = _compute_expected_duration(
        event.expected_duration_days, pattern_dict
    )

    context = {
        "triggering_event": event.model_dump(mode="json"),
        "diagnosis": diagnosis.model_dump(mode="json"),
        "historical_pattern": pattern_dict,  # may be null
        "computed_expected_duration_days": computed_expected_duration,
    }

    user_message = (
        "You are given:\n"
        "1) Diagnosis output (Agent 1)\n"
        "2) Triggering event\n"
        "3) Historical pattern record (may be null)\n\n"
        "Produce the pattern forecast output.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )

    result = call_llm(SYSTEM_PROMPT, user_message, PatternForecastOutput)
    logger.info("Pattern forecast: %s [%s]", result.classification, result.confidence)
    return result