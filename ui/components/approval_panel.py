# ui/components/approval_panel.py
import streamlit as st
import time


def render_approval_panel():
    risk = st.session_state.selected_risk
    if not risk:
        return

    st.subheader("Approval")

    if not st.session_state.approved:
        if st.button("✅ Approve Selected Option", type="primary"):
            st.session_state.approved = True
            st.session_state.approved_option = st.session_state.get("selected_option")

    if st.session_state.approved:
        st.success(f"Approved: **{st.session_state.approved_option}**")

        st.caption("POC Execution Plan / Dispatch Preview (simulated)")
        steps = [
            "Create PO / sourcing instruction (simulated)",
            "Reserve / transfer inventory (simulated)",
            "Book freight / route change (simulated)",
            "Draft customer notification (simulated)",
        ]

        for step in steps:
            st.write(f"⏳ {step}")
            time.sleep(0.2)

        st.write("✅ Plan prepared (POC).")