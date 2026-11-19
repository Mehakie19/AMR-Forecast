# AMR-Sense

AMR-Sense is a research and surveillance platform for exploring antimicrobial resistance (AMR) data and evaluating models that identify high resistance and rising-resistance patterns.

> **Important:** This project is for research and population-level surveillance only. It is not for choosing a patient's treatment or antibiotic dose. A predicted resistance percentage is not a probability of clinical cure. Project alert thresholds are not clinical guidelines.

## What the project does

- Validates and explores country-, year-, pathogen-, and antibiotic-level surveillance observations.
- Builds time-aware features using only information from years before the target year.
- Compares Logistic Regression, Random Forest, XGBoost, Ridge regression, soft voting, and time-safe stacking against simple baselines.
- Evaluates models with rolling-origin validation and later-year test sets.
- Provides a FastAPI backend and React/Vite dashboard.
- Offers an interactive map overview and exploratory five-year resistance estimates.

The research models are evaluated as next-year classifiers/regressors. The five-year estimates are a separate, newer exploratory feature and should not be presented as having the same validation evidence as the saved final test results.

## Data

The analytical source of truth is `data/raw/combined_amr_dataset.csv` (6,634 observations):

| Source | Rows | Years | Countries | Resistance definition |
|---|---:|---|---:|---|
| WHO GLASS-AMR | 2,394 | 2018–2023 | 31 | Resistant (R), as reported by GLASS |
| ECDC-derived EARS-Net data | 4,240 | 1999–2019 | 27 | Intermediate + Resistant (I+R) |

Across both sources, the data contains 57 unique countries, three pathogens (*Acinetobacter* spp., *Escherichia coli*, and *Klebsiella pneumoniae*), and nine antibiotics. Eight Malta records are flagged as overlapping source observations.

GLASS and ECDC use different resistance definitions; do not directly compare their percentages as though they measured the same outcome. The models are available in `glass`, `ecdc`, and `pooled` configurations, with source flags used for the pooled configuration.

## Models and targets

The primary classification targets are:

- **High resistance (`high_risk_next`):** target-year resistance is at least 30%.
- **Rising resistance (`rising_next`):** resistance increases by at least 5 percentage points in consecutive years, each with at least 30 tests, and passes the project's one-sided two-proportion test (`p < 0.05`).
- **Resistance regression (`y_reg`):** target-year resistance percentage.

The 30% high-resistance threshold is a project-defined modeling label. Separately, the five-year forecast page categorizes estimates as **Low Resistance** below 40% and **High Resistance** at or above 40%.

### Regularization

- Logistic Regression tuning considers no penalty, L1 (Lasso), L2 (Ridge), and Elastic Net penalties.
- The continuous-resistance model uses Ridge regression (L2); its `alpha` is tuned for the original regression experiments.
- XGBoost uses L1/L2 penalties (`reg_alpha`, `reg_lambda`) and tree-complexity controls. Random Forest complexity is also constrained through settings such as tree depth and minimum leaf size.
- The comparisons of penalty choices and train/validation gaps are documented in `reports/results/regularization.md`.

### Validation design

Training and validation use time-ordered splits and rolling-origin folds; later target years are not used to train earlier predictions. No random train/test split is used.

| Configuration | Training target years | Validation target years | Final test target years |
|---|---|---|---|
| GLASS | 2019–2021 | 2022 | 2023 |
| ECDC | 1999–2015 | 2016–2017 | 2018–2019 |
| Pooled | Source-specific years, with overlap exclusions | Source-specific / rolling-origin folds | GLASS 2023 and ECDC 2018–2019 |

Final-test classification metrics and their differences from baseline use 1,000 paired, country-cluster bootstrap resamples. The models and thresholds are frozen before the final test run using the `models/FROZEN` marker.

## Headline final test results

PR-AUC (area under the precision-recall curve) is shown because the rising-resistance class is relatively uncommon. Brackets show the 95% country-cluster bootstrap interval for the difference from baseline.

| Configuration | Target | Baseline PR-AUC | Best model | Best model PR-AUC | Difference from baseline (95% interval) |
|---|---|---:|---|---:|---:|
| GLASS, 2023 | High resistance | 0.9527 | Soft voting / stacking | 0.9908 | Voting: +0.0381 [+0.0163, +0.0646] |
| ECDC, 2018–2019 | High resistance | 0.9298 | Logistic Regression | 0.9834 | +0.0537 [+0.0306, +0.0865] |
| Pooled | High resistance | 0.9401 | Random Forest / voting / stacking | 0.9875 | Voting: +0.0474 [+0.0300, +0.0690] |
| GLASS, 2023 | Rising resistance | 0.1399 | XGBoost | 0.2884 | +0.1486 [+0.0620, +0.2969] |
| ECDC, 2018–2019 | Rising resistance | 0.0695 | Random Forest | 0.1623 | +0.0928 [+0.0345, +0.1775] |
| Pooled | Rising resistance | 0.0960 | XGBoost | 0.2313 | +0.1353 [+0.0602, +0.2403] |

The saved regression test results show that continuous-value models do not consistently beat the persistence baseline on mean absolute error. See `reports/results/test_results.md` for the full metrics and intervals, and `reports/results/validation_results.md` for validation results.

## Dashboard

The React/Vite dashboard has seven pages:

