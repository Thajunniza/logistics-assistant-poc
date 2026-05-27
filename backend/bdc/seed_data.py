"""
Seed data for the port-congestion scenario.

This is what BDC would return if it were live. Every record traces to a specific
data product and represents what the harmonised data layer would serve. The
agents don't see this module — they see the query functions in
bdc_data_products.py, which read from here.

When swapping to live BDC: replace bdc_data_products.py's implementations with
Datasphere client calls. This _seed_data module is no longer needed in
production.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from .models import (
    Commitment,
    DisruptionPattern,
    InventoryPosition,
    PortEvent,
    Shipment,
    Supplier,
)

NOW = datetime(2026, 5, 26, 8, 42, 0, tzinfo=timezone.utc)


# ============================================================================
# DP5 — Port and Logistics Events (active disruption events)
# ============================================================================
PORT_EVENTS: list[PortEvent] = [
    PortEvent(
        event_id="EVT-CNSHA-2026-05-26-001",
        event_type="port_congestion",
        location_type="port",
        location_code="CNSHA",
        location_name="Port of Shanghai",
        severity="critical",
        started_at=datetime(2026, 5, 26, 6, 15, 0, tzinfo=timezone.utc),
        expected_duration_days=10,
        cause_description=(
            "Typhoon Maemi storm surge backlog plus extended customs processing"
        ),
        affected_vessels=47,
        affected_carrier_ids=["MAERSK-PAC", "EVERGREEN-AS", "ONE-NETWORK"],
        reported_by="Port Operations API (GCP)",
        confidence="high",
        last_updated=NOW,
    )
]


# ============================================================================
# DP1 — Shipments
# ============================================================================
SHIPMENTS: list[Shipment] = [
    Shipment(
        po_number="PO-PRM-2026-08-2241",
        entity="PrismCorp APAC",
        supplier_id="ARB-78421",
        material_sku="FLT-XR-9924",
        quantity=8400,
        uom="units",
        containers=12,
        shipment_value_usd=2_840_000.0,
        source_port_code="CNSHA",
        destination_port_code="SGSIN",
        original_eta=date(2026, 6, 2),
        current_eta=date(2026, 6, 2),  # Carrier hasn't updated yet — agent predicts slip
        status="in_transit",
        carrier_id="MAERSK-PAC",
        last_updated=NOW,
    )
]


# ============================================================================
# DP2 — Suppliers (primary + alternates for FLT-XR-9924)
# ============================================================================
SUPPLIERS: list[Supplier] = [
    Supplier(
        supplier_id="ARB-78421",
        supplier_name="Meridian Pacific Components Ltd",
        region="China",
        tier="tier1_strategic",
        quality_rating="AA",
        skus_supplied=["FLT-XR-9924", "FLT-XR-9925", "FLT-XR-9926"],
        typical_lead_time_days=18,
        price_index=1.00,
        max_capacity_per_month=12000,
        current_capacity_status="constrained",  # affected by typhoon
        contract_status="active",
    ),
    Supplier(
        supplier_id="ARB-91244",
        supplier_name="Sentinel Filtration GmbH",
        region="Germany",
        tier="tier1",
        quality_rating="AA",
        skus_supplied=["FLT-XR-9924", "FLT-XR-9925", "FLT-XR-9980"],
        typical_lead_time_days=14,
        price_index=1.08,
        max_capacity_per_month=8500,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
    Supplier(
        supplier_id="ARB-66021",
        supplier_name="Pacific Components Express",
        region="Vietnam",
        tier="tier2",
        quality_rating="A",
        skus_supplied=["FLT-XR-9924"],
        typical_lead_time_days=9,
        price_index=1.12,
        max_capacity_per_month=5000,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
]


# ============================================================================
# DP3 — Cross-Entity Inventory Position (for SKU FLT-XR-9924)
# ============================================================================
INVENTORY: list[InventoryPosition] = [
    InventoryPosition(
        sku="FLT-XR-9924",
        entity="PrismCorp APAC",
        warehouse_id="WH-SIN-01",
        warehouse_region="Singapore",
        on_hand=420,
        committed=380,
        available=40,
        in_transit_to=8400,  # the affected shipment
        transfer_lead_days_to={
            "PrismCorp EMEA": 11,
            "PrismCorp AMER": 14,
            "PrismCorp APAC": 0,
            "PrismCorp LATAM": 16,
            "PrismCorp MENA": 9,
        },
        transfer_cost_per_unit_usd={
            "PrismCorp EMEA": 11.05,
            "PrismCorp AMER": 20.00,
            "PrismCorp APAC": 0.0,
            "PrismCorp LATAM": 22.40,
            "PrismCorp MENA": 8.10,
        },
        last_updated=NOW,
    ),
    InventoryPosition(
        sku="FLT-XR-9924",
        entity="PrismCorp EMEA",
        warehouse_id="WH-ROT-01",
        warehouse_region="Rotterdam, NL",
        on_hand=3800,
        committed=0,
        available=3800,
        in_transit_to=0,
        transfer_lead_days_to={
            "PrismCorp APAC": 11,
            "PrismCorp AMER": 8,
            "PrismCorp EMEA": 0,
            "PrismCorp LATAM": 12,
            "PrismCorp MENA": 6,
        },
        transfer_cost_per_unit_usd={
            "PrismCorp APAC": 11.05,
            "PrismCorp AMER": 7.40,
            "PrismCorp EMEA": 0.0,
            "PrismCorp LATAM": 9.80,
            "PrismCorp MENA": 5.50,
        },
        last_updated=NOW,
    ),
    InventoryPosition(
        sku="FLT-XR-9924",
        entity="PrismCorp AMER",
        warehouse_id="WH-HOU-01",
        warehouse_region="Houston, US",
        on_hand=1900,
        committed=0,
        available=1900,
        in_transit_to=0,
        transfer_lead_days_to={
            "PrismCorp APAC": 14,
            "PrismCorp EMEA": 10,
            "PrismCorp AMER": 0,
            "PrismCorp LATAM": 5,
            "PrismCorp MENA": 12,
        },
        transfer_cost_per_unit_usd={
            "PrismCorp APAC": 20.00,
            "PrismCorp EMEA": 12.30,
            "PrismCorp AMER": 0.0,
            "PrismCorp LATAM": 8.50,
            "PrismCorp MENA": 14.20,
        },
        last_updated=NOW,
    ),
]


# ============================================================================
# DP4 — Customer Commitments (depending on the affected PO)
# ============================================================================
COMMITMENTS: list[Commitment] = [
    Commitment(
        commitment_id="CMT-HELIOS-2026-Q2-088",
        customer_id="CST-HELIOS-001",
        customer_name="Helios Energy Systems",
        customer_region="Singapore",
        contract_tier="platinum",
        sku="FLT-XR-9924",
        committed_quantity=6200,
        deadline=date(2026, 6, 8),
        supplying_po="PO-PRM-2026-08-2241",
        sla_penalty_per_day_usd=14_000.0,
        sla_penalty_cap_usd=84_000.0,
        order_value_usd=740_000.0,
        status="pending",
    ),
    Commitment(
        commitment_id="CMT-TRITON-2026-Q2-041",
        customer_id="CST-TRITON-001",
        customer_name="Triton Marine Tech",
        customer_region="Malaysia",
        contract_tier="gold",
        sku="FLT-XR-9924",
        committed_quantity=2200,
        deadline=date(2026, 6, 10),
        supplying_po="PO-PRM-2026-08-2241",
        sla_penalty_per_day_usd=5_500.0,
        sla_penalty_cap_usd=31_000.0,
        order_value_usd=500_000.0,
        status="pending",
    ),
]


# ============================================================================
# DP6 — Historical Disruption Patterns
# ============================================================================
PATTERNS: list[DisruptionPattern] = [
    DisruptionPattern(
        pattern_id="PAT-CNSHA-PORT_CONGESTION",
        event_type="port_congestion",
        location_code="CNSHA",
        occurrence_count=4,
        time_window="last_3_years",
        avg_duration_days=9.5,
        avg_recovery_days=8.0,
        seasonality_pattern="typhoon_season",
        last_occurrence_date=date(2025, 7, 14),
        typical_root_causes=["typhoon", "customs_backlog", "labor_action"],
        typical_resolution_paths=[
            "alternate_supplier_emea",
            "internal_transfer_emea",
            "expedited_freight",
        ],
    )
]
