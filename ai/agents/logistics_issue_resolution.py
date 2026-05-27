"""
Logistics Issue Resolution Agent.

Custom AI agent modelled on SAP's Logistics Assistant catalogue.
Diagnoses delivery exceptions and quantifies impact from BDC data.
"""
from __future__ import annotations

import json
import logging

from ai.llm import call_llm
from ai.agents.schemas import LogisticsIssueResolutionOutput

from backend.bdc.data_products import (
    get_shipment,
    get_events_for_port,
    get_commitments_for_shipment,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Logistics Issue Resolution Agent in PrismCorp's Logistics Assistant on SAP BTP.

Your job: diagnose the delivery exception. You receive a triggering port event, the affected shipment,
and the customer commitments depending on that shipment — all from SAP Business Data Cloud.

Be evidence-led. Write in the voice of a senior supply chain analyst briefing the Supply Chain Head.

CRITICAL: You are reading UPSTREAM signals. The port congestion is reported NOW; the carrier's ETA has
not yet updated. Your job is to PREDICT the delay impact before it materialises — not to report on
a delay that has already happened.

Compute predicted_delay_days from the port event's expected_duration_days.
Compute sla_exposure_usd per commitment as:
  min(sla_penalty_per_day_usd * predicted_delay_days, sla_penalty_cap_usd)
Then sum across commitments.
Compute revenue_at_risk_usd as the sum of order_value_usd across affected commitments.
Compute customers_at_risk as the count of commitments.

Return JSON matching the provided schema exactly. Do not invent fields.
"""

def run(po_number: str, triggering_event_id: str) -> LogisticsIssueResolutionOutput:
    shipment = get_shipment(po_number)
    if shipment is None:
        raise ValueError(f"Shipment {po_number} not found")

    events = get_events_for_port(shipment.source_port_code)
    triggering_event = next((e for e in events if e.event_id == triggering_event_id), None)
    if triggering_event is None:
        raise ValueError(f"Event {triggering_event_id} not found for port {shipment.source_port_code}")

    commitments = get_commitments_for_shipment(po_number)
    if not commitments:
        raise ValueError(f"No commitments found for shipment {po_number}")

    context = {
        "triggering_event": triggering_event.model_dump(mode="json"),
        "affected_shipment": shipment.model_dump(mode="json"),
        "dependent_commitments": [c.model_dump(mode="json") for c in commitments],
    }

    user_message = (
        "BDC has surfaced the following harmonised data:\n"
        f"{json.dumps(context, indent=2, default=str)}\n\n"
        "Diagnose the issue. Predict the customer impact before it materialises."
    )

    result = call_llm(SYSTEM_PROMPT, user_message, LogisticsIssueResolutionOutput)

    # ensure affected_order is set (either by model or force it here)
    if not getattr(result, "affected_order", None):
        result.affected_order = po_number  # type: ignore

    logger.info("Diagnosis: %s [%s]", result.risk_title, result.severity)
    return result
