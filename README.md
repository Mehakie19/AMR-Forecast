# AMR-Sense (Phase 1)

> ⚠️ **Persistent Disclaimer:** Surveillance and research tool only. Not for treatment decisions. Predicted resistance is not the probability of clinical cure. High-risk and rising resistance thresholds are **project-defined**, not clinical guidelines.

AMR-Sense is a research-oriented, explainable antimicrobial resistance (AMR) early-warning and decision-support system built on population-level surveillance records from the World Health Organization (WHO GLASS-AMR) and the European Centre for Disease Prevention and Control (ECDC-EARSNet, Zenodo record 14224680).

---

## 1. Research Question & Purpose

*Can historical resistance inertia, sample-quality characteristics, and cross-resistance co-occurrence improve next-year surveillance forecasting and early identification of high-resistance and accelerating resistance trends compared to naive persistence baselines?*

Phase 1 delivers:
- **Rigorous Data & EDA Layer:** Ingestion of 6,634 longitudinal surveillance observations across 42 countries, 3 priority Gram-negative pathogens (*E. coli*, *K. pneumoniae*, *Acinetobacter* spp.), and 9 critical antibiotic targets.
- **Leakage-Safe Feature Engineering:** 23 temporal, sample-quality, cross-resistance, and contextual features built strictly under the temporal invariant $t \le t-1$.
- **Time-Ordered Splits & Rolling-Origin Validation:** Forward-chaining folds that prevent lookahead bias; no random splits or synthetic oversampling.
- **Calibrated Classifiers & Companion Regressors:** Regularized Logistic Regression (Elastic Net), Random Forests, XGBoost, Soft Voting, and Time-Safe Out-Of-Fold Stacking across three distinct configurations: `glass`, `ecdc`, and `pooled`.
- **Country-Clustered Bootstrap CIs:** 1,000 paired cluster resamples for all headline metrics and differences against baselines.
- **Guarded Final-Test Execution:** Single-shot test set evaluation guarded by a `models/FROZEN` lock.
- **FastAPI Read-Only Backend:** Serving precomputed UI datasets and on-demand model inference with Pydantic validation.
- **Interactive React/Vite Frontend:** Seven research pages for dataset coverage, EDA, features, model results, forecasting, watchlists, and methods. A legacy Streamlit interface also remains under `app/`.

---

## 2. Surveillance Data & Single Source of Truth

**Single Source of Truth:** `data/raw/combined_amr_dataset.csv`
- Total records: **6,634** rows
- **GLASS-AMR:** 2,394 rows (2018–2023, 31 countries, 399 balanced series × 6 rounds). Definition: **Resistant (R)** as reported by GLASS.
- **ECDC-derived:** 4,240 rows (1999–2019, 29 European countries). Definition: **Intermediate + Resistant (I+R)** combined.
- **Overlap Audit:** 8 records (Malta 2018–2019). Because ECDC includes Intermediate isolates, ECDC resistance rates run ~2–3 percentage points higher than GLASS on identical series.

> ℹ️ **Definition Caveat:** Because resistance metrics differ (R vs I+R), models and analyses are rigorously trained both separately (`glass`, `ecdc`) and in a pooled setting (`pooled`) with explicit source indicators. Rates are never naively averaged across definitions.

---

## 3. How to Run the Pipeline

All steps are managed via `Makefile` targets:

```bash
# 1. Environment installation
pip install -r requirements.txt
export PYTHONPATH=src   # On Windows PowerShell: $env:PYTHONPATH="src"

# 2. Stage 1: Data validation & EDA
make eda
# Generates reports/eda/data_quality.md, reports/figures/eda/ (23 figures), and reports/eda/eda_findings.md

# 3. Stage 2: Feature engineering
make features
# Generates data/processed/panel_{glass,ecdc,pooled}.parquet and reports/results/feature_dictionary.md

# 4. Stage 3 & 4: Model training, tuning, ensembles, and validation
make train
# Tunes hyperparameters with Optuna, evaluates rolling-origin folds, writes models/FROZEN

# 5. Stage 4: Guarded final-test evaluation (single-shot)
make final-test
# Evaluates on held-out test sets (GLASS 2023, ECDC 2018-2019), writes reports/results/test_results.md

# 6. Stage 5: Precompute UI data for API
make ui-data
# Exports 20 parquet and JSON artifacts into data/ui/

# 7. Run automated test suite
make test
# Executes pytest tests/ -v (all 26 unit, leakage, API, and Vite smoke tests pass)

# 8. Start FastAPI backend (Port 8001)
make api
# Or: uvicorn api.main:app --reload --host 127.0.0.1 --port 8001

# 9. Start Vite Frontend (Port 5173)
make frontend
# Or: cd frontend && npm run dev
```

