# ui/components/header.py
import streamlit as st
from datetime import datetime, timezone

from ui.api_client import health_check, run_risk_check


def render_header(user_name: str = "Supply Chain Lead"):
    """
    Top bar header:
    - Left: Title + welcome message
    - Middle: Status chips (backend, last check, risk count)
    - Right: Primary action button (Run Risk Check) + optional secondary action
    """

    # --- Calculate lightweight status values ---
    risk_count = len(st.session_state.get("risks", []))
    last_check = st.session_state.get("last_check")

    # --- Top bar layout ---
    left, mid, right = st.columns([0.55, 0.25, 0.20], vertical_alignment="center")

    with left:
        st.markdown("## 🚚 Logistics Assistant")
        st.caption(f"Welcome, **{user_name}** — Quickly detect fulfilment risks and review mitigation options.")

    with mid:
        # Backend status
        try:
            h = health_check()
            backend_text = f"✅ Backend: {h.get('status', 'ok')}"
        except Exception:
            backend_text = "❌ Backend: not reachable"

        st.markdown(
            f"""
            <div style="font-size: 0.85rem; line-height: 1.6;">
              <div>{backend_text}</div>
              <div>⚠️ Risks: <b>{risk_count}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        # Primary CTA: Run Risk Check
        if st.button("🔍 Run Risk Check", type="primary", use_container_width=True):
            with st.spinner("Checking BDC data products…"):
                st.session_state.risks = run_risk_check()
                st.session_state.last_check = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                st.session_state.selected_risk = None
                st.session_state.approved = False
                st.session_state.approved_option = None
                st.session_state.chat = []

        # # Optional: Clear selected risk
        # if st.button("🧹 Clear", use_container_width=True):
        #     st.session_state.selected_risk = None
        #     st.session_state.approved = False
        #     st.session_state.approved_option = None

    st.divider()