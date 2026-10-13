"""Leakage-safe feature builder (uses information from year <= t-1 only)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from amr_sense.config import load_config
from amr_sense.panel import SERIES_COLS, add_consecutive_lags, build_eligible_panel, classification_eligible
from amr_sense.splits import assign_split

ConfigName = Literal["glass", "ecdc", "pooled"]


def wilson_width(n: float, p_pct: float, z: float = 1.96) -> float:
    """95% Wilson interval width in percentage points."""
    if n <= 0 or np.isnan(p_pct):
        return np.nan
    p = p_pct / 100.0
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return 100.0 * 2 * margin


def _region_median_at_year(
    df_source: pd.DataFrame, year: int, pathogen: str, antibiotic: str
) -> float:
    sub = df_source[
        (df_source["year"] == year)
        & (df_source["pathogen"] == pathogen)
        & (df_source["antibiotic"] == antibiotic)
    ]
    if len(sub) == 0:
        return np.nan
    return float(sub["pct_resistant"].median())


def build_cross_resistance_row(
    df_year: pd.DataFrame,
    iso3: str,
    pathogen: str,
    antibiotic: str,
    T: float,
) -> dict[str, float]:
    """Cross-resistance features at t-1 for one country-pathogen."""
    sub = df_year[
        (df_year["iso3"] == iso3) & (df_year["pathogen"] == pathogen)
    ]
    if len(sub) == 0:
        return {
            "class_mean_other": np.nan,
            "other_mean_all": np.nan,
            "n_high_other": np.nan,
            "mdr_burden": np.nan,
        }
    row = sub[sub["antibiotic"] == antibiotic]
    if len(row) == 0:
        return {
            "class_mean_other": np.nan,
            "other_mean_all": np.nan,
            "n_high_other": np.nan,
            "mdr_burden": np.nan,
        }
    atc = row["antibiotic_class"].iloc[0]
    others = sub[sub["antibiotic"] != antibiotic]
    same_class = others[others["antibiotic_class"] == atc]
    n_high = (others["pct_resistant"] >= T).sum()
    n_other = len(others)
    return {
        "class_mean_other": float(same_class["pct_resistant"].mean()) if len(same_class) else np.nan,
        "other_mean_all": float(others["pct_resistant"].mean()) if n_other else np.nan,
        "n_high_other": float(n_high),
        "mdr_burden": float(n_high / n_other) if n_other else np.nan,
    }


def compute_wilson_width_vec(n_arr: np.ndarray, p_arr: np.ndarray, z: float = 1.96) -> np.ndarray:
    """Vectorized 95% Wilson score interval width in percentage points."""
    n = n_arr.astype(float)
    p_pct = p_arr.astype(float)
    p = p_pct / 100.0
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = 1.0 + z**2 / n
        inner = np.maximum(0.0, (p * (1.0 - p) + z**2 / (4.0 * n)) / n)
        margin = z * np.sqrt(inner) / denom
        width = 100.0 * 2.0 * margin
        width[n <= 0] = np.nan
        width[np.isnan(p_pct)] = np.nan
        width[np.isnan(n)] = np.nan
    return width


def build_features_for_panel(
    raw: pd.DataFrame,
    config_name: ConfigName,
) -> pd.DataFrame:
    """Build feature matrix for one configuration (leakage-safe, year <= t-1 only)."""
    cfg = load_config()
    sg, se = cfg["sources"]["glass"], cfg["sources"]["ecdc"]
    T = float(cfg["thresholds"]["high_risk_T"])
    min_tested = int(cfg["thresholds"]["min_tested"])

    if config_name == "glass":
        sub = raw[raw["source"] == sg].copy()
    elif config_name == "ecdc":
        sub = raw[raw["source"] == se].copy()
    else:
        sub = raw.copy()

    panel = build_eligible_panel(sub)
    panel = classification_eligible(panel, min_tested).copy()

    # Pre-sort sub for historical temporal features
    sub_sorted = sub.sort_values(SERIES_COLS + ["year"]).copy()
    grp_series = [sub_sorted[c] for c in SERIES_COLS]
    shifted_pct = sub_sorted.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)

    sub_sorted["hist_max"] = shifted_pct.groupby(grp_series, observed=True).cummax()
    sub_sorted["hist_min"] = shifted_pct.groupby(grp_series, observed=True).cummin()
    sub_sorted["years_observed"] = sub_sorted.groupby(SERIES_COLS, observed=True).cumcount()

    if "ast_coverage" in sub_sorted.columns:
        sub_sorted["ast_coverage_prev"] = sub_sorted.groupby(SERIES_COLS, observed=True)["ast_coverage"].shift(1)
    else:
        sub_sorted["ast_coverage_prev"] = np.nan

    hist_cols = ["source", "iso3", "year", "pathogen", "antibiotic", "hist_max", "hist_min", "years_observed", "ast_coverage_prev"]
    panel = panel.merge(sub_sorted[hist_cols], on=["source", "iso3", "year", "pathogen", "antibiotic"], how="left")

    # Temporal dynamics from lag_1 and lag_2 (already in panel from add_consecutive_lags)
    panel["has_lag2"] = panel["lag_2"].notna().astype(int)
    panel["delta_1"] = panel["lag_1"] - panel["lag_2"]
    panel["roll_mean_2"] = np.where(panel["has_lag2"] == 1, (panel["lag_1"] + panel["lag_2"]) / 2.0, panel["lag_1"])
    panel["roll_std_2"] = np.where(panel["has_lag2"] == 1, np.abs(panel["lag_1"] - panel["lag_2"]) / 2.0, np.nan)

    # Sample quality at t-1
    panel["log_tested"] = np.log1p(panel["number_tested_prev"])
    panel["n_ge_30_prev"] = (panel["number_tested_prev"] >= 30).astype(int)
    panel["wilson_width"] = compute_wilson_width_vec(panel["number_tested_prev"].values, panel["lag_1"].values)

    if config_name == "glass":
        panel["ast_coverage"] = panel["ast_coverage_prev"]
    elif config_name == "ecdc":
        panel["ast_coverage"] = np.nan
    else:
        panel["ast_coverage"] = np.where(panel["source"] == sg, panel["ast_coverage_prev"], np.nan)

    # Precompute cross-resistance metrics on sub at each year
    grp = ["source", "iso3", "year", "pathogen"]
    sub_cr = sub.copy()
    sub_cr["total_count"] = sub_cr.groupby(grp, observed=True)["pct_resistant"].transform("count")
    sub_cr["total_sum"] = sub_cr.groupby(grp, observed=True)["pct_resistant"].transform("sum")
    sub_cr["total_high"] = sub_cr.groupby(grp, observed=True)["pct_resistant"].transform(lambda s: (s >= T).sum())

    n_other = sub_cr["total_count"] - 1
    sub_cr["other_mean_all"] = np.where(n_other > 0, (sub_cr["total_sum"] - sub_cr["pct_resistant"]) / n_other, np.nan)
    sub_cr["n_high_other"] = np.where(n_other > 0, (sub_cr["total_high"] - (sub_cr["pct_resistant"] >= T).astype(int)).astype(float), np.nan)
    sub_cr["mdr_burden"] = np.where(n_other > 0, sub_cr["n_high_other"] / n_other, np.nan)

    grp_class = ["source", "iso3", "year", "pathogen", "antibiotic_class"]
    sub_cr["class_count"] = sub_cr.groupby(grp_class, observed=True)["pct_resistant"].transform("count")
    sub_cr["class_sum"] = sub_cr.groupby(grp_class, observed=True)["pct_resistant"].transform("sum")
    class_n_other = sub_cr["class_count"] - 1
    sub_cr["class_mean_other"] = np.where(class_n_other > 0, (sub_cr["class_sum"] - sub_cr["pct_resistant"]) / class_n_other, np.nan)

    cross_cols = ["source", "iso3", "year", "pathogen", "antibiotic", "class_mean_other", "other_mean_all", "n_high_other", "mdr_burden"]
    cross_table = sub_cr[cross_cols].rename(columns={"year": "prev_year"})

    panel["prev_year"] = panel["year"] - 1
    panel = panel.merge(
        cross_table,
        on=["source", "iso3", "prev_year", "pathogen", "antibiotic"],
        how="left",
    )

    # Regional median at t-1 within source
    reg_med = (
        sub.groupby(["source", "year", "pathogen", "antibiotic"], observed=True)["pct_resistant"]
        .median()
        .rename("region_median_prev")
        .reset_index()
        .rename(columns={"year": "prev_year"})
    )
    panel = panel.merge(
        reg_med,
        on=["source", "prev_year", "pathogen", "antibiotic"],
        how="left",
    )
    panel["gap_from_region_prev"] = panel["lag_1"] - panel["region_median_prev"]

    # Source-specific configuration flags
    if config_name == "pooled":
        panel["is_glass"] = (panel["source"] == sg).astype(int)
        panel["ecdc_definition_ipr"] = (panel["source"] == se).astype(int)
    if config_name == "ecdc":
        panel = panel.drop(columns=["who_region", "ast_coverage", "ast_coverage_prev"], errors="ignore")
    else:
        panel = panel.drop(columns=["ast_coverage_prev"], errors="ignore")

    panel = panel.drop(columns=["prev_year"], errors="ignore")

    panel["split"] = panel.apply(
        lambda r: assign_split(int(r["year"]), r["source"], config_name, bool(r.get("key_overlap", False))),
        axis=1,
    )
    return panel


FEATURE_DEFINITIONS: list[dict[str, str]] = [
    {"name": "lag_1", "group": "temporal", "availability": "derived", "definition": "pct_resistant at t-1 (consecutive year only).", "justification": "Persistence is a strong AMR baseline; last observed resistance anchors forecasts."},
    {"name": "lag_2", "group": "temporal", "availability": "derived", "definition": "pct_resistant at t-2 when consecutive.", "justification": "Two-year history helps detect acceleration beyond single-year noise."},
    {"name": "delta_1", "group": "temporal", "availability": "derived", "definition": "lag_1 minus lag_2.", "justification": "Recent momentum complements level for rising-resistance detection."},
    {"name": "roll_mean_2", "group": "temporal", "availability": "derived", "definition": "Mean of resistance in last two observed years before t.", "justification": "Smooths single-year sampling noise in surveillance counts."},
    {"name": "roll_std_2", "group": "temporal", "availability": "derived", "definition": "Std dev of last two years before t.", "justification": "Volatile series may need different alert thresholds in review."},
    {"name": "hist_max", "group": "temporal", "availability": "derived", "definition": "Maximum pct_resistant in years < t.", "justification": "Historical peaks indicate prior selection pressure in the population."},
    {"name": "hist_min", "group": "temporal", "availability": "derived", "definition": "Minimum pct_resistant in years < t.", "justification": "Floor resistance contextualizes how far a series has already risen."},
    {"name": "years_observed", "group": "temporal", "availability": "derived", "definition": "Count of years with data strictly before t.", "justification": "Maturity of surveillance series affects forecast reliability."},
    {"name": "has_lag2", "group": "temporal", "availability": "derived", "definition": "1 if lag_2 is available.", "justification": "Flags when two-year dynamics features are defined."},
    {"name": "log_tested", "group": "sample quality", "availability": "derived", "definition": "log1p(number_tested at t-1).", "justification": "Larger denominators stabilize proportion estimates in surveillance."},
    {"name": "ast_coverage", "group": "sample quality", "availability": "direct (GLASS)", "definition": "GLASS AST coverage at t-1 row.", "justification": "Incomplete testing can bias apparent resistance levels."},
    {"name": "wilson_width", "group": "sample quality", "availability": "derived", "definition": "95% Wilson interval width from t-1 counts.", "justification": "Quantifies uncertainty in the lagged resistance estimate."},
    {"name": "n_ge_30_prev", "group": "sample quality", "availability": "derived", "definition": "1 if number_tested at t-1 >= 30.", "justification": "WHO-style minimum denominators for reliable proportions."},
    {"name": "class_mean_other", "group": "cross-resistance", "availability": "derived", "definition": "Mean resistance of other drugs same ATC class at t-1.", "justification": "Class-level co-resistance is common in Gram-negative surveillance."},
    {"name": "other_mean_all", "group": "cross-resistance", "availability": "derived", "definition": "Mean resistance of all other antibiotics at t-1.", "justification": "Background multidrug resistance signals ecosystem pressure."},
    {"name": "n_high_other", "group": "cross-resistance", "availability": "derived", "definition": "Count of other antibiotics with resistance >= T at t-1.", "justification": "Counts co-resistant drugs relevant to multidrug phenotypes."},
    {"name": "mdr_burden", "group": "cross-resistance", "availability": "derived", "definition": "n_high_other divided by number of other antibiotics observed.", "justification": "Normalizes multidrug burden to comparable scale across pathogens."},
    {"name": "pathogen", "group": "context", "availability": "direct", "definition": "Pathogen name.", "justification": "Species drives intrinsic resistance mechanisms and trends."},
    {"name": "antibiotic", "group": "context", "availability": "direct", "definition": "Antibiotic name.", "justification": "Drug-specific epidemiology varies by mechanism and usage."},
    {"name": "antibiotic_class", "group": "context", "availability": "direct", "definition": "ATC level-3 class.", "justification": "Groups agents with related resistance pathways."},
    {"name": "who_region", "group": "context", "availability": "direct (GLASS)", "definition": "WHO region (GLASS only).", "justification": "Regional policies and circulation patterns differ globally."},
    {"name": "region_median_prev", "group": "context", "availability": "derived", "definition": "Median resistance for pathogen x antibiotic across countries at t-1 within source.", "justification": "Peer benchmark for whether a country is an outlier."},
    {"name": "gap_from_region_prev", "group": "context", "availability": "derived", "definition": "lag_1 minus region_median_prev.", "justification": "Relative elevation may persist or mean-revert differently."},
    {"name": "covid_flag", "group": "flags", "availability": "derived", "definition": "1 if target year is 2020.", "justification": "Pandemic years disrupted sampling and hospital mix."},
    {"name": "is_glass", "group": "flags", "availability": "derived (pooled)", "definition": "1 if row is GLASS.", "justification": "Lets pooled models respect source-specific measurement."},
    {"name": "ecdc_definition_ipr", "group": "flags", "availability": "derived (pooled)", "definition": "1 if row is ECDC (I+R definition).", "justification": "Captures systematic definition difference in pooled training."},
]


def write_feature_dictionary(path) -> None:
    lines = ["# Feature dictionary", "", "| Name | Group | Availability | Definition | Justification |", "|------|-------|--------------|------------|---------------|"]
    for f in FEATURE_DEFINITIONS:
        lines.append(
            f"| {f['name']} | {f['group']} | {f['availability']} | {f['definition']} | {f['justification']} |"
        )
    Path(path).write_text("\n".join(lines), encoding="utf-8")
