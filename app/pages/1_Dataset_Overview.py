"""Page 1: Dataset Overview & Data Quality."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import (
    api_get,
    render_banner_and_header,
    render_chart_expander,
    render_key_takeaway,
    render_sidebar,
)

st.set_page_config(page_title="AMR-Sense — Dataset Overview", layout="wide")
render_banner_and_header("Dataset Overview & Surveillance Coverage")
filters = render_sidebar(allow_pathogen_filter=True, allow_antibiotic_filter=True)
source_param = filters["source"]

# 1. KPI Cards
summary = api_get(f"/datasets/summary?source={source_param}")
glass_summary = api_get("/datasets/summary?source=glass")
ecdc_summary = api_get("/datasets/summary?source=ecdc")

if summary:
    st.subheader("Surveillance Scope Metrics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Records", f"{summary['rows']:,}")
    c2.metric("Unique Series", f"{summary['series']:,}")
    c3.metric("Countries", summary["countries"])
    c4.metric("Years Span", f"{summary['years'][0]}–{summary['years'][1]}")
    c5.metric("Pathogens", summary["pathogens"])
    c6.metric("Antibiotics", summary["antibiotics"])

    if source_param == "combined" and glass_summary and ecdc_summary:
        st.markdown("**Breakdown by Surveillance System:**")
        b1, b2, b3 = st.columns(3)
        b1.info(f"**GLASS-AMR:** {glass_summary['rows']:,} rows | {glass_summary['countries']} countries | {glass_summary['years'][0]}–{glass_summary['years'][1]} | Def: Reported R")
        b2.warning(f"**ECDC-derived:** {ecdc_summary['rows']:,} rows | {ecdc_summary['countries']} countries | {ecdc_summary['years'][0]}–{ecdc_summary['years'][1]} | Def: I+R (Inpatient)")
        b3.success(f"**Overlap Cases:** 8 records (Malta 2018–2019, 2 pathogen/abx pairs)")

# 2. Source Comparison Table
st.markdown("---")
st.subheader("Surveillance Data Provenance & Definition Comparison")
comparison_data = [
    {
        "Attribute": "Publisher / System",
        "GLASS-AMR": "World Health Organization (WHO GLASS Dashboard)",
        "ECDC-EARSNet (Derived)": "European Centre for Disease Prevention & Control (Zenodo record 14224680)",
    },
    {
        "Attribute": "Temporal Range",
        "GLASS-AMR": "2018 – 2023 (6 annual rounds)",
        "ECDC-EARSNet (Derived)": "1999 – 2019 (21 annual rounds)",
    },
    {
        "Attribute": "Geographic Scope",
        "GLASS-AMR": "31 participating countries across 5 WHO regions",
        "ECDC-EARSNet (Derived)": "29 European countries (EU/EEA)",
    },
    {
        "Attribute": "Patient / Specimen Setting",
        "GLASS-AMR": "Bloodstream infection isolates",
        "ECDC-EARSNet (Derived)": "Inpatient invasive blood & CSF isolates",
    },
    {
        "Attribute": "Resistance Metric & Definition",
        "GLASS-AMR": "R as reported by GLASS",
        "ECDC-EARSNet (Derived)": "I+R (Intermediate + Resistant combined)",
    },
    {
        "Attribute": "Record Count",
        "GLASS-AMR": "2,394 rows (399 series × 6 complete years)",
        "ECDC-EARSNet (Derived)": "4,240 rows (unbalanced longitudinal expansion)",
    },
    {
        "Attribute": "Sample Size Policy",
        "GLASS-AMR": "~5% rows have N < 30 (noisy surveillance)",
        "ECDC-EARSNet (Derived)": "Pre-filtered N >= 30 isolates per observation",
    },
]
st.dataframe(pd.DataFrame(comparison_data).set_index("Attribute"), use_container_width=True)

# 3. Coverage Heatmap
st.markdown("---")
st.subheader("Country × Year Surveillance Reporting Density")
coverage_params = f"source={source_param}"
if filters.get("pathogen"):
    coverage_params += f"&pathogen={filters['pathogen']}"
if filters.get("antibiotic"):
    coverage_params += f"&antibiotic={filters['antibiotic']}"

coverage_res = api_get(f"/datasets/coverage?{coverage_params}")
if coverage_res and coverage_res.get("matrix"):
    matrix_df = pd.DataFrame(coverage_res["matrix"])
    if not matrix_df.empty and "iso3" in matrix_df.columns:
        pivot_df = matrix_df.pivot(index="iso3", columns="year", values="series_count").fillna(0)
        fig_heat = px.imshow(
            pivot_df,
            labels=dict(x="Year", y="Country (ISO3)", color="Series Count"),
            color_continuous_scale="Blues" if source_param == "glass" else "YlOrRd",
            aspect="auto",
            title=f"Reporting Coverage Matrix ({filters['scope']})",
        )
        fig_heat.update_layout(height=520, margin=dict(l=40, r=40, t=50, b=40))
        st.plotly_chart(fig_heat, use_container_width=True)
        render_chart_expander(
            "Coverage Heatmap",
            "Each cell shows the count of active pathogen-antibiotic series reported for a given country and year. "
            "Notice how GLASS-AMR forms a balanced panel across 2018–2023, whereas ECDC shows historical coverage expansion from 2002 to 2015."
        )

# 4. Data Quality Panel
st.markdown("---")
st.subheader("Data Quality & Provenance Checks")
quality = api_get("/datasets/quality")
if quality:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Missing Values", quality.get("missing_values", 0))
    q2.metric("Duplicates (Primary Key)", quality.get("duplicate_keys", 0))
    q3.metric("GLASS N < 30 Share", f"{quality.get('glass_n_lt_30_pct', 5.3):.1f}%")
    q4.metric("ECDC N < 30 Share", f"{quality.get('ecdc_n_lt_30_pct', 0.0):.1f}%")

    if quality.get("overlap_records"):
        st.markdown("**Malta Overlap Audit (Same Geography & Years in Both Systems):**")
        overlap_df = pd.DataFrame(quality["overlap_records"])
        st.dataframe(overlap_df, use_container_width=True)
        st.caption("ECDC values run approx 2–3 pp higher because ECDC includes Intermediate isolates (I+R) whereas GLASS reports Resistant (R).")

# 5. Pipeline Flow Diagram
st.markdown("---")
st.subheader("AMR-Sense Architecture Flow")
flow_cols = st.columns(6)
flow_cols[0].button("1. Ingestion\nImmutable CSVs", use_container_width=True, disabled=True)
flow_cols[1].button("2. Quality\nValidation & EDA", use_container_width=True, disabled=True)
flow_cols[2].button("3. Panel\nLeakage-Safe Features", use_container_width=True, disabled=True)
flow_cols[3].button("4. Time-Split\nRolling-Origin Folds", use_container_width=True, disabled=True)
flow_cols[4].button("5. Models\nLR, RF, XGB, Stacking", use_container_width=True, disabled=True)
flow_cols[5].button("6. Expert Review\nSurveillance Watchlist", use_container_width=True, disabled=True)

if summary:
    render_key_takeaway(
        f"The single source of truth holds {summary['rows']:,} records across {summary['countries']} countries. "
        f"GLASS represents a balanced 6-year panel (2018–2023), while ECDC provides deep longitudinal history (1999–2019). "
        f"Because resistance definitions differ (R vs I+R), models and analyses are rigorously trained both separately and in pooled configurations."
    )
