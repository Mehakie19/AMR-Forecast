# AMR-Sense Phase 1 Quality Gate Checkpoint

> Generated automatically from pipeline outputs and test verifications.
> Rule 1: Never fabricate numbers. Every number comes directly from code output.

## Checkpoint Criteria Pass / Fail Matrix

| Requirement / Criterion | Status | Evidence & Output Artifacts |
|---|---|---|
| **1. Data Layer & EDA** | **PASS ✅** | • `reports/eda/data_quality.md` (6,634 rows validated, Malta overlap audited)<br>• `reports/eda/eda_findings.md` (10 computed analytical sections)<br>• 23 generated PNG figures in `reports/figures/eda/` |
| **2. Feature Dictionary & Leakage Prevention** | **PASS ✅** | • `data/processed/panel_{glass,ecdc,pooled}.parquet` generated<br>• `reports/results/feature_dictionary.md` (23 features documented with surveillance rationale)<br>• Leakage tests pass in `tests/test_leakage.py` ($t \le t-1$ invariant verified) |
| **3. Time-Ordered Splits & Rolling-Origin Folds** | **PASS ✅** | • Time-ordered splits in `src/amr_sense/splits.py`<br>• Rolling-origin expanding folds unit-tested (`test_splits.py`)<br>• No random splits or data leakage |
| **4. Classifiers & Regularization Study** | **PASS ✅** | • LR (none, L1, L2, ElasticNet), RF, and XGBoost fit across `glass`, `ecdc`, `pooled`<br>• `reports/results/regularization.md` (overfitting gaps and L1 sparsity documented)<br>• Class weights applied without synthetic resampling |
| **5. Hyperparameter Tuning & Sensitivity** | **PASS ✅** | • Optuna TPE studies saved in `models/studies/`<br>• Rolling-origin fold cross-validation objective used<br>• Sensitivity heatmaps and curves generated in `reports/figures/` |
| **6. Ensembles (Soft Voting & Time-Safe Stacking)** | **PASS ✅** | • Soft voting across tuned base models<br>• Stacking meta-learner trained strictly on rolling-origin OOF predictions<br>• Meta-weights and excluded fold rows documented |
| **7. Performance Analysis with Bootstrap CIs** | **PASS ✅** | • `reports/results/validation_results.md` and `reports/results/test_results.md`<br>• 1,000 country-cluster paired bootstrap CIs on all headline metrics and differences vs persistence<br>• Segment analysis and error breakdown tables |
| **8. Final Test Guard & One-Shot Evaluation** | **PASS ✅** | • Models frozen with `models/FROZEN` marker during `make train`<br>• Final test evaluated once via `make final-test` on held-out test year(s)<br>• No test labels or data used during tuning or threshold selection |
| **9. Three Configurations (`glass`, `ecdc`, `pooled`)** | **PASS ✅** | • All models compared against persistence/dummy baselines in all 3 configs<br>• Pooled-vs-separate comparison on identical test slices |
| **10. UI Data Precomputation & Read-Only API** | **PASS ✅** | • `make ui-data` precomputes 20 artifacts in `data/ui/`<br>• FastAPI service in `api/main.py` with 13 endpoints and Pydantic validation<br>• All 7 API unit tests pass in `tests/test_api.py` |
| **11. Interactive Streamlit Multipage Frontend** | **PASS ✅** | • 7 complete pages in `app/pages/` with interactive Plotly visualisations<br>• Mandatory disclaimer banner, status strip, and scope filter<br>• Smoke-tested via `streamlit.testing.v1.AppTest` (`tests/test_streamlit_smoke.py`) |
| **12. Automated Test Suite** | **PASS ✅** | • 22 / 22 pytest tests pass (`pytest tests/ -v`) |

---

## Key Experimental Findings (From Actual Code Outputs)

1. **High-Risk Classification ($T = 30\%$):**
   - **GLASS 2023 Test:** Persistence baseline PR-AUC = 0.9527. Best ML models achieve **0.9886 to 0.9908** (Stacking / Voting difference vs baseline: **+0.0380 [+0.0163, +0.0646]**, statistically significant).
   - **ECDC 2018–2019 Test:** Persistence baseline PR-AUC = 0.9298. Models achieve **0.9816 to 0.9834** (LR difference: **+0.0537 [+0.0306, +0.0865]**).
   - **Pooled Test:** Persistence baseline PR-AUC = 0.9401. Models achieve **0.9867 to 0.9875** (Difference: **+0.0474 [+0.0300, +0.0690]**).

2. **Rising Resistance Acceleration ($+5\text{ pp}$ & $p < 0.05$):**
   - **GLASS 2023 Test:** Naive delta baseline PR-AUC = 0.1399. XGBoost achieves **0.2884** (Difference: **+0.1486 [+0.0620, +0.2969]**).
   - **ECDC 2018–2019 Test:** Baseline PR-AUC = 0.0695. Random Forest achieves **0.1623** (Difference: **+0.0928 [+0.0345, +0.1775]**).
   - **Pooled Test:** Baseline PR-AUC = 0.0960. XGBoost achieves **0.2313** (Difference: **+0.1353 [+0.0602, +0.2403]**).

3. **Pooled vs Separate Verdict on Identical Test Slices:**
   - **High-Risk Alerts:** Pooling heterogeneous datasets yielded no statistically significant difference (GLASS: $+0.0010$ $[-0.0043, +0.0065]$; ECDC: $-0.0003$ $[-0.0016, +0.0012]$).
   - **Rising Acceleration Alerts:** On ECDC held-out test rows, pooling significantly improved detection precision from $0.1172$ to $0.1694$ (Difference: **$+0.0522 [+0.0160, +0.0869]$**).

4. **Continuous Resistance Regressors:**
   - Persistence baseline remains a tough benchmark in regression: GLASS test MAE = 4.71 pp (Ridge: 5.30 pp, XGB: 5.26 pp); ECDC test MAE = 3.06 pp (Ridge: 3.22 pp, XGB: 3.24 pp). ML regressors beat persistence on 38%–46% of individual surveillance series.
