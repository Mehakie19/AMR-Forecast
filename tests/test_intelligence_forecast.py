from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from amr_sense.serving import predict_series
from api.main import intelligence_overview


class _ConstantClassifier:
    def predict_proba(self, _features):
        return np.array([[0.4, 0.6]])


def test_intelligence_overview_keeps_sources_separate():
    glass = intelligence_overview("glass")
    ecdc = intelligence_overview("ecdc")

    assert glass["resistance_definition"] == "R"
    assert ecdc["resistance_definition"] == "I+R"
    assert glass["source"] != ecdc["source"]
    assert glass["high_resistance_threshold_pct"] == 40
    assert glass["countries"]
    assert {"iso3", "country", "year", "pct_resistant"} <= set(glass["countries"][0])
    assert glass["important_pathogens"]


def test_predict_series_returns_five_direct_horizons(monkeypatch):
    import amr_sense.serving as serving

    monkeypatch.setattr(serving.joblib, "load", lambda _path: _ConstantClassifier())
    result = predict_series(
        "ecdc",
        "AUT",
        "Acinetobacter spp.",
        "Ciprofloxacin",
        "ecdc",
    )

    assert result["forecast_method"] == "direct_horizon_ridge"
    assert result["high_resistance_threshold_pct"] == 40
    assert len(result["forecast_horizons"]) == 5
    assert [row["year"] for row in result["forecast_horizons"]] == [2020, 2021, 2022, 2023, 2024]
    assert all(0 <= row["forecast_pct"] <= 100 for row in result["forecast_horizons"])
    assert all(row["category"] in {"Low Resistance", "High Resistance"} for row in result["forecast_horizons"])
    assert result["forecast_pct"] == result["forecast_horizons"][0]["forecast_pct"]
