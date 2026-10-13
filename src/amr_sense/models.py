"""Model factories, preprocessing, and baselines."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import xgboost as xgb

TargetName = Literal["high_risk_next", "rising_next", "y_reg"]

CAT_COLS = ["pathogen", "antibiotic", "antibiotic_class"]
OPTIONAL_CAT = ["who_region"]


def feature_columns(config_name: str, for_trees: bool = False) -> tuple[list[str], list[str]]:
    """Numeric and categorical feature names for a configuration."""
    num = [
        "lag_1", "lag_2", "delta_1", "roll_mean_2", "roll_std_2",
        "hist_max", "hist_min", "years_observed", "has_lag2",
        "log_tested", "wilson_width", "n_ge_30_prev",
        "class_mean_other", "other_mean_all", "n_high_other", "mdr_burden",
        "region_median_prev", "gap_from_region_prev", "covid_flag",
    ]
    if config_name == "glass":
        num.append("ast_coverage")
    elif config_name == "ecdc":
        pass
    else:
        num.extend(["is_glass", "ecdc_definition_ipr", "ast_coverage"])
    cats = CAT_COLS.copy()
    if config_name == "glass":
        cats.append("who_region")
    return num, cats


def make_preprocessor(config_name: str, scale: bool = True) -> ColumnTransformer:
    num, cats = feature_columns(config_name)
    num_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
    ])
    if scale:
        num_pipe.steps.append(("scale", StandardScaler()))
    cat_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", num_pipe, num),
        ("cat", cat_pipe, cats),
    ])


def logistic_pipeline(config_name: str, **lr_kw) -> Pipeline:
    defaults = dict(penalty="l2", solver="saga", class_weight="balanced", max_iter=5000, random_state=42)
    defaults.update(lr_kw)
    return Pipeline([
        ("prep", make_preprocessor(config_name, scale=True)),
        ("clf", LogisticRegression(**defaults)),
    ])


def random_forest_pipeline(config_name: str, **rf_kw) -> Pipeline:
    defaults = dict(n_estimators=200, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    defaults.update(rf_kw)
    return Pipeline([
        ("prep", make_preprocessor(config_name, scale=False)),
        ("clf", RandomForestClassifier(**defaults)),
    ])


def xgb_classifier(config_name: str, scale_pos_weight: float = 1.0, **xkw) -> xgb.XGBClassifier:
    num, cats = feature_columns(config_name)
    # XGB with manual prep in training loop — use pipeline wrapper
    defaults = dict(
        objective="binary:logistic",
        eval_metric="aucpr",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        reg_alpha=0.0,
        gamma=0.0,
        min_child_weight=3,
    )
    defaults.update(xkw)
    pipe = Pipeline([
        ("prep", make_preprocessor(config_name, scale=False)),
        ("clf", xgb.XGBClassifier(**defaults)),
    ])
    return pipe


def ridge_pipeline(config_name: str, alpha: float = 1.0) -> Pipeline:
    return Pipeline([
        ("prep", make_preprocessor(config_name, scale=True)),
        ("reg", Ridge(alpha=alpha, random_state=42)),
    ])


def xgb_regressor_pipeline(config_name: str, **xkw) -> Pipeline:
    defaults = dict(
        objective="reg:squarederror",
        random_state=42,
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        reg_lambda=1.0,
    )
    defaults.update(xkw)
    return Pipeline([
        ("prep", make_preprocessor(config_name, scale=False)),
        ("reg", xgb.XGBRegressor(**defaults)),
    ])


def prepare_xy(df: pd.DataFrame, target: TargetName, config_name: str) -> tuple[pd.DataFrame, np.ndarray]:
    num, cats = feature_columns(config_name)
    cols = [c for c in num + cats if c in df.columns]
    X = df[cols].copy()
    y = df[target].values
    return X, y


def persistence_baseline_reg(df: pd.DataFrame) -> np.ndarray:
    return df["lag_1"].values


def roll_mean_baseline_reg(df: pd.DataFrame) -> np.ndarray:
    rm = df["roll_mean_2"].values
    l1 = df["lag_1"].values
    out = np.where(np.isnan(rm), l1, rm)
    return out


def persistence_baseline_clf(df: pd.DataFrame, T: float) -> np.ndarray:
    return (df["lag_1"] >= T).astype(int).values


def rising_dummy_prevalence(y_train: np.ndarray, n: int) -> np.ndarray:
    prev = y_train.mean()
    return (np.random.RandomState(42).random(n) < prev).astype(int)


def rising_delta_baseline(df: pd.DataFrame, rise_pp: float = 5.0) -> np.ndarray:
    return (df["delta_1"] >= rise_pp).astype(int).values
