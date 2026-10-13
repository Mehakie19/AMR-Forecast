"""Tests for time-ordered splits."""

from __future__ import annotations

import pandas as pd

from amr_sense.config import load_config
from amr_sense.splits import assign_split, rolling_origin_folds, validate_folds


def test_glass_split_years():
    cfg = load_config()
    sg = cfg["sources"]["glass"]
    assert assign_split(2021, sg, "glass", False) == "train"
    assert assign_split(2022, sg, "glass", False) == "validation"
    assert assign_split(2023, sg, "glass", False) == "test"


def test_rolling_origin_order():
    cfg = load_config()
    years = list(range(2019, 2022))
    df = pd.DataFrame({"year": years * 5})
    folds = rolling_origin_folds(df, train_years=[2019, 2020, 2021], val_years=[2020, 2021])
    assert validate_folds(folds, df)
