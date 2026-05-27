"""
Inventory Supervisor Agent (Agent 3) — POC

Goal:
- Generate exactly 3 mitigation options (OPT-A/B/C) with quantified trade-offs
- Use:
  - Diagnosis (Agent 1)
  - Pattern forecast posture (Agent 2) if provided
  - BDC DP3 Inventory, DP2 Alternate suppliers, DP4 Customer commitments
- NO recommendation selection here: recommended=False for all options.
  Orchestrator will choose later.

Why it matters:
- This is where decision latency is reduced by surfacing alternatives proactively. (PrismCorp case study)
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
EXPEDITE_PREMIUM_RATE = 0.12               # 12% of shipment value (POC assumption; explicit)
ALTERNATE_SUPPLIER_PREMIUM_RATE = 0.18     # Step A: ensure alternate sourcing is clearly premium (POC tuned)
ADMIN_STRUCTURAL_COST_USD = 5000.0         # small admin cost for structural follow-up (POC)


SYSTEM_PROMPT = """\
You are the Inventory Supervisor Agent in PrismCorp's Logistics Assistant.

Your job:
- Produce EXACTLY 3 options: OPT-A, OPT-B, OPT-C.
- Each option must be genuinely different in approach.
- Use the provided data and the numeric fields supplied in the option templates.
- DO NOT change the numeric values provided in the templates.
- DO NOT mark any option as recommended (recommended must be false for all).

Posture shaping:
- If posture is 'structural' or 'hybrid', ensure at least one option includes a structural follow-up action
  (e.g., dual-sourcing / contract change), in addition to immediate mitigation.

Quality requirements:
- Customer impact must mention real customer names from commitments.
- Trade-off must be honest and clearly state what is sacrificed.

