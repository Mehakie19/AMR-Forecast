"""Time-ordered splits and rolling-origin folds."""

from __future__ import annotations

from typing import Iterator

import pandas as pd

from amr_sense.config import load_config

SplitLabel = str  # train | validation | test


def assign_split(
    target_year: int,
    source: str,
    config_name: str,
    key_overlap: bool,
) -> SplitLabel:
    """Assign train/validation/test by target year and configuration."""
    cfg = load_config()
    sg, se = cfg["sources"]["glass"], cfg["sources"]["ecdc"]
    splits = cfg["splits"]

    if config_name == "glass":
        if source != sg:
            return "exclude"
        if target_year in splits["glass"]["train_years"]:
            return "train"
        if target_year in splits["glass"]["val_years"]:
            return "validation"
        if target_year in splits["glass"]["test_years"]:
            return "test"
        return "exclude"

    if config_name == "ecdc":
        if source != se:
            return "exclude"
        if target_year in splits["ecdc"]["train_years"]:
            return "train"
        if target_year in splits["ecdc"]["val_years"]:
            return "validation"
        if target_year in splits["ecdc"]["test_years"]:
            return "test"
        return "exclude"

    # pooled
    if source == sg:
        if target_year in splits["glass"]["train_years"]:
            if key_overlap and cfg["splits"]["pooled"].get("exclude_key_overlap_from_train"):
                return "exclude"
            return "train"
        if target_year in splits["glass"]["val_years"]:
            return "validation"
        if target_year in splits["glass"]["test_years"]:
            return "test"
        return "exclude"
    if source == se:
        if target_year in splits["ecdc"]["train_years"]:
            if key_overlap and cfg["splits"]["pooled"].get("exclude_key_overlap_from_train"):
                return "exclude"
            return "train"
        if target_year in splits["ecdc"]["val_years"]:
            return "validation"
        if target_year in splits["ecdc"]["test_years"]:
            return "test"
        return "exclude"
    return "exclude"


def rolling_origin_folds(
    df: pd.DataFrame,
    train_years: list[int],
    val_years: list[int],
    year_col: str = "year",
) -> list[tuple[pd.Index, pd.Index]]:
    """
    Rolling-origin folds: fold k trains on target years < Y_k, validates on Y_k.

    Only uses years within train_years union val_years (training period).
    """
    allowed = set(train_years) | set(val_years)
    sub = df[df[year_col].isin(allowed)]
    folds = []
    for y in sorted(val_years):
        tr = sub[sub[year_col].isin([yr for yr in train_years if yr < y])].index
        va = sub[sub[year_col] == y].index
        if len(tr) and len(va):
            folds.append((tr, va))
    return folds


def validate_folds(folds: list[tuple[pd.Index, pd.Index]], df: pd.DataFrame, year_col: str = "year") -> bool:
    """Check max train year < min val year for each fold."""
    for tr, va in folds:
        if len(tr) == 0 or len(va) == 0:
            return False
        max_tr = df.loc[tr, year_col].max()
        min_va = df.loc[va, year_col].min()
        if max_tr >= min_va:
            return False
    return True
