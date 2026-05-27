# ui/components/detail_panel.py
import streamlit as st


def render_detail_panel():
    risk = st.session_state.selected_risk

    if not risk:
        st.info("Select a risk from the left panel to view details.")
        return

    # 1) Risk banner
    st.error(
        f"HIGH RISK — PO {risk.get('po_number')} | "
        f"{risk.get('predicted_delay_days')} day delay expected"
    )

    # 2) Diagnosis & impact (from risk object + placeholders)
    st.subheader("Diagnosis & Business Impact")
    st.write(f"**Cause:** {risk.get('cause')}")
    st.write(f"**Customers impacted:** {', '.join(risk.get('customers_impacted', []))}")
    st.write(f"**Revenue at risk:** ${risk.get('revenue_at_risk_usd', 0):,.2f}")
    st.caption("POC note: detailed diagnosis will come from Issue Resolution Agent in next step.")

    # 3) Pattern forecast placeholder
    st.subheader("Pattern Forecast")
    st.info("POC placeholder: Recurring disruption observed historically (typhoon season).")

    # 4) Mitigation options placeholder
    st.subheader("Mitigation Options")

    options = [
        "Option A: Internal transfer from EMEA (recommended)",
        "Option B: Expedite air shipment",
        "Option C: Alternate supplier sourcing",
    ]
    st.session_state.setdefault("selected_option", options[0])
    selected = st.radio("Select an option:", options, index=0)
    st.session_state.selected_option = selected

    # 5) Recommendation (highlight)
    st.success("✅ Recommended: Option A (best SLA recovery with acceptable cost for Platinum impact).")
