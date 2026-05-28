import streamlit as st
from ui.api_client import ask_risk_qna


def _to_jsonable(obj):
    """
    Convert objects in session_state to JSON-serialisable dicts.
    Handles:
    - None
    - Pydantic v2 models (model_dump)
    - dict/list primitives
    """
    if obj is None:
        return None

    # Pydantic v2 models
    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    # Already JSON-like
    if isinstance(obj, (dict, list, str, int, float, bool)):
        return obj

    # Fallback: stringify unknown objects (should not happen often)
    return str(obj)


def render_risk_qna_panel():
    """
    Chat-style conversational panel.
    - Answers questions using ONLY current risk context
    - No execution, no approvals, no agent re-runs
    """

    selected_risk = st.session_state.get("selected_risk")
    options = st.session_state.get("inventory_options")

    # Only show chat once we have something meaningful to ask about
    if not selected_risk or not options:
        return

    po = selected_risk.get("po_number", "UNKNOWN")
    decision_locked = st.session_state.get("risk_status") == "resolved_simulated"

    st.divider()
    st.subheader("💬 Ask about this risk")
    st.caption(
        "Ask questions to clarify impact, trade‑offs, and reasoning. "
        "This will not trigger actions or approvals."
    )

    # Initialise chat store (scoped per PO)
    if "risk_chat" not in st.session_state:
        st.session_state.risk_chat = []  # list of {po_number, role, content}

    chat_history = [m for m in st.session_state.risk_chat if m.get("po_number") == po]

    # Render chat history as bubbles
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # If decision is locked, keep chat read-only (optional but recommended)
    if decision_locked:
        st.info("Decision is locked. You can review the conversation above.")
        return

    user_question = st.chat_input("Ask a question (e.g. “Why is OPT‑C recommended?”)")

    if user_question:
        # Append user message immediately
        st.session_state.risk_chat.append(
            {"po_number": po, "role": "user", "content": user_question}
        )

        # Build strictly JSON-serialisable context (NO Pydantic objects)
        context = {
            "risk": _to_jsonable(st.session_state.get("selected_risk")),
            "diagnosis": _to_jsonable(st.session_state.get("diagnosis")),
            "pattern_forecast": _to_jsonable(st.session_state.get("pattern_forecast")),
            "mitigation_options": _to_jsonable(st.session_state.get("inventory_options")),
            "dispatch_plan": _to_jsonable(st.session_state.get("dispatch_plan")),
            "risk_status": _to_jsonable(st.session_state.get("risk_status")),
        }

        with st.spinner("Thinking…"):
            answer = ask_risk_qna(question=user_question, context=context)

        st.session_state.risk_chat.append(
            {"po_number": po, "role": "assistant", "content": answer}
        )

        st.rerun()
