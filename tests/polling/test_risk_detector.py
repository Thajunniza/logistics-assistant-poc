from datetime import datetime, timezone

from backend.polling.risk_detector import run_risk_check


def test_risk_detection_finds_one_risk():
    now = datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc)
    risks = run_risk_check(now)

    assert len(risks) == 1

    risk = risks[0]
    assert risk.po_number == "PO-PRM-2026-08-2241"
    assert risk.risk_level == "HIGH"
    assert "Helios Energy Systems" in risk.customers_impacted
    assert risk.revenue_at_risk_usd >= 250_000