import streamlit as st


def render_risk_panel():
    risks = st.session_state.get("risks", [])
    st.subheader(f"Detected Risks ({len(risks)})")

    if not risks:
        st.info("No material risks detected. Click **Run Risk Check** in the header.")
        return

    # ---------------------------------------------------------
    # Optional filter (kept simple for POC)
    # ---------------------------------------------------------
    with st.expander("Filters", expanded=False):
        levels = ["All"] + sorted({r.get("risk_level", "UNKNOWN") for r in risks})
        selected_level = st.selectbox("Risk level", levels, index=0)

    filtered = risks if selected_level == "All" else [
        r for r in risks if r.get("risk_level") == selected_level
    ]

    # ---------------------------------------------------------
    # Render each risk
    # ---------------------------------------------------------
    for idx, risk in enumerate(filtered):
        po = risk.get("po_number", "-")
        lvl = risk.get("risk_level", "-")
        cause = risk.get("cause", "-")
        delay = risk.get("predicted_delay_days", "-")
        revenue = risk.get("revenue_at_risk_usd", 0)
        customers = risk.get("customers_impacted", [])

        # A risk is considered resolved ONLY if:
        # - it is currently selected
        # - AND an option was approved for it
        is_resolved = (
            st.session_state.get("risk_status") == "resolved_simulated"
            and st.session_state.get("selected_risk", {}).get("po_number") == po
        )

        with st.container(border=True):
            c1, c2, c3 = st.columns([0.25, 0.50, 0.25])

            # -------------------------------
            # Left: Identity
            # -------------------------------
            with c1:
                st.markdown(f"**{po}**")
                st.caption(f"Level: {lvl}")
                if is_resolved:
                    st.caption("✅ Resolved (simulated)")

            # -------------------------------
            # Middle: Context
            # -------------------------------
            with c2:
                st.write(f"**Cause:** {cause}")
                st.write(f"**Delay:** {delay} days")
                st.caption(f"Customers impacted: {len(customers)}")

            # -------------------------------
            # Right: Action
            # -------------------------------
            with c3:
                st.markdown(f"**${revenue:,.0f}**")
                st.caption("Revenue at risk")

                # HARD DISABLE: resolved risks cannot be selected again
                if st.button(
                    "Select",
                    key=f"select_risk_{idx}",
                    use_container_width=True,
                    disabled=is_resolved,
                ):
                    # ---------------------------------------------
                    # New risk selected → RESET ALL DOWNSTREAM STATE
                    # ---------------------------------------------
                    st.session_state.selected_risk = risk

                    st.session_state.diagnosis = None
                    st.session_state.pattern_forecast = None
                    st.session_state.inventory_options = None
                    st.session_state.dispatch_plan = None
                    st.session_state.approved_option_id = None
                    st.session_state.risk_status = "open"
                    st.session_state.next_step = None