1. **Visual overview:** source-specific interactive country map, latest reported resistance, top resistance levels, recent observed increases, commonly reported pathogens, and key findings.
2. **Dataset overview:** source coverage and dataset summary.
3. **Explore data:** distributions, trends, year-to-year changes, and related EDA views.
4. **Model inputs:** feature definitions and information used by the models.
5. **Model results:** model comparisons, performance curves, group results, source/threshold comparisons, and continuous-resistance regression results.
6. **Five-year forecast:** reported history and one direct model estimate for each of the next five years, with the 40% display category and a per-horizon comparison to a time-ordered carry-forward baseline.
7. **Results to review:** surveillance records prioritized for human review.

The forecast fits separate Ridge models for each horizon instead of feeding each forecast into the next. It is exploratory: some source/horizon combinations have too few distinct target years for a separate time holdout, and models may not outperform carrying the last observed resistance value forward. The page shows the available historical check for each horizon.

The map uses country boundary data from Natural Earth, which is in the public domain. The map shows one reporting source at a time; each country's displayed value is its latest available report and countries may therefore represent different years. Hotspot rankings require at least 30 tests. Recent increases are observed consecutive-year changes with at least 30 tests in both years, not predictions or tests of statistical significance.

## Setup and run on macOS

Run the backend and frontend in **separate Terminal windows**. The project uses backend port **8001** and frontend port **5173**. The frontend Vite server proxies `/api` requests to `http://127.0.0.1:8001`.

### 1. Create the Python environment (one time)

If Homebrew or Python 3.12 is not installed:

```bash
# Install Homebrew first if it is not already installed.
brew install python@3.12
```

From the project root, create and populate the environment:

```bash
cd "/path/to/AMR-Forecast"
python3.12 -m venv .venv312
source .venv312/bin/activate
python -m pip install -r requirements.txt
```

Replace `"/path/to/AMR-Forecast"` with the actual location of your project folder. If your project already has a working `.venv`, you can activate that instead; do not create or install another environment unnecessarily.

### 2. Run the backend

In the first Terminal window, from the project root:

```bash
source .venv312/bin/activate
export PYTHONPATH=src
PYTHONPATH=src python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8001
```

Wait for Uvicorn to report that it is running on `http://127.0.0.1:8001`. Check the API at [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health); a working API returns JSON with `"status":"ok"`. Keep this Terminal window open.

### 3. Run the frontend

In a second Terminal window:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 26
cd "/path/to/AMR-Forecast/frontend"
npm install
npm run dev
```

Run `npm install` once when setting up the frontend (or after changing its package files). Open the local URL printed by Vite; it is normally [http://localhost:5173](http://localhost:5173). If Vite reports a different port because 5173 is occupied, use the URL it prints. Keep the frontend Terminal window open too.

### 4. Run tests

From the project root, with the Python environment activated:

```bash
source .venv312/bin/activate
export PYTHONPATH=src
pytest tests/ -v
```

If you already use a prepared `.venv` instead, the equivalent commands are:

```bash
source .venv/bin/activate
export PYTHONPATH=src
pytest tests/ -v
```

## Data and experiment pipeline

The scripts under `scripts/` run the analysis pipeline:

```bash
export PYTHONPATH=src
python scripts/run_eda.py
python scripts/run_features.py
python scripts/run_train.py
python scripts/run_final_test.py
python scripts/run_ui_data.py
```

Run training and final-test scripts only when you intend to regenerate model artifacts and reports. The `models/FROZEN` marker protects the saved final-test workflow; do not remove it or re-run final evaluation casually. Dashboard data is read from the existing artifacts in `data/ui/`.

### Generate report figures

With the project's Python environment activated, run:

```bash
export PYTHONPATH=src
python scripts/generate_report_figures.py
```

This writes PNG and PDF versions to `reports/figures/report/`:

- Figure 7.6: GLASS held-out test-set precision-recall and ROC curves for the saved classifiers and persistence baseline.
- Figure 7.7: validation performance by single decision-tree depth and L1/L2 Logistic Regression coefficient counts for `C = 0.01, 0.1, 1, 10`.
- Figure 7.8: GLASS test-set precision, recall, F1, and false-alert rate over probability cutoffs. The marked Logistic Regression cutoff is selected using validation data.

The tree-depth plot is a supplementary single-tree diagnostic; the project model comparison also includes Random Forest. L1 is the Lasso penalty; L2 is Ridge-type regularization, not Lasso. Numeric tree-depth and sparsity results are written to `reports/figures/report/figure_7_7_values.md`. The probability cutoff in Figure 7.8 is different from the 20%, 30%, and 50% resistance-label sensitivity experiment.

## Repository map

```text
api/main.py                         FastAPI routes
config/config.yaml                  Data paths, thresholds, splits, tuning settings
data/raw/combined_amr_dataset.csv   Combined surveillance data
data/processed/                     Feature panels for glass, ecdc, and pooled models
data/ui/                             Precomputed dashboard data
frontend/src/App.jsx                 React navigation and application shell
frontend/src/pages/                  Seven dashboard pages
frontend/public/data/                Local country boundaries for the map
models/                              Saved classifiers, regressors, studies, and freeze marker
reports/eda/                         EDA and data-quality reports
reports/results/                     Validation, final-test, and regularization reports
scripts/                             Data, feature, model, and UI-data pipeline scripts
src/amr_sense/                       Feature, model, evaluation, and serving code
tests/                               API, model, leakage, and frontend tests
```

## References and data provenance

- World Health Organization, [Global Antimicrobial Resistance and Use Surveillance System (GLASS)](https://www.who.int/initiatives/glass).
- Emons, Blanquart, and Lehtinen, [The Evolution of Antibiotic Resistance in Europe, 1998–2019](https://doi.org/10.5281/zenodo.14224680), Zenodo dataset record 14224680.
- Natural Earth, [Admin 0 – Countries, 1:110m](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/), public-domain country boundaries used by the map.
