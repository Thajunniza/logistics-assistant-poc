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
from ui.components.detail_panel import render_detail_panel
from ui.components.approval_panel import render_approval_panel
from ui.components.chat_panel import render_chat_panel
from ui.components.diagnosis_card import render_diagnosis_card
from ui.api_client import get_pattern_forecast
from ui.components.pattern_forecast_card import render_pattern_forecast_card



def main():

    init_state()
    st.set_page_config(page_title="Logistics Assitant",layout="wide")
    
    st.markdown(
        """
        <style>
        /* Reduce top padding and widen container */
        

        /* Remove extra space above the first element */
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: 0rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    render_header(user_name="Thajunniza")

    left, right = st.columns([0.30, 0.70])

    with left:
        render_risk_panel()

    with right:
        render_diagnosis_card()
        
# Trigger Pattern Forecast only when user asks
        if st.session_state.get("next_step") == "pattern_forecast" and st.session_state.get("pattern_forecast") is None:
            selected_risk = st.session_state.get("selected_risk")
            if selected_risk:
                with st.spinner("Analysing historical patterns…"):
                    st.session_state.pattern_forecast = get_pattern_forecast(
                        po_number=selected_risk["po_number"],
                        triggering_event_id=selected_risk["event_id"],
                    )

        # Render Pattern Forecast if available
        render_pattern_forecast_card()

        render_detail_panel()
        st.divider()
        render_approval_panel()
        st.divider()
        render_chat_panel()


if __name__ == "__main__":
    main()
