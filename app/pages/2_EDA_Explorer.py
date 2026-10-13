"""Page 2: EDA Explorer with interactive tabs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import (
    PATHOGEN_COLORS,
    SOURCE_COLORS,
    api_get,
    render_banner_and_header,
    render_chart_expander,
    render_key_takeaway,
    render_sidebar,
)

st.set_page_config(page_title="AMR-Sense — EDA Explorer", layout="wide")
render_banner_and_header("Exploratory Data Analysis Explorer")
filters = render_sidebar(allow_pathogen_filter=True, allow_antibiotic_filter=True)
source_param = filters["source"]

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Distributions",
    "2. Longitudinal Trends",
    "3. Sample Size Funnel",
    "4. Year-on-Year Dynamics",
    "5. Target Class Balance",
    "6. Cross-Resistance",
    "7. Data Issues & Decisions",
])

# TAB 1: Distributions
with tab1:
    st.subheader("Resistance Rate Distributions by Pathogen & Antibiotic")
    chart_type = st.radio("Chart Type", ["Box Plot", "Violin Plot"], horizontal=True)
    dist_data = api_get(f"/eda/distribution?source={source_param}")

    if dist_data and dist_data.get("rows"):
        df_dist = pd.DataFrame(dist_data["rows"])
        if filters.get("pathogen"):
            df_dist = df_dist[df_dist["pathogen"] == filters["pathogen"]]
        if filters.get("antibiotic"):
            df_dist = df_dist[df_dist["antibiotic"] == filters["antibiotic"]]

        if not df_dist.empty:
            if chart_type == "Box Plot":
                fig = px.box(
                    df_dist,
                    x="antibiotic",
                    y="pct_resistant",
                    color="source" if source_param == "combined" else "pathogen",
                    title="Resistance Distribution across Antibiotics",
                    labels={"pct_resistant": "Resistance (%)", "antibiotic": "Antibiotic Target"},
                    color_discrete_map={**SOURCE_COLORS, **PATHOGEN_COLORS},
                )
            else:
                fig = px.violin(
                    df_dist,
                    x="antibiotic",
                    y="pct_resistant",
                    color="source" if source_param == "combined" else "pathogen",
                    box=True,
                    points="outliers",
                    title="Resistance Distribution across Antibiotics",
                    labels={"pct_resistant": "Resistance (%)", "antibiotic": "Antibiotic Target"},
                    color_discrete_map={**SOURCE_COLORS, **PATHOGEN_COLORS},
                )
            fig.update_layout(height=520, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)
            render_chart_expander(
                "Resistance Distributions",
                "Displays the spread of resistance percentages across country-year surveillance points. "
                "Notice higher resistance in Acinetobacter spp. (especially carbapenems) and Ceftriaxone in K. pneumoniae."
            )
        else:
            st.warning("No records matched the selected filter criteria.")
    else:
        st.info("Distribution data loading or unavailable from API.")

# TAB 2: Longitudinal Trends
with tab2:
    st.subheader("Annual Resistance Trajectories & Regional Trends")
    trend_data = api_get(f"/eda/trend?source={source_param}")
    if trend_data and trend_data.get("series"):
        df_trend = pd.DataFrame(trend_data["series"])
        if filters.get("pathogen"):
            df_trend = df_trend[df_trend["pathogen"] == filters["pathogen"]]
        if filters.get("antibiotic"):
            df_trend = df_trend[df_trend["antibiotic"] == filters["antibiotic"]]

        if not df_trend.empty:
            # Group by year and antibiotic to compute median and IQR
            agg = df_trend.groupby(["year", "antibiotic"])["pct_resistant"].agg(
                median="median",
                q25=lambda s: s.quantile(0.25),
                q75=lambda s: s.quantile(0.75)
            ).reset_index()

            fig_trend = px.line(
                agg,
                x="year",
                y="median",
                color="antibiotic",
                title=f"Median Resistance Over Time ({filters['scope']})",
                labels={"median": "Median Resistance (%)", "year": "Surveillance Year"},
            )
            fig_trend.update_layout(height=480)
            st.plotly_chart(fig_trend, use_container_width=True)
            render_chart_expander(
                "Median Resistance Trajectories",
                "Displays longitudinal annual medians with IQR bounds across surveillance years. "
                "Highlights divergent trends between first-line aminoglycosides vs third-generation cephalosporins and carbapenems."
            )

            st.markdown("#### Top 10 Mover Series (Largest Multi-Year Shift)")
            # Calculate range per series
            movers = df_trend.groupby(["iso3", "pathogen", "antibiotic"])["pct_resistant"].agg(
                min_val="min", max_val="max", delta=lambda s: s.max() - s.min()
            ).reset_index().sort_values("delta", ascending=False).head(10)
            st.dataframe(movers, use_container_width=True)
        else:
            st.warning("No trend records available for selected pathogen/antibiotic.")
    else:
        st.info("Longitudinal trend data loading.")

# TAB 3: Sample Size Funnel
with tab3:
    st.subheader("Surveillance Sample Size vs Resistance Variability")
    sample_data = api_get(f"/eda/sample-size?source={source_param}")
    if sample_data and sample_data.get("rows"):
        df_sample = pd.DataFrame(sample_data["rows"])
        if not df_sample.empty:
            df_sample["is_noisy"] = df_sample["number_tested"] < 30
            fig_funnel = px.scatter(
                df_sample,
                x="number_tested",
                y="pct_resistant",
                color="is_noisy",
                log_x=True,
                title="Resistance Rate vs Number of Isolates Tested (Log Scale)",
                labels={
                    "number_tested": "Number Tested (Log scale)",
                    "pct_resistant": "Resistance (%)",
                    "is_noisy": "Low Sample Flag (N < 30)",
                },
                color_discrete_map={True: "#ef4444", False: "#3b82f6"},
                hover_data=["iso3", "year", "pathogen", "antibiotic"],
            )
            # Add N=30 threshold line
            fig_funnel.add_vline(x=30, line_dash="dash", line_color="#ef4444", annotation_text="N=30 cutoff")
            fig_funnel.update_layout(height=520)
            st.plotly_chart(fig_funnel, use_container_width=True)
            render_chart_expander(
                "Sample Size Funnel Effect",
                "Observations with small sample sizes (N < 30) exhibit extreme binomial dispersion (0% or 100%), "
                "which generates artificial volatility and false-alarm rises. This justifies the N >= 30 filter for classification targets."
            )
    else:
        st.info("Sample size funnel data loading.")

# TAB 4: Year-on-Year Dynamics
with tab4:
    st.subheader("Annual Acceleration & COVID-19 Surveillance Impact")
    yoy_data = api_get(f"/eda/year-change?source={source_param}")
    if yoy_data and yoy_data.get("changes"):
        df_yoy = pd.DataFrame(yoy_data["changes"])
        if not df_yoy.empty:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                fig_hist = px.histogram(
                    df_yoy,
                    x="delta",
                    color="source" if source_param == "combined" else None,
                    nbins=40,
                    title="Distribution of Annual Delta (pct_resistant_t - pct_resistant_t-1)",
                    labels={"delta": "Year-on-Year Change (pp)"},
                )
                fig_hist.add_vline(x=5.0, line_dash="dash", line_color="#dc2626", annotation_text="+5 pp threshold")
                st.plotly_chart(fig_hist, use_container_width=True)

            with col_c2:
                # Group by year to see COVID-19 impact in 2020
                covid_agg = df_yoy.groupby("year")["delta"].agg(["mean", "std", "count"]).reset_index()
                fig_covid = px.bar(
                    covid_agg,
                    x="year",
                    y="mean",
                    error_y="std",
                    title="Mean Year-on-Year Change by Target Year (COVID-19 Check)",
                    labels={"mean": "Mean YoY Change (pp)", "year": "Target Year"},
                    color_discrete_sequence=["#0284c7"],
                )
                st.plotly_chart(fig_covid, use_container_width=True)
            render_chart_expander(
                "Year-on-Year Dynamics",
                "GLASS displays approximately double the year-on-year standard deviation (~10 pp) compared to ECDC (~4.7 pp), "
                "reflecting heterogeneous testing practices across non-European surveillance sites."
            )
    else:
        st.info("Year-on-year dynamics data loading.")

# TAB 5: Target Class Balance
with tab5:
    st.subheader("Target Prevalence Across Surveillance Thresholds")
    balance_data = api_get(f"/eda/class-balance?source={source_param}")
    if balance_data and balance_data.get("records"):
        df_bal = pd.DataFrame(balance_data["records"])
        fig_bal = px.bar(
            df_bal,
            x="target",
            y="prevalence",
            color="source" if source_param == "combined" else "target",
            title="Prevalence of Surveillance Flags (high_risk_next & rising_next)",
            labels={"prevalence": "Positive Class Share (%)", "target": "Surveillance Target Definition"},
            barmode="group",
            text="prevalence",
        )
        fig_bal.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_bal.update_layout(height=450)
        st.plotly_chart(fig_bal, use_container_width=True)
        render_chart_expander(
            "Class Balance Implications",
            "At T=30, high_risk_next is relatively balanced (56% in GLASS, 23% in ECDC), while rising_next is rare (~7-17%). "
            "Because of this extreme class imbalance in rising_next, PR-AUC is the primary metric and class weights are strictly applied."
        )
    else:
        st.info("Class balance data loading.")

# TAB 6: Cross-Resistance
with tab6:
    st.subheader("Cross-Resistance Co-occurrence Patterns")
    pathogen_sel = filters.get("pathogen") or "Klebsiella pneumoniae"
    corr_data = api_get(f"/eda/correlation?source={source_param}&pathogen={pathogen_sel}")
    if corr_data and corr_data.get("matrix"):
        corr_matrix = pd.DataFrame(corr_data["matrix"])
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title=f"Cross-Resistance Correlation Matrix: {pathogen_sel}",
        )
        fig_corr.update_layout(height=520)
        st.plotly_chart(fig_corr, use_container_width=True)
        render_chart_expander(
            "Cross-Resistance Dynamics",
            "High correlation across beta-lactams and carbapenems confirms strong co-resistance signals. "
            "Our feature engineering leverages this via `class_mean_other` and `mdr_burden`."
        )
    else:
        st.info("Cross-resistance correlation data loading.")

# TAB 7: Data Issues & Modeling Decisions
with tab7:
    st.subheader("Documented Surveillance Data Issues & Modeling Mitigations")
    issues = [
        {
            "Issue": "1. Divergent Resistance Definitions",
            "Surveillance Reality": "ECDC reports Intermediate + Resistant (I+R); GLASS reports Resistant (R). ECDC is ~2-3 pp higher in Malta overlap.",
            "Pipeline Mitigation": "Models are evaluated in 3 configurations: glass, ecdc, and pooled (with source indicator features). Sources are never blended into a single naive metric.",
        },
        {
            "Issue": "2. Small Sample Binomial Noise",
            "Surveillance Reality": "5.3% of GLASS rows have N < 30, producing extreme volatility and false rising signals.",
            "Pipeline Mitigation": "Classification targets strictly require N >= 30 in both year t and t-1; sample size features (log_tested, wilson_width) inform the models.",
        },
        {
            "Issue": "3. Temporal History Imbalance",
            "Surveillance Reality": "GLASS has 6 years (2018-2023) whereas ECDC has 21 years (1999-2019).",
            "Pipeline Mitigation": "Time-ordered splits with rolling-origin folds ensure validation always uses forward-in-time years.",
        },
        {
            "Issue": "4. COVID-19 Surveillance Disruptions",
            "Surveillance Reality": "2020 experienced hospital capacity shifts and diagnostic backlogs.",
            "Pipeline Mitigation": "Added explicit `covid_flag` feature for target year 2020 rather than dropping valuable observations.",
        },
        {
            "Issue": "5. AST Coverage Missingness",
            "Surveillance Reality": "Reported only in GLASS; entirely unrecorded in ECDC.",
            "Pipeline Mitigation": "Column is excluded in ecdc config; in pooled config, imputed with training median plus `ast_coverage_missing` indicator.",
        },
    ]
    st.dataframe(pd.DataFrame(issues), use_container_width=True)

render_key_takeaway(
    "Surveillance data shows pronounced pathogen-specific resistance gradients, strong cross-resistance correlations among carbapenems, "
    "and distinct sampling variance under N < 30. All modeling decisions rigorously isolate source definitions and filter small-sample noise."
)
