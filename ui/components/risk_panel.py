# ui/components/risk_panel.py
import streamlit as st
from ui.api_client import get_diagnosis


def render_risk_panel():
    risks = st.session_state.get("risks", [])
    risk_count = len(risks)

    st.subheader(f"Detected Risks ({risk_count})")

    if not risks:
        st.info("No material risks detected. Click **Run Risk Check** in the header.")
        return

    # ---------------------------------------------------------------------
    # Optional filters (simple + POC-friendly)
    # ---------------------------------------------------------------------
    with st.expander("Filters", expanded=False):
        levels = ["All"] + sorted({r.get("risk_level", "UNKNOWN") for r in risks})
        selected_level = st.selectbox("Risk level", levels, index=0)

    # Apply filter
    filtered = risks
    if selected_level != "All":
        filtered = [r for r in risks if r.get("risk_level") == selected_level]

    # ---------------------------------------------------------------------
    # Render each risk row
    # ---------------------------------------------------------------------
    for idx, risk in enumerate(filtered):
        po = risk.get("po_number", "-")
        lvl = risk.get("risk_level", "-")
        cause = risk.get("cause", "-")
        delay = risk.get("predicted_delay_days", "-")
        customers = risk.get("customers_impacted", [])
        cust_count = len(customers)
        revenue = risk.get("revenue_at_risk_usd", 0)

        with st.container(border=True):
            c1, c2, c3 = st.columns([0.20, 0.55, 0.25])

            with c1:
                st.markdown(f"**{po}**")
                st.caption(f"Level: {lvl}")

            with c2:
                st.write(f"**Cause:** {cause}")
                st.write(f"**Delay:** {delay} days")
                st.caption(f"Customers impacted: {cust_count}")

            with c3:
                st.markdown(f"**${revenue:,.0f}**")
                st.caption("Revenue at risk")

                if st.button(
                    "Select",
                    key=f"select_risk_{idx}",
                    use_container_width=True,
                ):
                    # -----------------------------------------------------
                    # Store selected risk
                    # -----------------------------------------------------
                    st.session_state.selected_risk = risk

                    # Reset downstream state
                    st.session_state.approved = False
                    st.session_state.approved_option = None
                    st.session_state.diagnosis = None

                    # -----------------------------------------------------
                    # Call Diagnosis API (agentic)
                    # -----------------------------------------------------
                    with st.spinner("Running diagnosis…"):
                        st.session_state.diagnosis = get_diagnosis(
                            po_number=risk["po_number"],
                            triggering_event_id=risk["event_id"],
                        )