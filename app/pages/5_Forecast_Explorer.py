"""Page 5: Interactive Surveillance Forecast Explorer."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import (
    DISCLAIMER_TEXT,
    PATHOGEN_COLORS,
    SOURCE_COLORS,
    api_get,
    api_post,
    render_banner_and_header,
    render_chart_expander,
    render_key_takeaway,
)

st.set_page_config(page_title="AMR-Sense — Forecast Explorer", layout="wide")
render_banner_and_header("Interactive Surveillance Forecast Explorer")

# 1. Selectors
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    source_choice = st.selectbox("Surveillance Source", ["glass", "ecdc"], index=0)
with c2:
    # Common countries
    glass_countries = ["CAN", "SWE", "ZAF", "EGY", "IND", "FRA", "DEU", "ESP", "ITA", "BRA"]
    ecdc_countries = ["FRA", "DEU", "ITA", "ESP", "NLD", "SWE", "GBR", "POL", "GRC"]
    avail_countries = glass_countries if source_choice == "glass" else ecdc_countries
    iso3_choice = st.selectbox("Country (ISO3)", avail_countries, index=0)
with c3:
    pathogen_choice = st.selectbox(
        "Pathogen",
        ["Escherichia coli", "Klebsiella pneumoniae", "Acinetobacter spp."],
        index=0,
    )
with c4:
    antibiotic_choice = st.selectbox(
        "Antibiotic",
        ["Ciprofloxacin", "Ceftriaxone", "Meropenem", "Gentamicin", "Colistin"],
        index=0,
    )
with c5:
    config_choice = st.selectbox("Model Config", [source_choice, "pooled"], index=0)

# Fetch series history
series_hist = api_get(
    f"/series?source={source_choice}&iso3={iso3_choice}&pathogen={pathogen_choice}&antibiotic={antibiotic_choice}"
)

# Fetch prediction
pred_payload = {
    "source": source_choice,
    "iso3": iso3_choice,
    "pathogen": pathogen_choice,
    "antibiotic": antibiotic_choice,
    "model_config": config_choice,
}
pred_res = api_post("/predict", pred_payload)

if series_hist and series_hist.get("records"):
    df_hist = pd.DataFrame(series_hist["records"])
    st.subheader(f"Surveillance Trajectory: {iso3_choice} — {pathogen_choice} against {antibiotic_choice}")

    # 2. History & Forecast Chart
    fig = go.Figure()

    # Observed points
    solid_pts = df_hist[df_hist["number_tested"] >= 30]
    hollow_pts = df_hist[df_hist["number_tested"] < 30]

    if not solid_pts.empty:
        fig.add_trace(go.Scatter(
            x=solid_pts["year"],
            y=solid_pts["pct_resistant"],
            mode="lines+markers",
            name="Observed (N >= 30)",
            line=dict(color="#2563eb", width=2),
            marker=dict(size=solid_pts["number_tested"].clip(30, 500) / 25 + 6, color="#2563eb"),
            hovertemplate="Year %{x}: %{y:.1f}% (N=%{text})",
            text=solid_pts["number_tested"],
        ))

    if not hollow_pts.empty:
        fig.add_trace(go.Scatter(
            x=hollow_pts["year"],
            y=hollow_pts["pct_resistant"],
            mode="markers",
            name="Noisy Observed (N < 30)",
            marker=dict(symbol="circle-open", size=10, line=dict(color="#ef4444", width=2)),
            hovertemplate="Year %{x}: %{y:.1f}% (N=%{text}, Low Sample)",
            text=hollow_pts["number_tested"],
        ))

    # Add forecasts if available
    if pred_res:
        last_year = df_hist["year"].max()
        target_year = last_year + 1
        forecast_val = pred_res.get("forecast_pct", df_hist["pct_resistant"].iloc[-1])
        persistence_val = df_hist["pct_resistant"].iloc[-1]

        # Forecast point
        fig.add_trace(go.Scatter(
            x=[last_year, target_year],
            y=[persistence_val, forecast_val],
            mode="lines+markers",
            name="ML Forecast (Best Model)",
            line=dict(color="#10b981", dash="dot", width=3),
            marker=dict(symbol="star", size=14, color="#10b981"),
            hovertemplate=f"Forecast Year {target_year}: {forecast_val:.1f}%",
        ))

        # Persistence baseline
        fig.add_trace(go.Scatter(
            x=[last_year, target_year],
            y=[persistence_val, persistence_val],
            mode="lines",
            name="Persistence Baseline",
            line=dict(color="#94a3b8", dash="dash"),
        ))

    fig.update_layout(
        height=480,
        title=f"Longitudinal Trajectory & Next-Year Forecast ({source_choice.upper()})",
        xaxis_title="Surveillance Year",
        yaxis_title="Resistance (%)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"⚠️ {DISCLAIMER_TEXT}")

    # 3. Probability Cards
    if pred_res:
        st.markdown("---")
        st.subheader("Surveillance Risk Evaluation Cards")
        p_col1, p_col2, p_col3 = st.columns(3)

        high_prob = pred_res.get("high_risk_probability", 0.0)
        high_thresh = pred_res.get("decision_threshold_high_risk", 0.40)
        high_alert = high_prob >= high_thresh

        with p_col1:
            st.metric(
                "High-Risk Probability (Resistance >= 30%)",
                f"{high_prob:.1%}",
                delta=f"{'Above' if high_alert else 'Below'} Review Threshold ({high_thresh:.0%})",
                delta_color="inverse" if high_alert else "normal",
            )
            st.caption(f"Status: **{'FLAGGED FOR REVIEW' if high_alert else 'Standard Monitoring'}**")

        rise_prob = pred_res.get("rising_probability", 0.0)
        rise_thresh = pred_res.get("decision_threshold_rising", 0.20)
        rise_alert = rise_prob >= rise_thresh

        with p_col2:
            st.metric(
                "Rising Resistance Probability (+5 pp Acceleration)",
                f"{rise_prob:.1%}",
                delta=f"{'Above' if rise_alert else 'Below'} Review Threshold ({rise_thresh:.0%})",
                delta_color="inverse" if rise_alert else "normal",
            )
            st.caption(f"Status: **{'ACCELERATION SIGNAL' if rise_alert else 'Stable Trajectory'}**")

        with p_col3:
            st.metric("Companion Point Forecast", f"{pred_res.get('forecast_pct', 0.0):.1f}%")
            dq_note = pred_res.get("data_quality_note", "Standard observation")
            st.caption(f"Data Quality: **{dq_note}**")

        # 4. Context Panel: Cross-Resistance
        st.markdown("---")
        st.subheader("Surveillance Feature Context & Cross-Resistance Profile")
        c_ctx1, c_ctx2 = st.columns(2)
        with c_ctx1:
            st.markdown("#### Feature Values Input into Models")
            feat_df = pd.DataFrame(
                [{"Feature": k, "Value": f"{v:.3f}" if isinstance(v, float) else str(v)}
                 for k, v in pred_res.get("features_used", {}).items()]
            )
            st.dataframe(feat_df, height=300, use_container_width=True)

        with c_ctx2:
            st.markdown(f"#### Co-Resistance Profile: {pathogen_choice} in {iso3_choice}")
            cross_data = pred_res.get("cross_resistance_context", {})
            if cross_data:
                cross_df = pd.DataFrame(
                    [{"Antibiotic": k, "Resistance (%)": v} for k, v in cross_data.items()]
                )
                fig_cross = px.bar(
                    cross_df,
                    x="Antibiotic",
                    y="Resistance (%)",
                    color="Resistance (%)",
                    color_continuous_scale="Reds",
                    title=f"Latest Resistance across Antibiotic Classes",
                )
                fig_cross.update_layout(height=300)
                st.plotly_chart(fig_cross, use_container_width=True)
            else:
                st.info("Co-resistance context not available for this series.")
else:
    st.warning("No historical series found for this combination in surveillance records.")

render_key_takeaway(
    "Interactive forecasting synthesizes temporal inertia, sample volatility, and cross-resistance co-occurrence. "
    "Probability flags denote surveillance priority for expert epidemiologist review, not clinical prescribing advice."
)
