from dotenv import load_dotenv
load_dotenv()

from ai.agents.logistics_issue_resolution import run

# Use the PO and event ID from your seed data
result = run(
    po_number="PO-CNSHA-1001",
    triggering_event_id="EVT-CNSHA-2026-05-27-001",
)

print(f"\nRisk: {result.risk_title}")
print(f"Severity: {result.severity}\n")
print(f"Summary: {result.summary}\n")
print(f"Root causes:")
for c in result.root_causes:
    print(f"  - {c}")
print(f"\nBusiness impact:")
print(f"  Customers at risk:   {result.business_impact.customers_at_risk}")
print(f"  SLA exposure:        ${result.business_impact.sla_exposure_usd:,}")
print(f"  Predicted delay:     {result.business_impact.predicted_delay_days} days")
print(f"  Revenue at risk:     ${result.business_impact.revenue_at_risk_usd:,}")
print(f"\nEvidence:")
for e in result.evidence:
    print(f"  - {e}")