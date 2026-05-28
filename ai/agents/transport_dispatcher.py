"""
Transport Dispatching Agent (Agent 4) — POC (Simulated)

Robust design:
- Build the plan skeleton deterministically (guarantees schema validity)
- Use the LLM only to fill in:
  - step details text
  - notification messages text
- Never execute any real system calls (status='simulated')
- Enforce operational dependency order in code:
  1) Procurement (SAP Ariba) if needed
  2) Logistics (S/4HANA + TM)
  3) Customer comms (Notifications)
  4) Finance (Finance)
  + Structural follow-up (Strategic Sourcing) for hybrid/structural

This matches a governance-safe POC approach. 
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from ai.llm import call_llm
from ai.agents.schemas import (
    TransportDispatchPlanOutput,
    ExecutionStep,
    Notification,
    LogisticsIssueResolutionOutput,
    PatternForecastOutput,
    InventorySupervisorOutput,
)

from backend.bdc.data_products import (
    get_shipment,
    get_commitments_for_shipment,
)

logger = logging.getLogger(__name__)


# -----------------------------
# Internal helper schema (LLM only fills text)
# -----------------------------
class _DispatchTextFill(BaseModel):
    step_details: List[str] = Field(description="Details text for each step, same length/order as steps")
    notification_messages: List[str] = Field(description="Message text for each notification, same length/order as audiences")


SYSTEM_PROMPT = """\
You are the Transport Dispatching Agent.

You are given:
- an approved mitigation option (already chosen by a human)
- shipment and commitments context
- a dispatch plan skeleton with ordered steps and audiences

Your task:
- Fill in clear, concrete DETAILS for each step (1–2 sentences each)
- Fill in clear notification messages for each audience (1 sentence each)

Rules:
- Do NOT change step order.
- Do NOT add/remove steps.
- Do NOT add/remove audiences.
- Return STRICT JSON only. No markdown. No code fences. No trailing commas.
"""


def _find_option(inventory_output: InventorySupervisorOutput, approved_option_id: str):
    for opt in inventory_output.options:
        if opt.option_id == approved_option_id:
            return opt
    raise ValueError(f"Approved option_id {approved_option_id} not found in InventorySupervisorOutput")


def _build_plan_skeleton(
    approved_option_id: str,
    approach: str,
    posture: Optional[str],
) -> tuple[list[ExecutionStep], list[Notification]]:
    """
    Deterministic plan structure:
    - Procurement step appears for alternate_supplier/hybrid
    - Logistics always present (S/4HANA + TM)
    - Notifications always present
    - Finance always last
    - Structural follow-up appears for hybrid/structural posture
    """

    steps: list[ExecutionStep] = []

    # 1) Procurement / sourcing
    if approach in ("alternate_supplier", "hybrid"):
        steps.append(ExecutionStep(
            step_number=1,
            target_system="SAP Ariba",
            action="Create/confirm sourcing instruction",
            details="",  # filled by LLM
            estimated_time_minutes=60,
        ))

    # 2) Logistics execution (S/4 + TM)
    steps.append(ExecutionStep(
        step_number=len(steps) + 1,
        target_system="SAP S/4HANA",
        action="Release stock transfer / logistics execution",
        details="",
        estimated_time_minutes=45,
    ))
    steps.append(ExecutionStep(
        step_number=len(steps) + 1,
        target_system="SAP TM",
        action="Book/confirm transport capacity",
        details="",
        estimated_time_minutes=45,
    ))

    # 3) Customer communications
    steps.append(ExecutionStep(
        step_number=len(steps) + 1,
        target_system="Notifications",
        action="Notify customer-facing teams with mitigation plan",
        details="",
        estimated_time_minutes=15,
    ))

    # 4) Finance postings
    steps.append(ExecutionStep(
        step_number=len(steps) + 1,
        target_system="Finance",
        action="Post cost delta and accounting entries",
        details="",
        estimated_time_minutes=30,
    ))

    # Structural follow-up (only when posture demands it)
    if posture in ("structural", "hybrid") or approach == "hybrid":
        steps.append(ExecutionStep(
            step_number=len(steps) + 1,
            target_system="Strategic Sourcing",
            action="Initiate structural mitigation follow-up",
            details="",
            estimated_time_minutes=30,
        ))

    # Notifications audiences
    audiences = ["Logistics Ops", "Procurement", "Customer Service", "Finance"]
    if posture in ("structural", "hybrid") or approach == "hybrid":
        audiences.append("Strategic Sourcing")

    notifs = [Notification(audience=a, message="") for a in audiences]
    return steps, notifs


def run(
    *,
    po_number: str,
    triggering_event_id: str,
    approved_option_id: str,
    diagnosis: LogisticsIssueResolutionOutput,
    pattern_forecast: Optional[PatternForecastOutput],
    inventory_output: InventorySupervisorOutput,
) -> TransportDispatchPlanOutput:
    """
    Generate a simulated dispatch plan for the approved option.
    """

    shipment = get_shipment(po_number)
    if shipment is None:
        raise ValueError(f"Shipment {po_number} not found")

    commitments = get_commitments_for_shipment(po_number)
    if not commitments:
        raise ValueError(f"No commitments found for shipment {po_number}")

    approved_option = _find_option(inventory_output, approved_option_id)
    posture = pattern_forecast.recommendation if pattern_forecast else None

    # Build deterministic skeleton
    steps, notifications = _build_plan_skeleton(
        approved_option_id=approved_option_id,
        approach=approved_option.approach,
        posture=posture,
    )

    # Ask LLM to fill only text
    context = {
        "approved_option": approved_option.model_dump(),
        "shipment": shipment.model_dump(mode="json"),
        "commitments": [c.model_dump(mode="json") for c in commitments],
        "diagnosis": diagnosis.model_dump(mode="json"),
        "pattern_forecast": pattern_forecast.model_dump(mode="json") if pattern_forecast else None,
        "steps": [{"step_number": s.step_number, "target_system": s.target_system, "action": s.action} for s in steps],
        "audiences": [n.audience for n in notifications],
    }

    user_message = (
        "Fill in step details and notification messages for the provided skeleton.\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )

    filled = call_llm(SYSTEM_PROMPT, user_message, _DispatchTextFill, temperature=0.1)

    # Apply filled text back onto skeleton
    for i, s in enumerate(steps):
        s.details = filled.step_details[i] if i < len(filled.step_details) else "Details pending (POC)."

    for i, n in enumerate(notifications):
        n.message = filled.notification_messages[i] if i < len(filled.notification_messages) else "Notification pending (POC)."

    completion_eta = sum(s.estimated_time_minutes for s in steps)

    plan = TransportDispatchPlanOutput(
        approved_option_id=approved_option_id,
        execution_steps=steps,
        notifications=notifications,
        completion_eta_minutes=completion_eta,
        status="simulated",
    )

    logger.info("Dispatch plan generated for %s option=%s", po_number, approved_option_id)
    return plan