The Vite development server proxies `/api` requests to `http://127.0.0.1:8001`, so start both the API and frontend. Port `8001` avoids conflicts with another local service on `8000`. For a separately hosted frontend, set `VITE_API_BASE_URL` to the FastAPI base URL before building. If UI artifacts are absent or stale, run `make ui-data` after the data and model pipeline is ready.

---

## 4. Key Experimental Results (True Numbers from Code)

All numbers below were computed by automated evaluation code and paired country-cluster bootstrap:

### Target 1: High-Risk Resistance Alarm (`high_risk_next`, $T = 30\%$)
- **GLASS 2023 Held-Out Test Set:**
  - Persistence Baseline: PR-AUC = 0.9527 [0.9212, 0.9795]
  - Tuned Logistic Regression: PR-AUC = 0.9886 [0.9790, 0.9952] (Diff: **+0.0358 [+0.0133, +0.0617]**)
  - Soft Voting Ensemble: PR-AUC = 0.9908 [0.9835, 0.9965] (Diff: **+0.0381 [+0.0163, +0.0646]**)
  - Time-Safe Stacking: PR-AUC = 0.9908 [0.9834, 0.9964] (Diff: **+0.0380 [+0.0163, +0.0646]**)
- **ECDC 2018–2019 Held-Out Test Set:**
  - Persistence Baseline: PR-AUC = 0.9298 [0.8735, 0.9629]
  - Tuned Logistic Regression: PR-AUC = 0.9834 [0.9505, 0.9963] (Diff: **+0.0537 [+0.0306, +0.0865]**)
  - Random Forest: PR-AUC = 0.9816 [0.9442, 0.9963] (Diff: **+0.0518 [+0.0301, +0.0816]**)
- **Pooled Held-Out Test Set:**
  - Persistence Baseline: PR-AUC = 0.9401 [0.9122, 0.9634]
  - Soft Voting Ensemble: PR-AUC = 0.9875 [0.9767, 0.9947] (Diff: **+0.0474 [+0.0300, +0.0690]**)

### Target 2: Statistically Significant Acceleration (`rising_next`, $+5\text{ pp}$ & $p < 0.05$)
- **GLASS 2023 Held-Out Test Set:**
  - Naive Baseline: PR-AUC = 0.1399 [0.0824, 0.2201]
  - XGBoost: PR-AUC = **0.2884 [0.1744, 0.4765]** (Diff: **+0.1486 [+0.0620, +0.2969]**)
  - Time-Safe Stacking: PR-AUC = **0.2644 [0.1546, 0.4728]** (Diff: **+0.1246 [+0.0469, +0.2885]**)
- **ECDC 2018–2019 Held-Out Test Set:**
  - Naive Baseline: PR-AUC = 0.0695 [0.0462, 0.0956]
  - Random Forest: PR-AUC = **0.1623 [0.1001, 0.2483]** (Diff: **+0.0928 [+0.0345, +0.1775]**)
  - Time-Safe Stacking: PR-AUC = **0.1425 [0.0923, 0.2310]** (Diff: **+0.0730 [+0.0259, +0.1675]**)

### Pooled vs. Dedicated Single-Source Models
- **High-Risk Alerts:** On identical test rows, pooling showed no significant difference compared to dedicated models (GLASS diff: $+0.0010$ $[-0.0043, +0.0065]$; ECDC diff: $-0.0003$ $[-0.0016, +0.0012]$).
- **Rising Resistance Alerts:** Pooling with source indicator features significantly improved alert precision on ECDC test rows (+0.0522 [+0.0160, +0.0869]).

---

## 5. Repository Layout

