"""Read-only FastAPI service for AMR-Sense UI and research exploration."""

from __future__ import annotations

from typing import Any, Literal, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from amr_sense.config import ROOT, data_version, load_config
from amr_sense.data import load_combined, malta_overlap_table
from amr_sense.features import FEATURE_DEFINITIONS
from amr_sense.serving import frozen_flag, load_ui_json, load_ui_table, predict_series

cfg = load_config()
DISCLAIMER = cfg["disclaimer"]

app = FastAPI(
    title="AMR-Sense API",
    version="0.1.0",
    description="Surveillance and research decision-support tool for population-level antimicrobial resistance forecasting.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class DisclaimerResponse(BaseModel):
    disclaimer: str = Field(default=DISCLAIMER)
    data_version: str


class HealthResponse(DisclaimerResponse):
    status: str
    frozen: bool
    configurations: list[str]


class PredictRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: Literal["glass", "ecdc"]
    iso3: str
    pathogen: str
    antibiotic: str
    model_config_name: Literal["glass", "ecdc", "pooled"] = Field(
        default="pooled", alias="model_config"
    )


def _filter_source(df: pd.DataFrame, source: Optional[str]) -> pd.DataFrame:
    if not source or source == "combined":
        return df
    key = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
    return df[df["source"] == key]


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert table rows to strict JSON-safe records (NaN is not valid JSON)."""
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


# ==========================================
# System & Meta Endpoints
# ==========================================

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return health status, data hash, frozen status, and available model configurations."""
    return HealthResponse(
        status="ok",
        data_version=data_version(),
        frozen=frozen_flag(),
        configurations=["glass", "ecdc", "pooled"],
    )


@app.get("/methods")
def methods() -> dict[str, Any]:
    """Return methodology definitions, thresholds, project caveats, and roadmap."""
    methods_data = load_ui_json("methods") or {}
    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "thresholds": cfg["thresholds"],
        "splits": cfg["splits"],
        "limitations": load_ui_json("limitations") or [],
        "methods": methods_data,
    }


# ==========================================
# Dataset & EDA Endpoints
# ==========================================

@app.get("/datasets/summary")
def dataset_summary(source: Optional[str] = Query(None)) -> dict[str, Any]:
    """Summary counts (rows, series, countries, years) per source or combined."""
    cached = load_ui_json("dataset_summary")
    if cached and (source in cached or (source is None and "combined" in cached)):
        res = cached.get(source or "combined", {})
        return {"disclaimer": DISCLAIMER, "data_version": data_version(), **res}

    df = load_combined()
    df = _filter_source(df, source)
    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "rows": len(df),
        "series": int(df.groupby(["source", "iso3", "pathogen", "antibiotic"]).ngroups),
        "countries": int(df["iso3"].nunique()),
        "years": [int(df["year"].min()), int(df["year"].max())],
        "pathogens": sorted(df["pathogen"].unique().tolist()),
        "antibiotics": sorted(df["antibiotic"].unique().tolist()),
    }


@app.get("/datasets/quality")
def dataset_quality() -> dict[str, Any]:
    """Missingness, duplicate counts, sample size violations, and Malta overlap."""
    cached = load_ui_json("quality")
    if cached:
        return {"disclaimer": DISCLAIMER, "data_version": data_version(), **cached}

    df = load_combined()
    dup = int(df.duplicated(subset=["source", "iso3", "year", "pathogen", "antibiotic"]).sum())
    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "missingness": df.isna().sum().astype(int).to_dict(),
        "duplicates": dup,
        "n_lt_30_share": {
            s: float((df[df["source"] == s]["number_tested"] < 30).mean())
            for s in df["source"].unique()
        },
        "malta_overlap": malta_overlap_table(df).to_dict(orient="records"),
    }


@app.get("/datasets/coverage")
def coverage(
    source: Optional[str] = None,
    pathogen: Optional[str] = None,
    antibiotic: Optional[str] = None,
) -> dict[str, Any]:
    """Coverage matrix across countries and years."""
    df = load_ui_table("coverage")
    if df is None:
        df = load_combined()
    df = _filter_source(df, source)
    if pathogen and "pathogen" in df.columns:
        df = df[df["pathogen"] == pathogen]
    if antibiotic and "antibiotic" in df.columns:
        df = df[df["antibiotic"] == antibiotic]
    mat = _records(df)
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "coverage": mat, "matrix": mat}


@app.get("/eda/distribution")
def eda_distribution(source: Optional[str] = None, pathogen: Optional[str] = None) -> dict[str, Any]:
    """Distribution of percent resistant values."""
    df = load_ui_table("eda_distribution")
    if df is None:
        df = load_combined()[["source", "pathogen", "antibiotic", "pct_resistant"]]
    df = _filter_source(df, source)
    if pathogen:
        df = df[df["pathogen"] == pathogen]
    records = _records(df)
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "records": records, "rows": records}


