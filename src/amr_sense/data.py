"""Load, validate, and document the combined AMR dataset."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from amr_sense.config import ROOT, load_config

SERIES_COLS = ["source", "iso3", "pathogen", "antibiotic"]
KEY_COLS = ["source", "iso3", "year", "pathogen", "antibiotic"]

EXPECTED = {
    "total_rows": 6634,
    "glass_rows": 2394,
    "ecdc_rows": 4240,
    "glass_series": 399,
    "glass_years_per_series": 6,
    "key_overlap_rows": 8,
    "pathogens": [
        "Acinetobacter spp.",
        "Escherichia coli",
        "Klebsiella pneumoniae",
    ],
    "antibiotics": [
        "Amikacin",
        "Ceftazidime",
        "Ceftriaxone",
        "Ciprofloxacin",
        "Colistin",
        "Ertapenem",
        "Gentamicin",
        "Imipenem",
        "Meropenem",
    ],
    "ecdc_resistance_definition": "I_plus_R",
    "glass_resistance_definition": "R_as_reported_by_GLASS",
}


@dataclass
class ValidationIssue:
    message: str
    expected: Any = None
    actual: Any = None


@dataclass
class DataValidationResult:
    df: pd.DataFrame
    issues: list[ValidationIssue] = field(default_factory=list)

    def warn(self, message: str, expected: Any = None, actual: Any = None) -> None:
        self.issues.append(ValidationIssue(message, expected, actual))


def _source_glass(cfg: dict) -> str:
    return cfg["sources"]["glass"]


def _source_ecdc(cfg: dict) -> str:
    return cfg["sources"]["ecdc"]


def load_combined(path: Path | None = None) -> pd.DataFrame:
    """Load combined AMR dataset CSV."""
    cfg = load_config()
    p = path or (ROOT / cfg["paths"]["raw_combined"])
    df = pd.read_csv(p)
    return df


def recompute_pct_resistant(df: pd.DataFrame) -> pd.Series:
    """Recompute percent resistant from counts."""
    tested = df["number_tested"].astype(float)
    resistant = df["number_resistant"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(tested > 0, 100.0 * resistant / tested, np.nan)
    return pd.Series(pct, index=df.index)


def validate_combined(df: pd.DataFrame, cfg: dict | None = None) -> DataValidationResult:
    """Run schema and expected-value checks (warn, do not crash)."""
    cfg = cfg or load_config()
    result = DataValidationResult(df=df)
    sg, se = _source_glass(cfg), _source_ecdc(cfg)

    n = len(df)
    if n != EXPECTED["total_rows"]:
        result.warn("Total row count", EXPECTED["total_rows"], n)

    glass_n = (df["source"] == sg).sum()
    ecdc_n = (df["source"] == se).sum()
    if glass_n != EXPECTED["glass_rows"]:
        result.warn("GLASS row count", EXPECTED["glass_rows"], int(glass_n))
    if ecdc_n != EXPECTED["ecdc_rows"]:
        result.warn("ECDC row count", EXPECTED["ecdc_rows"], int(ecdc_n))

    glass = df[df["source"] == sg]
    n_series = glass.groupby(SERIES_COLS, observed=True).ngroups
    if n_series != EXPECTED["glass_series"]:
        result.warn("GLASS series count", EXPECTED["glass_series"], n_series)
    lens = glass.groupby(SERIES_COLS, observed=True)["year"].nunique()
    if not (lens == EXPECTED["glass_years_per_series"]).all():
        bad = lens[lens != EXPECTED["glass_years_per_series"]]
        result.warn(
            "GLASS series with != 6 years",
            "all 6",
            bad.to_dict(),
        )

    ecdc = df[df["source"] == se]
    if ecdc["year"].min() != 1999 or ecdc["year"].max() != 2019:
        result.warn(
            "ECDC year range",
            "1999-2019",
            f"{ecdc['year'].min()}-{ecdc['year'].max()}",
        )

    for col, exp in [("pathogen", EXPECTED["pathogens"]), ("antibiotic", EXPECTED["antibiotics"])]:
        got = sorted(df[col].dropna().unique().tolist())
        if got != sorted(exp):
            result.warn(f"Unique {col}", exp, got)

    overlap = int(df["key_overlap"].sum()) if "key_overlap" in df.columns else -1
    if overlap != EXPECTED["key_overlap_rows"]:
        result.warn("key_overlap=True rows", EXPECTED["key_overlap_rows"], overlap)

    ecdc_def = ecdc["resistance_definition"].dropna().unique()
    if len(ecdc_def) != 1 or ecdc_def[0] != EXPECTED["ecdc_resistance_definition"]:
        result.warn("ECDC resistance_definition", EXPECTED["ecdc_resistance_definition"], list(ecdc_def))

    glass_def = glass["resistance_definition"].dropna().unique()
    if len(glass_def) != 1 or glass_def[0] != EXPECTED["glass_resistance_definition"]:
        result.warn(
            "GLASS resistance_definition",
            EXPECTED["glass_resistance_definition"],
            list(glass_def),
        )

    classes = sorted(df["antibiotic_class"].dropna().unique().tolist())
    expected_classes = ["J01D", "J01G", "J01M", "J01X"]
    if classes != expected_classes:
        result.warn("antibiotic_class (ATC L3)", expected_classes, classes)

    return result


def malta_overlap_table(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where GLASS and ECDC overlap on Malta."""
    if "key_overlap" not in df.columns:
        return pd.DataFrame()
    return df[df["key_overlap"]].sort_values(
        ["iso3", "year", "pathogen", "antibiotic", "source"]
    )


