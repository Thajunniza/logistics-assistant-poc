import streamlit as st


def render_dispatch_plan_panel():
    plan = st.session_state.get("dispatch_plan")
    status = st.session_state.get("risk_status", "open")

    if not plan:
        return

    st.divider()
    st.subheader("Dispatch Plan (Simulated)")

    st.caption(
        f"Approved option: {plan['approved_option_id']}  •  "
        f"Status: {plan.get('status', 'simulated')}  •  "
        f"Completion ETA: {plan['completion_eta_minutes']} minutes"
    )

    st.markdown("### Execution Steps")
    for step in plan["execution_steps"]:
        st.markdown(
            f"**{step['step_number']}. [{step['target_system']}] {step['action']}**  \n"
            f"{step['details']}  \n"
            f"_~{step['estimated_time_minutes']} min_"
        )

    with st.expander("Notifications"):
        for n in plan["notifications"]:
            st.markdown(f"- **{n['audience']}**: {n['message']}")

    if status == "resolved_simulated":
        st.success("✅ Risk marked resolved (simulated).")