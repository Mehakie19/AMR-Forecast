"""Load artifacts and build predictions for API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from amr_sense.config import ROOT, data_version, load_config
from amr_sense.features import build_features_for_panel


def frozen_flag() -> bool:
    """Check if model weights and thresholds have been frozen."""
    return (ROOT / "models" / "FROZEN").exists()


def load_ui_table(name: str) -> pd.DataFrame | None:
    """Load a parquet table exported into data/ui/."""
    p = ROOT / "data" / "ui" / f"{name}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return None


def load_ui_json(name: str) -> dict | list | None:
    """Load a JSON artifact exported into data/ui/."""
    p = ROOT / "data" / "ui" / f"{name}.json"
    if p.exists():
        # pandas may serialize missing floating-point values as bare NaN tokens;
        # normalize those to JSON null before FastAPI encodes the response.
        return json.loads(p.read_text(encoding="utf-8"), parse_constant=lambda _value: None)
    return None


@lru_cache(maxsize=3)
def _direct_horizon_models(model_config: str) -> dict[int, dict]:
    """Train and time-test one direct Ridge regressor for each forecast horizon."""
    from amr_sense.models import prepare_xy, ridge_pipeline

    cfg = load_config()
    raw = pd.read_csv(ROOT / cfg["paths"]["raw_combined"])
    panel = build_features_for_panel(raw, model_config)
    future_values = raw[
        ["source", "iso3", "pathogen", "antibiotic", "year", "pct_resistant", "number_tested"]
    ].rename(
        columns={
            "year": "forecast_year",
            "pct_resistant": "future_pct",
            "number_tested": "future_n",
        }
    )
    min_tested = int(cfg["thresholds"]["min_tested"])
    results: dict[int, dict] = {}

    for horizon in range(1, 6):
        examples = panel.assign(forecast_year=panel["year"] + horizon - 1).merge(
            future_values,
            on=["source", "iso3", "pathogen", "antibiotic", "forecast_year"],
            how="inner",
        )
        examples = examples[examples["future_n"] >= min_tested].copy()
        if len(examples) < min_tested:
            results[horizon] = {
                "model": None,
                "training_samples": len(examples),
                "evaluation": None,
            }
            continue

        examples["y_reg"] = examples["future_pct"]
        evaluation = None
        holdout_year = int(examples["forecast_year"].max())
        train = examples[examples["forecast_year"] < holdout_year]
        test = examples[examples["forecast_year"] == holdout_year]
        if len(train) >= min_tested and len(test) >= min_tested:
            evaluation_model = ridge_pipeline(model_config)
            X_train, y_train = prepare_xy(train, "y_reg", model_config)
            X_test, y_test = prepare_xy(test, "y_reg", model_config)
            evaluation_model.fit(X_train, y_train)
            predicted = np.clip(evaluation_model.predict(X_test), 0.0, 100.0)
            baseline = np.clip(test["lag_1"].to_numpy(dtype=float), 0.0, 100.0)
            evaluation = {
                "holdout_year": holdout_year,
                "holdout_samples": int(len(test)),
                "holdout_mae_pct": round(float(np.mean(np.abs(y_test - predicted))), 2),
                "persistence_mae_pct": round(float(np.mean(np.abs(y_test - baseline))), 2),
            }
            evaluation["beats_persistence"] = (
                evaluation["holdout_mae_pct"] < evaluation["persistence_mae_pct"]
            )

        X, y = prepare_xy(examples, "y_reg", model_config)
        model = ridge_pipeline(model_config)
        model.fit(X, y)
        results[horizon] = {
            "model": model,
            "training_samples": int(len(examples)),
            "evaluation": evaluation,
        }

    return results


def predict_series(source: str, iso3: str, pathogen: str, antibiotic: str, model_config: str) -> dict:
    """
    Build direct year-ahead forecasts from the latest observed year.
    Returns forecast_horizons, model probabilities, feature values,
    cross-resistance context, and data-quality notes.
    """
    from amr_sense.models import prepare_xy

    cfg = load_config()
    raw = pd.read_csv(ROOT / cfg["paths"]["raw_combined"])
    src_val = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
    if model_config not in (source, "pooled"):
        raise ValueError("Choose a model trained for the selected source or the pooled model.")
    sub = raw[
        (raw["source"] == src_val)
        & (raw["iso3"] == iso3)
        & (raw["pathogen"] == pathogen)
        & (raw["antibiotic"] == antibiotic)
    ].sort_values("year")

    if len(sub) < 2:
        raise ValueError(
            f"Series ({source}, {iso3}, {pathogen}, {antibiotic}) has fewer than 2 observed years; "
            "cannot build lag/momentum features for next-year forecasting."
        )

    latest_year = int(sub["year"].max())
    forecast_input = sub.iloc[[-1]].copy()
    forecast_input["year"] = latest_year + 1
    panel = build_features_for_panel(pd.concat([raw, forecast_input], ignore_index=True), model_config)
    forecast_rows = panel[
        (panel["source"] == src_val)
        & (panel["iso3"] == iso3)
        & (panel["pathogen"] == pathogen)
        & (panel["antibiotic"] == antibiotic)
        & (panel["year"] == latest_year + 1)
    ]

    if len(forecast_rows) == 0:
        raise ValueError(
            f"Series ({source}, {iso3}, {pathogen}, {antibiotic}) does not have enough recent data "
            "to build forecast features (at least 30 tests in each of the latest two years are required)."
        )

    row = forecast_rows.iloc[-1]
    models_dir = ROOT / cfg["paths"]["models_dir"] / model_config
    threshold = float(cfg["thresholds"]["forecast_high_resistance_T"])

    out = {
        "forecast_pct": None,
        "forecast_horizons": [],
        "forecast_method": "direct_horizon_ridge",
        "high_resistance_threshold_pct": threshold,
        "high_risk_probability": None,
        "rising_probability": None,
        "models": {},
        "features": {},
        "cross_resistance_context": [],
        "data_quality_note": "Sample size OK",
        "disclaimer": cfg["disclaimer"],
        "data_version": data_version(),
    }

    # Features used
    feat_cols = [
        c for c in row.index
        if c.startswith(("lag_", "delta_", "roll_", "log_", "class_", "region_", "hist_", "years_", "has_", "wilson_"))
    ]
    out["features"] = {k: float(row[k]) if pd.notna(row[k]) else None for k in feat_cols}

    # Model predictions
    for target in ["high_risk_next", "rising_next"]:
        for name in ["lr", "rf", "xgb"]:
            path = models_dir / f"{name}_{target}.joblib"
            if not path.exists():
                continue
            m = joblib.load(path)
            X, _ = prepare_xy(pd.DataFrame([row]), target, model_config)
            prob = float(m.predict_proba(X)[0, 1])
            out["models"][f"{name}_{target}"] = round(prob, 4)

    # Best model headline probabilities (default to xgb or lr)
    out["high_risk_probability"] = out["models"].get("xgb_high_risk_next", out["models"].get("lr_high_risk_next"))
    out["rising_probability"] = out["models"].get("xgb_rising_next", out["models"].get("lr_rising_next"))

    X_reg, _ = prepare_xy(pd.DataFrame([row]), "y_reg", model_config)
    direct_models = _direct_horizon_models(model_config)
    for horizon in range(1, 6):
        trained = direct_models[horizon]
        model = trained["model"]
        estimate = None
        if model is not None:
            estimate = float(np.clip(model.predict(X_reg)[0], 0.0, 100.0))
        forecast_year = latest_year + horizon
        out["forecast_horizons"].append(
            {
                "horizon": horizon,
                "year": forecast_year,
                "forecast_pct": round(estimate, 2) if estimate is not None else None,
                "category": (
                    "High Resistance" if estimate is not None and estimate >= threshold
                    else "Low Resistance" if estimate is not None
                    else None
                ),
                "training_samples": trained["training_samples"],
                "evaluation": trained["evaluation"],
            }
        )
    out["forecast_pct"] = out["forecast_horizons"][0]["forecast_pct"]

    # Cross-resistance context (other antibiotics for same country-pathogen at latest year)
    other_ab = raw[
        (raw["source"] == src_val)
        & (raw["iso3"] == iso3)
        & (raw["pathogen"] == pathogen)
        & (raw["year"] == latest_year)
    ].sort_values("pct_resistant", ascending=False)

    out["cross_resistance_context"] = [
        {
            "antibiotic": r["antibiotic"],
            "pct_resistant": float(r["pct_resistant"]),
            "number_tested": float(r["number_tested"]),
        }
        for _, r in other_ab.iterrows()
    ]

    n_prev = row.get("number_tested_prev", row.get("number_tested"))
    if pd.notna(n_prev) and n_prev < 30:
        out["data_quality_note"] = f"Warning: small lagged sample (n={int(n_prev)} < 30)"

    return out
