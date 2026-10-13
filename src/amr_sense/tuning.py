"""Optuna hyperparameter tuning with rolling-origin CV."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import average_precision_score, mean_absolute_error

from amr_sense.config import ROOT, load_config
from amr_sense.evaluate import classification_metrics
from amr_sense.models import (
    feature_columns,
    logistic_pipeline,
    prepare_xy,
    random_forest_pipeline,
    ridge_pipeline,
    xgb_classifier,
    xgb_regressor_pipeline,
)
from amr_sense.splits import rolling_origin_folds


def _mean_pr_auc(model, df: pd.DataFrame, target: str, config_name: str, folds) -> float:
    scores = []
    num, cats = feature_columns(config_name)
    cols = [c for c in num + cats if c in df.columns]
    X_all = df[cols].copy()
    y_all = df[target].copy()
    for tr_idx, va_idx in folds:
        from sklearn.base import clone
        m = clone(model)
        m.fit(X_all.loc[tr_idx], y_all.loc[tr_idx].values)
        prob = m.predict_proba(X_all.loc[va_idx])[:, 1]
        y_va = y_all.loc[va_idx].values
        if len(np.unique(y_va)) > 1:
            scores.append(average_precision_score(y_va, prob))
    return float(np.mean(scores)) if scores else 0.0


def _mean_neg_mae(model, df: pd.DataFrame, target: str, config_name: str, folds) -> float:
    scores = []
    num, cats = feature_columns(config_name)
    cols = [c for c in num + cats if c in df.columns]
    X_all = df[cols].copy()
    y_all = df[target].copy()
    for tr_idx, va_idx in folds:
        from sklearn.base import clone
        m = clone(model)
        m.fit(X_all.loc[tr_idx], y_all.loc[tr_idx].values)
        pred = m.predict(X_all.loc[va_idx])
        y_va = y_all.loc[va_idx].values
        scores.append(-float(mean_absolute_error(y_va, pred)))
    return float(np.mean(scores)) if scores else -999.0


def tune_logistic(df_train: pd.DataFrame, target: str, config_name: str, folds, n_trials: int) -> dict:
    def objective(trial: optuna.Trial) -> float:
        penalty = trial.suggest_categorical("penalty", ["l2", "l1", "elasticnet", "none"])
        C = trial.suggest_float("C", 1e-3, 100, log=True)
        l1_ratio = trial.suggest_float("l1_ratio", 0.0, 1.0) if penalty == "elasticnet" else None
        if penalty == "none":
            kw = dict(penalty=None, solver="saga", max_iter=3000)
        elif penalty == "elasticnet":
            kw = dict(penalty="elasticnet", C=C, l1_ratio=l1_ratio, solver="saga", max_iter=3000)
        else:
            kw = dict(penalty=penalty, C=C, solver="saga", max_iter=3000)
        pipe = logistic_pipeline(config_name, **kw)
        return _mean_pr_auc(pipe, df_train, target, config_name, folds)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return {"best_params": study.best_params, "best_value": study.best_value, "trials": [
        {"number": t.number, "value": t.value, **t.params} for t in study.trials
    ]}


def tune_rf(df_train: pd.DataFrame, target: str, config_name: str, folds, n_trials: int) -> dict:
    def objective(trial: optuna.Trial) -> float:
        pipe = random_forest_pipeline(
            config_name,
            n_estimators=trial.suggest_int("n_estimators", 100, 250, step=50),
            max_depth=trial.suggest_int("max_depth", 3, 10),
            min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 10),
            max_features=trial.suggest_categorical("max_features", ["sqrt", "log2"]),
        )
        return _mean_pr_auc(pipe, df_train, target, config_name, folds)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return {"best_params": study.best_params, "best_value": study.best_value, "trials": [
        {"number": t.number, "value": t.value, **t.params} for t in study.trials
    ]}


def tune_xgb_clf(df_train: pd.DataFrame, target: str, config_name: str, folds, n_trials: int) -> dict:
    prev = float(df_train[target].mean())
    spw = (1.0 - prev) / max(prev, 1e-6)

    def objective(trial: optuna.Trial) -> float:
        pipe = xgb_classifier(
            config_name,
            scale_pos_weight=spw,
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            max_depth=trial.suggest_int("max_depth", 2, 5),
            reg_lambda=trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 1.0, log=True),
            gamma=trial.suggest_float("gamma", 0.0, 2.0),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 7),
            subsample=trial.suggest_float("subsample", 0.7, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),
        )
        return _mean_pr_auc(pipe, df_train, target, config_name, folds)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return {"best_params": study.best_params, "best_value": study.best_value, "trials": [
        {"number": t.number, "value": t.value, **t.params} for t in study.trials
    ]}


def tune_ridge(df_train: pd.DataFrame, target: str, config_name: str, folds, n_trials: int = 15) -> dict:
    def objective(trial: optuna.Trial) -> float:
        alpha = trial.suggest_float("alpha", 0.01, 100.0, log=True)
        pipe = ridge_pipeline(config_name, alpha=alpha)
        return _mean_neg_mae(pipe, df_train, target, config_name, folds)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return {"best_params": study.best_params, "best_value": study.best_value, "trials": [
        {"number": t.number, "value": t.value, **t.params} for t in study.trials
    ]}


def tune_xgb_reg(df_train: pd.DataFrame, target: str, config_name: str, folds, n_trials: int = 15) -> dict:
    def objective(trial: optuna.Trial) -> float:
        pipe = xgb_regressor_pipeline(
            config_name,
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            max_depth=trial.suggest_int("max_depth", 2, 5),
            reg_lambda=trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
        )
        return _mean_neg_mae(pipe, df_train, target, config_name, folds)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return {"best_params": study.best_params, "best_value": study.best_value, "trials": [
        {"number": t.number, "value": t.value, **t.params} for t in study.trials
    ]}


def save_study(study_dict: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(study_dict, indent=2), encoding="utf-8")
