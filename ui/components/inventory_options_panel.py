import streamlit as st


def _complexity_badge(level: str):
    colours = {
        "low": "#5cb85c",
        "medium": "#f0ad4e",
        "high": "#d9534f",
    }
    colour = colours.get(level.lower(), "#777777")

    st.markdown(
        f"""
        <span style="
            background-color:{colour};
            color:white;
            padding:0.2rem 0.5rem;
            border-radius:0.4rem;
            font-size:0.8rem;
            font-weight:600;
        ">
            {level.upper()} COMPLEXITY
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_inventory_options_panel():
    data = st.session_state.get("inventory_options")
    if not data:
        return

    st.divider()
    st.subheader("Mitigation Options")

    st.caption(
        "Review the three most viable mitigation paths below. "
        "Each option presents a different trade‑off between cost, speed, and operational complexity."
    )

    for opt in data["options"]:
        with st.container(border=True):
            # ---------------------------------------------------------
            # Header
            # ---------------------------------------------------------
            h1, h2 = st.columns([4, 1])
            with h1:
                st.markdown(f"### {opt['option_id']}: {opt['title']}")
                st.caption(f"Approach: {opt['approach'].replace('_', ' ').title()}")
            with h2:
                _complexity_badge(opt["complexity"])

            # ---------------------------------------------------------
            # Description
            # ---------------------------------------------------------
            st.markdown(opt["description"])

            # ---------------------------------------------------------
            # Metrics row
            # ---------------------------------------------------------
            c1, c2, c3 = st.columns(3)
            c1.metric("Cost delta (USD)", f"${opt['cost_delta_usd']:,.0f}")
            c2.metric("SLA recovery", f"{opt['sla_recovery_days']} days")
            c3.markdown("**Customer impact**")
            c3.markdown(opt["customer_impact"])

            # ---------------------------------------------------------
            # Trade-off (callout)
            # ---------------------------------------------------------
            st.markdown(
                f"""
                <div style="
                    background-color:#f8f9fa;
                    border-left:4px solid #6c757d;
                    padding:0.75rem;
                    margin-top:0.5rem;
                ">
                    <strong>Trade‑off:</strong> {opt['trade_off']}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ---------------------------------------------------------
            # Approval action
            # ---------------------------------------------------------
            if st.button(
                f"Approve {opt['option_id']}",
                key=f"approve_{opt['option_id']}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.approved_option_id = opt["option_id"]
                st.success(
                    f"✅ Decision recorded: {opt['option_id']} approved. "
                    "No action executed — recommendation captured for audit."
                )
