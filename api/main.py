"""Read-only FastAPI backend for precomputed AMR-Sense research data."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from amr_sense.config import ROOT, data_version, load_config
from amr_sense.serving import load_ui_json, load_ui_table, predict_series

cfg = load_config()
DISCLAIMER = cfg["disclaimer"].strip()
SOURCE_NAMES = {"glass": cfg["sources"]["glass"], "ecdc": cfg["sources"]["ecdc"]}
CONFIGS = ("glass", "ecdc", "pooled")
TARGETS = ("high_risk_next", "rising_next", "y_reg")

app = FastAPI(title="AMR-Sense API", version="1.0.0", description=DISCLAIMER)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def artifact(name: str):
    value = load_ui_json(name)
    if value is None:
        raise HTTPException(status_code=503, detail=f"UI artifact '{name}' is unavailable; run make ui-data.")
    return value


def select_source(data, source: str):
    if source not in ("glass", "ecdc", "combined"):
        raise HTTPException(status_code=422, detail="source must be glass, ecdc, or combined")
    if isinstance(data, dict) and source in data:
        return data[source]
    return data


def source_rows(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if source not in ("glass", "ecdc", "combined"):
        raise HTTPException(status_code=422, detail="source must be glass, ecdc, or combined")
    if source != "combined" and "source" in df:
        df = df[df.source == SOURCE_NAMES[source]]
    return df


@lru_cache(maxsize=1)
def raw_data() -> pd.DataFrame:
    path = ROOT / cfg["paths"]["raw_combined"]
    if not path.exists():
        raise HTTPException(status_code=503, detail="Raw surveillance dataset is unavailable")
    return pd.read_csv(path)


@app.get("/health")
def health():
    summary = artifact("dataset_summary")
    return {"status": "ok", "data_version": data_version(), "configurations": list(CONFIGS),
            "disclaimer": DISCLAIMER, "frozen": (ROOT / "models" / "FROZEN").exists(),
            "dataset_summary": summary}


@app.get("/methods")
def methods():
    result = artifact("methods")
    result.update(disclaimer=DISCLAIMER, thresholds=cfg["thresholds"], limitations=artifact("limitations"))
    return result


@app.get("/datasets/summary")
def datasets_summary(source: str = "combined"):
    return {**select_source(artifact("dataset_summary"), source), "source": source, "disclaimer": DISCLAIMER}


@app.get("/datasets/coverage")
def datasets_coverage(source: str = "combined", pathogen: str = "", antibiotic: str = ""):
    table = load_ui_table("coverage")
    rows = source_rows(table if table is not None else pd.DataFrame(artifact("coverage")), source)
    if pathogen: rows = rows[rows.pathogen == pathogen]
    if antibiotic: rows = rows[rows.antibiotic == antibiotic]
    return {"coverage": rows.where(pd.notna(rows), None).to_dict(orient="records"), "count": len(rows), "disclaimer": DISCLAIMER}


@app.get("/intelligence/overview")
def intelligence_overview(
    source: Literal["glass", "ecdc"] = "glass",
    pathogen: str = "",
    antibiotic: str = "",
):
    """Return one-source, latest-year map data and supporting surveillance summaries."""
    df = raw_data()
    df = df[df.source == SOURCE_NAMES[source]].copy()
    if df.empty:
        raise HTTPException(status_code=503, detail=f"No observations are available for source '{source}'")

    threshold = float(cfg["thresholds"]["forecast_high_resistance_T"])
    pathogens = sorted(df.pathogen.dropna().unique().tolist())
    if not pathogen and pathogens:
        pathogen = pathogens[0]
    antibiotics = sorted(df[df.pathogen == pathogen].antibiotic.dropna().unique().tolist())
    if not antibiotic and antibiotics:
        antibiotic = antibiotics[0]

    latest = (
        df.sort_values("year")
        .drop_duplicates(["iso3", "pathogen", "antibiotic"], keep="last")
    )
    selected = latest[(latest.pathogen == pathogen) & (latest.antibiotic == antibiotic)].copy()
    map_columns = ["iso3", "country", "year", "pathogen", "antibiotic", "pct_resistant", "number_tested"]
    map_rows = selected[map_columns].where(pd.notna(selected[map_columns]), None).to_dict(orient="records")

    eligible_hotspots = selected[selected.number_tested >= cfg["thresholds"]["min_tested"]]
    hotspots = eligible_hotspots.sort_values("pct_resistant", ascending=False).head(5)

    filtered = df
    if pathogen:
        filtered = filtered[filtered.pathogen == pathogen]
    if antibiotic:
        filtered = filtered[filtered.antibiotic == antibiotic]
    rising_rows = []
    series_cols = ["iso3", "country", "pathogen", "antibiotic"]
    for _, group in filtered.sort_values("year").groupby(series_cols, observed=True):
        if len(group) < 2:
            continue
        previous, current = group.iloc[-2], group.iloc[-1]
        if (
            int(current.year) - int(previous.year) != 1
            or current.number_tested < cfg["thresholds"]["min_tested"]
            or previous.number_tested < cfg["thresholds"]["min_tested"]
        ):
            continue
        change = float(current.pct_resistant - previous.pct_resistant)
        if change > 0:
            rising_rows.append(
                {
                    "iso3": current.iso3,
                    "country": current.country,
                    "pathogen": current.pathogen,
                    "antibiotic": current.antibiotic,
                    "from_year": int(previous.year),
                    "to_year": int(current.year),
                    "previous_pct": float(previous.pct_resistant),
                    "latest_pct": float(current.pct_resistant),
                    "change_pp": round(change, 2),
                    "number_tested": float(current.number_tested),
                }
            )
    fastest_rising = sorted(rising_rows, key=lambda row: row["change_pp"], reverse=True)[:5]

    pathogen_rows = (
        latest.groupby("pathogen", observed=True)
        .agg(
            countries_reporting=("iso3", "nunique"),
            reported_series=("antibiotic", "size"),
            latest_year=("year", "max"),
        )
        .reset_index()
        .sort_values(["countries_reporting", "reported_series", "pathogen"], ascending=[False, False, True])
        .head(5)
    )
    important_pathogens = pathogen_rows.rename(columns={"pathogen": "name"}).to_dict(orient="records")

    reliable = selected[selected.number_tested >= cfg["thresholds"]["min_tested"]]
    high_count = int((reliable.pct_resistant >= threshold).sum())
    findings = []
    if len(reliable):
        findings.append(
            f"{high_count} of {len(reliable)} latest country reports with at least "
            f"{cfg['thresholds']['min_tested']} tests are at or above {threshold:g}% resistance."
        )
        findings.append(
            f"The median latest reported resistance for {pathogen} / {antibiotic} is "
            f"{reliable.pct_resistant.median():.1f}% across {len(reliable)} eligible country reports."
        )
    else:
        findings.append(f"No latest {pathogen} / {antibiotic} country reports meet the minimum sample-size rule.")
    if fastest_rising:
        fastest = fastest_rising[0]
        findings.append(
            f"The largest recent increase is {fastest['change_pp']:.1f} percentage points in "
            f"{fastest['country']} ({fastest['from_year']}–{fastest['to_year']})."
        )
    else:
        findings.append("No consecutive-year increases with 30 or more tests in both years were found for this selection.")

    return {
        "source": source,
        "resistance_definition": "R" if source == "glass" else "I+R",
        "pathogen": pathogen,
        "antibiotic": antibiotic,
        "pathogens": pathogens,
        "antibiotics": antibiotics,
        "high_resistance_threshold_pct": threshold,
        "minimum_tests_for_rankings": int(cfg["thresholds"]["min_tested"]),
        "countries": map_rows,
        "hotspots": hotspots[map_columns].where(pd.notna(hotspots[map_columns]), None).to_dict(orient="records"),
        "fastest_rising": fastest_rising,
        "important_pathogens": important_pathogens,
        "key_findings": findings,
        "disclaimer": DISCLAIMER,
    }


@app.get("/datasets/quality")
def datasets_quality():
    return {**artifact("quality"), "disclaimer": DISCLAIMER}


@app.get("/eda/distribution")
def eda_distribution(source: str = "combined"):
    df = load_ui_table("eda_distribution")
    if df is None: raise HTTPException(503, "Distribution artifact unavailable")
    df = source_rows(df, source)
    return {"rows": df.where(pd.notna(df), None).to_dict(orient="records"), "disclaimer": DISCLAIMER}


@app.get("/eda/trend")
def eda_trend(source: str = "combined"):
    df = load_ui_table("eda_trends")
    if df is None: raise HTTPException(503, "Trend artifact unavailable")
    df = source_rows(df, source)
    return {"rows": df.where(pd.notna(df), None).to_dict(orient="records"), "disclaimer": DISCLAIMER}


@app.get("/eda/sample-size")
def eda_sample_size(source: str = "combined"):
    df = load_ui_table("eda_sample_size")
    if df is None: raise HTTPException(503, "Sample-size artifact unavailable")
    df = source_rows(df, source)
    return {"rows": df.where(pd.notna(df), None).to_dict(orient="records"), "disclaimer": DISCLAIMER}


@app.get("/eda/class-balance")
def eda_class_balance(source: str = "combined"):
    return {"data": select_source(artifact("eda_class_balance"), source), "disclaimer": DISCLAIMER}


@app.get("/eda/correlation")
def eda_correlation(source: Literal["glass", "ecdc"] = "glass", pathogen: str = "Klebsiella pneumoniae"):
    data = artifact("eda_correlations").get(source, {})
    return {"correlations": data.get(pathogen, {}), "source": source, "pathogen": pathogen, "disclaimer": DISCLAIMER}


@app.get("/eda/year-change")
def eda_year_change(source: str = "combined"):
    return {"data": select_source(artifact("eda_year_change"), source), "disclaimer": DISCLAIMER}


@app.get("/features/dictionary")
def features_dictionary():
    return {"features": artifact("feature_dictionary"), "disclaimer": DISCLAIMER}


@app.get("/features/importance-preview")
def features_importance(source: str = "combined"):
    return {"data": select_source(artifact("feature_importance"), source), "disclaimer": DISCLAIMER}


@app.get("/results/comparison")
def results_comparison(config: str = "glass", target: str = "high_risk_next", split: str = "validation"):
    if config not in CONFIGS or target not in TARGETS or split not in ("validation", "test"):
        raise HTTPException(422, "Invalid config, target, or split")
    name = "model_results_validation" if split == "validation" else "model_results_test"
    result = artifact(name).get(config, {})
    return {"rows": result.get(target, result), "config": config, "target": target, "split": split, "disclaimer": DISCLAIMER}


@app.get("/results/curves")
def results_curves(config: str = "glass", target: str = "high_risk_next", model: str = "xgb"):
    if config not in CONFIGS or target not in TARGETS or model not in ("lr", "rf", "xgb", "voting", "stacking"):
        raise HTTPException(422, "Invalid config, target, or model")
    key = f"{config}_{target}_{model}"
    return {"curves": artifact("curves").get(key, {}), "config": config, "target": target, "model": model, "disclaimer": DISCLAIMER}


@app.get("/results/regularization")
def results_regularization():
    path = ROOT / "reports" / "results" / "regularization.md"
    return {"markdown": path.read_text(encoding="utf-8") if path.exists() else "", "disclaimer": DISCLAIMER}


@app.get("/results/tuning")
def results_tuning(config: str = "glass"):
    if config not in CONFIGS: raise HTTPException(422, "Invalid config")
    path = ROOT / "models" / "studies"
    import json
    studies = {}
    if path.exists():
        for p in path.glob(f"study_*_{config}.json"):
            studies[p.stem.removeprefix("study_")] = json.loads(p.read_text(encoding="utf-8"))
    return {"study": studies, "config": config, "disclaimer": DISCLAIMER}


@app.get("/results/ensembles")
def results_ensembles(config: str = "glass"):
    if config not in CONFIGS: raise HTTPException(422, "Invalid config")
    val = artifact("model_results_validation").get(config, {})
    return {"voting_description": "Soft voting combines calibrated model probabilities using validation-selected weights.",
            "stacking_description": "Time-safe stacking trains the meta-model on forward-chaining out-of-fold predictions.",
            "data": val.get("ensembles", val), "config": config, "disclaimer": DISCLAIMER}


@app.get("/results/segments")
def results_segments(config: str = "glass", target: str = "high_risk_next"):
    if config not in CONFIGS or target not in TARGETS: raise HTTPException(422, "Invalid config or target")
    return {"segments": artifact("segments").get(f"{config}_{target}", {}), "disclaimer": DISCLAIMER}


@app.get("/results/errors")
def results_errors(config: str = "glass"):
    if config not in CONFIGS: raise HTTPException(422, "Invalid config")
    return {"data": artifact("errors").get(config, {}), "disclaimer": DISCLAIMER}


@app.get("/results/threshold-sensitivity")
def results_threshold_sensitivity():
    return {"data": artifact("threshold_sensitivity"), "disclaimer": DISCLAIMER}


@app.get("/results/pooled-vs-separate")
def results_pooled_vs_separate():
    path = ROOT / "reports" / "results" / "checkpoint.md"
    return {"markdown": path.read_text(encoding="utf-8") if path.exists() else "", "disclaimer": DISCLAIMER}


@app.get("/series/options")
def series_options(source: Literal["glass", "ecdc"] = "glass"):
    df = raw_data()
    df = df[df.source == SOURCE_NAMES[source]]
    return {"countries": sorted(df.iso3.dropna().unique().tolist()),
            "pathogens": sorted(df.pathogen.dropna().unique().tolist()),
            "antibiotics": sorted(df.antibiotic.dropna().unique().tolist()),
            "items": (df[["iso3", "pathogen", "antibiotic"]]
                      .dropna()
                      .drop_duplicates()
                      .to_dict(orient="records")),
            "disclaimer": DISCLAIMER}


@app.get("/series")
def series_history(source: Literal["glass", "ecdc"], iso3: str, pathogen: str, antibiotic: str):
    df = raw_data()
    df = df[(df.source == SOURCE_NAMES[source]) & (df.iso3 == iso3) & (df.pathogen == pathogen) & (df.antibiotic == antibiotic)].sort_values("year")
    if df.empty: raise HTTPException(404, "No matching surveillance series found")
    return {"history": df[[c for c in ("year", "pct_resistant", "number_tested", "country", "source") if c in df]].where(pd.notna(df), None).to_dict(orient="records"), "disclaimer": DISCLAIMER}


class PredictionRequest(BaseModel):
    source: Literal["glass", "ecdc"]
    iso3: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    pathogen: str = Field(min_length=1)
    antibiotic: str = Field(min_length=1)
    config_name: Literal["glass", "ecdc", "pooled"] = Field(default="glass", alias="model_config")


@app.post("/predict")
def predict(request: PredictionRequest):
    subset = raw_data()
    exists = ((subset.source == SOURCE_NAMES[request.source]) & (subset.iso3 == request.iso3) &
              (subset.pathogen == request.pathogen) & (subset.antibiotic == request.antibiotic)).any()
    if not exists: raise HTTPException(422, "The requested surveillance series does not exist")
    try:
        return predict_series(request.source, request.iso3, request.pathogen, request.antibiotic, request.config_name)
    except ValueError as exc:
        if type(exc).__name__ == "XGBoostError":
            raise HTTPException(
                status_code=503,
                detail="XGBoost is unavailable. Install the macOS OpenMP runtime (libomp) to enable predictions.",
            ) from exc
        raise HTTPException(422, str(exc)) from exc


@app.get("/watchlist")
def watchlist(source: str = "combined", pathogen: str = "", antibiotic: str = "",
              country: str = "", limit: int = Query(200, ge=1, le=2000),
              sort_by: str = "high_risk_probability", descending: bool = True):
    df = load_ui_table("watchlist")
    if df is None: raise HTTPException(503, "Watchlist artifact unavailable")
    df = source_rows(df, source)
    for col, value in (("pathogen", pathogen), ("antibiotic", antibiotic), ("iso3", country)):
        if value and col in df: df = df[df[col] == value]
    if sort_by in df.columns: df = df.sort_values(sort_by, ascending=not descending, na_position="last")
    return {"rows": df.head(limit).where(pd.notna(df), None).to_dict(orient="records"), "count": min(len(df), limit), "disclaimer": DISCLAIMER}
