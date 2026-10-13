"""Leakage safety tests for feature construction."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from amr_sense.data import load_combined
from amr_sense.features import build_features_for_panel
from amr_sense.panel import SERIES_COLS, add_consecutive_lags


@pytest.fixture(scope="module")
def raw():
    return load_combined()


@pytest.fixture(scope="module")
def panel_glass(raw):
    return build_features_for_panel(raw, "glass")


def test_lag1_matches_raw(raw, panel_glass):
    rng = np.random.RandomState(42)
    sample = panel_glass.sample(min(50, len(panel_glass)), random_state=42)
    for _, row in sample.iterrows():
        prev = raw[
            (raw["source"] == row["source"])
            & (raw["iso3"] == row["iso3"])
            & (raw["pathogen"] == row["pathogen"])
            & (raw["antibiotic"] == row["antibiotic"])
            & (raw["year"] == row["year"] - 1)
        ]
        if len(prev) != 1:
            continue
        assert row["lag_1"] == pytest.approx(prev["pct_resistant"].iloc[0], abs=1e-6)


def test_permute_target_year_does_not_change_features(raw):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = raw.copy()
        panel_before = build_features_for_panel(df, "glass")
        # permute pct_resistant for year 2023 only
        m = df["year"] == 2023
        df.loc[m, "pct_resistant"] = df.loc[m, "pct_resistant"] + 17.0
        panel_after = build_features_for_panel(df, "glass")
    feat_cols = [c for c in panel_before.columns if c.startswith("lag_") or c in ("delta_1", "roll_mean_2")]
    merged = panel_before[["year", "iso3", "pathogen", "antibiotic"] + feat_cols].merge(
        panel_after[["year", "iso3", "pathogen", "antibiotic"] + feat_cols],
        on=["year", "iso3", "pathogen", "antibiotic"],
        suffixes=("_a", "_b"),
    )
    for c in feat_cols:
        a = merged[f"{c}_a"]
        b = merged[f"{c}_b"]
        mask = a.notna() & b.notna()
        assert np.allclose(a[mask], b[mask], equal_nan=True)


def test_years_observed_excludes_target(raw, panel_glass):
    for _, row in panel_glass.head(100).iterrows():
        hist = raw[
            (raw["source"] == row["source"])
            & (raw["iso3"] == row["iso3"])
            & (raw["pathogen"] == row["pathogen"])
            & (raw["antibiotic"] == row["antibiotic"])
            & (raw["year"] < row["year"])
        ]
        assert row["years_observed"] == len(hist)


def test_region_median_uses_t_minus_1(raw, panel_glass):
    row = panel_glass.iloc[0]
    yr = int(row["year"] - 1)
    sub = raw[
        (raw["source"] == row["source"])
        & (raw["pathogen"] == row["pathogen"])
        & (raw["antibiotic"] == row["antibiotic"])
        & (raw["year"] == yr)
    ]
    expected = sub["pct_resistant"].median()
    assert row["region_median_prev"] == pytest.approx(expected, abs=1e-6)
