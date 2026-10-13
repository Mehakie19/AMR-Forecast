"""Page 4: Model Lab — Rigorous Model Benchmarking & Diagnostics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.ui import (
    METRIC_TOOLTIPS,
    api_get,
    render_banner_and_header,
    render_chart_expander,
    render_key_takeaway,
)

st.set_page_config(page_title="AMR-Sense — Model Lab", layout="wide")
render_banner_and_header("Model Lab: Benchmarking, Diagnostics & Ensembles")

# Top controls
c_cfg, c_tgt, c_split = st.columns(3)
with c_cfg:
    config_sel = st.selectbox("Model Configuration", ["glass", "ecdc", "pooled"], index=0)
with c_tgt:
    target_sel = st.selectbox(
        "Surveillance Target",
        ["high_risk_next", "rising_next", "y_reg"],
        index=0,
        format_func=lambda x: {
            "high_risk_next": "High-Risk Next Year (>= 30%)",
            "rising_next": "Rising Next Year (+5 pp & p < 0.05)",
            "y_reg": "Resistance % Regression Forecast",
        }.get(x, x),
    )
with c_split:
    health = api_get("/health")
    is_frozen = health.get("frozen", False) if health else False
    split_options = ["val"]
    if is_frozen:
        split_options.append("test")
    split_sel = st.selectbox(
        "Evaluation Split",
        split_options,
        index=0,
        format_func=lambda s: "Validation Split (Forward OOF)" if s == "val" else "Guarded Final Test Set (Single Shot)",
    )

tab_comp, tab_curves, tab_reg, tab_tune, tab_ens, tab_seg, tab_err, tab_thresh, tab_regress = st.tabs([
    "1. Model Comparison",
    "2. Performance Curves",
    "3. Regularization Evidence",
    "4. Hyperparameter Tuning",
    "5. Ensembles & Diversity",
    "6. Segment Performance",
    "7. Error & False Alert Analysis",
    "8. Thresholds & Pooling",
    "9. Companion Regressors",
])

# TAB 1: Comparison
with tab_comp:
    st.subheader(f"Model Comparison Table ({config_sel.upper()} | {target_sel} | {split_sel.upper()})")
    for m, tip in METRIC_TOOLTIPS.items():
        st.caption(f"**{m}**: {tip}")

    comp_res = api_get(f"/results/comparison?config={config_sel}&target={target_sel}&split={split_sel}")
    if comp_res and comp_res.get("rows"):
        df_comp = pd.DataFrame(comp_res["rows"])
        st.dataframe(df_comp, use_container_width=True)

        metric_choice = st.selectbox("Metric for Bar Chart", ["pr_auc", "roc_auc", "f1", "recall", "precision", "brier"], index=0)
        if metric_choice in df_comp.columns:
            fig_bar = px.bar(
                df_comp,
                x="model",
                y=metric_choice,
                title=f"Model Comparison on {metric_choice.upper()} with 95% Country Bootstrap CIs",
                labels={"model": "Model", metric_choice: metric_choice.upper()},
                color="model",
            )
            fig_bar.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
            render_chart_expander(
                "Model Benchmark Interpretation",
                "Compares machine learning models against persistence and dummy baselines. "
                "Notice that country-level bootstrap CIs account for intra-country clustering of resistance series."
            )
    else:
        st.info("Comparison results loading or models currently training.")

# TAB 2: Curves
with tab_curves:
    st.subheader("Precision-Recall, ROC, and Calibration Curves")
    model_choice = st.selectbox("Select Model", ["logistic_regression", "random_forest", "xgboost", "soft_voting", "stacking"], index=2)
    curves_res = api_get(f"/results/curves?config={config_sel}&target={target_sel}&model={model_choice}")
    if curves_res:
        c1, c2 = st.columns(2)
        with c1:
            if curves_res.get("pr_curve"):
                pr_df = pd.DataFrame(curves_res["pr_curve"])
                fig_pr = px.line(pr_df, x="recall", y="precision", title=f"PR Curve ({model_choice})")
                st.plotly_chart(fig_pr, use_container_width=True)
        with c2:
            if curves_res.get("roc_curve"):
                roc_df = pd.DataFrame(curves_res["roc_curve"])
                fig_roc = px.line(roc_df, x="fpr", y="tpr", title=f"ROC Curve ({model_choice})")
                st.plotly_chart(fig_roc, use_container_width=True)

        if curves_res.get("calibration"):
            cal_df = pd.DataFrame(curves_res["calibration"])
            fig_cal = px.scatter(cal_df, x="mean_predicted_value", y="fraction_of_positives", title="Reliability Diagram (Calibration)")
            fig_cal.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect Calibration", line=dict(dash="dash")))
            st.plotly_chart(fig_cal, use_container_width=True)
    else:
        st.info("Performance curve data loading.")

# TAB 3: Regularization
with tab_reg:
    st.subheader("Regularization Evidence: Controlling Overfitting")
    reg_res = api_get("/results/regularization")
    if reg_res and reg_res.get("records"):
        df_reg = pd.DataFrame(reg_res["records"])
        st.dataframe(df_reg, use_container_width=True)

        st.markdown("#### Sparsity & L1 Feature Selection")
        if reg_res.get("l1_coefficients"):
            coef_df = pd.DataFrame(reg_res["l1_coefficients"])
            fig_coef = px.bar(
                coef_df.sort_values("weight", ascending=True),
                x="weight",
                y="feature",
                orientation="h",
                title=f"L1 Logistic Regression Nonzero Coefficients ({len(coef_df)} active features)",
            )
            fig_coef.update_layout(height=480)
            st.plotly_chart(fig_coef, use_container_width=True)
            render_chart_expander(
                "L1 Regularization Sparsity",
                "L1 penalty shrinks redundant correlated features to exactly zero. "
                "Notice that core temporal lag and cross-resistance features retain non-zero weights."
            )
    else:
        st.info("Regularization records loading.")

# TAB 4: Tuning
with tab_tune:
    st.subheader("Optuna Hyperparameter Optimization Studies")
    tune_res = api_get(f"/results/tuning?config={config_sel}")
    if tune_res and tune_res.get("best_params"):
        st.markdown("#### Best Discovered Hyperparameters")
        st.json(tune_res["best_params"])

        if tune_res.get("trial_history"):
            trials_df = pd.DataFrame(tune_res["trial_history"])
            fig_hist = px.line(
                trials_df,
                x="trial",
                y="value",
                color="model",
                title="Optimization Convergence across Rolling-Origin Folds (PR-AUC)",
                labels={"trial": "Trial #", "value": "Mean OOF PR-AUC"},
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("Optuna tuning artifacts loading.")

# TAB 5: Ensembles
with tab_ens:
    st.subheader("Soft Voting & Time-Safe Stacking Ensembles")
    ens_res = api_get(f"/results/ensembles?config={config_sel}")
    if ens_res:
        st.markdown(
            """
            - **Bagging / Soft Voting:** Reduces variance by averaging calibrated probabilities across diverse model families.
            - **Time-Safe Stacking:** Trains a logistic meta-learner on out-of-fold rolling-origin predictions only.
            """
        )
        if ens_res.get("meta_weights"):
            st.markdown("#### Meta-Learner Model Weights")
            st.json(ens_res["meta_weights"])
        if ens_res.get("error_correlation"):
            corr_df = pd.DataFrame(ens_res["error_correlation"])
            fig_corr = px.imshow(corr_df, text_auto=".2f", title="Base Model Error Diversity Correlation")
            st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Ensemble artifacts loading.")

# TAB 6: Segments
with tab_seg:
    st.subheader("Granular Segment Performance")
    seg_res = api_get(f"/results/segments?config={config_sel}")
    if seg_res and seg_res.get("segments"):
        df_seg = pd.DataFrame(seg_res["segments"])
        st.dataframe(df_seg, use_container_width=True)
    else:
        st.info("Segment analysis loading.")

# TAB 7: Errors
with tab_err:
    st.subheader("Error Analysis & High-Confidence False Alerts")
    err_res = api_get(f"/results/errors?config={config_sel}")
    if err_res:
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.markdown("#### 15 Largest Regression Forecast Errors")
            if err_res.get("largest_errors"):
                st.dataframe(pd.DataFrame(err_res["largest_errors"]), use_container_width=True)
        with col_e2:
            st.markdown("#### 15 Highest-Confidence False Alerts")
            if err_res.get("false_alerts"):
                st.dataframe(pd.DataFrame(err_res["false_alerts"]), use_container_width=True)
    else:
        st.info("Error analysis tables loading.")

# TAB 8: Thresholds & Pooling
with tab_thresh:
    st.subheader("Threshold Sensitivity & Pooled vs Separate Comparison")
    st.markdown("#### High-Risk Threshold Sensitivity (T = 20%, 30%, 50%)")
    thresh_res = api_get("/results/threshold-sensitivity")
    if thresh_res and thresh_res.get("records"):
        st.dataframe(pd.DataFrame(thresh_res["records"]), use_container_width=True)

    st.markdown("#### Pooled vs Separate Performance on Common Test Rows")
    pool_res = api_get("/results/pooled-vs-separate")
    if pool_res and pool_res.get("comparison"):
        st.dataframe(pd.DataFrame(pool_res["comparison"]), use_container_width=True)
        st.caption("Evaluates whether pooling heterogeneous datasets helped, hurt, or made no difference relative to dedicated single-source models.")

# TAB 9: Companion Regressors
with tab_regress:
    st.subheader("Companion Resistance Regressors (MAE & RMSE)")
    reg_comp_res = api_get(f"/results/comparison?config={config_sel}&target=y_reg&split={split_sel}")
    if reg_comp_res and reg_comp_res.get("rows"):
        df_regress = pd.DataFrame(reg_comp_res["rows"])
        st.dataframe(df_regress, use_container_width=True)
        render_chart_expander(
            "Companion Regressor Analysis",
            "Regression predicts the continuous percentage resistance for year t. "
            "Evaluated by MAE, RMSE, and the percentage of series beating naive persistence."
        )

render_key_takeaway(
    f"Model evaluation on {config_sel} demonstrates rigorous out-of-fold generalization. "
    "Tree ensembles and tuned regularization constrain overfitting, providing calibrated surveillance probabilities."
)
