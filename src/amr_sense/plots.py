"""Matplotlib/seaborn figures for EDA and results."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

SERIES_COLS = ["source", "iso3", "pathogen", "antibiotic"]

PALETTE = {
    "GLASS-AMR": "#0173B2",
    "ECDC-EARSNet(Zenodo)": "#DE8F05",
}


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_resistance_distribution(df: pd.DataFrame, source: str, out: Path) -> None:
    """Violin of pct_resistant by pathogen x antibiotic."""
    sub = df[df["source"] == source].copy()
    sub["pa"] = sub["pathogen"].str.replace(" spp.", "") + " | " + sub["antibiotic"]
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.violinplot(data=sub, x="pa", y="pct_resistant", ax=ax, color=PALETTE.get(source, "gray"))
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="right", fontsize=8)
    ax.set_ylabel("Percent resistant (%)")
    ax.set_xlabel("Pathogen | Antibiotic")
    ax.set_title(f"Distribution of resistance — {source}")
    _save(fig, out)


def plot_trends_by_year(df: pd.DataFrame, source: str, out: Path) -> None:
    """Median resistance by year with IQR bands, faceted by pathogen-antibiotic."""
    sub = df[df["source"] == source].copy()
    sub["pa"] = sub["pathogen"] + "\n" + sub["antibiotic"]
    agg = (
        sub.groupby(["year", "pa"], observed=True)["pct_resistant"]
        .agg(["median", lambda s: s.quantile(0.25), lambda s: s.quantile(0.75)])
        .reset_index()
    )
    agg.columns = ["year", "pa", "median", "q25", "q75"]
    pas = agg["pa"].unique()
    n = len(pas)
    ncol = 3
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 4, nrow * 2.5), sharex=True)
    axes = np.atleast_1d(axes).flatten()
    for i, pa in enumerate(sorted(pas)):
        ax = axes[i]
        g = agg[agg["pa"] == pa]
        ax.fill_between(g["year"], g["q25"], g["q75"], alpha=0.3, color=PALETTE.get(source, "C0"))
        ax.plot(g["year"], g["median"], marker="o", color=PALETTE.get(source, "C0"))
        ax.set_title(pa, fontsize=7)
        ax.set_ylabel("%")
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle(f"Median resistance by year (IQR) — {source}", y=1.02)
    fig.tight_layout()
    _save(fig, out)


def plot_who_region_trends_glass(df: pd.DataFrame, out: Path) -> None:
    """Mean resistance by WHO region over years (GLASS)."""
    sub = df[df["source"] == "GLASS-AMR"].copy()
    agg = (
        sub.groupby(["year", "who_region"], observed=True)["pct_resistant"]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    for region, g in agg.groupby("who_region", observed=True):
        ax.plot(g["year"], g["pct_resistant"], marker="o", label=region)
    ax.set_ylabel("Mean % resistant")
    ax.set_xlabel("Year")
    ax.set_title("GLASS: mean resistance by WHO region")
    ax.legend(fontsize=7, bbox_to_anchor=(1.02, 1))
    _save(fig, out)


def plot_top_country_movers_ecdc(df: pd.DataFrame, out: Path, n: int = 10) -> None:
    """Line plots for ECDC countries with largest total change."""
    sub = df[df["source"] == "ECDC-EARSNet(Zenodo)"].copy()
    changes = []
    for key, g in sub.groupby(SERIES_COLS, observed=True):
        g = g.sort_values("year")
        if len(g) < 2:
            continue
        changes.append((key, g["pct_resistant"].iloc[-1] - g["pct_resistant"].iloc[0]))
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    top_iso = {c[0][1] for c in changes[:n]}
    fig, ax = plt.subplots(figsize=(10, 5))
    for iso in top_iso:
        g = sub[sub["iso3"] == iso].groupby("year", observed=True)["pct_resistant"].mean()
        ax.plot(g.index, g.values, marker="o", label=iso)
    ax.set_title(f"ECDC: top {n} countries by |total change| (mean across series)")
    ax.set_ylabel("Mean % resistant")
    ax.legend(fontsize=8)
    _save(fig, out)


def plot_sample_size_funnel(df: pd.DataFrame, source: str, out: Path) -> None:
    """pct_resistant vs number_tested (log x)."""
    sub = df[df["source"] == source]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        sub["number_tested"],
        sub["pct_resistant"],
        alpha=0.35,
        s=12,
        c=PALETTE.get(source, "gray"),
    )
    ax.set_xscale("log")
    ax.axvline(30, color="red", linestyle="--", label="n=30")
    ax.set_xlabel("Number tested (log scale)")
    ax.set_ylabel("Percent resistant (%)")
    ax.set_title(f"Sample-size funnel — {source}")
    ax.legend()
    _save(fig, out)


def plot_yoy_change_distribution(df: pd.DataFrame, source: str, out: Path) -> None:
    """Distribution of year-on-year change in pct_resistant."""
    sub = df[df["source"] == source].sort_values(SERIES_COLS + ["year"])
    sub["pct_prev"] = sub.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    sub["yoy"] = sub["pct_resistant"] - sub["pct_prev"]
    yoy = sub["yoy"].dropna()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(yoy, bins=40, color=PALETTE.get(source, "gray"), edgecolor="white")
    share_rise = (yoy >= 5).mean()
    ax.axvline(5, color="red", linestyle="--", label="rise_pp=5")
    ax.set_title(f"YoY change — {source} (share rises ≥5pp: {100 * share_rise:.1f}%)")
    ax.set_xlabel("Change in % resistant (pp)")
    ax.legend()
    _save(fig, out)


def plot_class_balance(df: pd.DataFrame, source: str, out: Path, thresholds: list[int]) -> None:
    """Bar chart of high_risk and rising prevalence (from panel-style labels on raw)."""
    from amr_sense.panel import build_eligible_panel

    panel = build_eligible_panel(df[df["source"] == source], cfg_source="glass" if "GLASS" in source else "ecdc")
    fig, axes = plt.subplots(1, len(thresholds) + 1, figsize=(4 * (len(thresholds) + 1), 4))
    for i, T in enumerate(thresholds):
        col = f"high_risk_next_{T}"
        if col not in panel.columns:
            continue
        prev = panel[col].mean()
        axes[i].bar(["positive", "negative"], [prev, 1 - prev], color=["#CC3311", "#88CCEE"])
        axes[i].set_title(f"high_risk T={T}\nprev={100 * prev:.1f}%")
        axes[i].set_ylim(0, 1)
    if "rising_next" in panel.columns:
        prev = panel["rising_next"].mean()
        axes[-1].bar(["rising", "not"], [prev, 1 - prev], color=["#CC3311", "#88CCEE"])
        axes[-1].set_title(f"rising_next\nprev={100 * prev:.1f}%")
    fig.suptitle(f"Class balance — {source}")
    fig.tight_layout()
    _save(fig, out)


def plot_correlation_heatmap(df: pd.DataFrame, source: str, pathogen: str, out: Path) -> None:
    """Cross-antibiotic correlation within pathogen (country-year observations)."""
    sub = df[(df["source"] == source) & (df["pathogen"] == pathogen)]
    wide = sub.pivot_table(
        index=["iso3", "year"],
        columns="antibiotic",
        values="pct_resistant",
        observed=True,
    )
    corr = wide.corr(min_periods=5)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax, vmin=-1, vmax=1)
    ax.set_title(f"Cross-resistance correlation — {pathogen} ({source})")
    _save(fig, out)


def plot_ast_coverage_glass(df: pd.DataFrame, out: Path) -> None:
    """ast_coverage distribution and vs resistance."""
    sub = df[df["source"] == "GLASS-AMR"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(sub["ast_coverage"].dropna(), bins=30, color=PALETTE["GLASS-AMR"])
    axes[0].set_title("ast_coverage distribution (GLASS)")
    axes[0].set_xlabel("ast_coverage")
    axes[1].scatter(sub["ast_coverage"], sub["pct_resistant"], alpha=0.3, s=10)
    axes[1].set_xlabel("ast_coverage")
    axes[1].set_ylabel("pct_resistant")
    axes[1].set_title("Coverage vs resistance")
    fig.tight_layout()
    _save(fig, out)


def plot_covid_yoy(df: pd.DataFrame, source: str, out: Path) -> None:
    """Mean YoY change by target year."""
    sub = df[df["source"] == source].sort_values(SERIES_COLS + ["year"])
    sub["pct_prev"] = sub.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    sub["yoy"] = sub["pct_resistant"] - sub["pct_prev"]
    agg = sub.groupby("year", observed=True)["yoy"].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(agg.index.astype(str), agg.values, color=PALETTE.get(source, "gray"))
    ax.axvline("2020", color="red", linestyle="--", alpha=0.5)
    ax.set_title(f"Mean YoY change by year — {source}")
    ax.set_ylabel("Mean change (pp)")
    _save(fig, out)


def plot_persistence_mae(df: pd.DataFrame, source: str, out: Path) -> None:
    """Persistence baseline MAE by pathogen x antibiotic."""
    sub = df[df["source"] == source].sort_values(SERIES_COLS + ["year"])
    sub["lag_1"] = sub.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    sub = sub.dropna(subset=["lag_1"])
    sub["err"] = (sub["pct_resistant"] - sub["lag_1"]).abs()
    agg = (
        sub.groupby(["pathogen", "antibiotic"], observed=True)["err"]
        .mean()
        .reset_index()
    )
    agg["label"] = agg["pathogen"].str[:10] + " | " + agg["antibiotic"]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.barh(agg["label"], agg["err"], color=PALETTE.get(source, "gray"))
    ax.set_xlabel("Mean absolute error (pp) — persistence")
    ax.set_title(f"Persistence baseline error — {source}")
    _save(fig, out)


def plot_xgb_tuning_heatmap(study_dict: dict, out: Path, title_suffix: str = "") -> None:
    """XGBoost learning_rate x max_depth heatmap of mean objective from Optuna trials."""
    trials = study_dict.get("trials", [])
    if not trials:
        return
    tdf = pd.DataFrame(trials)
    if "learning_rate" not in tdf.columns or "max_depth" not in tdf.columns or "value" not in tdf.columns:
        return
    tdf["lr_bin"] = pd.qcut(tdf["learning_rate"], q=min(4, tdf["learning_rate"].nunique()), duplicates="drop").astype(str)
    grid = tdf.pivot_table(index="max_depth", columns="lr_bin", values="value", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(grid, annot=True, fmt=".3f", cmap="viridis", ax=ax)
    ax.set_title(f"XGBoost tuning: max_depth vs learning_rate {title_suffix}".strip())
    ax.set_xlabel("learning_rate (binned)")
    ax.set_ylabel("max_depth")
    _save(fig, out)


def plot_lr_regularization_curves(study_dict: dict, out: Path, title_suffix: str = "") -> None:
    """Logistic regression validation PR-AUC against C for each penalty from Optuna trials."""
    trials = study_dict.get("trials", [])
    if not trials:
        return
    tdf = pd.DataFrame(trials)
    if "C" not in tdf.columns or "penalty" not in tdf.columns or "value" not in tdf.columns:
        return
    tdf["penalty"] = tdf["penalty"].fillna("none")
    fig, ax = plt.subplots(figsize=(7, 4))
    for pen, g in tdf.groupby("penalty"):
        g = g.sort_values("C")
        ax.plot(g["C"], g["value"], marker="o", label=str(pen))
    ax.set_xscale("log")
    ax.set_xlabel("C (regularization strength, log scale)")
    ax.set_ylabel("Mean validation PR-AUC")
    ax.set_title(f"Logistic regression regularization sensitivity {title_suffix}".strip())
    ax.legend(title="Penalty")
    _save(fig, out)

