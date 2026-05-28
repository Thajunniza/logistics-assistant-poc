# ui/main.py
import sys
from pathlib import Path

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from ui.state import init_state
from ui.components.header import render_header
from ui.components.risk_panel import render_risk_panel

from ui.components.diagnosis_card import render_diagnosis_card
from ui.components.pattern_forecast_card import render_pattern_forecast_card
from ui.components.inventory_options_panel import render_inventory_options_panel

from ui.components.detail_panel import render_detail_panel
from ui.components.chat_panel import render_chat_panel

from ui.api_client import get_diagnosis, get_pattern_forecast, get_inventory_options
from ui.components.dispatch_plan_panel import render_dispatch_plan_panel

from ui.components.risk_qna_panel import render_risk_qna_panel


def main():
    init_state()

    st.set_page_config(page_title="Logistics Assistant", layout="wide")

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: 0rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_header(user_name="Thajunniza")

    left, right = st.columns([0.30, 0.70])

    # -----------------------------
    # LEFT: Risk list
    # -----------------------------
    with left:
        render_risk_panel()

    # -----------------------------
    # RIGHT: Pipeline controller
    # -----------------------------
    with right:
        selected_risk = st.session_state.get("selected_risk")

        if not selected_risk:
            st.info("Select a risk from the left panel to view analysis.")
            return

        # ---------------------------------------------------------
        # Stage 1: Auto-run Diagnosis (Agent 1) when a risk is selected
        # ---------------------------------------------------------
        if st.session_state.get("diagnosis") is None:
            with st.spinner("Running diagnosis…"):
                st.session_state.diagnosis = get_diagnosis(
                    po_number=selected_risk["po_number"],
                    triggering_event_id=selected_risk["event_id"],
                )

        # Render Diagnosis if available
        render_diagnosis_card()

        # ---------------------------------------------------------
        # Stage 2: Pattern forecast (Agent 2) only when user requests it
        # ---------------------------------------------------------
        if (
            st.session_state.get("next_step") == "pattern_forecast"
            and st.session_state.get("pattern_forecast") is None
        ):
            with st.spinner("Analysing historical patterns…"):
                st.session_state.pattern_forecast = get_pattern_forecast(
                    po_number=selected_risk["po_number"],
                    triggering_event_id=selected_risk["event_id"],
                )
            st.session_state.next_step = None

        render_pattern_forecast_card()

        # ---------------------------------------------------------
        # Stage 3: Mitigation options (Agent 3) only when user requests it
        # ---------------------------------------------------------
        if (
            st.session_state.get("next_step") == "inventory_supervisor"
            and st.session_state.get("inventory_options") is None
        ):
            with st.spinner("Generating mitigation options…"):
                st.session_state.inventory_options = get_inventory_options(
                    po_number=selected_risk["po_number"],
                    triggering_event_id=selected_risk["event_id"],
                )
            st.session_state.next_step = None

        render_inventory_options_panel()
        render_risk_qna_panel()
        render_dispatch_plan_panel()

        # Optional: keep these if you still want them
        render_detail_panel()
        st.divider()


if __name__ == "__main__":
    main()