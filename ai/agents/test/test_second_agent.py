from dotenv import load_dotenv
load_dotenv()

from ai.agents.logistics_issue_resolution import run as run_agent_1
from ai.agents.pattern_forecast import run as run_agent_2

# First get the diagnosis from Agent 1
diagnosis = run_agent_1(
    po_number="PO-CNSHA-1001",
    triggering_event_id="EVT-CNSHA-2026-05-27-001",
)

print(f"\n--- Agent 1 (Diagnosis) ---")
print(f"Risk: {diagnosis.risk_title}")
print(f"Severity: {diagnosis.severity}\n")

# Then feed it to Agent 2
forecast = run_agent_2(
    po_number="PO-CNSHA-1001",
    triggering_event_id="EVT-CNSHA-2026-05-27-001",
    diagnosis=diagnosis)

print(f"--- Agent 2 (Pattern Forecast) ---")
print(f"Classification: {forecast.classification}")
print(f"Expected duration: {forecast.expected_duration_days} days")
print(f"Confidence: {forecast.confidence}\n")
print(f"Pattern narrative: {forecast.pattern_narrative}\n")
print(f"Recommendation: {forecast.recommendation}")
print(f"Rationale: {forecast.rationale}")