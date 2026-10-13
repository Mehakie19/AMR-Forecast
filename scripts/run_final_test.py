#!/usr/bin/env python
"""Stage 4 final test evaluation (guarded by models/FROZEN marker; evaluated once)."""

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
from sklearn.metrics import average_precision_score

from amr_sense.config import load_config
from amr_sense.evaluate import (
    beat_persistence_share,
    classification_metrics,
    country_bootstrap_ci,
    country_bootstrap_diff_ci,
    error_analysis_tables,
    regression_metrics,
    segment_analysis,
)
from amr_sense.models import (
    persistence_baseline_clf,
    persistence_baseline_reg,
    prepare_xy,
    rising_delta_baseline,
    roll_mean_baseline_reg,
)

warnings.filterwarnings("ignore")

TARGETS = ["high_risk_next", "rising_next"]


def evaluate_final_test() -> None:
    cfg = load_config()
    frozen = ROOT / cfg["paths"]["models_dir"] / "FROZEN"
    if not frozen.exists():
        raise SystemExit("Refusing final-test: models/FROZEN missing. Run `make train` first.")

    T = float(cfg["thresholds"]["high_risk_T"])
    n_boot = int(cfg["tuning"].get("n_bootstrap", 1000))
    sg, se = cfg["sources"]["glass"], cfg["sources"]["ecdc"]

    lines = [
        "# Final test results",
        "",
        "> **Guarded one-shot evaluation on final held-out test year(s).**",
        "> Models and decision thresholds were frozen before this run.",
        "",
    ]

    all_test_metrics = {}
    pooled_vs_separate_data = []

    def pr_metric(y, p):
        return average_precision_score(y, p) if len(np.unique(y)) > 1 else 0.0

    for config_name in ["glass", "ecdc", "pooled"]:
        panel_path = ROOT / cfg["paths"]["processed_dir"] / f"panel_{config_name}.parquet"
        df = pd.read_parquet(panel_path)
        test_df = df[df["split"] == "test"].reset_index(drop=True)
        if len(test_df) == 0:
            continue

        models_dir = ROOT / cfg["paths"]["models_dir"] / config_name
        lines.append(f"## Configuration: `{config_name.upper()}`")
        lines.append(f"Test row count: **{len(test_df)}** (Target years: {sorted(test_df['year'].unique().tolist())})")
        lines.append("")

        config_results = {}

        for target in TARGETS:
            print(f"[{config_name}] evaluating target: {target}...", flush=True)
            lines.append(f"### Target: `{target}`")
            lines.append("")
            X_te, y_te = prepare_xy(test_df, target, config_name)

            if target == "high_risk_next":
                base_prob = persistence_baseline_clf(test_df, T).astype(float)
            else:
                base_prob = rising_delta_baseline(test_df).astype(float)

            base_metrics = classification_metrics(y_te, base_prob, threshold=0.5)

            # Load models
            lr = joblib.load(models_dir / f"lr_{target}.joblib")
            rf = joblib.load(models_dir / f"rf_{target}.joblib")
            xgb_m = joblib.load(models_dir / f"xgb_{target}.joblib")
            voting = joblib.load(models_dir / f"voting_{target}.joblib")
            stack_artifact = joblib.load(models_dir / f"stacking_{target}.joblib")

            prob_lr = lr.predict_proba(X_te)[:, 1]
            prob_rf = rf.predict_proba(X_te)[:, 1]
            prob_xgb = xgb_m.predict_proba(X_te)[:, 1]
            prob_vote = voting.predict_proba(X_te)[:, 1]

            val_meta = np.column_stack([prob_lr, prob_rf, prob_xgb])
            meta_lr = stack_artifact["meta"]
            prob_stack = meta_lr.predict_proba(val_meta)[:, 1]

            models_dict = {
                "lr": prob_lr,
                "rf": prob_rf,
                "xgb": prob_xgb,
                "voting": prob_vote,
                "stacking": prob_stack,
            }

            lines.append("| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |")
            lines.append("|---|---|---|---|---|---|---|---|")

            test_eval_df = test_df.copy()
            test_eval_df["y_true"] = y_te
            test_eval_df["p_base"] = base_prob

            base_ci = country_bootstrap_ci(test_eval_df, pr_metric, "y_true", "p_base", n_boot=n_boot)
            lines.append(f"| **Baseline** | {base_metrics['pr_auc']:.4f} [{base_ci[1]:.4f}, {base_ci[2]:.4f}] | {base_metrics['roc_auc']:.4f} | {base_metrics['f1']:.3f} | {base_metrics['recall']:.3f} | {base_metrics['false_alert_rate']:.3f} | {base_metrics['brier']:.4f} | ref |")

            target_models_res = {}
            for name, prob in models_dict.items():
                test_eval_df[f"p_{name}"] = prob
                meta_path = models_dir / f"{name}_{target}_meta.json"
                thr = 0.5
                if meta_path.exists():
                    thr = json.loads(meta_path.read_text()).get("threshold", 0.5)

                m = classification_metrics(y_te, prob, threshold=thr)
                ci = country_bootstrap_ci(test_eval_df, pr_metric, "y_true", f"p_{name}", n_boot=n_boot)
                dci = country_bootstrap_diff_ci(test_eval_df, pr_metric, "y_true", f"p_{name}", "p_base", n_boot=n_boot)
                m["pr_auc_ci"] = ci
                m["diff_ci"] = dci
                target_models_res[name] = m
                lines.append(
                    f"| {name.upper()} | {m['pr_auc']:.4f} [{ci[1]:.4f}, {ci[2]:.4f}] | {m['roc_auc']:.4f} | {m['f1']:.3f} | {m['recall']:.3f} | {m['false_alert_rate']:.3f} | {m['brier']:.4f} | {dci[0]:+.4f} [{dci[1]:+.4f}, {dci[2]:+.4f}] |"
                )

            lines.append("")
            config_results[target] = target_models_res

        # Companion Regression
        lines.append("### Companion Regression (`y_reg`)")
        lines.append("")
        y_te_reg = test_df["y_reg"].values
        pers_pred = persistence_baseline_reg(test_df)
        roll_pred = roll_mean_baseline_reg(test_df)
        X_reg, _ = prepare_xy(test_df, "y_reg", config_name)
        ridge = joblib.load(models_dir / "ridge_y_reg.joblib")
        xgb_reg = joblib.load(models_dir / "xgb_y_reg.joblib")
        ridge_pred = ridge.predict(X_reg)
        xgb_pred = xgb_reg.predict(X_reg)

        lines.append("| Model | MAE (pp) | RMSE (pp) | Beat Persistence Share |")
        lines.append("|---|---|---|---|")
        reg_models = [
            ("Persistence", pers_pred),
            ("Roll Mean 2", roll_pred),
            ("Ridge", ridge_pred),
            ("XGBoost Regressor", xgb_pred),
        ]
        for name, pred in reg_models:
            m = regression_metrics(y_te_reg, pred)
            bps = beat_persistence_share(y_te_reg, pred, pers_pred) if name != "Persistence" else 0.0
            lines.append(f"| {name} | {m['mae']:.3f} | {m['rmse']:.3f} | {100 * bps:.1f}% |")
        lines.append("")

        all_test_metrics[config_name] = config_results

    # Pooled vs Separate Comparison on exact same test slices
    lines.append("## Pooled vs Separate Comparison (on same test slices)")
    lines.append("")
    lines.append("> Evaluates whether pooling ECDC and GLASS surveillance improved next-year alert precision on each source's held-out test data.")
    lines.append("")

    pooled_df = pd.read_parquet(ROOT / cfg["paths"]["processed_dir"] / "panel_pooled.parquet")
    glass_df = pd.read_parquet(ROOT / cfg["paths"]["processed_dir"] / "panel_glass.parquet")
    ecdc_df = pd.read_parquet(ROOT / cfg["paths"]["processed_dir"] / "panel_ecdc.parquet")

    pooled_models_dir = ROOT / cfg["paths"]["models_dir"] / "pooled"
    glass_models_dir = ROOT / cfg["paths"]["models_dir"] / "glass"
    ecdc_models_dir = ROOT / cfg["paths"]["models_dir"] / "ecdc"

    lines.append("| Test Slice | Target | Separate Model PR-AUC (95% CI) | Pooled Model PR-AUC (95% CI) | Difference (Pooled - Sep) [95% CI] | Verdict |")
    lines.append("|---|---|---|---|---|---|")

    for target in TARGETS:
        # 1. GLASS 2023 slice
        test_glass = glass_df[glass_df["split"] == "test"].reset_index(drop=True)
        test_glass_pooled = pooled_df[(pooled_df["source"] == sg) & (pooled_df["split"] == "test")].reset_index(drop=True)

        if len(test_glass) and len(test_glass_pooled):
            X_sep, y_sep = prepare_xy(test_glass, target, "glass")
            X_pool, y_pool = prepare_xy(test_glass_pooled, target, "pooled")

            lr_sep = joblib.load(glass_models_dir / f"lr_{target}.joblib")
            lr_pool = joblib.load(pooled_models_dir / f"lr_{target}.joblib")

            p_sep = lr_sep.predict_proba(X_sep)[:, 1]
            p_pool = lr_pool.predict_proba(X_pool)[:, 1]

            eval_df_g = test_glass.copy()
            eval_df_g["y"] = y_sep
            eval_df_g["p_sep"] = p_sep
            eval_df_g["p_pool"] = p_pool

            ci_sep = country_bootstrap_ci(eval_df_g, pr_metric, "y", "p_sep", n_boot=n_boot)
            ci_pool = country_bootstrap_ci(eval_df_g, pr_metric, "y", "p_pool", n_boot=n_boot)
            diff_ci = country_bootstrap_diff_ci(eval_df_g, pr_metric, "y", "p_pool", "p_sep", n_boot=n_boot)

            verdict = "No significant difference"
            if diff_ci[1] > 0:
                verdict = "Pooling significantly helped"
            elif diff_ci[2] < 0:
                verdict = "Pooling significantly hurt"

            lines.append(
                f"| GLASS (2023) | {target} | {ci_sep[0]:.4f} [{ci_sep[1]:.4f}, {ci_sep[2]:.4f}] | {ci_pool[0]:.4f} [{ci_pool[1]:.4f}, {ci_pool[2]:.4f}] | {diff_ci[0]:+.4f} [{diff_ci[1]:+.4f}, {diff_ci[2]:+.4f}] | {verdict} |"
            )

        # 2. ECDC 2018-2019 slice
        test_ecdc = ecdc_df[ecdc_df["split"] == "test"].reset_index(drop=True)
        test_ecdc_pooled = pooled_df[(pooled_df["source"] == se) & (pooled_df["split"] == "test")].reset_index(drop=True)

        if len(test_ecdc) and len(test_ecdc_pooled):
            X_sep, y_sep = prepare_xy(test_ecdc, target, "ecdc")
            X_pool, y_pool = prepare_xy(test_ecdc_pooled, target, "pooled")

            lr_sep = joblib.load(ecdc_models_dir / f"lr_{target}.joblib")
            lr_pool = joblib.load(pooled_models_dir / f"lr_{target}.joblib")

            p_sep = lr_sep.predict_proba(X_sep)[:, 1]
            p_pool = lr_pool.predict_proba(X_pool)[:, 1]

            eval_df_e = test_ecdc.copy()
            eval_df_e["y"] = y_sep
            eval_df_e["p_sep"] = p_sep
            eval_df_e["p_pool"] = p_pool

            ci_sep = country_bootstrap_ci(eval_df_e, pr_metric, "y", "p_sep", n_boot=n_boot)
            ci_pool = country_bootstrap_ci(eval_df_e, pr_metric, "y", "p_pool", n_boot=n_boot)
            diff_ci = country_bootstrap_diff_ci(eval_df_e, pr_metric, "y", "p_pool", "p_sep", n_boot=n_boot)

            verdict = "No significant difference"
            if diff_ci[1] > 0:
                verdict = "Pooling significantly helped"
            elif diff_ci[2] < 0:
                verdict = "Pooling significantly hurt"

            lines.append(
                f"| ECDC (2018-2019) | {target} | {ci_sep[0]:.4f} [{ci_sep[1]:.4f}, {ci_sep[2]:.4f}] | {ci_pool[0]:.4f} [{ci_pool[1]:.4f}, {ci_pool[2]:.4f}] | {diff_ci[0]:+.4f} [{diff_ci[1]:+.4f}, {diff_ci[2]:+.4f}] | {verdict} |"
            )

    lines.append("")

    # Threshold sensitivity experiment on T = 20, 30, 50
    lines.append("## Threshold sensitivity experiment (T in {20, 30, 50})")
    lines.append("")
    lines.append("| Configuration | Threshold T | Prevalence | Persistence PR-AUC | LR PR-AUC | XGBoost PR-AUC |")
    lines.append("|---|---|---|---|---|---|")
    for config_name in ["glass", "ecdc", "pooled"]:
        df_p = pd.read_parquet(ROOT / cfg["paths"]["processed_dir"] / f"panel_{config_name}.parquet")
        te_p = df_p[df_p["split"] == "test"].reset_index(drop=True)
        if len(te_p) == 0:
            continue
        models_dir = ROOT / cfg["paths"]["models_dir"] / config_name
        lr_m = joblib.load(models_dir / "lr_high_risk_next.joblib")
        xgb_m = joblib.load(models_dir / "xgb_high_risk_next.joblib")
        X_p, _ = prepare_xy(te_p, "high_risk_next", config_name)
        prob_lr = lr_m.predict_proba(X_p)[:, 1]
        prob_xgb = xgb_m.predict_proba(X_p)[:, 1]

        for T_val in [20, 30, 50]:
            y_col = f"high_risk_next_{T_val}"
            if y_col in te_p.columns:
                y_true = te_p[y_col].values
            else:
                y_true = (te_p["pct_resistant"] >= T_val).astype(int).values
            prev = float(y_true.mean())
            p_pers = (te_p["lag_1"] >= T_val).astype(float).values
            sc_pers = float(average_precision_score(y_true, p_pers)) if len(np.unique(y_true)) > 1 else float("nan")
            sc_lr = float(average_precision_score(y_true, prob_lr)) if len(np.unique(y_true)) > 1 else float("nan")
            sc_xgb = float(average_precision_score(y_true, prob_xgb)) if len(np.unique(y_true)) > 1 else float("nan")
            lines.append(f"| {config_name.upper()} | T={T_val}% | {100 * prev:.1f}% | {sc_pers:.4f} | {sc_lr:.4f} | {sc_xgb:.4f} |")
    lines.append("")

    out_file = ROOT / cfg["paths"]["reports_results"] / "test_results.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Final test evaluation complete. Results written to {out_file}")


def main() -> None:
    evaluate_final_test()


if __name__ == "__main__":
    main()
