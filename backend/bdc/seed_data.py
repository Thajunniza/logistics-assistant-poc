"""
Seed data for Logistics Assistant POC.

This is a mock snapshot of what SAP Business Data Cloud (BDC) would contain.
Agents/UI never import this file directly — only data_product.py reads it.

=============================================================================
SCENARIO CATALOGUE (8 scenarios across 5 events)
=============================================================================

EVENT A — Shanghai congestion (4-day delay, HAS systemic historical pattern)
  - CNSHA-1001 → Helios (platinum) + Triton (gold)  => RISK  [multi-customer]
  - CNSHA-1002 → Orion (gold, $620K)                => RISK  [revenue trigger]
  - CNSHA-1003 → Local Distributor TH (std, $90K)   => NON-RISK
  - CNSHA-1004 → Regional Reseller VN (std, $180K)  => NON-RISK

EVENT B — Rotterdam strike (6-day delay, HAS recurring historical pattern)
  - NLRTM-2001 → Euro Retail Group (gold, $280K)    => RISK  [delay trigger]
  - NLRTM-2002 → France Industrial (std, $160K)     => RISK  [delay trigger]

EVENT C — Singapore weather (2-day delay, low impact)
  - SGSIN-3001 → Small Reseller MY (std, $55K)      => NON-RISK [noise filter]

EVENT D — LA congestion (7-day delay, NO commitments)
  - USLAX-4001, USLAX-4002 → (no commitments)       => NON-RISK [relevance filter]

EVENT E — Busan customs hold (5-day delay, NO historical pattern)   [NEW]
  - KRPUS-5001 → Apex Aerospace (platinum, $810K)   => RISK  [one-off forecast]

=============================================================================
SKU COVERAGE (inventory + alternate suppliers exist for every RISK shipment)
=============================================================================
  SKU-ALPHA   (CNSHA-1001) : inventory + alt supplier  ✓
  SKU-BETA    (CNSHA-1002) : inventory + alt supplier  ✓  [added]
  SKU-EPSILON (NLRTM-2001) : inventory + alt supplier  ✓
  SKU-ZETA    (NLRTM-2002) : inventory + alt supplier  ✓  [added]
  SKU-OMEGA   (KRPUS-5001) : inventory + alt supplier  ✓  [added, one-off scenario]
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from .models import (
    Shipment,
    Supplier,
    InventoryPosition,
    Commitment,
    PortEvent,
    DisruptionPattern,
)

NOW = datetime(2026, 5, 27, 13, 0, tzinfo=timezone.utc)

# =============================================================================
# DP5 — Port & Logistics Events (5 total)
# =============================================================================
PORT_EVENTS: list[PortEvent] = [
    # EVENT A (RISK) — Shanghai congestion. 4-day delay (< 5) so risk depends on
    # revenue/tier thresholds. Has a systemic historical pattern (4 in 3 years).
    PortEvent(
        event_id="EVT-CNSHA-2026-05-27-001",
        event_type="port_congestion",
        location_type="port",
        location_code="CNSHA",
        location_name="Port of Shanghai",
        severity="high",
        started_at=datetime(2026, 5, 27, 2, 0, tzinfo=timezone.utc),
        expected_duration_days=4,
        cause_description="Congestion due to storm recovery and yard backlog",
        affected_vessels=20,
        affected_carrier_ids=["MAERSK-PAC", "COSCO-AS"],
        reported_by="Port Ops Feed",
        confidence="high",
        last_updated=NOW,
    ),

    # EVENT B (RISK) — Rotterdam strike. 6-day delay (>= 5) so any affected
    # shipment with a commitment becomes a risk. Recurring historical pattern.
    PortEvent(
        event_id="EVT-NLRTM-2026-05-27-001",
        event_type="port_congestion",
        location_type="port",
        location_code="NLRTM",
        location_name="Port of Rotterdam",
        severity="high",
        started_at=datetime(2026, 5, 27, 3, 0, tzinfo=timezone.utc),
        expected_duration_days=6,
        cause_description="Labour strike at terminal gates",
        affected_vessels=18,
        affected_carrier_ids=["MAERSK-EU"],
        reported_by="EU Port Authority",
        confidence="medium",
        last_updated=NOW,
    ),

    # EVENT C (NON-RISK) — Singapore weather. 2-day delay, low-value standard
    # customer. Should be filtered out (noise).
    PortEvent(
        event_id="EVT-SGSIN-2026-05-27-001",
        event_type="weather",
        location_type="port",
        location_code="SGSIN",
        location_name="Port of Singapore",
        severity="low",
        started_at=datetime(2026, 5, 27, 8, 0, tzinfo=timezone.utc),
        expected_duration_days=2,
        cause_description="Heavy rain advisory, minor operational slowdown",
        affected_vessels=3,
        affected_carrier_ids=["ONE"],
        reported_by="Weather Service",
        confidence="high",
        last_updated=NOW,
    ),

    # EVENT D (NON-RISK) — LA congestion. 7-day delay (>= 5) BUT affected
    # shipments have NO commitments. Should be filtered out (no business exposure).
    PortEvent(
        event_id="EVT-USLAX-2026-05-27-001",
        event_type="port_congestion",
        location_type="port",
        location_code="USLAX",
        location_name="Port of Los Angeles",
        severity="medium",
        started_at=datetime(2026, 5, 27, 5, 0, tzinfo=timezone.utc),
        expected_duration_days=7,
        cause_description="Yard congestion, slow crane availability",
        affected_vessels=12,
        affected_carrier_ids=["HAPAG"],
        reported_by="Port Authority",
        confidence="medium",
        last_updated=NOW,
    ),

    # EVENT E (RISK) — Busan customs hold. 5-day delay, platinum customer.
    # NO historical pattern at KRPUS => forecast must classify as one-off.
    # This is the discrimination scenario: proves the forecast agent reasons
    # from data, not from script.
    PortEvent(
        event_id="EVT-KRPUS-2026-05-27-001",
        event_type="customs_delay",
        location_type="port",
        location_code="KRPUS",
        location_name="Port of Busan",
        severity="high",
        started_at=datetime(2026, 5, 27, 6, 0, tzinfo=timezone.utc),
        expected_duration_days=5,
        cause_description="Unscheduled customs inspection hold on inbound containers",
        affected_vessels=4,
        affected_carrier_ids=["HMM"],
        reported_by="Customs Authority Feed",
        confidence="high",
        last_updated=NOW,
    ),
]

# =============================================================================
# DP1 — Shipments
# =============================================================================
SHIPMENTS: list[Shipment] = [
    # ---- EVENT A (CNSHA) impacts 4 shipments ----
    Shipment(
        po_number="PO-CNSHA-1001",
        entity="PrismCorp APAC",
        supplier_id="SUP-01",
        material_sku="SKU-ALPHA",
        quantity=8000,
        uom="units",
        containers=10,
        shipment_value_usd=1_500_000.0,
        source_port_code="CNSHA",
        destination_port_code="HKHKG",
        original_eta=date(2026, 6, 2),
        current_eta=date(2026, 6, 2),
        status="in_transit",
        carrier_id="MAERSK-PAC",
        last_updated=NOW,
    ),
    Shipment(
        po_number="PO-CNSHA-1002",
        entity="PrismCorp APAC",
        supplier_id="SUP-02",
        material_sku="SKU-BETA",
        quantity=4200,
        uom="units",
        containers=6,
        shipment_value_usd=620_000.0,
        source_port_code="CNSHA",
        destination_port_code="JPTYO",
        original_eta=date(2026, 6, 3),
        current_eta=date(2026, 6, 3),
        status="in_transit",
        carrier_id="COSCO-AS",
        last_updated=NOW,
    ),
    Shipment(
        po_number="PO-CNSHA-1003",
        entity="PrismCorp APAC",
        supplier_id="SUP-03",
        material_sku="SKU-GAMMA",
        quantity=900,
        uom="units",
        containers=1,
        shipment_value_usd=90_000.0,
        source_port_code="CNSHA",
        destination_port_code="THBKK",
        original_eta=date(2026, 6, 4),
        current_eta=date(2026, 6, 4),
        status="in_transit",
        carrier_id="MAERSK-PAC",
        last_updated=NOW,
    ),
    Shipment(
        po_number="PO-CNSHA-1004",
        entity="PrismCorp APAC",
        supplier_id="SUP-04",
        material_sku="SKU-DELTA",
        quantity=1500,
        uom="units",
        containers=2,
        shipment_value_usd=180_000.0,
        source_port_code="CNSHA",
        destination_port_code="VNSGN",
        original_eta=date(2026, 6, 5),
        current_eta=date(2026, 6, 5),
        status="in_transit",
        carrier_id="COSCO-AS",
        last_updated=NOW,
    ),

    # ---- EVENT B (NLRTM) impacts 2 shipments ----
    Shipment(
        po_number="PO-NLRTM-2001",
        entity="PrismCorp EMEA",
        supplier_id="SUP-10",
        material_sku="SKU-EPSILON",
        quantity=5000,
        uom="units",
        containers=8,
        shipment_value_usd=900_000.0,
        source_port_code="NLRTM",
        destination_port_code="GBFXT",
        original_eta=date(2026, 6, 6),
        current_eta=date(2026, 6, 6),
        status="in_transit",
        carrier_id="MAERSK-EU",
        last_updated=NOW,
    ),
    Shipment(
        po_number="PO-NLRTM-2002",
        entity="PrismCorp EMEA",
        supplier_id="SUP-11",
        material_sku="SKU-ZETA",
        quantity=2600,
        uom="units",
        containers=4,
        shipment_value_usd=310_000.0,
        source_port_code="NLRTM",
        destination_port_code="FRLEH",
        original_eta=date(2026, 6, 7),
        current_eta=date(2026, 6, 7),
        status="in_transit",
        carrier_id="MAERSK-EU",
        last_updated=NOW,
    ),

    # ---- EVENT C (SGSIN) impacts 1 shipment (non-risk) ----
    Shipment(
        po_number="PO-SGSIN-3001",
        entity="PrismCorp APAC",
        supplier_id="SUP-20",
        material_sku="SKU-THETA",
        quantity=600,
        uom="units",
        containers=1,
        shipment_value_usd=55_000.0,
        source_port_code="SGSIN",
        destination_port_code="MYTPP",
        original_eta=date(2026, 6, 4),
        current_eta=date(2026, 6, 4),
        status="in_transit",
        carrier_id="ONE",
        last_updated=NOW,
    ),

    # ---- EVENT D (USLAX) impacts 2 shipments (NO commitments => non-risk) ----
    Shipment(
        po_number="PO-USLAX-4001",
        entity="PrismCorp AMER",
        supplier_id="SUP-30",
        material_sku="SKU-IOTA",
        quantity=3000,
        uom="units",
        containers=4,
        shipment_value_usd=410_000.0,
        source_port_code="USLAX",
        destination_port_code="USSEA",
        original_eta=date(2026, 6, 6),
        current_eta=date(2026, 6, 6),
        status="in_transit",
        carrier_id="HAPAG",
        last_updated=NOW,
    ),
    Shipment(
        po_number="PO-USLAX-4002",
        entity="PrismCorp AMER",
        supplier_id="SUP-31",
        material_sku="SKU-KAPPA",
        quantity=1200,
        uom="units",
        containers=2,
        shipment_value_usd=140_000.0,
        source_port_code="USLAX",
        destination_port_code="USOAK",
        original_eta=date(2026, 6, 6),
        current_eta=date(2026, 6, 6),
        status="in_transit",
        carrier_id="HAPAG",
        last_updated=NOW,
    ),

    # ---- EVENT E (KRPUS) impacts 1 shipment (one-off RISK) ----  [NEW]
    Shipment(
        po_number="PO-KRPUS-5001",
        entity="PrismCorp APAC",
        supplier_id="SUP-40",
        material_sku="SKU-OMEGA",
        quantity=3500,
        uom="units",
        containers=5,
        shipment_value_usd=1_100_000.0,
        source_port_code="KRPUS",
        destination_port_code="JPTYO",
        original_eta=date(2026, 6, 5),
        current_eta=date(2026, 6, 5),
        status="in_transit",
        carrier_id="HMM",
        last_updated=NOW,
    ),
]

# =============================================================================
# DP4 — Customer Commitments
# =============================================================================
COMMITMENTS: list[Commitment] = [
    # ---- EVENT A : CNSHA-1001 => RISK, MULTI-CUSTOMER (platinum + gold) ----
    Commitment(
        commitment_id="CMT-CNSHA-1001-A",
        customer_id="CUST-A",
        customer_name="Helios Energy Systems",
        customer_region="Singapore",
        contract_tier="platinum",
        sku="SKU-ALPHA",
        committed_quantity=6000,
        deadline=date(2026, 6, 8),
        supplying_po="PO-CNSHA-1001",
        sla_penalty_per_day_usd=15_000.0,
        sla_penalty_cap_usd=100_000.0,
        order_value_usd=740_000.0,
        status="pending",
    ),
    # NEW second commitment on the SAME shipment — the multi-customer scenario
    Commitment(
        commitment_id="CMT-CNSHA-1001-B",
        customer_id="CUST-H",
        customer_name="Triton Marine Technologies",
        customer_region="Malaysia",
        contract_tier="gold",
        sku="SKU-ALPHA",
        committed_quantity=2000,
        deadline=date(2026, 6, 10),
        supplying_po="PO-CNSHA-1001",
        sla_penalty_per_day_usd=6_000.0,
        sla_penalty_cap_usd=40_000.0,
        order_value_usd=500_000.0,
        status="pending",
    ),

    # ---- EVENT A : CNSHA-1002 => RISK (revenue >= 250k) ----
    Commitment(
        commitment_id="CMT-CNSHA-1002",
        customer_id="CUST-B",
        customer_name="Orion Industrial Systems",
        customer_region="Japan",
        contract_tier="gold",
        sku="SKU-BETA",
        committed_quantity=4200,
        deadline=date(2026, 6, 9),
        supplying_po="PO-CNSHA-1002",
        sla_penalty_per_day_usd=6_500.0,
        sla_penalty_cap_usd=45_000.0,
        order_value_usd=620_000.0,
        status="pending",
    ),

    # ---- EVENT A : CNSHA-1003 => NON-RISK ----
    Commitment(
        commitment_id="CMT-CNSHA-1003",
        customer_id="CUST-C",
        customer_name="Local Distributor TH",
        customer_region="Thailand",
        contract_tier="standard",
        sku="SKU-GAMMA",
        committed_quantity=900,
        deadline=date(2026, 6, 10),
        supplying_po="PO-CNSHA-1003",
        sla_penalty_per_day_usd=1_000.0,
        sla_penalty_cap_usd=5_000.0,
        order_value_usd=90_000.0,
        status="pending",
    ),

    # ---- EVENT A : CNSHA-1004 => NON-RISK ----
    Commitment(
        commitment_id="CMT-CNSHA-1004",
        customer_id="CUST-D",
        customer_name="Regional Reseller VN",
        customer_region="Vietnam",
        contract_tier="standard",
        sku="SKU-DELTA",
        committed_quantity=1500,
        deadline=date(2026, 6, 11),
        supplying_po="PO-CNSHA-1004",
        sla_penalty_per_day_usd=2_000.0,
        sla_penalty_cap_usd=10_000.0,
        order_value_usd=180_000.0,
        status="pending",
    ),

    # ---- EVENT B : both shipments => RISK (delay >= 5) ----
    Commitment(
        commitment_id="CMT-NLRTM-2001",
        customer_id="CUST-E",
        customer_name="Euro Retail Group",
        customer_region="UK",
        contract_tier="gold",
        sku="SKU-EPSILON",
        committed_quantity=5000,
        deadline=date(2026, 6, 12),
        supplying_po="PO-NLRTM-2001",
        sla_penalty_per_day_usd=5_000.0,
        sla_penalty_cap_usd=40_000.0,
        order_value_usd=280_000.0,
        status="pending",
    ),
    Commitment(
        commitment_id="CMT-NLRTM-2002",
        customer_id="CUST-F",
        customer_name="France Industrial Parts",
        customer_region="France",
        contract_tier="standard",
        sku="SKU-ZETA",
        committed_quantity=2600,
        deadline=date(2026, 6, 12),
        supplying_po="PO-NLRTM-2002",
        sla_penalty_per_day_usd=2_500.0,
        sla_penalty_cap_usd=18_000.0,
        order_value_usd=160_000.0,
        status="pending",
    ),

    # ---- EVENT C : NON-RISK ----
    Commitment(
        commitment_id="CMT-SGSIN-3001",
        customer_id="CUST-G",
        customer_name="Small Reseller MY",
        customer_region="Malaysia",
        contract_tier="standard",
        sku="SKU-THETA",
        committed_quantity=600,
        deadline=date(2026, 6, 12),
        supplying_po="PO-SGSIN-3001",
        sla_penalty_per_day_usd=500.0,
        sla_penalty_cap_usd=2_500.0,
        order_value_usd=55_000.0,
        status="pending",
    ),

    # ---- EVENT E : KRPUS-5001 => RISK (platinum), one-off (no pattern) ----  [NEW]
    Commitment(
        commitment_id="CMT-KRPUS-5001",
        customer_id="CUST-I",
        customer_name="Apex Aerospace Components",
        customer_region="Japan",
        contract_tier="platinum",
        sku="SKU-OMEGA",
        committed_quantity=3500,
        deadline=date(2026, 6, 9),
        supplying_po="PO-KRPUS-5001",
        sla_penalty_per_day_usd=12_000.0,
        sla_penalty_cap_usd=80_000.0,
        order_value_usd=810_000.0,
        status="pending",
    ),

    # NOTE: EVENT D (USLAX) intentionally has NO commitments
]

# =============================================================================
# DP3 — Inventory (one transferable position per RISK SKU)
# =============================================================================
INVENTORY: list[InventoryPosition] = [
    # SKU-ALPHA (CNSHA-1001) — transfer to APAC
    InventoryPosition(
        sku="SKU-ALPHA",
        entity="PrismCorp EMEA",
        warehouse_id="WH-ROT-01",
        warehouse_region="Rotterdam",
        on_hand=4000,
        committed=0,
        available=4000,
        in_transit_to=0,
        transfer_lead_days_to={"PrismCorp APAC": 11},
        transfer_cost_per_unit_usd={"PrismCorp APAC": 10.5},
        last_updated=NOW,
    ),
    # SKU-BETA (CNSHA-1002) — transfer to APAC  [added]
    InventoryPosition(
        sku="SKU-BETA",
        entity="PrismCorp AMER",
        warehouse_id="WH-NJ-02",
        warehouse_region="New Jersey",
        on_hand=3000,
        committed=200,
        available=2800,
        in_transit_to=0,
        transfer_lead_days_to={"PrismCorp APAC": 13},
        transfer_cost_per_unit_usd={"PrismCorp APAC": 12.0},
        last_updated=NOW,
    ),
    # SKU-EPSILON (NLRTM-2001) — transfer to EMEA
    InventoryPosition(
        sku="SKU-EPSILON",
        entity="PrismCorp AMER",
        warehouse_id="WH-NJ-01",
        warehouse_region="New Jersey",
        on_hand=2500,
        committed=200,
        available=2300,
        in_transit_to=0,
        transfer_lead_days_to={"PrismCorp EMEA": 7},
        transfer_cost_per_unit_usd={"PrismCorp EMEA": 9.2},
        last_updated=NOW,
    ),
    # SKU-ZETA (NLRTM-2002) — transfer to EMEA  [added]
    InventoryPosition(
        sku="SKU-ZETA",
        entity="PrismCorp APAC",
        warehouse_id="WH-SIN-01",
        warehouse_region="Singapore",
        on_hand=3200,
        committed=600,
        available=2600,
        in_transit_to=0,
        transfer_lead_days_to={"PrismCorp EMEA": 12},
        transfer_cost_per_unit_usd={"PrismCorp EMEA": 8.4},
        last_updated=NOW,
    ),
    # SKU-OMEGA (KRPUS-5001) — transfer to APAC  [added, one-off scenario]
    InventoryPosition(
        sku="SKU-OMEGA",
        entity="PrismCorp EMEA",
        warehouse_id="WH-HAM-01",
        warehouse_region="Hamburg",
        on_hand=2000,
        committed=0,
        available=2000,
        in_transit_to=0,
        transfer_lead_days_to={"PrismCorp APAC": 14},
        transfer_cost_per_unit_usd={"PrismCorp APAC": 13.5},
        last_updated=NOW,
    ),
]

# =============================================================================
# DP2 — Suppliers (primary + at least one alternate per RISK SKU)
# =============================================================================
SUPPLIERS: list[Supplier] = [
    # ---- Primary suppliers (referenced by shipments) ----
    Supplier(
        supplier_id="SUP-01",
        supplier_name="Meridian Pacific Components Ltd",
        region="China",
        tier="tier1_strategic",
        quality_rating="AA",
        skus_supplied=["SKU-ALPHA", "SKU-GAMMA", "SKU-DELTA"],
        typical_lead_time_days=18,
        price_index=1.00,
        max_capacity_per_month=12000,
        current_capacity_status="constrained",
        contract_status="active",
    ),
    Supplier(
        supplier_id="SUP-02",
        supplier_name="Eastwind Manufacturing Co",
        region="China",
        tier="tier1",
        quality_rating="A",
        skus_supplied=["SKU-BETA"],
        typical_lead_time_days=16,
        price_index=1.00,
        max_capacity_per_month=9000,
        current_capacity_status="constrained",
        contract_status="active",
    ),

    # ---- Alternate suppliers (one per RISK SKU, exclude primary) ----
    # SKU-ALPHA alternate
    Supplier(
        supplier_id="SUP-12",
        supplier_name="Sentinel Filtration GmbH",
        region="Germany",
        tier="tier1",
        quality_rating="AA",
        skus_supplied=["SKU-ALPHA", "SKU-EPSILON"],
        typical_lead_time_days=14,
        price_index=1.08,
        max_capacity_per_month=8500,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
    # SKU-BETA alternate  [added]
    Supplier(
        supplier_id="SUP-13",
        supplier_name="Hokkaido Precision Works",
        region="Japan",
        tier="tier1",
        quality_rating="AA",
        skus_supplied=["SKU-BETA"],
        typical_lead_time_days=12,
        price_index=1.11,
        max_capacity_per_month=7000,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
    # SKU-ZETA alternate  [added]
    Supplier(
        supplier_id="SUP-14",
        supplier_name="Iberia Components SA",
        region="Spain",
        tier="tier2",
        quality_rating="A",
        skus_supplied=["SKU-ZETA"],
        typical_lead_time_days=10,
        price_index=1.15,
        max_capacity_per_month=6000,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
    # SKU-OMEGA alternate  [added, one-off scenario]
    Supplier(
        supplier_id="SUP-15",
        supplier_name="Nordic Aerotech AB",
        region="Sweden",
        tier="tier1",
        quality_rating="AA",
        skus_supplied=["SKU-OMEGA"],
        typical_lead_time_days=15,
        price_index=1.10,
        max_capacity_per_month=5000,
        current_capacity_status="available",
        contract_status="framework_only",
    ),
]

# =============================================================================
# DP6 — Historical Patterns
# Note: deliberately NO pattern for KRPUS (the one-off scenario).
# =============================================================================
PATTERNS: list[DisruptionPattern] = [
    DisruptionPattern(
        pattern_id="PAT-CNSHA-PORT_CONGESTION",
        event_type="port_congestion",
        location_code="CNSHA",
        occurrence_count=4,
        time_window="last_3_years",
        avg_duration_days=6.0,
        avg_recovery_days=5.0,
        seasonality_pattern="typhoon_season",
        last_occurrence_date=date(2025, 7, 14),
        typical_root_causes=["typhoon", "yard_backlog"],
        typical_resolution_paths=["inventory_transfer", "alternate_supplier"],
    ),
    DisruptionPattern(
        pattern_id="PAT-NLRTM-LABOUR",
        event_type="port_congestion",
        location_code="NLRTM",
        occurrence_count=3,
        time_window="last_5_years",
        avg_duration_days=5.5,
        avg_recovery_days=4.0,
        seasonality_pattern="none",
        last_occurrence_date=date(2024, 10, 3),
        typical_root_causes=["labour_dispute"],
        typical_resolution_paths=["alternate_port", "expedited_trucking"],
    ),
    # NOTE: No pattern for KRPUS customs_delay => forecast agent must classify
    # EVENT E as one-off with low confidence.
]