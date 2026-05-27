"""
Risk detection (polling) logic for the Logistics Assistant POC.

This module implements the core behaviour that turns harmonised BDC data
into actionable delivery risks.

IMPORTANT DESIGN NOTES
----------------------
- This file contains *no scheduling logic*.
  In production, this function would be triggered every N minutes by a scheduler.
  In the POC, it is triggered manually (e.g. via a UI button).

- This module does NOT talk to SAP systems or non-SAP APIs.
  It reads only from the BDC query interface (data_product.py).

- The output of this module is a *decision object* ("DetectedRisk"),
  not a data product. This is the boundary between data and reasoning.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel

# BDC query interface (single chokepoint to data)
from backend.bdc.data_products import (
    get_active_port_events,
    get_shipments_at_port,
    get_commitments_for_shipment,
)


# =============================================================================
# Decision Object: DetectedRisk
# =============================================================================
class DetectedRisk(BaseModel):
    """
    A decision-ready representation of a delivery risk.

    This is NOT a BDC data product.
    It is derived by reasoning across multiple BDC data products.

    This object is what:
    - the UI displays in the "Risk List"
    - the orchestrator uses to activate agents
    """

    event_id: str
    po_number: str
    risk_level: str
    cause: str
    predicted_delay_days: int
    customers_impacted: list[str]
    revenue_at_risk_usd: float
    detected_at: datetime


# =============================================================================
# Core Function: run_risk_check
# =============================================================================
def run_risk_check(now: datetime) -> List[DetectedRisk]:
    """
    Execute one full risk-detection pass.

    This function represents ONE polling cycle.

    Steps performed:
    1. Read active logistics disruption events from BDC (DP5)
    2. For each event, find affected shipments (DP1)
    3. For each shipment, find dependent customer commitments (DP4)
    4. Apply materiality thresholds
    5. Return a list of detected risks

    In the POC:
    - This function is triggered manually from the UI

    In production:
    - This function would be triggered on a schedule (e.g. every 5 minutes)
    """

    detected_risks: List[DetectedRisk] = []

    # -------------------------------------------------------------------------
    # Step 1 — Fetch active disruption events (Port & Logistics Events)
    # -------------------------------------------------------------------------
    events = get_active_port_events()

    # In most cycles, this list will be empty.
    # That is normal and expected in production systems.
    for event in events:

        # ---------------------------------------------------------------------
        # Step 2 — Find shipments affected by this event
        # ---------------------------------------------------------------------
        shipments = get_shipments_at_port(event.location_code)

        # If no shipments are affected, this event is noise for PrismCorp.
        for shipment in shipments:

            # -----------------------------------------------------------------
            # Step 3 — Find customer commitments depending on this shipment
            # -----------------------------------------------------------------
            commitments = get_commitments_for_shipment(shipment.po_number)

            # If no customer commitments depend on this shipment,
            # there is no business impact.
            if not commitments:
                continue

            # -----------------------------------------------------------------
            # Step 4 — Compute business impact metrics
            # -----------------------------------------------------------------
            revenue_at_risk = sum(c.order_value_usd for c in commitments)
            has_platinum_customer = any(
                c.contract_tier == "platinum" for c in commitments
            )

            # -----------------------------------------------------------------
            # Step 5 — Apply materiality thresholds (LOCKED FOR POC)
            # -----------------------------------------------------------------
            #
            # A risk is considered "material" if ANY of the following is true:
            #   - Expected delay is >= 5 days
            #   - Revenue at risk >= $250,000
            #   - Any impacted customer is Platinum tier
            #
            if (
                event.expected_duration_days >= 5
                or revenue_at_risk >= 250_000
                or has_platinum_customer
            ):
                detected_risks.append(
                    DetectedRisk(
                        event_id=event.event_id,
                        po_number=shipment.po_number,
                        risk_level="HIGH",
                        cause=event.event_type,
                        predicted_delay_days=event.expected_duration_days,
                        customers_impacted=[
                            c.customer_name for c in commitments
                        ],
                        revenue_at_risk_usd=revenue_at_risk,
                        detected_at=now,
                    )
                )

    return detected_risks