def write_data_quality_report(
    df: pd.DataFrame,
    validation: DataValidationResult,
    out_path: Path,
) -> None:
    """Write reports/eda/data_quality.md from computed values."""
    cfg = load_config()
    sg, se = _source_glass(cfg), _source_ecdc(cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dup = df.duplicated(subset=KEY_COLS, keep=False).sum()
    missing = df.isna().sum()
    pct_recomp = recompute_pct_resistant(df)
    pct_diff = (pct_recomp - df["pct_resistant"]).abs()
    large_diff = (pct_diff > 0.01).sum()

    viol = (df["number_resistant"] > df["number_tested"]).sum()

    lines: list[str] = [
        "# Data quality report",
        "",
        "Single source of truth: `data/raw/combined_amr_dataset.csv`.",
        "",
        "## Provenance",
        "",
        "Original `ML_DATASET.csv` and `summary_AMR_filtered.csv` were **not** present "
        "in this workspace; row-level reproduction against those files was skipped.",
        "",
        "## Expected-value assertions",
        "",
    ]
    if validation.issues:
        for iss in validation.issues:
            lines.append(f"- **WARN:** {iss.message} (expected `{iss.expected}`, got `{iss.actual}`)")
    else:
        lines.append("- All expected-value checks matched.")

    lines.extend(
        [
            "",
            "## Row counts per source",
            "",
            f"| Source | Rows |",
            f"|--------|------|",
            f"| {sg} | {(df['source'] == sg).sum()} |",
            f"| {se} | {(df['source'] == se).sum()} |",
            f"| **Total** | {len(df)} |",
            "",
            "## Missing values (column counts)",
            "",
        ]
    )
    for col, cnt in missing.items():
        if cnt > 0:
            lines.append(f"- `{col}`: {int(cnt)} ({100 * cnt / len(df):.2f}%)")

    lines.extend(
        [
            "",
            f"## Duplicates on `{', '.join(KEY_COLS)}`",
            "",
            f"Duplicate row count (including pairs): **{int(dup)}**",
            "",
            "## Count consistency",
            "",
            f"Rows with `number_resistant > number_tested`: **{int(viol)}**",
            f"Rows where recomputed `pct_resistant` differs from stored by >0.01 pp: **{int(large_diff)}**",
            "",
            "## Sample size (`number_tested < 30`)",
            "",
        ]
    )
    for src in [sg, se]:
        sub = df[df["source"] == src]
        share = (sub["number_tested"] < 30).mean()
        lines.append(f"- **{src}**: {100 * share:.2f}% of rows ({int((sub['number_tested'] < 30).sum())} rows)")

    lines.extend(["", "## Series length distribution", ""])
    for src in [sg, se]:
        sub = df[df["source"] == src]
        lens = sub.groupby(SERIES_COLS, observed=True)["year"].nunique()
        lines.append(f"### {src}")
        lines.append(f"- Series count: {lens.shape[0]}")
        lines.append(f"- Min / median / max years per series: {lens.min()} / {lens.median():.0f} / {lens.max()}")
        lines.append("")

    lines.extend(["", "## Countries per source and year", ""])
    for src in [sg, se]:
        sub = df[df["source"] == src]
        cy = sub.groupby("year")["iso3"].nunique()
        lines.append(f"### {src}")
        lines.append(f"- Countries per year: min {cy.min()}, max {cy.max()}, median {cy.median():.0f}")
        lines.append(f"- Unique countries (overall): {sub['iso3'].nunique()}")
        lines.append("")

    lines.extend(["", "## Malta overlap (`key_overlap=True`)", ""])
    malta = malta_overlap_table(df)
    if len(malta):
        lines.append(malta[
            ["source", "iso3", "country", "year", "pathogen", "antibiotic", "pct_resistant", "number_tested"]
        ].to_markdown(index=False))
    else:
        lines.append("_No overlap rows._")

    issues_path = ROOT / "reports" / "issues.md"
    if validation.issues:
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        with open(issues_path, "a", encoding="utf-8") as f:
            f.write("\n## Data validation warnings\n\n")
            for iss in validation.issues:
                f.write(f"- {iss.message}: expected {iss.expected}, got {iss.actual}\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def load_and_validate() -> tuple[pd.DataFrame, DataValidationResult]:
    """Load combined data and validate."""
    df = load_combined()
    validation = validate_combined(df)
    return df, validation
