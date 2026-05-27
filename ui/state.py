# ui/state.py
"""
Centralised Streamlit session state keys.
"""

import streamlit as st


def init_state():
    if "risks" not in st.session_state:
        st.session_state.risks = []

    if "selected_risk" not in st.session_state:
        st.session_state.selected_risk = None

    if "last_check" not in st.session_state:
        st.session_state.last_check = None

    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of {"role": "user"/"assistant", "content": str}

    if "approved" not in st.session_state:
        st.session_state.approved = False

    if "approved_option" not in st.session_state:
        st.session_state.approved_option = None
    
    if "diagnosis" not in st.session_state:
        st.session_state.diagnosis = None

    if "pattern_forecast" not in st.session_state:
        st.session_state.pattern_forecast = None

    if "next_step" not in st.session_state:
        st.session_state.next_step = None
    
    if "inventory_options" not in st.session_state:
        st.session_state.inventory_options = None

    if "approved_option_id" not in st.session_state:
        st.session_state.approved_option_id = None



