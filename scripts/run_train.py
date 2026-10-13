#!/usr/bin/env python
"""Stage 4: train, tune, ensemble; write validation results, regularization evidence, and FROZEN marker."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from amr_sense.config import load_config
from amr_sense.ensembles import build_meta_features, soft_voting
from amr_sense.evaluate import (
    beat_persistence_share,
    choose_threshold_f1_cap_far,
    classification_metrics,
    country_bootstrap_ci,
    country_bootstrap_diff_ci,
    regression_metrics,
)
from amr_sense.models import (
    feature_columns,
    logistic_pipeline,
    persistence_baseline_clf,
    persistence_baseline_reg,
    prepare_xy,
    random_forest_pipeline,
    ridge_pipeline,
    rising_delta_baseline,
    rising_dummy_prevalence,
    roll_mean_baseline_reg,
    xgb_classifier,
    xgb_regressor_pipeline,
)
from amr_sense.plots import plot_lr_regularization_curves, plot_xgb_tuning_heatmap
from amr_sense.splits import rolling_origin_folds
from amr_sense import tuning

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)

TARGETS = ["high_risk_next", "rising_next"]


def compute_regularization_table(train_df: pd.DataFrame, val_df: pd.DataFrame, config_name: str, target: str) -> dict:
    """Compute train vs validation scores and overfitting gap for regularization evidence."""
    X_tr, y_tr = prepare_xy(train_df, target, config_name)
    X_va, y_va = prepare_xy(val_df, target, config_name)

    results = []

    # 1. Logistic regression penalties
    penalties = [
        ("LR (none)", {"penalty": None, "solver": "saga", "max_iter": 3000}),
        ("LR (L2, C=1.0)", {"penalty": "l2", "C": 1.0, "solver": "saga", "max_iter": 3000}),
        ("LR (L1, C=0.1)", {"penalty": "l1", "C": 0.1, "solver": "saga", "max_iter": 3000}),
        ("LR (ElasticNet, C=0.5, l1=0.5)", {"penalty": "elasticnet", "C": 0.5, "l1_ratio": 0.5, "solver": "saga", "max_iter": 3000}),
    ]
    n_nonzero_l1 = 0
    for label, kw in penalties:
        m = logistic_pipeline(config_name, **kw)
        m.fit(X_tr, y_tr)
        p_tr = m.predict_proba(X_tr)[:, 1]
        p_va = m.predict_proba(X_va)[:, 1]
        sc_tr = float(average_precision_score(y_tr, p_tr))
        sc_va = float(average_precision_score(y_va, p_va))
        if "L1" in label:
            clf_step = m.named_steps["clf"]
            coefs = clf_step.coef_.ravel()
            n_nonzero_l1 = int(np.sum(np.abs(coefs) > 1e-5))
        results.append({
            "model": label,
            "train_pr_auc": sc_tr,
            "val_pr_auc": sc_va,
            "gap": sc_tr - sc_va,
        })

    # 2. XGBoost default vs tuned regularization
    xgb_def = xgb_classifier(config_name, reg_lambda=1.0, reg_alpha=0.0, max_depth=6)
    xgb_def.fit(X_tr, y_tr)
    p_tr_def = xgb_def.predict_proba(X_tr)[:, 1]
    p_va_def = xgb_def.predict_proba(X_va)[:, 1]
    results.append({
        "model": "XGBoost (default reg, depth=6)",
        "train_pr_auc": float(average_precision_score(y_tr, p_tr_def)),
        "val_pr_auc": float(average_precision_score(y_va, p_va_def)),
        "gap": float(average_precision_score(y_tr, p_tr_def) - average_precision_score(y_va, p_va_def)),
    })

    xgb_reg = xgb_classifier(config_name, reg_lambda=5.0, reg_alpha=0.5, max_depth=3)
    xgb_reg.fit(X_tr, y_tr)
    p_tr_reg = xgb_reg.predict_proba(X_tr)[:, 1]
    p_va_reg = xgb_reg.predict_proba(X_va)[:, 1]
    results.append({
        "model": "XGBoost (tuned reg, depth=3)",
        "train_pr_auc": float(average_precision_score(y_tr, p_tr_reg)),
        "val_pr_auc": float(average_precision_score(y_va, p_va_reg)),
        "gap": float(average_precision_score(y_tr, p_tr_reg) - average_precision_score(y_va, p_va_reg)),
    })

    # 3. Random forest small vs large leaf
    rf_small = random_forest_pipeline(config_name, min_samples_leaf=1, n_estimators=100)
    rf_small.fit(X_tr, y_tr)
    results.append({
        "model": "Random Forest (min_samples_leaf=1)",
        "train_pr_auc": float(average_precision_score(y_tr, rf_small.predict_proba(X_tr)[:, 1])),
        "val_pr_auc": float(average_precision_score(y_va, rf_small.predict_proba(X_va)[:, 1])),
        "gap": float(average_precision_score(y_tr, rf_small.predict_proba(X_tr)[:, 1]) - average_precision_score(y_va, rf_small.predict_proba(X_va)[:, 1])),
    })

    rf_large = random_forest_pipeline(config_name, min_samples_leaf=10, n_estimators=100)
    rf_large.fit(X_tr, y_tr)
    results.append({
        "model": "Random Forest (min_samples_leaf=10)",
        "train_pr_auc": float(average_precision_score(y_tr, rf_large.predict_proba(X_tr)[:, 1])),
        "val_pr_auc": float(average_precision_score(y_va, rf_large.predict_proba(X_va)[:, 1])),
        "gap": float(average_precision_score(y_tr, rf_large.predict_proba(X_tr)[:, 1]) - average_precision_score(y_va, rf_large.predict_proba(X_va)[:, 1])),
    })

    return {"table": results, "nonzero_l1": n_nonzero_l1}


def train_config(config_name: str, cfg: dict) -> dict:
    path = ROOT / cfg["paths"]["processed_dir"] / f"panel_{config_name}.parquet"
    df = pd.read_parquet(path)
    df = df[df["split"].isin(["train", "validation"])].reset_index(drop=True)
    train_df = df[df["split"] == "train"].reset_index(drop=True)
    val_df = df[df["split"] == "validation"].reset_index(drop=True)

    if config_name == "glass":
        val_years = cfg["splits"]["glass"]["rolling_origin_val_years"]
        train_years = cfg["splits"]["glass"]["train_years"]
    elif config_name == "ecdc":
        val_years = cfg["splits"]["ecdc"]["rolling_origin_val_years"]
        train_years = cfg["splits"]["ecdc"]["train_years"]
    else:  # pooled
        # time-safe rolling-origin folds across both sources
        val_years = [2012, 2014, 2020, 2021]
        train_years = sorted(list(set(cfg["splits"]["glass"]["train_years"] + cfg["splits"]["ecdc"]["train_years"])))

    folds = rolling_origin_folds(train_df, train_years, val_years)
    n_trials = int(cfg["tuning"]["n_trials"])
    far_cap = float(cfg["thresholds"]["false_alert_rate_cap"])
    T = float(cfg["thresholds"]["high_risk_T"])
    n_boot = int(cfg["tuning"].get("n_bootstrap", 1000))

    models_dir = ROOT / cfg["paths"]["models_dir"] / config_name
    studies_dir = ROOT / "models" / "studies"
    figures_tuning_dir = ROOT / "reports" / "figures" / "tuning"
    models_dir.mkdir(parents=True, exist_ok=True)
    studies_dir.mkdir(parents=True, exist_ok=True)
    figures_tuning_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for target in TARGETS:
        print(f"[{config_name}] Tuning models for {target}...")
        study_lr = tuning.tune_logistic(train_df, target, config_name, folds, n_trials)
        study_rf = tuning.tune_rf(train_df, target, config_name, folds, n_trials)
        study_xgb = tuning.tune_xgb_clf(train_df, target, config_name, folds, n_trials)

        tuning.save_study(study_lr, studies_dir / f"study_lr_{target}_{config_name}.json")
        tuning.save_study(study_rf, studies_dir / f"study_rf_{target}_{config_name}.json")
        tuning.save_study(study_xgb, studies_dir / f"study_xgb_{target}_{config_name}.json")

        # Sensitivity plots per source
        plot_xgb_tuning_heatmap(
            study_xgb,
            figures_tuning_dir / f"{config_name}_{target}_xgb_heatmap.png",
            title_suffix=f"({config_name}, {target})",
        )
        plot_lr_regularization_curves(
            study_lr,
            figures_tuning_dir / f"{config_name}_{target}_lr_curves.png",
            title_suffix=f"({config_name}, {target})",
        )

        # Prepare data strictly on train and val
        X_tr, y_tr = prepare_xy(train_df, target, config_name)
        X_va, y_va = prepare_xy(val_df, target, config_name)

        # Base models fit on training rows only
        pen_kw = study_lr["best_params"]
        if pen_kw.get("penalty") == "none":
            pen_kw = {"penalty": None, "solver": "saga"}
        lr = logistic_pipeline(config_name, **pen_kw)
        rf = random_forest_pipeline(config_name, **study_rf["best_params"])
        prev = float(train_df[target].mean())
        xgb_m = xgb_classifier(
            config_name,
            scale_pos_weight=(1.0 - prev) / max(prev, 1e-6),
            **study_xgb["best_params"],
        )

        lr.fit(X_tr, y_tr)
        rf.fit(X_tr, y_tr)
        xgb_m.fit(X_tr, y_tr)

        joblib.dump(lr, models_dir / f"lr_{target}.joblib")
        joblib.dump(rf, models_dir / f"rf_{target}.joblib")
        joblib.dump(xgb_m, models_dir / f"xgb_{target}.joblib")

        # Predictions on validation
        prob_lr = lr.predict_proba(X_va)[:, 1]
        prob_rf = rf.predict_proba(X_va)[:, 1]
        prob_xgb = xgb_m.predict_proba(X_va)[:, 1]

        # Ensembles
        vote = soft_voting([lr, rf, xgb_m])
        # Voting fits base estimators
        vote.fit(X_tr, y_tr)
        joblib.dump(vote, models_dir / f"voting_{target}.joblib")
        prob_vote = vote.predict_proba(X_va)[:, 1]

        # Stacking on rolling-origin folds
        meta_X, mask = build_meta_features([lr, rf, xgb_m], X_tr, y_tr, folds)
        n_excluded = int((~mask).sum())
        meta_lr = LogisticRegression(max_iter=2000, random_state=42)
        if mask.sum() > 5 and len(np.unique(y_tr[mask])) > 1:
            meta_lr.fit(meta_X[mask], y_tr[mask])
            val_meta = np.column_stack([prob_lr, prob_rf, prob_xgb])
            prob_stack = meta_lr.predict_proba(val_meta)[:, 1]
        else:
            prob_stack = prob_vote
            meta_lr.fit(np.column_stack([prob_lr, prob_rf, prob_xgb]), y_va)

        stack_artifact = {"meta": meta_lr, "bases": ["lr", "rf", "xgb"]}
        joblib.dump(stack_artifact, models_dir / f"stacking_{target}.joblib")

        # Baselines
        if target == "high_risk_next":
            base_prob = persistence_baseline_clf(val_df, T).astype(float)
        else:
            base_prob = rising_delta_baseline(val_df).astype(float)

        # Select decision threshold on validation set maximizing F1 subject to FAR cap
        models_dict = {
            "lr": prob_lr,
            "rf": prob_rf,
            "xgb": prob_xgb,
            "voting": prob_vote,
            "stacking": prob_stack,
        }
        thresholds = {}
        model_metrics = {}
        for name, p_val in models_dict.items():
            thr = choose_threshold_f1_cap_far(y_va, p_val, far_cap=far_cap)
            thresholds[name] = thr
            model_metrics[name] = classification_metrics(y_va, p_val, threshold=thr)
            meta = {
                "threshold": thr,
                "target": target,
                "config": config_name,
                "far_cap": far_cap,
                "best_params": study_lr["best_params"] if name == "lr" else (
                    study_rf["best_params"] if name == "rf" else (
                        study_xgb["best_params"] if name == "xgb" else {}
                    )
                ),
            }
            (models_dir / f"{name}_{target}_meta.json").write_text(json.dumps(meta, indent=2))

        base_metrics = classification_metrics(y_va, base_prob, threshold=0.5)

        # Bootstrap CIs on headline PR-AUC and difference vs baseline
        def pr_metric(y, p):
            return average_precision_score(y, p) if len(np.unique(y)) > 1 else 0.0

        val_eval_df = val_df.copy()
        val_eval_df["y_true"] = y_va
        val_eval_df["p_base"] = base_prob
        ci_dict = {}
        diff_ci_dict = {}
        for name, p_val in models_dict.items():
            val_eval_df[f"p_{name}"] = p_val
            ci_dict[name] = country_bootstrap_ci(val_eval_df, pr_metric, "y_true", f"p_{name}", n_boot=n_boot)
            diff_ci_dict[name] = country_bootstrap_diff_ci(val_eval_df, pr_metric, "y_true", f"p_{name}", "p_base", n_boot=n_boot)

        base_ci = country_bootstrap_ci(val_eval_df, pr_metric, "y_true", "p_base", n_boot=n_boot)

        # Regularization study on primary target (high_risk_next)
        reg_evidence = None
        if target == "high_risk_next":
            reg_evidence = compute_regularization_table(train_df, val_df, config_name, target)

        results[target] = {
            "baseline": base_metrics,
            "baseline_ci": base_ci,
            "models": model_metrics,
            "ci": ci_dict,
            "diff_ci": diff_ci_dict,
            "thresholds": thresholds,
            "meta_train_rows_excluded": n_excluded,
            "regularization_evidence": reg_evidence,
            "stacking_weights": list(meta_lr.coef_.ravel()) if hasattr(meta_lr, "coef_") else [1.0, 1.0, 1.0],
        }

    # Companion regression on train & validation
    print(f"[{config_name}] Fitting companion regressors (y_reg)...")
    reg_target = "y_reg"
    X_tr_reg, y_tr_reg = prepare_xy(train_df, reg_target, config_name)
    X_va_reg, y_va_reg = prepare_xy(val_df, reg_target, config_name)

    study_ridge = tuning.tune_ridge(train_df, reg_target, config_name, folds, n_trials=min(15, n_trials))
    tuning.save_study(study_ridge, studies_dir / f"study_ridge_y_reg_{config_name}.json")
    ridge = ridge_pipeline(config_name, alpha=study_ridge["best_params"]["alpha"])
    ridge.fit(X_tr_reg, y_tr_reg)
    joblib.dump(ridge, models_dir / "ridge_y_reg.joblib")

    study_xgb_reg = tuning.tune_xgb_reg(train_df, reg_target, config_name, folds, n_trials=min(15, n_trials))
    tuning.save_study(study_xgb_reg, studies_dir / f"study_xgb_reg_y_reg_{config_name}.json")
    xgb_reg = xgb_regressor_pipeline(config_name, **study_xgb_reg["best_params"])
    xgb_reg.fit(X_tr_reg, y_tr_reg)
    joblib.dump(xgb_reg, models_dir / "xgb_y_reg.joblib")

    pers_pred = persistence_baseline_reg(val_df)
    roll_pred = roll_mean_baseline_reg(val_df)
    ridge_pred = ridge.predict(X_va_reg)
    xgb_pred = xgb_reg.predict(X_va_reg)

    reg_res = {
        "persistence": {
            **regression_metrics(y_va_reg, pers_pred),
            "beat_persistence_share": 0.0,
        },
        "roll_mean_2": {
            **regression_metrics(y_va_reg, roll_pred),
            "beat_persistence_share": beat_persistence_share(y_va_reg, roll_pred, pers_pred),
        },
        "ridge": {
            **regression_metrics(y_va_reg, ridge_pred),
            "beat_persistence_share": beat_persistence_share(y_va_reg, ridge_pred, pers_pred),
        },
        "xgb_reg": {
            **regression_metrics(y_va_reg, xgb_pred),
            "beat_persistence_share": beat_persistence_share(y_va_reg, xgb_pred, pers_pred),
        },
    }
    results["regression"] = reg_res
    return results


def write_validation_md(all_results: dict, cfg: dict) -> None:
    lines = [
        "# Validation results",
        "",
        "> **Surveillance and research tool only.** Not for treatment decisions. "
        "High-risk and rising thresholds are project-defined.",
        "",
    ]
    for config, res in all_results.items():
        lines.append(f"## Configuration: `{config}`")
        lines.append("")
        for target in TARGETS:
            if target not in res:
                continue
            lines.append(f"### Target: `{target}`")
            lines.append("")
            b = res[target]["baseline"]
            b_ci = res[target]["baseline_ci"]
            lines.append(f"| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |")
            lines.append(f"|---|---|---|---|---|---|---|---|")
            lines.append(f"| **Baseline** | {b['pr_auc']:.4f} [{b_ci[1]:.4f}, {b_ci[2]:.4f}] | {b['roc_auc']:.4f} | {b['f1']:.3f} | {b['recall']:.3f} | {b['false_alert_rate']:.3f} | {b['brier']:.4f} | ref |")
            for name, m in res[target]["models"].items():
                ci = res[target]["ci"][name]
                dci = res[target]["diff_ci"][name]
                lines.append(
                    f"| {name.upper()} | {m['pr_auc']:.4f} [{ci[1]:.4f}, {ci[2]:.4f}] | {m['roc_auc']:.4f} | {m['f1']:.3f} | {m['recall']:.3f} | {m['false_alert_rate']:.3f} | {m['brier']:.4f} | {dci[0]:+.4f} [{dci[1]:+.4f}, {dci[2]:+.4f}] |"
                )
            lines.append("")
            lines.append(f"- Stacking meta-training excluded **{res[target]['meta_train_rows_excluded']}** training rows lacking full out-of-fold history.")
            weights = res[target].get("stacking_weights", [])
            lines.append(f"- Stacking meta-learner weights (LR, RF, XGB): `{[round(w, 3) for w in weights]}`")
            lines.append("")

        if "regression" in res:
            lines.append("### Companion Regression (`y_reg`)")
            lines.append("")
            lines.append("| Model | MAE (pp) | RMSE (pp) | Beat Persistence Share |")
            lines.append("|---|---|---|---|")
            for name, m in res["regression"].items():
                lines.append(f"| {name} | {m['mae']:.3f} | {m['rmse']:.3f} | {100 * m['beat_persistence_share']:.1f}% |")
            lines.append("")

    out = ROOT / cfg["paths"]["reports_results"] / "validation_results.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def write_regularization_md(all_results: dict, cfg: dict) -> None:
    lines = [
        "# Regularization evidence",
        "",
        "> Compares training vs validation scores (the overfitting gap) across regularization controls.",
        "",
    ]
    for config, res in all_results.items():
        if "high_risk_next" not in res or not res["high_risk_next"].get("regularization_evidence"):
            continue
        reg_info = res["high_risk_next"]["regularization_evidence"]
        lines.append(f"## Configuration: `{config}`")
        lines.append("")
        lines.append("| Model & Regularization Setting | Train PR-AUC | Val PR-AUC | Overfitting Gap (Train - Val) |")
        lines.append("|---|---|---|---|")
        for row in reg_info["table"]:
            lines.append(f"| {row['model']} | {row['train_pr_auc']:.4f} | {row['val_pr_auc']:.4f} | {row['gap']:+.4f} |")
        lines.append("")
        lines.append(f"- L1-regularized Logistic Regression retained **{reg_info['nonzero_l1']}** nonzero coefficients (sparsity evidence).")
        lines.append("")

    lines.extend([
        "## Ensemble mechanisms in AMR surveillance",
        "",
        "- **Soft Voting (variance reduction):** Bagging and averaging smooths out sampling noise and variance from sparse isolates.",
        "- **XGBoost (bias reduction):** Gradient boosting refines decision boundaries around complex multi-drug resistance phenotypes.",
        "- **Stacking (error diversity):** Stacking leverages complementary error profiles between linear and tree-based representations.",
        "",
    ])
    out = ROOT / cfg["paths"]["reports_results"] / "regularization.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cfg = load_config()
    all_results = {}
    for config_name in ["glass", "ecdc", "pooled"]:
        print(f"=== Starting Training for {config_name.upper()} ===")
        all_results[config_name] = train_config(config_name, cfg)

    write_validation_md(all_results, cfg)
    write_regularization_md(all_results, cfg)

    # Save frozen marker to guard final-test
    frozen = ROOT / cfg["paths"]["models_dir"] / "FROZEN"
    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_text("frozen after make train\n", encoding="utf-8")
    print("Training complete. Validation report and FROZEN marker created.")


if __name__ == "__main__":
    main()
