import streamlit as st


def render_diagnosis_card():
    """
    Render the Diagnosis card using agent output stored in session state.

    - Diagnosis content comes from st.session_state.diagnosis
    - Severity is taken from the selected risk to keep classification consistent
    """

    diagnosis = st.session_state.get("diagnosis")
    selected_risk = st.session_state.get("selected_risk")

    # Nothing to render yet
    if not diagnosis or not selected_risk:
        return

    # Use risk severity as the single source of truth
    severity = selected_risk.get("risk_level", "UNKNOWN")

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    st.subheader("Diagnosis")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### {diagnosis['risk_title']}")
    with col2:
        st.markdown(f"**Severity:** `{severity}`")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    st.markdown(diagnosis["summary"])
    st.divider()

    # ------------------------------------------------------------------
    # Business Impact
    # ------------------------------------------------------------------
    st.markdown("#### Business Impact")
    bi = diagnosis["business_impact"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers at Risk", bi["customers_at_risk"])
    c2.metric("Predicted Delay (days)", bi["predicted_delay_days"])
    c3.metric("SLA Exposure ($)", f"{bi['sla_exposure_usd']:,.0f}")
    c4.metric("Revenue at Risk ($)", f"{bi['revenue_at_risk_usd']:,.0f}")

    # ------------------------------------------------------------------
    # Root Causes (clean labels)
    # ------------------------------------------------------------------
    st.markdown("#### Root Causes")
    for cause in diagnosis["root_causes"]:
        if cause.startswith("PRIMARY:"):
            st.markdown(
                f"**Primary cause:** {cause.replace('PRIMARY:', '').strip()}"
            )
        elif cause.startswith("CONTRIB:"):
            st.markdown(
                f"**Contributing factor:** {cause.replace('CONTRIB:', '').strip()}"
            )
        else:
            st.markdown(f"- {cause}")

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------
    with st.expander("Evidence"):
        for ev in diagnosis["evidence"]:
            st.markdown(f"- {ev}")

    # ------------------------------------------------------------------
    # Next step affordance (future agents)
    # ------------------------------------------------------------------
    st.divider()
    if st.button("Continue to forecast and options", type="primary"):
        st.session_state.next_step = "pattern_forecast"