@app.get("/eda/trend")
def eda_trend(source: Optional[str] = None, pathogen: Optional[str] = None, antibiotic: Optional[str] = None) -> dict[str, Any]:
    """Yearly trends with mean, median, IQR."""
    df = load_ui_table("eda_trends")
    if df is not None:
        df = _filter_source(df, source)
        if pathogen:
            df = df[df["pathogen"] == pathogen]
        if antibiotic:
            df = df[df["antibiotic"] == antibiotic]
        records = _records(df)
        return {"disclaimer": DISCLAIMER, "data_version": data_version(), "trends": records, "series": records}
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "trends": []}


@app.get("/eda/sample-size")
def eda_sample_size(source: Optional[str] = None) -> dict[str, Any]:
    """pct_resistant vs number_tested for funnel plots."""
    df = load_ui_table("eda_sample_size")
    if df is not None:
        df = _filter_source(df, source)
        records = _records(df)
        return {"disclaimer": DISCLAIMER, "data_version": data_version(), "points": records, "rows": records}
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "points": []}


@app.get("/eda/class-balance")
def eda_class_balance() -> dict[str, Any]:
    """Class balance for high_risk_next at T in {20, 30, 50} and rising_next."""
    cb = load_ui_json("eda_class_balance") or {}
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "class_balance": cb}


@app.get("/eda/correlation")
def eda_correlation(source: str = "glass", pathogen: Optional[str] = None) -> dict[str, Any]:
    """Cross-resistance correlation matrices per pathogen."""
    corr = load_ui_json("eda_correlations") or {}
    source_corr = corr.get(source, {})
    data = source_corr.get(pathogen, {}) if pathogen else source_corr
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "correlations": data, **data}


@app.get("/eda/year-change")
def eda_year_change(source: str = "combined") -> dict[str, Any]:
    """Year-on-year change distributions and COVID check."""
    yoy = load_ui_json("eda_year_change") or {}
    data = {key: yoy[key] for key in ("glass", "ecdc")} if source == "combined" else yoy.get(source, {})
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "yoy": data, **data}


# ==========================================
# Feature Endpoints
# ==========================================

@app.get("/features/dictionary")
def feature_dictionary() -> dict[str, Any]:
    """Feature dictionary with definitions, groups, availability, and clinical justifications."""
    feats = load_ui_json("feature_dictionary") or FEATURE_DEFINITIONS
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "features": feats}


@app.get("/features/importance-preview")
def feature_importance_preview() -> dict[str, Any]:
    """Univariate association of features with targets on training rows only."""
    imp = load_ui_json("feature_importance") or []
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "importance": imp, "items": imp}


# ==========================================
# Results & Model Lab Endpoints
# ==========================================

@app.get("/results/comparison")
def results_comparison(
    config: str = "glass",
    target: str = "high_risk_next",
    split: str = "validation",
) -> dict[str, Any]:
    """Model comparison table with bootstrap CIs for baselines, single models, and ensembles."""
    split = {"val": "validation", "valid": "validation"}.get(split, split)
    if split not in {"validation", "test"}:
        raise HTTPException(422, "split must be validation or test")
    cached = load_ui_json(f"model_results_{split}")
    rows = []
    if cached and config in cached and target in cached[config]:
        rows = cached[config][target]
    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "config": config,
        "target": target,
        "split": split,
        "rows": rows,
    }


@app.get("/results/curves")
def results_curves(config: str = "glass", target: str = "high_risk_next", model: str = "xgb") -> dict[str, Any]:
    """PR curve, ROC curve, calibration curve, and confusion matrix."""
    curves = load_ui_json("curves") or {}
    model = {"xgboost": "xgb", "random_forest": "rf", "logistic_regression": "lr", "soft_voting": "voting"}.get(model, model)
    key = f"{config}_{target}_{model}"
    data = curves.get(key, {})
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "curves": data}


@app.get("/results/regularization")
def results_regularization() -> dict[str, Any]:
    """Regularization evidence: train vs validation overfitting gap and L1 sparsity."""
    reg_file = ROOT / "reports" / "results" / "regularization.md"
    text = reg_file.read_text(encoding="utf-8") if reg_file.exists() else ""
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "markdown": text}


@app.get("/results/tuning")
def results_tuning(config: str = "glass", target: str = "high_risk_next", model: str = "xgb") -> dict[str, Any]:
    """Optuna study history and best parameters."""
    model = {"xgboost": "xgb", "random_forest": "rf", "logistic_regression": "lr", "soft_voting": "voting"}.get(model, model)
    study_path = ROOT / "models" / "studies" / f"study_{model}_{target}_{config}.json"
    study_data = json.loads(study_path.read_text(encoding="utf-8")) if study_path.exists() else {}
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "study": study_data}


