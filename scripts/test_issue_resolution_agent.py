from ai.agents.logistics_issue_resolution import run

if __name__ == "__main__":
    result = run(
        po_number="PO-PRM-2026-08-2241",
        triggering_event_id="EVT-CNSHA-2026-05-26-001",
    )
    print("\n=== Logistics Issue Resolution ===")
    print(result.model_dump(indent=2))