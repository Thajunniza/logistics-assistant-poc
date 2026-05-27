"""
Manual runner for the Logistics Assistant POC.

This script executes the real risk-detection logic using the mocked
BDC data layer and prints the detected risks to the console.

Purpose:
- Validate behaviour end-to-end
- See real data flowing through the system
- Support demos and debugging

This is NOT a test and NOT production code.
"""

from datetime import datetime, timezone

from backend.polling.risk_detector import run_risk_check


def main():
    print("=" * 80)
    print("Running Logistics Assistant – Risk Detection (POC)")
    print("=" * 80)

    now = datetime.now(timezone.utc)
    print(f"\nCurrent time: {now.isoformat()}")

    print("\nExecuting risk check...\n")

    risks = run_risk_check(now)

    if not risks:
        print("✅ No material delivery risks detected.")
        return

    print(f"⚠️  Detected {len(risks)} material delivery risk(s):\n")

    for idx, risk in enumerate(risks, start=1):
        print(f"--- Risk #{idx} ---")
        print(f"Event ID           : {risk.event_id}")
        print(f"PO Number          : {risk.po_number}")
        print(f"Risk Level         : {risk.risk_level}")
        print(f"Cause              : {risk.cause}")
        print(f"Predicted Delay    : {risk.predicted_delay_days} days")
        print(f"Customers Impacted : {', '.join(risk.customers_impacted)}")
        print(f"Revenue at Risk    : ${risk.revenue_at_risk_usd:,.2f}")
        print(f"Detected At        : {risk.detected_at.isoformat()}")
        print()

    print("✅ Risk detection run completed.")


if __name__ == "__main__":
    main()