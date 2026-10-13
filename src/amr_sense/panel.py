"""Series keys, eligibility, and row-level targets."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest

from amr_sense.config import load_config

SERIES_COLS = ["source", "iso3", "pathogen", "antibiotic"]


def add_consecutive_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag_1, lag_2 only across consecutive calendar years (no gap crossing)."""
    out = df.sort_values(SERIES_COLS + ["year"]).copy()
    out["year_prev"] = out.groupby(SERIES_COLS, observed=True)["year"].shift(1)
    out["year_prev2"] = out.groupby(SERIES_COLS, observed=True)["year"].shift(2)
    out["pct_prev"] = out.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    out["pct_prev2"] = out.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(2)
    out["nt_prev"] = out.groupby(SERIES_COLS, observed=True)["number_tested"].shift(1)
    out["nt_prev2"] = out.groupby(SERIES_COLS, observed=True)["number_tested"].shift(2)
    out["nr_prev"] = out.groupby(SERIES_COLS, observed=True)["number_resistant"].shift(1)
    out["nr_prev2"] = out.groupby(SERIES_COLS, observed=True)["number_resistant"].shift(2)

    consecutive_1 = out["year"] - out["year_prev"] == 1
    consecutive_2 = out["year_prev"] - out["year_prev2"] == 1

    out["lag_1"] = np.where(consecutive_1, out["pct_prev"], np.nan)
    out["lag_2"] = np.where(consecutive_1 & consecutive_2, out["pct_prev2"], np.nan)
    out["number_tested_prev"] = np.where(consecutive_1, out["nt_prev"], np.nan)
    out["number_tested_prev2"] = np.where(consecutive_1 & consecutive_2, out["nt_prev2"], np.nan)
    out["number_resistant_prev"] = np.where(consecutive_1, out["nr_prev"], np.nan)
    out["number_resistant_prev2"] = np.where(
        consecutive_1 & consecutive_2, out["nr_prev2"], np.nan
    )
    out["eligible"] = consecutive_1
    return out


def _rising_label(row: pd.Series, rise_pp: float, alpha: float, min_tested: int) -> int:
    if pd.isna(row.get("lag_1")) or pd.isna(row.get("pct_resistant")):
        return 0
    if row["number_tested"] < min_tested or row["number_tested_prev"] < min_tested:
        return 0
    delta = row["pct_resistant"] - row["lag_1"]
    if delta < rise_pp:
        return 0
    count = np.array([row["number_resistant"], row["number_resistant_prev"]])
    nobs = np.array([row["number_tested"], row["number_tested_prev"]])
    try:
        _, pval = proportions_ztest(count, nobs, alternative="larger")
    except Exception:
        return 0
    return int(pval < alpha)


def build_eligible_panel(
    df: pd.DataFrame,
    cfg_source: Literal["glass", "ecdc", "pooled"] | None = None,
) -> pd.DataFrame:
    """Build rows with targets for eligible consecutive-year pairs."""
    cfg = load_config()
    rise_pp = cfg["thresholds"]["rise_pp"]
    alpha = cfg["thresholds"]["alpha"]
    min_tested = cfg["thresholds"]["min_tested"]
    Ts = cfg["thresholds"]["high_risk_sensitivity"]
    primary_T = cfg["thresholds"]["high_risk_T"]

    panel = add_consecutive_lags(df)
    panel = panel[panel["eligible"]].copy()

    panel["y_reg"] = panel["pct_resistant"]
    all_Ts = sorted(list(set(Ts + [primary_T])))
    for T in all_Ts:
        panel[f"high_risk_next_{T}"] = (panel["pct_resistant"] >= T).astype(int)
    panel["high_risk_next"] = (panel["pct_resistant"] >= primary_T).astype(int)

    panel["rising_next"] = panel.apply(
        lambda r: _rising_label(r, rise_pp, alpha, min_tested), axis=1
    )

    panel["covid_flag"] = (panel["year"] == 2020).astype(int)
    panel["target_year"] = panel["year"]
    return panel


def classification_eligible(panel: pd.DataFrame, min_tested: int | None = None) -> pd.DataFrame:
    """Filter to rows with number_tested >= min in t and t-1."""
    cfg = load_config()
    min_tested = min_tested or cfg["thresholds"]["min_tested"]
    m = (panel["number_tested"] >= min_tested) & (panel["number_tested_prev"] >= min_tested)
    return panel[m].copy()


def report_classification_filter(panel: pd.DataFrame) -> dict[str, int]:
    """Count rows removed by n>=30 filter per source."""
    cfg = load_config()
    min_tested = cfg["thresholds"]["min_tested"]
    before = panel.groupby("source").size()
    after = classification_eligible(panel).groupby("source").size()
    removed = (before - after.reindex(before.index, fill_value=0)).astype(int)
    return removed.to_dict()