Output must match the schema exactly.
"""


@dataclass
class _OptionNumbers:
    cost_delta_usd: float
    sla_recovery_days: int


def _pick_destination_entity(shipment) -> str:
    # Treat shipment.entity as destination business entity for transfer calculations
    return shipment.entity


def _tier_rank(tier: str) -> int:
    # Used for customer prioritisation; smaller is higher priority
    return {"platinum": 0, "gold": 1, "silver": 2, "standard": 3}.get(tier, 9)


def _choose_best_inventory_source(inventory_positions, dest_entity: str) -> Optional[Tuple[object, float, int]]:
    """
    Pick the best inventory position outside the destination entity:
    - has available > 0
    - has transfer cost and lead-time to dest_entity

    Returns: (inventory_position, cost_per_unit, lead_days)
    """
    candidates = []
    for p in inventory_positions:
        if p.available <= 0:
            continue
        if p.entity == dest_entity:
            continue

        cost_map = getattr(p, "transfer_cost_per_unit_usd", {}) or {}
        lead_map = getattr(p, "transfer_lead_days_to", {}) or {}

        cost = cost_map.get(dest_entity)
        lead = lead_map.get(dest_entity)

        # Keep numeric grounding strict: if we can't compute, we skip
        if cost is None or lead is None:
            continue

        candidates.append((p, float(cost), int(lead)))

    if not candidates:
        return None

    # Cheapest cost first, then fastest lead time
    candidates.sort(key=lambda x: (x[1], x[2]))
    return candidates[0]


def _compute_transfer_option(commitments, inventory_pick) -> _OptionNumbers:
    """
    Compute internal transfer numbers:
    - Transfer units to cover highest priority commitments first, limited by available.
    - Cost delta = units_transferred * cost_per_unit
    - SLA recovery days = lead_days
    """
    p, cost_per_unit, lead_days = inventory_pick

    remaining = int(p.available)
    units_to_transfer = 0

    ordered = sorted(
        commitments,
        key=lambda c: (_tier_rank(c.contract_tier), c.deadline),
    )
    for c in ordered:
        if remaining <= 0:
            break
        need = int(c.committed_quantity)
        take = min(need, remaining)
        units_to_transfer += take
        remaining -= take

    cost_delta = units_to_transfer * cost_per_unit
    return _OptionNumbers(cost_delta_usd=round(cost_delta, 2), sla_recovery_days=lead_days)


def _choose_best_alternate_supplier(alternates) -> Optional[object]:
    """
    Choose cheapest usable alternate supplier by price_index.
    """
    if not alternates:
        return None
    usable = [s for s in alternates if getattr(s, "current_capacity_status", "available") != "unavailable"]
    if not usable:
        usable = alternates
    usable.sort(key=lambda s: float(getattr(s, "price_index", 1.0)))
    return usable[0]


def _compute_alternate_supplier_option(diagnosis: LogisticsIssueResolutionOutput, supplier) -> _OptionNumbers:
    """
    Step A tuning:
    - Ensure alternate supplier has a clearly premium cost delta.
    - Use max(ALTERNATE_SUPPLIER_PREMIUM_RATE, (price_index - 1.0))

    Cost delta = revenue_at_risk_usd * premium
    SLA recovery days = supplier typical lead time
    """
    revenue = float(diagnosis.business_impact.revenue_at_risk_usd)
    price_index = float(getattr(supplier, "price_index", 1.0))
    premium = max(ALTERNATE_SUPPLIER_PREMIUM_RATE, price_index - 1.0)

    cost_delta = revenue * premium
    lead = int(getattr(supplier, "typical_lead_time_days", 14))
    return _OptionNumbers(cost_delta_usd=round(cost_delta, 2), sla_recovery_days=lead)


def _compute_expedite_option(shipment, diagnosis: LogisticsIssueResolutionOutput) -> _OptionNumbers:
    """
    Expedite: explicit premium rate on shipment value (POC assumption).
    SLA recovery days: assume expedite reduces effective recovery time.
    """
    shipment_value = float(getattr(shipment, "shipment_value_usd", 0.0))
    cost_delta = shipment_value * EXPEDITE_PREMIUM_RATE

    base_delay = int(diagnosis.business_impact.predicted_delay_days)
    sla_days = max(1, base_delay - 2)
    return _OptionNumbers(cost_delta_usd=round(cost_delta, 2), sla_recovery_days=sla_days)


def run(
    po_number: str,
    diagnosis: LogisticsIssueResolutionOutput,
    pattern_forecast: Optional[PatternForecastOutput] = None,
) -> InventorySupervisorOutput:
    """
    Generate 3 mitigation options and return InventorySupervisorOutput.

    Inputs:
    - po_number: shipment identifier
    - diagnosis: Agent 1 output
    - pattern_forecast: Agent 2 output (may be None)

    BDC data products:
    - DP1 shipment -> SKU/entity
    - DP4 commitments -> customer names, deadlines, quantities
    - DP3 inventory -> transfer options (lead/cost)
    - DP2 alternates -> supplier options (lead/premium)
    """

    shipment = get_shipment(po_number)
    if shipment is None:
        raise ValueError(f"Shipment {po_number} not found")

    # DP4 commitments (required for customer names + deadlines)
    commitments = get_commitments_for_shipment(po_number)
    if not commitments:
        raise ValueError(f"No commitments found for shipment {po_number} (DP4 required)")

    sku = shipment.material_sku
    dest_entity = _pick_destination_entity(shipment)

    # DP3 inventory
    inventory_positions = get_inventory_for_sku(sku)

    # DP2 suppliers (exclude current supplier)
    alternates = get_alternate_suppliers(sku, exclude_supplier_id=shipment.supplier_id)

    posture = pattern_forecast.recommendation if pattern_forecast else "tactical"

    # ----------------------------
    # Precompute grounded numbers
    # ----------------------------
    inventory_pick = _choose_best_inventory_source(inventory_positions, dest_entity)
    best_alt = _choose_best_alternate_supplier(alternates)

    # OPT-A (internal transfer)
    if inventory_pick:
        opt_a = _compute_transfer_option(commitments, inventory_pick)
    else:
        opt_a = _OptionNumbers(cost_delta_usd=0.0, sla_recovery_days=999)  # will be explained via trade-off text

    # OPT-B (alternate supplier)
    if best_alt:
        opt_b = _compute_alternate_supplier_option(diagnosis, best_alt)
    else:
        opt_b = _OptionNumbers(cost_delta_usd=0.0, sla_recovery_days=999)

    # OPT-C (expedite or hybrid)
    opt_c = _compute_expedite_option(shipment, diagnosis)

    # Structural/hybrid posture: add explicit admin cost to represent follow-up work
    if posture in ("structural", "hybrid"):
        opt_c = _OptionNumbers(
            cost_delta_usd=round(opt_c.cost_delta_usd + ADMIN_STRUCTURAL_COST_USD, 2),
            sla_recovery_days=opt_c.sla_recovery_days,
        )

    # ----------------------------
    # Option templates (numbers locked)
    # ----------------------------
    option_templates = [
        {"option_id": "OPT-A", "approach": "internal_transfer", "cost_delta_usd": opt_a.cost_delta_usd, "sla_recovery_days": opt_a.sla_recovery_days},
        {"option_id": "OPT-B", "approach": "alternate_supplier", "cost_delta_usd": opt_b.cost_delta_usd, "sla_recovery_days": opt_b.sla_recovery_days},
        {"option_id": "OPT-C", "approach": "hybrid" if posture in ("structural", "hybrid") else "expedited_freight", "cost_delta_usd": opt_c.cost_delta_usd, "sla_recovery_days": opt_c.sla_recovery_days},
    ]

    # Context payload
    context = {
        "posture": posture,
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
            "must_include_customer_names_in_customer_impact": True,
            "must_produce_distinct_approaches": True,
        },
    }

    user_message = (
        "Create exactly 3 mitigation options based on the context. "
        "Use the option_templates numbers exactly as provided. "
        "Set recommended=false for all options.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )

    result = call_llm(SYSTEM_PROMPT, user_message, InventorySupervisorOutput)

    # ----------------------------
    # Post-validation guards
    # ----------------------------
    if len(result.options) != 3:
        raise ValueError("Agent 3 must return exactly 3 options")

    ids: Set[str] = {o.option_id for o in result.options}
    if ids != {"OPT-A", "OPT-B", "OPT-C"}:
        raise ValueError(f"Agent 3 returned wrong option IDs: {ids}")

    # Enforce recommended=False and enforce numeric fields from templates
    template_map = {t["option_id"]: t for t in option_templates}
    for o in result.options:
        o.recommended = False
        tpl = template_map[o.option_id]
        o.cost_delta_usd = float(tpl["cost_delta_usd"])
        o.sla_recovery_days = int(tpl["sla_recovery_days"])

    # Step A tuning: stronger, briefing-style notes
    result.notes = (
        "This disruption reflects a recurring systemic pattern at the Port of Shanghai. "
        "At least one option should address long‑term mitigation in addition to resolving the immediate delay."
        if posture in ("structural", "hybrid")
        else "This appears tactical; prioritise fastest SLA recovery with the least operational disruption."
    )

    logger.info("Inventory Supervisor generated 3 options for %s (posture=%s)", po_number, posture)
    return result