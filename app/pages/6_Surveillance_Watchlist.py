"""Page 6: Surveillance Watchlist — Prioritized Candidates for Expert Review."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import (
    DISCLAIMER_TEXT,
    PATHOGEN_COLORS,
    api_get,
    render_banner_and_header,
    render_chart_expander,
    render_key_takeaway,
    render_sidebar,
)

st.set_page_config(page_title="AMR-Sense — Surveillance Watchlist", layout="wide")
render_banner_and_header("Surveillance Watchlist: Candidates for Expert Review")

filters = render_sidebar(allow_pathogen_filter=True, allow_antibiotic_filter=True)
source_param = filters["source"]

# Fetch watchlist from API
params = {
    "source": source_param,
    "min_tested": filters["min_tested"],
}
if filters.get("pathogen"):
    params["pathogen"] = filters["pathogen"]
if filters.get("antibiotic"):
    params["antibiotic"] = filters["antibiotic"]

watchlist_res = api_get("/watchlist", params=params)

if watchlist_res and watchlist_res.get("items"):
    df_watch = pd.DataFrame(watchlist_res["items"])

    # 3. Summary Tiles
    st.subheader("Surveillance Prioritization Overview")
    t1, t2, t3, t4 = st.columns(4)

    high_risk_count = (df_watch["high_risk_probability"] >= 0.40).sum() if "high_risk_probability" in df_watch.columns else 0
    rising_count = (df_watch["rising_probability"] >= 0.20).sum() if "rising_probability" in df_watch.columns else 0
    low_sample_count = (df_watch["number_tested"] < 30).sum() if "number_tested" in df_watch.columns else 0

    t1.metric("Series in Scope", len(df_watch))
    t2.metric("High-Risk Candidates (P >= 40%)", high_risk_count)
    t3.metric("Rising Acceleration Candidates (P >= 20%)", rising_count)
    t4.metric("Small Sample Alerts (N < 30)", low_sample_count)

    # 2. Choropleth Map
    st.markdown("---")
    st.subheader("Geographic Resistance Distribution Map")
    map_pathogen = filters.get("pathogen") or "Klebsiella pneumoniae"
    map_abx = filters.get("antibiotic") or "Ceftriaxone"

    map_subset = df_watch[
        (df_watch["pathogen"] == map_pathogen) & (df_watch["antibiotic"] == map_abx)
    ]

    if not map_subset.empty and "iso3" in map_subset.columns:
        fig_map = px.choropleth(
            map_subset,
            locations="iso3",
            color="pct_resistant",
            hover_name="country",
            hover_data=["number_tested", "forecast_pct", "high_risk_probability"],
            color_continuous_scale="Reds",
            title=f"Latest Surveillance Resistance (%): {map_pathogen} — {map_abx}",
            labels={"pct_resistant": "Resistance (%)"},
        )
        fig_map.update_layout(height=480, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
        render_chart_expander(
            "Geographic Choropleth Map",
            "Displays the latest reported percentage resistance across surveillance jurisdictions. "
            "In Combined scope, note that GLASS values reflect R while ECDC values reflect I+R."
        )

    # 1. Ranked Watchlist Table
    st.markdown("---")
    st.subheader("Prioritized Candidate Series Table")
    sort_col = st.selectbox(
        "Sort By",
        ["high_risk_probability", "rising_probability", "forecast_pct", "pct_resistant", "number_tested"],
        index=0,
    )
    df_sorted = df_watch.sort_values(sort_col, ascending=False).reset_index(drop=True)

    # Format percentages for display
    display_df = df_sorted.copy()
    display_df["pct_resistant"] = display_df["pct_resistant"].map(lambda x: f"{x:.1f}%")
    display_df["forecast_pct"] = display_df["forecast_pct"].map(lambda x: f"{x:.1f}%")
    display_df["high_risk_probability"] = display_df["high_risk_probability"].map(lambda x: f"{x:.1%}")
    display_df["rising_probability"] = display_df["rising_probability"].map(lambda x: f"{x:.1%}")

    st.dataframe(display_df, use_container_width=True, height=450)

    # 4. CSV Download
    csv_bytes = df_sorted.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Candidates for Expert Review (CSV)",
        data=csv_bytes,
        file_name="amr_sense_candidates_for_expert_review.csv",
        mime="text/csv",
    )
    st.caption("Title: **Candidates for expert review**. This table represents surveillance prioritization for human review, not automated prescribing.")
else:
    st.info("Watchlist data loading or no series matched the active filters.")

render_key_takeaway(
    f"The surveillance watchlist ranks latest-year series to guide public health investigation and lab audit priorities. "
    f"Identified candidates represent statistical surveillance flags rather than patient treatment recommendations."
)
