from backend.bdc.data_products import (
    get_active_port_events,
    get_shipments_at_port,
    get_commitments_for_shipment,
)


def test_get_active_port_events():
    events = get_active_port_events()
    assert len(events) == 1
    assert events[0].location_code == "CNSHA"


def test_get_shipments_at_port():
    shipments = get_shipments_at_port("CNSHA")
    assert len(shipments) == 1


def test_get_commitments_for_shipment():
    commitments = get_commitments_for_shipment("PO-PRM-2026-08-2241")
    assert len(commitments) >= 1