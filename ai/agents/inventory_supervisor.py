"""
Inventory Supervisor Agent (Agent 3)

Goal:
- Generate exactly 3 mitigation options (OPT-A/B/C) with quantified trade-offs
- Use:
  - Diagnosis (Agent 1)
  - Pattern forecast posture (Agent 2) if provided
  - BDC DP3 Inventory, DP2 Alternate suppliers, DP4 Customer commitments
- NO recommendation selection here: recommended=False for all options.
  Orchestrator will choose later.

Fixes in this version:
- Dynamic port/location name (no hardcoded "Shanghai")
- Explicit structural element named in OPT-C when posture is structural/hybrid
- Graceful handling when no inventory or no alternate supplier exists
- Multi-customer awareness: prompt requires addressing all affected customers,
  and computes coverage when inventory is partial
- Transfer coverage flag so the trade-off text is honest about partial fulfilment
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Set

from ai.llm import call_llm
from ai.agents.schemas import (
    InventorySupervisorOutput,
    LogisticsIssueResolutionOutput,
    PatternForecastOutput,
)

# BDC facade (your project path)
from backend.bdc.data_products import (
    get_shipment,
    get_inventory_for_sku,
    get_alternate_suppliers,
    get_commitments_for_shipment,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# POC constants (explicit, reviewer-safe assumptions)
# -----------------------------------------------------------------------------
EXPEDITE_PREMIUM_RATE = 0.12               # 12% of shipment value (POC assumption)
ALTERNATE_SUPPLIER_PREMIUM_RATE = 0.18     # ensure alternate sourcing is clearly premium
ADMIN_STRUCTURAL_COST_USD = 5000.0         # admin cost for structural follow-up (POC)
NO_OPTION_SENTINEL_DAYS = 999              # marks an unavailable lever


SYSTEM_PROMPT = """\
You are the Inventory Supervisor Agent in PrismCorp's Logistics Assistant on SAP BTP.

Your job:
- Produce EXACTLY 3 options: OPT-A, OPT-B, OPT-C.
- Each option must be genuinely different in approach.
- Use the numeric fields supplied in option_templates EXACTLY. Do NOT change them.
- DO NOT mark any option as recommended (recommended must be false for all).

