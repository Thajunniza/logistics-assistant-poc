"""
Token usage dashboard — simplified, with Capacity Units (SAP Gen AI Hub billing unit).

One filterable table. One filterable chart. Top-line metrics that respect filters.

Run:
    streamlit run ui/dashboard.py
or from your project root:
    streamlit run ui/dashboard.py --server.port 8502
"""

from datetime import datetime

import streamlit as st
import pandas as pd

from backend.token_tracker import (
    init_db,
    get_conn,
    PRICING,
    DEFAULT_MODEL_FOR_PRICING,
    EUR_PER_CU,
)


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Token Usage",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Make text bolder and darker — Streamlit defaults are a little thin
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Base body text — darker, slightly bolder */
    html, body, [class*="css"] {
        color: #0F1F2E !important;
        font-weight: 500;
    }

    /* Headings — heavier weight, stronger colour */
    h1, h2, h3, h4 {
        color: #0B2545 !important;
        font-weight: 700 !important;
    }

    /* Captions and helper text — readable, not faded */
    .stCaption, .stMarkdown p, [data-testid="stCaptionContainer"] {
        color: #2A3B4D !important;
        font-weight: 500 !important;
    }

    /* Metric labels — make them visible */
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #2A3B4D !important;
    }

    /* Metric values — big and bold */
    [data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
        font-weight: 700 !important;
        color: #0B2545 !important;
    }

    /* Metric deltas (the small text under each metric) */
    [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }

    /* Dataframe / table cells — bolder text */
    [data-testid="stDataFrame"] div, [data-testid="stTable"] div {
        font-weight: 500 !important;
        color: #0F1F2E !important;
    }

    /* Dataframe headers */
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-weight: 700 !important;
        color: #0B2545 !important;
        background-color: #F0F4F8 !important;
    }

    /* Filter widget labels (multiselect / date inputs) */
    .stMultiSelect label, .stDateInput label, .stSelectbox label {
        font-weight: 600 !important;
        color: #0B2545 !important;
        font-size: 0.95rem !important;
    }

    /* Selected items inside multiselect chips */
    .stMultiSelect [data-baseweb="tag"] {
        font-weight: 600 !important;
    }

    /* Buttons */
    .stButton button {
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Data layer
# -----------------------------------------------------------------------------

@st.cache_data(ttl=10)
def load_all_calls() -> pd.DataFrame:
    """Load every recorded LLM call. Cached for 10s so the dashboard stays snappy."""
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                id,
                timestamp_utc,
                application_name,
                user_name,
                agent_name,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                capacity_units,
                cost_eur,
                latency_ms,
                success
            FROM llm_calls
            ORDER BY id DESC
            """,
            conn,
        )
    if df.empty:
        return df
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df["date"] = df["timestamp_utc"].dt.date
    df["status"] = df["success"].map({1: "OK", 0: "FAIL"})
    return df


def _fmt_eur(x) -> str:
    if pd.isna(x):
        return "—"
    return f"€{x:.4f}" if abs(x) < 1 else f"€{x:.2f}"


def _fmt_cu(x) -> str:
    if pd.isna(x):
        return "—"
    return f"{x:.4f} CU" if abs(x) < 1 else f"{x:.2f} CU"


# -----------------------------------------------------------------------------
# Main render
# -----------------------------------------------------------------------------

def render():
    init_db()
    df = load_all_calls()

    st.title("Token usage & cost")
    st.caption(
        "One filterable view of every LLM call. Filters apply to the metrics, the table, and the chart. "
        f"Cost is computed from SAP Gen AI Hub Capacity Units at €{EUR_PER_CU:.2f}/CU."
    )

    if df.empty:
        st.info("No LLM calls recorded yet. Run a scenario in the main app, then refresh this page.")
        return

    # -------------------------------------------------------------------------
    # Filters (top row)
    # -------------------------------------------------------------------------

    def opts(col: str) -> list:
        """Distinct sorted values for a filter dropdown."""
        return sorted([v for v in df[col].dropna().unique().tolist()])

    f1, f2, f3, f4 = st.columns(4)
    sel_app   = f1.multiselect("Application", opts("application_name"))
    sel_user  = f2.multiselect("User",        opts("user_name"))
    sel_agent = f3.multiselect("Agent",       opts("agent_name"))
    sel_model = f4.multiselect("Model",       opts("model"))

    d1, d2, d3 = st.columns([2, 2, 1])
    min_date = df["date"].min()
    max_date = df["date"].max()
    start_date = d1.date_input("From date", value=min_date, min_value=min_date, max_value=max_date)
    end_date   = d2.date_input("To date",   value=max_date, min_value=min_date, max_value=max_date)
    d3.write("")
    if d3.button("Clear filters", use_container_width=True):
        st.rerun()

    # -------------------------------------------------------------------------
    # Apply filters
    # -------------------------------------------------------------------------

    fdf = df.copy()
    if sel_app:   fdf = fdf[fdf["application_name"].isin(sel_app)]
    if sel_user:  fdf = fdf[fdf["user_name"].isin(sel_user)]
    if sel_agent: fdf = fdf[fdf["agent_name"].isin(sel_agent)]
    if sel_model: fdf = fdf[fdf["model"].isin(sel_model)]
    fdf = fdf[(fdf["date"] >= start_date) & (fdf["date"] <= end_date)]

    successful = fdf[fdf["success"] == 1]

    # -------------------------------------------------------------------------
    # Top-line metrics (driven by filtered data)
    # -------------------------------------------------------------------------

    total_calls  = len(fdf)
    total_tokens = int(successful["total_tokens"].sum())
    total_cu     = float(successful["capacity_units"].sum())
    total_cost   = float(successful["cost_eur"].sum())

    # Projected monthly: extrapolate cost-per-day to 30 days
    if not successful.empty:
        ts_min = successful["timestamp_utc"].min()
        ts_max = successful["timestamp_utc"].max()
        days_span = max((ts_max - ts_min).total_seconds() / 86400.0, 1 / 24)
        projected_cu  = round((total_cu   / days_span) * 30.0, 4)
        projected_eur = round((total_cost / days_span) * 30.0, 2)
    else:
        projected_cu = 0.0
        projected_eur = 0.0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Calls",              f"{total_calls:,}")
    m2.metric("Tokens",             f"{total_tokens:,}")
    m3.metric("Capacity Units",     _fmt_cu(total_cu))
    m4.metric("Cost",               _fmt_eur(total_cost))
    m5.metric("Projected / mo",     _fmt_eur(projected_eur),
              delta=f"{projected_cu:.2f} CU", delta_color="off")

    st.divider()

    # -------------------------------------------------------------------------
    # Chart — Capacity Units over time, group-by selectable
    # -------------------------------------------------------------------------

    chart_col1, chart_col2, chart_col3 = st.columns([2, 1, 1])
    chart_col1.subheader("Consumption over time")
    metric_choice = chart_col2.selectbox(
        "Metric",
        options=["Capacity Units", "Cost (EUR)", "Tokens"],
        index=0,
        label_visibility="collapsed",
    )
    group_by = chart_col3.selectbox(
        "Group by",
        options=["(none)", "user_name", "application_name", "agent_name", "model"],
        index=0,
        label_visibility="collapsed",
    )

    metric_col = {
        "Capacity Units": "capacity_units",
        "Cost (EUR)":     "cost_eur",
        "Tokens":         "total_tokens",
    }[metric_choice]

    if successful.empty:
        st.info("No successful calls in the filtered range.")
    else:
        if group_by == "(none)":
            chart_df = (
                successful
                .groupby("date", as_index=True)[metric_col]
                .sum()
                .to_frame(metric_choice)
            )
        else:
            chart_df = (
                successful
                .groupby(["date", group_by])[metric_col]
                .sum()
                .unstack(fill_value=0)
            )
        st.bar_chart(chart_df, height=320)

    st.divider()

    # -------------------------------------------------------------------------
    # Table — every call
    # -------------------------------------------------------------------------

    st.subheader("All calls")
    st.caption(f"Showing {len(fdf):,} calls. Click a column header to sort. Use the filters above to narrow.")

    display = fdf.copy()
    display["timestamp_utc"]  = display["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display["capacity_units"] = display["capacity_units"].map(lambda v: f"{v:.5f}" if pd.notna(v) else "—")
    display["cost_eur"]       = display["cost_eur"].map(_fmt_eur)
    display["latency_ms"]     = display["latency_ms"].map(
        lambda v: f"{int(v)} ms" if pd.notna(v) else "—"
    )
    display = display[[
        "timestamp_utc", "application_name", "user_name", "agent_name",
        "model", "prompt_tokens", "completion_tokens", "total_tokens",
        "capacity_units", "cost_eur", "latency_ms", "status",
    ]].rename(columns={
        "timestamp_utc":     "Timestamp (UTC)",
        "application_name":  "Application",
        "user_name":         "User",
        "agent_name":        "Agent",
        "model":             "Model",
        "prompt_tokens":     "Input tokens",
        "completion_tokens": "Output tokens",
        "total_tokens":      "Total tokens",
        "capacity_units":    "CU",
        "cost_eur":          "Cost",
        "latency_ms":        "Latency",
        "status":            "Status",
    })

    # Pandas Styler gives us cell/header styling that survives Streamlit's
    # data-grid shadow DOM (where plain CSS selectors don't reach).
    styled = (
        display.style
        .set_properties(**{
            "color": "#0F1F2E",
            "font-weight": "600",
            "font-size": "14px",
        })
        .set_table_styles([
            {"selector": "th",
             "props": [
                 ("color",          "#FFFFFF"),
                 ("background-color","#0B2545"),
                 ("font-weight",    "700"),
                 ("font-size",      "14px"),
                 ("text-align",     "left"),
                 ("padding",        "8px 10px"),
             ]},
            {"selector": "td",
             "props": [
                 ("padding",        "6px 10px"),
                 ("border-bottom",  "1px solid #DCE4EA"),
             ]},
            {"selector": "tr:nth-child(even) td",
             "props": [("background-color", "#F5F8FA")]},
        ])
        .hide(axis="index")
    )
    st.markdown(
        f'<div style="max-height:460px;overflow-y:auto;border:1px solid #DCE4EA;'
        f'border-radius:4px;">{styled.to_html()}</div>',
        unsafe_allow_html=True,
    )

    csv_bytes = fdf.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered view as CSV",
        data=csv_bytes,
        file_name=f"token_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    # -------------------------------------------------------------------------
    # Pricing transparency
    # -------------------------------------------------------------------------

    with st.expander("Pricing assumptions (SAP Gen AI Hub Capacity Units)", expanded=False):
        st.markdown(
            f"**Capacity Unit rate:** €{EUR_PER_CU:.2f} per CU (SAP list price). "
            f"Override via `EUR_PER_CU` environment variable.\n\n"
            "**Per-model CU consumption per 1,000 tokens** — calibrated from the "
            "SAP Gen AI Hub in SAP AI Core Calculator (gpt-4o, 1K input + 1K output = 0.0235 CU)."
        )
        rates_df = pd.DataFrame([
            {
                "Model":            m,
                "Input  CU / 1K":   f"{r['input_cu_per_1k']:.5f}",
                "Output CU / 1K":   f"{r['output_cu_per_1k']:.5f}",
                "EUR / 1K input":   f"€{r['input_cu_per_1k']  * EUR_PER_CU:.5f}",
                "EUR / 1K output":  f"€{r['output_cu_per_1k'] * EUR_PER_CU:.5f}",
            }
            for m, r in PRICING.items()
        ])
        rates_styled = (
            rates_df.style
            .set_properties(**{
                "color": "#0F1F2E", "font-weight": "600", "font-size": "13px",
            })
            .set_table_styles([
                {"selector": "th",
                 "props": [("color","#FFFFFF"), ("background-color","#0B2545"),
                           ("font-weight","700"), ("font-size","13px"),
                           ("text-align","left"), ("padding","6px 10px")]},
                {"selector": "td",
                 "props": [("padding","5px 10px"), ("border-bottom","1px solid #DCE4EA")]},
                {"selector": "tr:nth-child(even) td",
                 "props": [("background-color", "#F5F8FA")]},
            ])
            .hide(axis="index")
        )
        st.markdown(rates_styled.to_html(), unsafe_allow_html=True)
        st.caption(
            f"Default rate (for unknown models): `{DEFAULT_MODEL_FOR_PRICING}`. "
            "Public list prices — CPEA agreements typically discount 15–30%."
        )


if __name__ == "__main__":
    render()
