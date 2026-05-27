# ui/components/risk_panel.py
import streamlit as st


def render_risk_panel():
    risk_count = len(st.session_state.get("risks", []))
    st.subheader(f"Detected Risks ({risk_count})")

    risks = st.session_state.risks

    if not risks:
        st.info("No material risks detected. Click **Run Risk Check** in the header.")
        return

    # Optional filters (simple + POC-friendly)
    with st.expander("Filters", expanded=False):
        levels = ["All"] + sorted(list({r.get("risk_level", "UNKNOWN") for r in risks}))
        selected_level = st.selectbox("Risk level", levels, index=0)

    # Apply filter
    filtered = risks
    if selected_level != "All":
        filtered = [r for r in risks if r.get("risk_level") == selected_level]

    # Render each risk as a structured row
    for idx, risk in enumerate(filtered):
        po = risk.get("po_number", "-")
        lvl = risk.get("risk_level", "-")
        cause = risk.get("cause", "-")
        delay = risk.get("predicted_delay_days", "-")
        customers = risk.get("customers_impacted", [])
        cust_count = len(customers)
        revenue = risk.get("revenue_at_risk_usd", 0)

        row = st.container(border=True)
        with row:
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
                if st.button("Select", key=f"select_risk_{idx}", use_container_width=True):
                    st.session_state.selected_risk = risk
                    st.session_state.approved = False
                    st.session_state.approved_option = None