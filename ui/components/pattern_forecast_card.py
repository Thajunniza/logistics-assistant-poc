import streamlit as st


def _classification_badge(classification: str):
    """
    Render classification as a visually prominent badge.
    """
    colour = {
        "systemic": "#d9534f",   # red
        "recurring": "#f0ad4e",  # amber
        "one-off": "#5cb85c",    # green
    }.get(classification.lower(), "#777777")

    st.markdown(
        f"""
        <span style="
            background-color: {colour};
            color: white;
            padding: 0.25rem 0.6rem;
            border-radius: 0.5rem;
            font-weight: 600;
        ">
            {classification.upper()}
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_pattern_forecast_card():
    forecast = st.session_state.get("pattern_forecast")
    diagnosis = st.session_state.get("diagnosis")

    if not forecast:
        return

    st.divider()
    st.subheader("Pattern Forecast")

    # ------------------------------------------------------------------
    # Header row — classification must dominate
    # ------------------------------------------------------------------
    col1, col2, col3 = st.columns([2.5, 1.5, 2])

    with col1:
        st.markdown("**Classification**")
        _classification_badge(forecast["classification"])

    with col2:
        st.markdown("**Confidence**")
        st.markdown(forecast["confidence"].upper())

    with col3:
        # Provide context: forecast vs event report
        reported = None
        if diagnosis:
            reported = diagnosis["business_impact"]["predicted_delay_days"]

        if reported:
            st.markdown("**Expected duration**")
            st.markdown(
                f"{forecast['expected_duration_days']} days "
                f"*(longer than reported {reported})*"
            )
        else:
            st.markdown("**Expected duration**")
            st.markdown(f"{forecast['expected_duration_days']} days")

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------
    st.markdown(forecast["pattern_narrative"])
    st.divider()

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------
    st.markdown("#### Recommended Posture")
    st.markdown(f"**{forecast['recommendation'].capitalize()}**")
    st.caption(forecast["rationale"])

    # ------------------------------------------------------------------
    # Next step CTA — moved to the correct place
    # ------------------------------------------------------------------
    st.divider()
    if st.button("Continue to mitigation options", type="primary"):
        st.session_state.next_step = "inventory_supervisor"