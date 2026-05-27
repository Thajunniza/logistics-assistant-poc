"""
Tests for BDC seed data.

These tests validate that the POC seed data represents a coherent,
internally consistent snapshot of harmonised BDC data.

IMPORTANT:
- These tests do NOT validate business logic.
- These tests do NOT validate agent reasoning.
- They only ensure that the mocked BDC layer is well-formed.

If these tests fail, the POC scenario itself is broken.
"""

from backend.bdc import seed_data


# =============================================================================
# DP5 — Port and Logistics Events
# =============================================================================
def test_seed_has_single_port_event():
    """POC scenario should contain exactly one active disruption event."""
    assert len(seed_data.PORT_EVENTS) == 1


def test_port_event_has_location_code():
    event = seed_data.PORT_EVENTS[0]
    assert event.location_code
    assert isinstance(event.location_code, str)


# =============================================================================
# DP1 — Shipments
# =============================================================================
def test_seed_has_shipments():
    """At least one shipment must exist in the scenario."""
    assert len(seed_data.SHIPMENTS) > 0


def test_shipment_ports_match_event():
    """Shipment source or destination must match the port event."""
    event = seed_data.PORT_EVENTS[0]
    shipment = seed_data.SHIPMENTS[0]

    assert (
        shipment.source_port_code == event.location_code
        or shipment.destination_port_code == event.location_code
    )


# =============================================================================
# DP4 — Customer Commitments
# =============================================================================
def test_commitments_link_to_shipment():
    """All commitments must reference an existing shipment PO."""
    po_numbers = {s.po_number for s in seed_data.SHIPMENTS}

    for commitment in seed_data.COMMITMENTS:
        assert commitment.supplying_po in po_numbers


def test_at_least_one_platinum_commitment():
    """POC scenario must include at least one Platinum-tier customer."""
    assert any(
        c.contract_tier == "platinum" for c in seed_data.COMMITMENTS
    )


# =============================================================================
# DP3 — Inventory
# =============================================================================
def test_inventory_exists_for_shipment_sku():
    """Inventory must exist for the SKU affected by the shipment."""
    shipment = seed_data.SHIPMENTS[0]
    skus_in_inventory = {i.sku for i in seed_data.INVENTORY}

    assert shipment.material_sku in skus_in_inventory


# =============================================================================
# DP2 — Suppliers
# =============================================================================
def test_suppliers_exist_for_sku():
    """At least one supplier must be able to supply the shipment SKU."""
    shipment = seed_data.SHIPMENTS[0]

    assert any(
        shipment.material_sku in s.skus_supplied
        for s in seed_data.SUPPLIERS
    )


# =============================================================================
# DP6 — Historical Disruption Patterns
# =============================================================================
def test_historical_pattern_exists_for_event():
    """Historical pattern must exist for the active port event."""
    event = seed_data.PORT_EVENTS[0]

    assert any(
        p.event_type == event.event_type
        and p.location_code == event.location_code
        for p in seed_data.PATTERNS
    )