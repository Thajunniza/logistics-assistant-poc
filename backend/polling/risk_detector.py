"""
Risk detection logic for the Logistics Assistant POC.

Design principles:
- Deterministic, explainable detection (NO agentic AI here)
- One consolidated risk per shipment (PO)
- Explicit severity classification (VERY HIGH vs HIGH)
- Fully auditable and governance-friendly
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Set

from pydantic import BaseModel

from backend.bdc.data_products import (
    get_active_port_events,
    get_shipments_at_port,
    get_commitments_for_shipment,
)


# =============================================================================
# Decision Object — DetectedRisk
# =============================================================================
class DetectedRisk(BaseModel):
    event_id: str
    po_number: str
    risk_level: str              # VERY HIGH | HIGH
    cause: str
    predicted_delay_days: int
    customers_impacted: list[str]
    revenue_at_risk_usd: float
    detected_at: datetime


# =============================================================================
# Core Detection Function
# =============================================================================
def run_risk_check(now: datetime) -> List[DetectedRisk]:
    """
    Execute one deterministic risk-detection pass.

    Logic flow:
    Event → Shipments → Commitments → Materiality → Severity → Emit Risk

    Guarantees:
    - ONE risk per shipment (PO)
    - No duplicate risks
    """

    detected_risks: List[DetectedRisk] = []
    seen_shipments: Set[str] = set()   # ✅ de-duplication guard

    # -------------------------------------------------------------------------
    # Step 1 — Fetch active logistics events (BDC DP5)
    # -------------------------------------------------------------------------
    events = get_active_port_events()

    for event in events:

        # ---------------------------------------------------------------------
        # Step 2 — Find shipments impacted by this event (BDC DP1)
        # ---------------------------------------------------------------------
        shipments = get_shipments_at_port(event.location_code)

        for shipment in shipments:

            # ✅ Prevent duplicate risk for same PO
            if shipment.po_number in seen_shipments:
                continue

            # -----------------------------------------------------------------
            # Step 3 — Fetch customer commitments (BDC DP4)
            # -----------------------------------------------------------------
            commitments = get_commitments_for_shipment(shipment.po_number)

            # No commitments = no business risk
            if not commitments:
                continue

            # -----------------------------------------------------------------
            # Step 4 — Compute business impact
            # -----------------------------------------------------------------
            revenue_at_risk = sum(c.order_value_usd for c in commitments)
            has_platinum = any(c.contract_tier == "platinum" for c in commitments)

            # -----------------------------------------------------------------
            # Step 5 — Materiality gate (RISK vs NON-RISK)
            # -----------------------------------------------------------------
            is_material_risk = (
                event.expected_duration_days >= 5
                or revenue_at_risk >= 250_000
                or has_platinum
            )

            if not is_material_risk:
                continue

            # -----------------------------------------------------------------
            # Step 6 — Severity classification
            # -----------------------------------------------------------------
            #
            # VERY HIGH:
            #   - Platinum customer
            #   - Revenue >= $500K
            #
            # HIGH:
            #   - All other material risks
            #
            risk_level = "HIGH"

            if has_platinum and revenue_at_risk >= 500_000:
                risk_level = "VERY HIGH"

            # -----------------------------------------------------------------
            # Step 7 — Emit ONE consolidated risk for this shipment
            # -----------------------------------------------------------------
            detected_risks.append(
                DetectedRisk(
                    event_id=event.event_id,
                    po_number=shipment.po_number,
                    risk_level=risk_level,
                    cause=event.event_type,
                    predicted_delay_days=event.expected_duration_days,
                    customers_impacted=[c.customer_name for c in commitments],
                    revenue_at_risk_usd=revenue_at_risk,
                    detected_at=now,
                )
            )

            # ✅ Mark shipment as processed
            seen_shipments.add(shipment.po_number)

    return detected_risks
