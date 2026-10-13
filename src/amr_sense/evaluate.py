"""Metrics, thresholds, bootstrap CIs, and report helpers."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    mean_absolute_error,
    mean_squared_error,
)


def classification_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    far = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    return {
        "pr_auc": float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else float("nan"),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else float("nan"),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_alert_rate": float(far),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return {"mae": float(mae), "rmse": float(rmse)}


def choose_threshold_f1_cap_far(y_true: np.ndarray, y_prob: np.ndarray, far_cap: float = 0.2) -> float:
    """Pick threshold maximizing F1 subject to false-alert rate cap."""
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 91):
        y_pred = (y_prob >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        far = fp / (fp + tn) if (fp + tn) else 1.0
        if far > far_cap:
            continue
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return float(best_t)


def country_bootstrap_ci(
    df: pd.DataFrame,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    y_col: str,
    prob_col: str,
    n_boot: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Paired cluster bootstrap over countries: point estimate and 95% CI."""
    countries = np.unique(df["iso3"].values)
    y = df[y_col].values
    p = df[prob_col].values
    point = metric_fn(y, p)
    rng = np.random.RandomState(seed)

    # Pre-index country row indices for 100x speedup
    iso_vals = df["iso3"].values
    country_indices = {c: np.where(iso_vals == c)[0] for c in countries}

    stats = []
    for _ in range(n_boot):
        sampled = rng.choice(countries, size=len(countries), replace=True)
        idx = np.concatenate([country_indices[c] for c in sampled])
        if len(idx) < 5 or len(np.unique(y[idx])) < 2:
            continue
        stats.append(metric_fn(y[idx], p[idx]))
    if not stats:
        return point, point, point
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def country_bootstrap_diff_ci(
    df: pd.DataFrame,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    y_col: str,
    prob_model_col: str,
    prob_base_col: str,
    n_boot: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Paired cluster bootstrap difference (model - baseline) over countries."""
    countries = np.unique(df["iso3"].values)
    y = df[y_col].values
    pm = df[prob_model_col].values
    pb = df[prob_base_col].values
    point = metric_fn(y, pm) - metric_fn(y, pb)
    rng = np.random.RandomState(seed)

    iso_vals = df["iso3"].values
    country_indices = {c: np.where(iso_vals == c)[0] for c in countries}

    diffs = []
    for _ in range(n_boot):
        sampled = rng.choice(countries, size=len(countries), replace=True)
        idx = np.concatenate([country_indices[c] for c in sampled])
        if len(idx) < 5 or len(np.unique(y[idx])) < 2:
            continue
        diffs.append(metric_fn(y[idx], pm[idx]) - metric_fn(y[idx], pb[idx]))
    if not diffs:
        return float(point), float(point), float(point)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def calibration_table(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    bins = np.linspace(0, 1, n_bins + 1)
    rows = []
    for i in range(n_bins):
        m = (y_prob >= bins[i]) & (y_prob < bins[i + 1]) if i < n_bins - 1 else (y_prob >= bins[i])
        if m.sum() == 0:
            continue
        rows.append({
            "bin_lo": float(bins[i]),
            "bin_hi": float(bins[i + 1]),
            "mean_pred": float(y_prob[m].mean()),
            "frac_pos": float(y_true[m].mean()),
            "count": int(m.sum()),
        })
    return pd.DataFrame(rows)


def compute_curves_data(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    """Compute PR curve, ROC curve, and confusion matrix points."""
    from sklearn.metrics import precision_recall_curve, roc_curve
    prec, rec, pr_thresh = precision_recall_curve(y_true, y_prob)
    fpr, tpr, roc_thresh = roc_curve(y_true, y_prob)
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    calib = calibration_table(y_true, y_prob)
    return {
        "pr_curve": {
            "precision": [float(x) for x in prec[::max(1, len(prec)//50)]],
            "recall": [float(x) for x in rec[::max(1, len(rec)//50)]],
        },
        "roc_curve": {
            "fpr": [float(x) for x in fpr[::max(1, len(fpr)//50)]],
            "tpr": [float(x) for x in tpr[::max(1, len(tpr)//50)]],
        },
        "calibration": calib.to_dict(orient="records"),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
            "threshold": float(threshold),
        },
    }


def segment_analysis(
    df: pd.DataFrame,
    y_col: str,
    prob_col: str,
    threshold: float = 0.5,
) -> dict[str, list[dict]]:
    """Compute metrics across segments: pathogen, antibiotic, sample size band, WHO region."""
    res: dict[str, list[dict]] = {"pathogen": [], "antibiotic": [], "sample_band": [], "who_region": []}

    # Pathogen
    for p, g in df.groupby("pathogen", observed=True):
        y, prob = g[y_col].values, g[prob_col].values
        m = classification_metrics(y, prob, threshold)
        m["segment"] = str(p)
        m["n_rows"] = int(len(g))
        res["pathogen"].append(m)

    # Antibiotic
    for a, g in df.groupby("antibiotic", observed=True):
        y, prob = g[y_col].values, g[prob_col].values
        m = classification_metrics(y, prob, threshold)
        m["segment"] = str(a)
        m["n_rows"] = int(len(g))
        res["antibiotic"].append(m)

    # Sample band
    bands = [
        ("<30", df["number_tested"] < 30),
        ("30-99", (df["number_tested"] >= 30) & (df["number_tested"] < 100)),
        ("100-299", (df["number_tested"] >= 100) & (df["number_tested"] < 300)),
        (">=300", df["number_tested"] >= 300),
    ]
    for band_name, mask in bands:
        g = df[mask]
        if len(g) > 0:
            y, prob = g[y_col].values, g[prob_col].values
            m = classification_metrics(y, prob, threshold)
            m["segment"] = band_name
            m["n_rows"] = int(len(g))
            res["sample_band"].append(m)

    # WHO region
    if "who_region" in df.columns:
        for r, g in df.dropna(subset=["who_region"]).groupby("who_region", observed=True):
            y, prob = g[y_col].values, g[prob_col].values
            m = classification_metrics(y, prob, threshold)
            m["segment"] = str(r)
            m["n_rows"] = int(len(g))
            res["who_region"].append(m)

    return res


def error_analysis_tables(
    df: pd.DataFrame,
    y_clf_col: str,
    prob_col: str,
    y_reg_col: str,
    pred_reg_col: str,
) -> dict[str, list[dict]]:
    """Return top 15 regression forecast errors and top 15 false alerts."""
    df_eval = df.copy()
    df_eval["abs_error"] = (df_eval[y_reg_col] - df_eval[pred_reg_col]).abs()

    cols_to_show = [
        "source", "iso3", "year", "pathogen", "antibiotic",
        "lag_1", "delta_1", "number_tested", "abs_error",
    ]
    avail_cols = [c for c in cols_to_show if c in df_eval.columns]

    top_reg_errors = (
        df_eval.sort_values("abs_error", ascending=False)
        .head(15)[avail_cols + [y_reg_col, pred_reg_col]]
        .to_dict(orient="records")
    )

    # False alerts: true negative (y == 0), highest predicted probability
    tn_df = df_eval[df_eval[y_clf_col] == 0].copy()
    top_false_alerts = (
        tn_df.sort_values(prob_col, ascending=False)
        .head(15)[[c for c in avail_cols if c in tn_df.columns] + [prob_col]]
        .to_dict(orient="records")
    )

    return {
        "largest_forecast_errors": top_reg_errors,
        "highest_confidence_false_alerts": top_false_alerts,
    }


def beat_persistence_share(y_true: np.ndarray, y_pred: np.ndarray, pers_pred: np.ndarray) -> float:
    err = np.abs(y_true - y_pred)
    err_p = np.abs(y_true - pers_pred)
    return float((err < err_p).mean())
