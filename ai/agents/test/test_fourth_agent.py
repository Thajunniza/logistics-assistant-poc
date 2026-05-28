from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------
# Agent imports
# ---------------------------------------------------------
from ai.agents.logistics_issue_resolution import run as run_agent_1
from ai.agents.pattern_forecast import run as run_agent_2
from ai.agents.inventory_supervisor import run as run_agent_3
from ai.agents.transport_dispatcher import run as run_agent_4


PO_NUMBER = "PO-CNSHA-1001"
EVENT_ID = "EVT-CNSHA-2026-05-27-001"
APPROVED_OPTION_ID = "OPT-C"  # simulate human approval


def main():
    # ---------------------------------------------------------
    # Agent 1 — Diagnosis
    # ---------------------------------------------------------
    diagnosis = run_agent_1(
        po_number=PO_NUMBER,
        triggering_event_id=EVENT_ID,
    )

    print("\n==============================")
    print("AGENT 1 — DIAGNOSIS")
    print("==============================")
    print(f"Risk title: {diagnosis.risk_title}")
    print(f"Severity:   {diagnosis.severity}")
    print(f"Delay:      {diagnosis.business_impact.predicted_delay_days} days")
    print(f"Revenue:    ${diagnosis.business_impact.revenue_at_risk_usd:,.0f}")

    # ---------------------------------------------------------
    # Agent 2 — Pattern Forecast
    # ---------------------------------------------------------
    forecast = run_agent_2(
        po_number=PO_NUMBER,
        triggering_event_id=EVENT_ID,
        diagnosis=diagnosis,
    )

    print("\n==============================")
    print("AGENT 2 — PATTERN FORECAST")
    print("==============================")
    print(f"Classification: {forecast.classification.upper()}")
    print(f"Confidence:     {forecast.confidence.upper()}")
    print(f"Expected dur.:  {forecast.expected_duration_days} days")
    print(f"Posture:        {forecast.recommendation.upper()}")
    print(f"Narrative:      {forecast.pattern_narrative}")

    # ---------------------------------------------------------
    # Agent 3 — Inventory Supervisor
    # ---------------------------------------------------------
    inventory = run_agent_3(
        po_number=PO_NUMBER,
        diagnosis=diagnosis,
        pattern_forecast=forecast,
    )

    print("\n==============================")
    print("AGENT 3 — INVENTORY SUPERVISOR")
    print("==============================")

    for opt in inventory.options:
        print(f"\n--- {opt.option_id} ---")
        print(f"Title:        {opt.title}")
        print(f"Approach:     {opt.approach}")
        print(f"Cost delta:   ${opt.cost_delta_usd:,.0f}")
        print(f"SLA recovery: {opt.sla_recovery_days} days")
        print(f"Trade-off:    {opt.trade_off}")
        print(f"Recommended:  {opt.recommended}")

    print("\n--- Supervisor Notes ---")
    print(inventory.notes)

    # ---------------------------------------------------------
    # Agent 4 — Transport Dispatching (SIMULATED EXECUTION)
    # ---------------------------------------------------------
    dispatch_plan = run_agent_4(
        po_number=PO_NUMBER,
        triggering_event_id=EVENT_ID,
        approved_option_id=APPROVED_OPTION_ID,
        diagnosis=diagnosis,
        pattern_forecast=forecast,
        inventory_output=inventory,
    )

    print("\n==============================")
    print("AGENT 4 — TRANSPORT DISPATCH PLAN")
    print("==============================")
    print(f"Approved option: {dispatch_plan.approved_option_id}")
    print(f"Status:          {dispatch_plan.status}")
    print(f"Completion ETA:  {dispatch_plan.completion_eta_minutes} minutes")

    print("\n--- Execution Steps (Ordered) ---")
    for step in dispatch_plan.execution_steps:
        print(
            f"{step.step_number}. [{step.target_system}] "
            f"{step.action} — {step.details} "
            f"(~{step.estimated_time_minutes} min)"
        )

    print("\n--- Notifications ---")
    for n in dispatch_plan.notifications:
        print(f"- {n.audience}: {n.message}")


if __name__ == "__main__":
    main()