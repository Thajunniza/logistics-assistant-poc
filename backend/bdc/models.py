"""
Typed data models for the six BDC data products consumed by the Logistics Assistant.

These are the contracts between BDC (via Datasphere) and the agent crew. In
production, a Datasphere client returns instances of these classes. In the POC,
app/data/bdc_data_products.py returns instances of these classes from seed data.

The agents never look at SAP table names or non-SAP API payloads — they only
see these harmonised data products. That's the whole point of BDC, and these
models are the contract that makes the abstraction stick.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# DP1 — Shipment
# ============================================================================
ShipmentStatus = Literal["planned", "in_transit", "at_risk", "arrived", "cleared"]


class Shipment(BaseModel):
    """
    Single source of truth for any in-transit or planned shipment.
    Source: SAP S/4HANA. Composed by BDC from EKKO, EKPO, LIKP, VTTK, VTTP, VBKD.
    """
    po_number: str
    entity: str
    supplier_id: str
    material_sku: str
    quantity: int
    uom: str
    containers: int
    shipment_value_usd: float
    source_port_code: str
    destination_port_code: str
    original_eta: date
    current_eta: date
    status: ShipmentStatus
    carrier_id: str
    last_updated: datetime


# ============================================================================
# DP2 — Supplier and Alternate Suppliers
# ============================================================================
SupplierTier = Literal["tier1_strategic", "tier1", "tier2", "tier3"]
QualityRating = Literal["AA", "A", "B", "C"]
CapacityStatus = Literal["available", "constrained", "unavailable"]
ContractStatus = Literal["active", "framework_only", "none"]


class Supplier(BaseModel):
    """
    Suppliers and alternate suppliers, harmonised view.
    Source: SAP Ariba. Composed by BDC from LFA1, LFM1, Ariba Sourcing,
    Contracts, and Supplier Risk.
    """
    supplier_id: str
    supplier_name: str
    region: str
    tier: SupplierTier
    quality_rating: QualityRating
    skus_supplied: list[str]
    typical_lead_time_days: int
    price_index: float = Field(description="1.0 = baseline pricing")
    max_capacity_per_month: int
    current_capacity_status: CapacityStatus
    contract_status: ContractStatus


# ============================================================================
# DP3 — Cross-Entity Inventory Position
# ============================================================================
class InventoryPosition(BaseModel):
    """
    Real-time stock visibility across all five PrismCorp entities and warehouses.
    Source: SAP S/4HANA per-entity. Composed by BDC from MARD, MARC, MSEG, MKPF,
    EBAN, LIPS, with cross-entity harmonisation of SKU codes and computed
    transfer attributes.
    """
    sku: str
    entity: str
    warehouse_id: str
    warehouse_region: str
    on_hand: int
    committed: int
    available: int
    in_transit_to: int
    transfer_lead_days_to: dict[str, int] = Field(
        description="entity -> lead time days for transfer TO that entity"
    )
    transfer_cost_per_unit_usd: dict[str, float] = Field(
        description="entity -> cost per unit for transfer TO that entity"
    )
    last_updated: datetime


# ============================================================================
# DP4 — Customer Commitments
# ============================================================================
ContractTier = Literal["platinum", "gold", "silver", "standard"]
CommitmentStatus = Literal["pending", "at_risk", "fulfilled", "breached"]


class Commitment(BaseModel):
    """
    What we've promised to whom, when, with what penalty if we miss.
    Source: SAP S/4HANA SD. Composed by BDC from VBAK, VBAP, VBKD, VEDA,
    KNA1, KNB1, plus SLA contract terms. The supplying_po linkage is BDC's
    derived MRP attribute.
    """
    commitment_id: str
    customer_id: str
    customer_name: str
    customer_region: str
    contract_tier: ContractTier
    sku: str
    committed_quantity: int
    deadline: date
    supplying_po: str = Field(description="The shipment fulfilling this commitment")
    sla_penalty_per_day_usd: float
    sla_penalty_cap_usd: float
    order_value_usd: float
    status: CommitmentStatus


# ============================================================================
# DP5 — Port and Logistics Events
# ============================================================================
EventType = Literal[
    "port_congestion",
    "weather",
    "customs_delay",
    "carrier_disruption",
    "geopolitical",
]
LocationType = Literal["port", "region", "route"]
Severity = Literal["low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]


class PortEvent(BaseModel):
    """
    Real-time and recent disruption events from the non-SAP world.
    Source: NON-SAP (GCP-hosted port operations APIs, logistics providers,
    weather services). Path into BDC: GCP Pub/Sub -> SAP Integration Suite
    transformation -> BDC canonical "Port and Logistics Events" data product.
    """
    event_id: str
    event_type: EventType
    location_type: LocationType
    location_code: str = Field(description="UN/LOCODE for port, ISO for region")
    location_name: str
    severity: Severity
    started_at: datetime
    expected_duration_days: int
    cause_description: str
    affected_vessels: Optional[int] = None
    affected_carrier_ids: list[str] = Field(default_factory=list)
    reported_by: str
    confidence: Confidence
    last_updated: datetime


# ============================================================================
# DP6 — Historical Disruption Patterns
# ============================================================================
Seasonality = Literal[
    "none", "q1", "q2", "q3", "q4", "summer", "winter", "typhoon_season"
]


class DisruptionPattern(BaseModel):
    """
    Historical pattern lookup: "has this happened before, how often, how does
    it typically resolve?"
    Source: SAP BW (historical analytics) enriched by BDC. Updates via SAP's
    batch consumption pattern (Pattern 2 from the reference architecture).
    """
    pattern_id: str
    event_type: EventType
    location_code: str
    occurrence_count: int
    time_window: str = Field(description="e.g. 'last_3_years'")
    avg_duration_days: float
    avg_recovery_days: float
    seasonality_pattern: Seasonality
    last_occurrence_date: date
    typical_root_causes: list[str]
    typical_resolution_paths: list[str]
