"""Load artifacts and build predictions for API."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from amr_sense.config import ROOT, data_version, load_config
from amr_sense.features import build_features_for_panel
from amr_sense.models import prepare_xy


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


def predict_series(source: str, iso3: str, pathogen: str, antibiotic: str, model_config: str) -> dict:
    """
    Build next-year prediction for a series at its latest observed year.
    Returns forecast_pct, high_risk_probability, rising_probability,
    feature_values, cross_resistance_context, and data_quality_note.
    """
    cfg = load_config()
    raw = pd.read_csv(ROOT / cfg["paths"]["raw_combined"])
    src_val = cfg["sources"]["glass"] if source == "glass" else cfg["sources"]["ecdc"]
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

    # Check panel features
    panel = build_features_for_panel(raw, model_config)
    series_rows = panel[
        (panel["source"] == src_val)
        & (panel["iso3"] == iso3)
        & (panel["pathogen"] == pathogen)
        & (panel["antibiotic"] == antibiotic)
    ].sort_values("year")

    if len(series_rows) == 0:
        raise ValueError(
            f"Series ({source}, {iso3}, {pathogen}, {antibiotic}) did not produce eligible feature rows (e.g. minimum sample size)."
        )

    row = series_rows.iloc[-1]
    models_dir = ROOT / cfg["paths"]["models_dir"] / model_config

    out = {
        "forecast_pct": None,
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

    # Companion regression
    ridge_path = models_dir / "ridge_y_reg.joblib"
    if ridge_path.exists():
        m_ridge = joblib.load(ridge_path)
        X_reg, _ = prepare_xy(pd.DataFrame([row]), "y_reg", model_config)
        out["forecast_pct"] = round(float(m_ridge.predict(X_reg)[0]), 2)
    else:
        out["forecast_pct"] = round(float(row.get("lag_1", row.get("pct_resistant", 0.0))), 2)

    # Cross-resistance context (other antibiotics for same country-pathogen at latest year)
    latest_yr = int(row["year"])
    other_ab = raw[
        (raw["source"] == src_val)
        & (raw["iso3"] == iso3)
        & (raw["pathogen"] == pathogen)
        & (raw["year"] == latest_yr)
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
