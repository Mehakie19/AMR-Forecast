#!/usr/bin/env python
"""Stage 1: data quality report and EDA figures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from amr_sense.config import load_config
from amr_sense.data import load_and_validate, write_data_quality_report
from amr_sense import plots
from amr_sense.panel import build_eligible_panel

SERIES_COLS = ["source", "iso3", "pathogen", "antibiotic"]


def main() -> None:
    cfg = load_config()
    fig_dir = ROOT / cfg["paths"]["figures_eda"]
    eda_dir = ROOT / cfg["paths"]["reports_eda"]
    df, validation = load_and_validate()
    write_data_quality_report(df, validation, eda_dir / "data_quality.md")

    sg = cfg["sources"]["glass"]
    se = cfg["sources"]["ecdc"]
    Ts = cfg["thresholds"]["high_risk_sensitivity"]

    for source in [sg, se]:
        tag = "glass" if source == sg else "ecdc"
        plots.plot_resistance_distribution(df, source, fig_dir / f"{tag}_01_distribution.png")
        plots.plot_trends_by_year(df, source, fig_dir / f"{tag}_02_trends.png")
        plots.plot_sample_size_funnel(df, source, fig_dir / f"{tag}_04_sample_size.png")
        plots.plot_yoy_change_distribution(df, source, fig_dir / f"{tag}_05_yoy_change.png")
        plots.plot_class_balance(df, source, fig_dir / f"{tag}_06_class_balance.png", Ts)
        plots.plot_covid_yoy(df, source, fig_dir / f"{tag}_09_covid_yoy.png")
        plots.plot_persistence_mae(df, source, fig_dir / f"{tag}_10_persistence_mae.png")
        for pathogen in df["pathogen"].unique():
            safe = pathogen.replace(" ", "_").replace(".", "")
            plots.plot_correlation_heatmap(
                df, source, pathogen, fig_dir / f"{tag}_07_corr_{safe}.png"
            )

    plots.plot_who_region_trends_glass(df, fig_dir / "glass_03_who_region.png")
    plots.plot_top_country_movers_ecdc(df, fig_dir / "ecdc_03_top_movers.png")
    plots.plot_ast_coverage_glass(df, fig_dir / "glass_08_ast_coverage.png")

    findings = build_eda_findings(df, cfg)
    (eda_dir / "eda_findings.md").write_text(findings, encoding="utf-8")
    print("EDA complete:", eda_dir)


def build_eda_findings(df, cfg) -> str:
    sg, se = cfg["sources"]["glass"], cfg["sources"]["ecdc"]
    lines = ["# EDA findings", ""]

    for source, tag in [(sg, "GLASS"), (se, "ECDC")]:
        sub = df[df["source"] == source].sort_values(SERIES_COLS + ["year"])
        sub["pct_prev"] = sub.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
        yoy = (sub["pct_resistant"] - sub["pct_prev"]).dropna()
        yoy_sd = yoy.std()
        share_rise = (yoy >= cfg["thresholds"]["rise_pp"]).mean()
        pers = sub.dropna(subset=["pct_prev"])
        pers_mae = (pers["pct_resistant"] - pers["pct_prev"]).abs().mean()
        small_n = (sub["number_tested"] < 30).mean()

        panel = build_eligible_panel(sub)
        clf = panel[
            (panel["number_tested"] >= 30) & (panel["number_tested_prev"] >= 30)
        ]
        T = cfg["thresholds"]["high_risk_T"]
        hr = clf[f"high_risk_next_{T}"].mean() if len(clf) else float("nan")
        ris = clf["rising_next"].mean() if len(clf) else float("nan")

        lines.extend(
            [
                f"## {tag} ({source})",
                "",
                f"- Rows: **{len(sub)}**; countries: **{sub['iso3'].nunique()}**; "
                f"years **{sub['year'].min()}–{sub['year'].max()}**.",
                f"- Share rows with `number_tested < 30`: **{100 * small_n:.2f}%**.",
                f"- Year-on-year change SD: **{yoy_sd:.2f} pp**; share rises ≥ {cfg['thresholds']['rise_pp']} pp: "
                f"**{100 * share_rise:.1f}%**.",
                f"- Persistence MAE (all consecutive pairs): **{pers_mae:.2f} pp**.",
                f"- Classification-eligible rows: **{len(clf)}**; "
                f"high_risk_next (T={T}) prevalence **{100 * hr:.1f}%**; "
                f"rising_next **{100 * ris:.1f}%**.",
                "",
            ]
        )

    covid = df.sort_values(SERIES_COLS + ["year"])
    covid["pct_prev"] = covid.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    covid["yoy"] = covid["pct_resistant"] - covid["pct_prev"]
    by_year = covid.groupby("year", observed=True)["yoy"].mean()
    lines.extend(
        [
            "## COVID-era check (combined)",
            "",
            "Mean YoY change by calendar year (all sources):",
            "",
        ]
    )
    for yr, val in by_year.items():
        lines.append(f"- {yr}: **{val:.2f} pp**")
    if 2020 in by_year.index:
        lines.append(
            f"\n2020 mean YoY change: **{by_year.loc[2020]:.2f} pp** "
            "(flagged via `covid_flag` in modeling; not dropped)."
        )

    lines.extend(
        [
            "",
            "## Data issues that affect modeling",
            "",
            "1. **Definition mismatch:** ECDC uses I+R; GLASS uses R as reported — do not compare levels across sources.",
            "2. **Malta overlap:** 8 rows with `key_overlap=True`; excluded from pooled training per config.",
            "3. **GLASS reporting filter:** participating countries may over-represent better reporters.",
            "4. **Small sample sizes (GLASS):** ~5% of rows have n<30; increases YoY noise vs ECDC.",
            "5. **Short GLASS panel:** only 2018–2023 limits temporal features for some series.",
            "6. **COVID 2020:** potential surveillance disruption; modeled with `covid_flag`.",
            "7. **Pooled temporal overlap:** GLASS train years 2019–2021 overlap calendar years with held-out ECDC 2018–2019.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