@app.get("/results/ensembles")
def results_ensembles() -> dict[str, Any]:
    """Ensemble performance and stacking meta-weights."""
    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "voting_description": "Soft voting averages predicted probabilities across tuned Logistic Regression, Random Forest, and XGBoost to reduce isolate-level sampling variance.",
        "stacking_description": "Stacking fits a Logistic Regression meta-learner on out-of-fold predictions from rolling-origin cross-validation, exploiting error diversity.",
    }


@app.get("/results/segments")
def results_segments(config: str = "glass", target: str = "high_risk_next") -> dict[str, Any]:
    """Segment breakdown by pathogen, antibiotic, sample size band, and WHO region."""
    segs = load_ui_json("segments") or {}
    key = f"{config}_{target}"
    data = segs.get(key, {})
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "segments": data}


@app.get("/results/errors")
def results_errors(config: str = "glass") -> dict[str, Any]:
    """Error analysis: 15 largest forecast errors and 15 highest-confidence false alerts."""
    errs = load_ui_json("errors") or {}
    data = errs.get(config, {})
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "errors": data}


@app.get("/results/threshold-sensitivity")
def results_threshold_sensitivity() -> dict[str, Any]:
    """Model performance sensitivity across project-defined thresholds T in {20, 30, 50}."""
    test_results_path = ROOT / "reports" / "results" / "test_results.md"
    txt = test_results_path.read_text(encoding="utf-8") if test_results_path.exists() else ""
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "markdown": txt}


@app.get("/results/pooled-vs-separate")
def results_pooled_vs_separate() -> dict[str, Any]:
    """Comparison of pooled model against separate source-specific models on identical test slices."""
    test_results_path = ROOT / "reports" / "results" / "test_results.md"
    txt = test_results_path.read_text(encoding="utf-8") if test_results_path.exists() else ""
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "markdown": txt}


# ==========================================
# Series, Predict, Watchlist
# ==========================================

@app.get("/series")
def series_history(
    source: str,
    iso3: str,
    pathogen: str,
    antibiotic: str,
) -> dict[str, Any]:
    """Complete historical longitudinal resistance for one series."""
    df = load_combined()
    key = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
    sub = df[
        (df["source"] == key)
        & (df["iso3"] == iso3)
        & (df["pathogen"] == pathogen)
        & (df["antibiotic"] == antibiotic)
    ].sort_values("year")
    records = _records(sub)
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "history": records, "records": records}


@app.get("/series/options")
def series_options(source: str = "glass") -> dict[str, Any]:
    """Distinct valid country/pathogen/antibiotic combinations for forecast selectors."""
    df = load_combined()
    key = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
    columns = ["iso3", "country", "pathogen", "antibiotic"]
    items = df.loc[df["source"] == key, columns].drop_duplicates().sort_values(columns)
    return {"disclaimer": DISCLAIMER, "data_version": data_version(), "items": _records(items)}


@app.post("/predict")
def predict(body: PredictRequest) -> dict[str, Any]:
    """
    Produce next-year forecast and alert probabilities for a series.
    Returns forecast_pct, high_risk_probability, rising_probability,
    features used, cross-resistance context, and data_quality_note.
    """
    try:
        result = predict_series(
            body.source,
            body.iso3,
            body.pathogen,
            body.antibiotic,
            body.model_config_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    result["disclaimer"] = DISCLAIMER
    result["data_version"] = data_version()
    return result


@app.get("/watchlist")
def watchlist(
    source: Optional[str] = None,
    pathogen: Optional[str] = None,
    antibiotic: Optional[str] = None,
    min_tested: Optional[int] = None,
    sort: str = "high_risk_probability",
) -> dict[str, Any]:
    """Surveillance watchlist ranked for expert review at latest observed year."""
    df = load_ui_table("watchlist")
    if df is None:
        raise HTTPException(503, "UI data not yet exported. Run `make ui-data` first.")

    if source and source != "combined":
        key = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
        df = df[df["source"] == key]
    if pathogen:
        df = df[df["pathogen"] == pathogen]
    if antibiotic:
        df = df[df["antibiotic"] == antibiotic]
    if min_tested:
        df = df[df["number_tested"] >= min_tested]
    sort = {"pct_resistant": "latest_resistance_pct"}.get(sort, sort)
    if sort in df.columns:
        df = df.sort_values(sort, ascending=False, na_position="last")

    return {
        "disclaimer": DISCLAIMER,
        "data_version": data_version(),
        "items": _records(df),
    }