Posture shaping (from the Pattern Forecast agent):
- If posture is 'structural' or 'hybrid', OPT-C MUST include an explicit structural
  follow-up action that addresses the RECURRING pattern — not just this one shipment.
  Name it concretely (e.g. "establish a standing dual-source agreement with <supplier>
  for <location> to reduce recurring exposure"). Use the structural_hint provided.
- If posture is 'tactical', all three options should be immediate fixes only.
  Do NOT propose structural/long-term actions for a one-off event.

Multi-customer requirement:
- The commitments list may contain MORE THAN ONE customer for this shipment.
- Customer impact for each option MUST name every affected customer and state what
  each one receives (full, partial, or delayed). If an option cannot serve everyone,
  say so honestly in the trade-off — name who is prioritised and who slips.

Quality requirements:
- Customer impact must mention the real customer names from commitments.
- Trade-off must be honest and clearly state what is sacrificed.
- Use the location_name provided for any reference to where the disruption is — never
  assume a location.

Output must match the schema exactly.
"""


@dataclass
class _OptionNumbers:
    cost_delta_usd: float
    sla_recovery_days: int
    covers_full_quantity: bool = True


def _pick_destination_entity(shipment) -> str:
    return shipment.entity


def _tier_rank(tier: str) -> int:
    return {"platinum": 0, "gold": 1, "silver": 2, "standard": 3}.get(tier, 9)


def _choose_best_inventory_source(inventory_positions, dest_entity: str) -> Optional[Tuple[object, float, int]]:
    """Pick cheapest-then-fastest inventory position outside the destination entity."""
    candidates = []
    for p in inventory_positions:
        if p.available <= 0 or p.entity == dest_entity:
            continue
        cost_map = getattr(p, "transfer_cost_per_unit_usd", {}) or {}
        lead_map = getattr(p, "transfer_lead_days_to", {}) or {}
        cost = cost_map.get(dest_entity)
        lead = lead_map.get(dest_entity)
        if cost is None or lead is None:
            continue
        candidates.append((p, float(cost), int(lead)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], x[2]))
    return candidates[0]


def _total_committed_quantity(commitments) -> int:
    return sum(int(c.committed_quantity) for c in commitments)


def _compute_transfer_option(commitments, inventory_pick) -> _OptionNumbers:
    """
    Internal transfer numbers:
    - Transfer units to cover highest-priority commitments first, limited by available.
    - Cost delta = units_transferred * cost_per_unit
    - SLA recovery days = lead_days
    - covers_full_quantity = whether available stock met total demand
    """
    p, cost_per_unit, lead_days = inventory_pick
    remaining = int(p.available)
    total_needed = _total_committed_quantity(commitments)
    units_to_transfer = 0

    ordered = sorted(commitments, key=lambda c: (_tier_rank(c.contract_tier), c.deadline))
    for c in ordered:
        if remaining <= 0:
            break
        take = min(int(c.committed_quantity), remaining)
        units_to_transfer += take
        remaining -= take

    cost_delta = units_to_transfer * cost_per_unit
    covers_full = units_to_transfer >= total_needed
    return _OptionNumbers(round(cost_delta, 2), lead_days, covers_full)


def _choose_best_alternate_supplier(alternates) -> Optional[object]:
    if not alternates:
        return None
    usable = [s for s in alternates if getattr(s, "current_capacity_status", "available") != "unavailable"]
    if not usable:
        usable = alternates
    usable.sort(key=lambda s: float(getattr(s, "price_index", 1.0)))
    return usable[0]


def _compute_alternate_supplier_option(diagnosis: LogisticsIssueResolutionOutput, supplier) -> _OptionNumbers:
    revenue = float(diagnosis.business_impact.revenue_at_risk_usd)
    price_index = float(getattr(supplier, "price_index", 1.0))
    premium = max(ALTERNATE_SUPPLIER_PREMIUM_RATE, price_index - 1.0)
    cost_delta = revenue * premium
    lead = int(getattr(supplier, "typical_lead_time_days", 14))
    return _OptionNumbers(round(cost_delta, 2), lead, True)


def _compute_expedite_option(shipment, diagnosis: LogisticsIssueResolutionOutput) -> _OptionNumbers:
    shipment_value = float(getattr(shipment, "shipment_value_usd", 0.0))
    cost_delta = shipment_value * EXPEDITE_PREMIUM_RATE
    base_delay = int(diagnosis.business_impact.predicted_delay_days)
    sla_days = max(1, base_delay - 2)
    return _OptionNumbers(round(cost_delta, 2), sla_days, True)


def run(
    po_number: str,
    diagnosis: LogisticsIssueResolutionOutput,
    pattern_forecast: Optional[PatternForecastOutput] = None,
) -> InventorySupervisorOutput:
    """Generate 3 mitigation options and return InventorySupervisorOutput."""

    shipment = get_shipment(po_number)
    if shipment is None:
        raise ValueError(f"Shipment {po_number} not found")

    commitments = get_commitments_for_shipment(po_number)
    if not commitments:
        raise ValueError(f"No commitments found for shipment {po_number} (DP4 required)")

    sku = shipment.material_sku
    dest_entity = _pick_destination_entity(shipment)

    inventory_positions = get_inventory_for_sku(sku)
    alternates = get_alternate_suppliers(sku, exclude_supplier_id=shipment.supplier_id)

    posture = pattern_forecast.recommendation if pattern_forecast else "tactical"

    # Dynamic location + structural hint (FIX: no hardcoded "Shanghai")
    location_name = getattr(shipment, "source_port_code", "the origin port")
    # Prefer a human-readable port name if your shipment carries one; else use code.
    location_label = getattr(shipment, "source_port_name", None) or location_name

    best_alt = _choose_best_alternate_supplier(alternates)
    alt_name = getattr(best_alt, "supplier_name", "a qualified alternate supplier") if best_alt else "a qualified alternate supplier"
    structural_hint = (
        f"Establish a standing dual-source agreement with {alt_name} for shipments routed "
        f"through {location_label}, reducing exposure to recurring disruption at this location."
    )

    # ----------------------------
    # Precompute grounded numbers
    # ----------------------------
    inventory_pick = _choose_best_inventory_source(inventory_positions, dest_entity)

    if inventory_pick:
        opt_a = _compute_transfer_option(commitments, inventory_pick)
        opt_a_available = True
    else:
        opt_a = _OptionNumbers(0.0, NO_OPTION_SENTINEL_DAYS, False)
        opt_a_available = False

    if best_alt:
        opt_b = _compute_alternate_supplier_option(diagnosis, best_alt)
        opt_b_available = True
    else:
        opt_b = _OptionNumbers(0.0, NO_OPTION_SENTINEL_DAYS, True)
        opt_b_available = False

    opt_c = _compute_expedite_option(shipment, diagnosis)
    if posture in ("structural", "hybrid"):
        opt_c = _OptionNumbers(
            round(opt_c.cost_delta_usd + ADMIN_STRUCTURAL_COST_USD, 2),
            opt_c.sla_recovery_days,
            opt_c.covers_full_quantity,
        )

    # ----------------------------
    # Option templates (numbers locked)
    # ----------------------------
    option_templates = [
        {
            "option_id": "OPT-A",
            "approach": "internal_transfer",
            "available": opt_a_available,
            "covers_full_quantity": opt_a.covers_full_quantity,
            "cost_delta_usd": opt_a.cost_delta_usd,
            "sla_recovery_days": opt_a.sla_recovery_days,
        },
        {
            "option_id": "OPT-B",
            "approach": "alternate_supplier",
            "available": opt_b_available,
            "covers_full_quantity": True,
            "cost_delta_usd": opt_b.cost_delta_usd,
            "sla_recovery_days": opt_b.sla_recovery_days,
        },
        {
            "option_id": "OPT-C",
            "approach": "hybrid" if posture in ("structural", "hybrid") else "expedited_freight",
            "available": True,
            "covers_full_quantity": True,
            "cost_delta_usd": opt_c.cost_delta_usd,
            "sla_recovery_days": opt_c.sla_recovery_days,
        },
    ]

    context = {
        "posture": posture,
        "location_name": location_label,
        "structural_hint": structural_hint,
        "shipment": shipment.model_dump(mode="json"),
        "diagnosis": diagnosis.model_dump(mode="json"),
        "pattern_forecast": pattern_forecast.model_dump(mode="json") if pattern_forecast else None,
        "commitments": [c.model_dump(mode="json") for c in commitments],
        "inventory_positions": [p.model_dump(mode="json") for p in inventory_positions],
        "alternate_suppliers": [s.model_dump(mode="json") for s in alternates],
        "option_templates": option_templates,
        "rules": {
            "recommended_must_be_false": True,
            "must_return_exactly_three_options": True,
            "must_keep_numbers_from_templates": True,
            "must_include_all_customer_names_in_customer_impact": True,
            "must_produce_distinct_approaches": True,
            "structural_required_when_posture_structural_or_hybrid": posture in ("structural", "hybrid"),
            "if_option_not_available_explain_in_tradeoff": True,
        },
    }

    user_message = (
        "Create exactly 3 mitigation options based on the context. "
        "Use the option_templates numbers exactly as provided. "
        "Set recommended=false for all options. "
        "Reference the disruption location only as the provided location_name. "
        "If an option_template has available=false, still produce the option but make the "
        "trade-off clearly state that this lever is not currently available and why "
        "(e.g. no transferable inventory, or no alternate supplier qualified for this SKU).\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )

    result = call_llm(
        SYSTEM_PROMPT, 
        user_message, 
        InventorySupervisorOutput,
        agent_name="Inventory Supervisor",
        user_name="thajunniza.a@aptiv.com",
        )

    # ----------------------------
    # Post-validation guards
    # ----------------------------
    if len(result.options) != 3:
        raise ValueError("Agent 3 must return exactly 3 options")

    ids: Set[str] = {o.option_id for o in result.options}
    if ids != {"OPT-A", "OPT-B", "OPT-C"}:
        raise ValueError(f"Agent 3 returned wrong option IDs: {ids}")

    # Enforce recommended=False and lock numeric fields from templates
    template_map = {t["option_id"]: t for t in option_templates}
    for o in result.options:
        o.recommended = False
        tpl = template_map[o.option_id]
        o.cost_delta_usd = float(tpl["cost_delta_usd"])
        o.sla_recovery_days = int(tpl["sla_recovery_days"])

    # Dynamic posture note (FIX: no hardcoded location)
    if posture in ("structural", "hybrid"):
        result.notes = (
            f"This disruption at {location_label} reflects a recurring pattern. "
            f"At least one option addresses long-term mitigation in addition to resolving "
            f"the immediate delay."
        )
    else:
        result.notes = (
            f"This appears to be a one-off disruption at {location_label}. "
            f"Prioritise fastest SLA recovery with the least operational disruption; "
            f"structural change is not warranted on current evidence."
        )

    logger.info(
        "Inventory Supervisor: 3 options for %s (posture=%s, location=%s)",
        po_number, posture, location_label,
    )
    return result