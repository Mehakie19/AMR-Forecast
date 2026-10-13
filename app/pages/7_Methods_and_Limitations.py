"""Page 7: Research Methodology, Systemic Limitations & Phase 2 Roadmap."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.ui import (
    DISCLAIMER_TEXT,
    api_get,
    render_banner_and_header,
    render_key_takeaway,
)

st.set_page_config(page_title="AMR-Sense — Methods & Limitations", layout="wide")
render_banner_and_header("Methodological Framework, Technical Limitations & Roadmap")

methods_res = api_get("/methods")

tab_def, tab_splits, tab_limits, tab_p2, tab_ver = st.tabs([
    "1. Target & Significance Definitions",
    "2. Time-Ordered Validation Design",
    "3. Surveillance Limitations",
    "4. Phase 2 Roadmap & Extension Stubs",
    "5. System & Reproducibility Provenance",
])

# TAB 1: Definitions
with tab_def:
    st.subheader("Surveillance Targets & Hypothesis Testing Rules")
    st.markdown(
        r"""
        ### 1. Regression Forecast Target (`y_reg`)
        - **Target:** Continuous percentage resistance $p_t$ in next surveillance year $t$.
        - **Evaluation:** Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and % of series beating persistence ($p_{t-1}$).

        ### 2. High-Risk Surveillance Alarm (`high_risk_next`)
        - **Binary Target:** $y = 1$ if $p_t \ge T$ (primary project-defined threshold $T = 30\%$).
        - **Sensitivity Experiments:** Repeated at project-defined $T = 20\%$ and $T = 50\%$.
        - **Decision Rule:** Threshold chosen on validation year to maximize $F_1$ subject to a False-Alert Rate cap ($\le 20\%$).

        ### 3. Statistically Significant Acceleration (`rising_next`)
        - **Composite Rule:** Flags rapid resistance acceleration requiring public health audit.
        - **Condition 1:** Magnitude rise: $p_t - p_{t-1} \ge 5.0\text{ pp}$.
        - **Condition 2:** Two-proportion one-sided z-test (`statsmodels.stats.proportion.proportions_ztest`) with $p < 0.05$.
        - **Condition 3:** Robust sample sizes: $N_t \ge 30$ and $N_{t-1} \ge 30$.
        """
    )

# TAB 2: Split Design
with tab_splits:
    st.subheader("Time-Ordered Split Design & Rolling-Origin Folds")
    st.markdown(
        r"""
        To eliminate temporal lookahead bias, all data splits strictly respect the historical timeline:

        | Configuration | Training Targets | Validation Folds | Guarded Final Test |
        |---|---|---|---|
        | **GLASS-AMR** | 2019 – 2021 | 2022 | 2023 |
        | **ECDC-derived** | 1999 – 2015 | 2016 – 2017 | 2018 – 2019 |
        | **Pooled** | ECDC $\le 2015$ + GLASS 2019–2021 | ECDC 2016–2017 + GLASS 2022 | ECDC 2018–2019 + GLASS 2023 |

        - **Rolling-Origin Cross-Validation:** Base models and meta-learners are tuned exclusively on training years using expanding rolling-origin windows: Fold $k$ trains on years $< Y_k$ and validates on $Y_k$.
        - **Frozen Test Evaluation:** The final test year is held strictly secret and unlocked once via guarded script execution.
        """
    )

# TAB 3: Limitations
with tab_limits:
    st.subheader("Surveillance Caveats & Technical Limitations")
    limits = [
        {
            "Domain": "Definition Disparity (I+R vs R)",
            "Limitation": "ECDC measures Intermediate + Resistant combined; GLASS reports Resistant. Malta overlap shows ECDC values run ~2-3 pp higher. Direct numeric comparison across sources is prohibited.",
        },
        {
            "Domain": "Reporting Filter Bias",
            "Limitation": "GLASS participation currently reflects higher-resourced reference laboratories and tertiary medical centers, potentially overestimating community resistance.",
        },
        {
            "Domain": "Short GLASS Panel",
            "Limitation": "GLASS provides 6 annual rounds (2018-2023). Lag-2 temporal features consume 2 years, leaving restricted training windows for non-European series.",
        },
        {
            "Domain": "Project-Defined Thresholds",
            "Limitation": "Cutoffs (T=30%, 5 pp rise) are chosen for surveillance triage and operational alerting, not clinical treatment failure boundaries.",
        },
        {
            "Domain": "Sample Size Attrition",
            "Limitation": "Surveillance series with N < 30 are excluded from binary classification benchmarks due to extreme binomial variance.",
        },
    ]
    st.dataframe(pd.DataFrame(limits), use_container_width=True)

# TAB 4: Phase 2 Roadmap
with tab_p2:
    st.subheader("Phase 2 Technical Roadmap & Extension Stubs")
    st.markdown(
        """
        The Phase 1 architecture provides clean extension hooks for upcoming Phase 2 research modules:

        - [ ] **SHAP TreeExplainers:** Feature attribution per forecast series (`src/amr_sense/explainability/shap_engine.py` TODO stub).
        - [ ] **Conformal Prediction:** Split-conformal distribution-free coverage intervals (`src/amr_sense/conformal/bands.py` TODO stub).
        - [ ] **Longitudinal Clustering:** Dynamic time warping / K-means trajectory clustering (`src/amr_sense/clustering/trajectories.py` TODO stub).
        - [ ] **Anomaly Detection:** Isolation Forests & CUSUM change-point detectors for outbreak discovery (`src/amr_sense/anomaly/cusum.py` TODO stub).
        - [ ] **Transfer Learning:** Zero-shot transfer from 21-year ECDC models to emerging GLASS sites.
        """
    )
    with st.expander("View Phase 2 Developer Extension Stubs"):
        st.code(
            """
            # Extension point: src/amr_sense/phase2_stubs.py
            def compute_shap_values(model, X):
                # TODO: Implement SHAP TreeExplainer / KernelExplainer in Phase 2
                raise NotImplementedError("Phase 2 module: SHAP explainability")

            def conformal_prediction_intervals(model, X_calib, y_calib, X_test, alpha=0.10):
                # TODO: Implement inductive conformal prediction in Phase 2
                raise NotImplementedError("Phase 2 module: Conformal prediction intervals")

            def detect_cusum_anomalies(series, threshold=5.0):
                # TODO: Implement CUSUM change-point detection in Phase 2
                raise NotImplementedError("Phase 2 module: CUSUM change-point detection")
            """,
            language="python",
        )

# TAB 5: Provenance
with tab_ver:
    st.subheader("System Versioning & Provenance Hashes")
    if methods_res:
        st.json(methods_res)

render_key_takeaway(
    "AMR-Sense enforces strict methodological guards: temporal rolling-origin validation, "
    "country-clustered bootstrap confidence intervals, and complete decoupling of clinical prescribing from epidemiological surveillance."
)
