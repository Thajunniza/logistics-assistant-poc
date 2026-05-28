import streamlit as st
from ui.api_client import get_dispatch_plan


def _pick_recommended_option(options: list[dict]) -> tuple[str, str]:
    """
    Simple, explainable recommendation heuristic for the POC UI.
    (Later you can move this to an orchestrator, but for POC it’s OK to highlight.)

    Rule:
    - Prefer the fastest SLA recovery option.
    - If tie, prefer lower cost delta.

    Returns: (option_id, reason)
    """
    best = None
    for o in options:
        key = (int(o.get("sla_recovery_days", 999)), float(o.get("cost_delta_usd", 1e18)))
        if best is None or key < best[0]:
            best = (key, o)

    option_id = best[1]["option_id"]
    reason = f"Fastest SLA recovery ({best[1]['sla_recovery_days']} days) with cost ${best[1]['cost_delta_usd']:,.0f}."
    return option_id, reason


def _card_header(option_id: str, title: str, recommended: bool, approved: bool, locked: bool):
    """
    Render the header block for one option card.
    """
    st.markdown(f"### {option_id}")
    st.markdown(f"**{title}**")

    badges = []
    if recommended:
        badges.append("⭐ Recommended")
    if approved:
        badges.append("✅ Approved")
    elif locked:
        badges.append("🔒 Locked")

    if badges:
        st.caption("  •  ".join(badges))


def render_inventory_options_panel():
    data = st.session_state.get("inventory_options")
    if not data:
        return

    options = data.get("options", [])
    if len(options) != 3:
        st.error("Expected exactly 3 options for the POC.")
        return

    approved_id = st.session_state.get("approved_option_id")
    is_locked = approved_id is not None

    # Recommendation (UI-level highlight for decision clarity)
    recommended_id, recommended_reason = _pick_recommended_option(options)

    st.divider()
    st.subheader("Mitigation Options")
    st.caption("Compare the options below. Once you approve one, the decision is locked.")

    # Small recommendation strip (executive friendly)
    st.info(f"**Recommended:** {recommended_id} — {recommended_reason}")

    # 3-column layout
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for col, opt in zip(cols, options):
        option_id = opt["option_id"]
        approved = (approved_id == option_id)
        locked = is_locked and not approved
        recommended = (recommended_id == option_id)

        with col:
            with st.container(border=True):
                _card_header(option_id, opt["title"], recommended, approved, locked)
                st.caption(f"Approach: {opt['approach'].replace('_', ' ').title()}")

                # Metrics (most important info to decide)
                st.metric("Cost delta", f"${opt['cost_delta_usd']:,.0f}")
                st.metric("SLA recovery", f"{opt['sla_recovery_days']} days")

                st.markdown("**Customer impact**")
                st.write(opt["customer_impact"])

                st.markdown("**Trade‑off**")
                st.write(opt["trade_off"])

                st.divider()

                # HARD LOCK behaviour:
                # - If decision is already locked, do NOT render any approve buttons at all.
                if is_locked:
                    if approved:
                        st.success("Decision locked on this option.")
                    else:
                        st.info("Another option has already been approved.")
                else:
                    # Only show a single clear action button
                    if st.button(
                        "Approve",
                        key=f"approve_{option_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state.approved_option_id = option_id

                        selected = st.session_state.get("selected_risk")
                        if selected:
                            with st.spinner("Generating dispatch plan (simulated)…"):
                                st.session_state.dispatch_plan = get_dispatch_plan(
                                    po_number=selected["po_number"],
                                    triggering_event_id=selected["event_id"],
                                    approved_option_id=option_id,
                                )
                            st.session_state.risk_status = "resolved_simulated"

                        st.success(f"✅ Approved {option_id}. Dispatch plan generated (simulated).")
