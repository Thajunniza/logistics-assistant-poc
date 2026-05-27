# ui/components/detail_panel.py
import streamlit as st


def render_detail_panel():
    risk = st.session_state.selected_risk

    if not risk:
        st.info("Select a risk from the left panel to view details.")
        return



