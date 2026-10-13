"""Soft voting and time-safe stacking."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import VotingClassifier


def soft_voting(models: list, weights: list[float] | None = None) -> VotingClassifier:
    estimators = [(f"m{i}", m) for i, m in enumerate(models)]
    return VotingClassifier(estimators=estimators, voting="soft", weights=weights)


def stacking_oof_predictions(
    base_models: list,
    df: pd.DataFrame,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: list,
) -> tuple[np.ndarray, int]:
    """
    Out-of-fold probabilities from rolling-origin folds.
    Returns oof array (nan where no prediction) and count of rows used for meta-training.
    """
    oof = np.full(len(y), np.nan)
    for tr_idx, va_idx in folds:
        for model in base_models:
            m = clone(model)
            m.fit(X.loc[tr_idx], y[tr_idx])
            oof[va_idx] = m.predict_proba(X.loc[va_idx])[:, 1]
            break  # one model at a time — caller stacks multiple columns
    return oof, int(np.isfinite(oof).sum())


def build_meta_features(
    base_models: list,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: list,
) -> tuple[np.ndarray, np.ndarray]:
    """Matrix of OOF probs shape (n_samples, n_models) and mask of rows with all OOF."""
    cols = []
    for model in base_models:
        oof = np.full(len(y), np.nan)
        for tr_idx, va_idx in folds:
            m = clone(model)
            m.fit(X.loc[tr_idx], y[tr_idx])
            oof[va_idx] = m.predict_proba(X.loc[va_idx])[:, 1]
        cols.append(oof)
    meta = np.column_stack(cols)
    mask = np.all(np.isfinite(meta), axis=1)
    return meta, mask
