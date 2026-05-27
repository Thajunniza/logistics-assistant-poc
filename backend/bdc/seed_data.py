"""
BDC data product query interface.

This is the single chokepoint between the agent crew and the data layer.
Every agent calls one of these functions; no agent reads seed data directly.

In production: each function's body is replaced by a Datasphere client call
that queries the corresponding BDC data product. Function signatures and
return types stay identical, so the swap is contained to this module.

The six data products correspond to:
  DP1 Shipment                       -> get_shipment, get_shipments_at_port
  DP2 Supplier and Alternates        -> get_supplier, get_alternate_suppliers
  DP3 Cross-Entity Inventory         -> get_inventory_for_sku
  DP4 Customer Commitments           -> get_commitments_for_shipment
  DP5 Port and Logistics Events      -> get_active_port_events, get_events_for_port
  DP6 Historical Disruption Patterns -> get_historical_pattern
"""
from __future__ import annotations

import logging
from typing import Optional

from . import _seed_data as seed
from .bdc_models import (
    Commitment,
    DisruptionPattern,
    EventType,
    InventoryPosition,
    PortEvent,
    Shipment,
    ShipmentStatus,
    Supplier,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DP1 — Shipment
# ============================================================================
def get_shipment(po_number: str) -> Optional[Shipment]:
    """Fetch a single shipment by PO number."""
    logger.debug("BDC query: get_shipment(%s)", po_number)
    return next((s for s in seed.SHIPMENTS if s.po_number == po_number), None)


def get_shipments_at_port(
    port_code: str,
    status: Optional[ShipmentStatus] = None,
) -> list[Shipment]:
    """All shipments inbound to or sourcing from the given port (UN/LOCODE)."""
    logger.debug("BDC query: get_shipments_at_port(%s, status=%s)", port_code, status)
    matches = [
        s for s in seed.SHIPMENTS
        if s.source_port_code == port_code or s.destination_port_code == port_code
    ]
    if status is not None:
        matches = [s for s in matches if s.status == status]
    return matches


# ============================================================================
# DP2 — Supplier and Alternate Suppliers
# ============================================================================
def get_supplier(supplier_id: str) -> Optional[Supplier]:
    """Single supplier lookup."""
    logger.debug("BDC query: get_supplier(%s)", supplier_id)
    return next((s for s in seed.SUPPLIERS if s.supplier_id == supplier_id), None)


def get_alternate_suppliers(sku: str, exclude_supplier_id: str = "") -> list[Supplier]:
    """All suppliers that can provide the given SKU, optionally excluding one."""
    logger.debug(
        "BDC query: get_alternate_suppliers(sku=%s, exclude=%s)", sku, exclude_supplier_id
    )
    return [
        s for s in seed.SUPPLIERS
        if sku in s.skus_supplied and s.supplier_id != exclude_supplier_id
    ]


# ============================================================================
# DP3 — Cross-Entity Inventory Position
# ============================================================================
def get_inventory_for_sku(sku: str) -> list[InventoryPosition]:
    """Inventory positions for an SKU across all entities and warehouses."""
    logger.debug("BDC query: get_inventory_for_sku(%s)", sku)
    return [p for p in seed.INVENTORY if p.sku == sku]


# ============================================================================
# DP4 — Customer Commitments
# ============================================================================
def get_commitments_for_shipment(po_number: str) -> list[Commitment]:
    """All customer commitments that depend on the given shipment."""
    logger.debug("BDC query: get_commitments_for_shipment(%s)", po_number)
    return [c for c in seed.COMMITMENTS if c.supplying_po == po_number]


# ============================================================================
# DP5 — Port and Logistics Events
# ============================================================================
def get_active_port_events() -> list[PortEvent]:
    """All currently-active disruption events."""
    logger.debug("BDC query: get_active_port_events()")
    return list(seed.PORT_EVENTS)


def get_events_for_port(port_code: str) -> list[PortEvent]:
    """Disruption events affecting a specific port."""
    logger.debug("BDC query: get_events_for_port(%s)", port_code)
    return [e for e in seed.PORT_EVENTS if e.location_code == port_code]


# ============================================================================
# DP6 — Historical Disruption Patterns
# ============================================================================
def get_historical_pattern(
    event_type: EventType,
    location_code: str,
) -> Optional[DisruptionPattern]:
    """Lookup historical pattern for this event type at this location."""
    logger.debug("BDC query: get_historical_pattern(%s, %s)", event_type, location_code)
    return next(
        (p for p in seed.PATTERNS
         if p.event_type == event_type and p.location_code == location_code),
        None,
    )