```
amr-sense/
├── README.md                          # Project documentation and true code results
├── Makefile                           # Unified automation targets (eda, features, train, etc.)
├── requirements.txt                   # Pinned production dependencies
├── config/config.yaml                 # Configuration (seed: 42, paths, splits, tuning grids)
├── data/
│   ├── raw/                           # Immutable raw surveillance exports
│   │   ├── combined_amr_dataset.csv   # Single source of truth (6,634 rows)
│   │   ├── ML_DATASET.csv             # Raw WHO GLASS bloodstream dataset
│   │   └── summary_AMR_filtered.csv   # Raw ECDC EARS-Net dataset
│   ├── processed/                     # Leakage-safe parquet panels with targets
│   └── ui/                            # 20 precomputed artifacts served by API
├── scripts/
│   ├── run_eda.py                     # Stage 1: Ingestion, checks, EDA figures, findings
│   ├── run_features.py                # Stage 2: Leakage-safe feature extraction
│   ├── run_train.py                   # Stage 4: Optuna tuning, validation, models/FROZEN
│   ├── run_final_test.py              # Stage 4: Guarded final test evaluation
│   └── run_ui_data.py                 # Stage 5: Precomputation of UI artifacts
├── src/amr_sense/
│   ├── config.py                      # YAML config loader
│   ├── data.py                        # Validation & provenance checks
│   ├── panel.py                       # Consecutive-year series tracking & targets
│   ├── features.py                    # Vectorized leakage-safe feature builder
│   ├── splits.py                      # Time-ordered splits & rolling-origin folds
│   ├── models.py                      # Model factories, baselines, pipelines
│   ├── tuning.py                      # Optuna objective functions & studies
│   ├── ensembles.py                   # Soft voting & time-safe stacking
│   ├── evaluate.py                    # Metrics, curves, segments, cluster bootstrap
│   ├── plots.py                       # EDA and diagnostic figures (Agg backend)
│   └── serving.py                     # Prediction inference & artifact loaders
├── reports/
│   ├── eda/                           # data_quality.md & eda_findings.md
│   ├── results/                       # validation_results.md, test_results.md, checkpoint.md
│   └── figures/                       # EDA charts & hyperparameter sensitivity plots
├── models/                            # Trained joblib pipelines, metadata JSONs, FROZEN marker
├── api/main.py                        # FastAPI backend (CORS & Pydantic)
├── frontend/                          # React/Vite seven-page research UI
│   └── src/pages/                     # Dataset, EDA, features, models, forecasts, watchlist, methods
├── app/                               # Legacy Streamlit multipage UI
│   ├── streamlit_app.py               # Home portal with persistent disclaimer & KPIs
│   ├── components/ui.py               # Shared UI cards, filters, styling, palettes
│   └── pages/
│       ├── 1_Dataset_Overview.py      # KPIs, source comparison table, coverage matrix
│       ├── 2_EDA_Explorer.py          # 7 tabs: distributions, trends, funnel, COVID check
│       ├── 3_Features.py              # Dictionary, leakage proofs, univariate association
│       ├── 4_Model_Lab.py             # Benchmarking, curves, regularization, tuning, ensembles
│       ├── 5_Forecast_Explorer.py     # Interactive next-year forecast with context cards
│       ├── 6_Surveillance_Watchlist.py# Prioritized candidate series, choropleth map, CSV export
│       └── 7_Methods_and_Limitations.py# Methodology, hypothesis tests, limitations, roadmap
└── tests/
    ├── test_api.py                    # 7 FastAPI endpoint tests
    ├── test_leakage.py                # 4 temporal leakage mathematical invariant tests
    ├── test_splits.py                 # 2 time-ordered split & rolling fold tests
    └── test_streamlit_smoke.py        # 9 AppTest smoke tests across all pages
```

---

## 6. Surveillance Limitations

1. **Short GLASS Longitudinal History:** GLASS currently provides 6 rounds (2018–2023). Requiring consecutive years and lag-2 features restricts the non-European training window.
2. **Reporting Filter Bias:** GLASS participation is concentrated in better-resourced tertiary hospital labs, which may over-represent resistant hospital-acquired infections relative to general community settings.
3. **Definition Disparity (R vs I+R):** ECDC reports Intermediate + Resistant isolates combined, whereas GLASS reports Resistant isolates. These metrics cannot be numerically cross-compared without calibration.
4. **Project-Defined Operational Thresholds:** The $T = 30\%$ high-risk alarm and $+5\text{ pp}$ acceleration thresholds were established for public health surveillance triage and audit prioritization, not clinical prescribing decisions.
5. **Surveillance Noise at Small Sample Sizes:** In GLASS, ~5.3% of series observations have $N < 30$, producing severe binomial dispersion (0% or 100% resistance). All classification targets exclude rows lacking $N \ge 30$ in consecutive years.

---

## 7. Phase 2 Extension Points & Roadmap

The Phase 1 architecture leaves clean extension points for subsequent research modules:
- **SHAP Feature Attribution:** Local TreeExplainer attributions per surveillance series forecast.
- **Conformal Prediction:** Finite-sample, distribution-free prediction intervals with guaranteed coverage.
- **Trajectory Clustering:** Longitudinal time-series clustering (Dynamic Time Warping) to discover shared regional resistance trajectories.
- **Change-Point Detection:** CUSUM and Isolation Forests for automated laboratory outbreak alarms.
- **Transfer Learning:** Domain adaptation transferring long-horizon European patterns to emerging surveillance networks.
