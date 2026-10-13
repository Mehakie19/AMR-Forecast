#!/usr/bin/env python
"""Stage 5: Precompute and export all data artifacts for the API and Streamlit UI into data/ui/."""

from __future__ import annotations

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
from amr_sense.data import load_combined, malta_overlap_table
from amr_sense.evaluate import (
    classification_metrics,
    compute_curves_data,
    country_bootstrap_ci,
    country_bootstrap_diff_ci,
    error_analysis_tables,
    regression_metrics,
    segment_analysis,
)
from amr_sense.features import FEATURE_DEFINITIONS
from amr_sense.models import (
    persistence_baseline_clf,
    persistence_baseline_reg,
    prepare_xy,
    rising_delta_baseline,
)

warnings.filterwarnings("ignore")

SERIES_COLS = ["source", "iso3", "pathogen", "antibiotic"]


def export_ui_data() -> None:
    cfg = load_config()
    ui_dir = ROOT / cfg["paths"]["ui_dir"]
    ui_dir.mkdir(parents=True, exist_ok=True)
    raw = load_combined()
    sg, se = cfg["sources"]["glass"], cfg["sources"]["ecdc"]
    T = float(cfg["thresholds"]["high_risk_T"])

    print("Exporting dataset summaries and coverage...")
    # 1. Dataset summary
    summary = {}
    for label, src in [("glass", sg), ("ecdc", se), ("combined", None)]:
        sub = raw if src is None else raw[raw["source"] == src]
        summary[label] = {
            "source_name": src or "Combined (GLASS-AMR + ECDC-EARSNet)",
            "rows": int(len(sub)),
            "series": int(sub.groupby(SERIES_COLS).ngroups),
            "countries": int(sub["iso3"].nunique()),
            "years": [int(sub["year"].min()), int(sub["year"].max())],
            "pathogens": sorted(sub["pathogen"].unique().tolist()),
            "antibiotics": sorted(sub["antibiotic"].unique().tolist()),
            "n_lt_30_share": float((sub["number_tested"] < 30).mean()),
        }
    (ui_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # 2. Coverage
    cov_df = raw.groupby(["source", "iso3", "country", "year"]).size().reset_index(name="series_count")
    cov_df.to_parquet(ui_dir / "coverage.parquet", index=False)
    (ui_dir / "coverage.json").write_text(json.dumps(cov_df.to_dict(orient="records")), encoding="utf-8")

    # 3. Quality
    dup = int(raw.duplicated(subset=["source", "iso3", "year", "pathogen", "antibiotic"]).sum())
    malta = malta_overlap_table(raw)
    quality = {
        "missingness": raw.isna().sum().astype(int).to_dict(),
        "duplicates": dup,
        "n_lt_30_share": {
            "glass": float((raw[raw["source"] == sg]["number_tested"] < 30).mean()),
            "ecdc": float((raw[raw["source"] == se]["number_tested"] < 30).mean()),
            "combined": float((raw["number_tested"] < 30).mean()),
        },
        "malta_overlap": malta.to_dict(orient="records") if len(malta) else [],
    }
    (ui_dir / "quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")

    # 4. EDA tables
    raw[["source", "pathogen", "antibiotic", "pct_resistant"]].to_parquet(
        ui_dir / "eda_distribution.parquet", index=False
    )

    trends = (
        raw.groupby(["source", "pathogen", "antibiotic", "year"], observed=True)["pct_resistant"]
        .agg(["mean", "median", lambda s: s.quantile(0.25), lambda s: s.quantile(0.75), "count"])
        .reset_index()
    )
    trends.columns = ["source", "pathogen", "antibiotic", "year", "mean", "median", "q25", "q75", "count"]
    trends.to_parquet(ui_dir / "eda_trends.parquet", index=False)

    raw[["source", "iso3", "country", "pathogen", "antibiotic", "year", "number_tested", "pct_resistant"]].to_parquet(
        ui_dir / "eda_sample_size.parquet", index=False
    )

    # Class balance
    cb = {}
    for src_label, src in [("glass", sg), ("ecdc", se)]:
        sub = raw[raw["source"] == src].copy()
        panel_path = ROOT / cfg["paths"]["processed_dir"] / f"panel_{src_label}.parquet"
        if panel_path.exists():
            pdf = pd.read_parquet(panel_path)
            cb[src_label] = {
                "high_risk_20": float((pdf["high_risk_next_20"]).mean()),
                "high_risk_30": float((pdf["high_risk_next_30"]).mean()),
                "high_risk_50": float((pdf["high_risk_next_50"]).mean()),
                "rising_next": float((pdf["rising_next"]).mean()),
                "rows_evaluated": len(pdf),
            }
    (ui_dir / "eda_class_balance.json").write_text(json.dumps(cb, indent=2), encoding="utf-8")

    # Cross-resistance correlations
    corr_dict = {}
    for src_label, src in [("glass", sg), ("ecdc", se)]:
        corr_dict[src_label] = {}
        sub = raw[raw["source"] == src]
        for p in sub["pathogen"].unique():
            wide = sub[sub["pathogen"] == p].pivot_table(
                index=["iso3", "year"], columns="antibiotic", values="pct_resistant", observed=True
            )
            cmat = wide.corr(min_periods=5).fillna(0.0)
            corr_dict[src_label][p] = {
                "antibiotics": list(cmat.columns),
                "matrix": cmat.values.tolist(),
            }
    (ui_dir / "eda_correlations.json").write_text(json.dumps(corr_dict, indent=2), encoding="utf-8")

    # Year-on-year changes
    yoy_dict = {}
    sub_yoy = raw.sort_values(SERIES_COLS + ["year"]).copy()
    sub_yoy["pct_prev"] = sub_yoy.groupby(SERIES_COLS, observed=True)["pct_resistant"].shift(1)
    sub_yoy["yoy"] = sub_yoy["pct_resistant"] - sub_yoy["pct_prev"]
    for src_label, src in [("glass", sg), ("ecdc", se), ("combined", None)]:
        s = sub_yoy if src is None else sub_yoy[sub_yoy["source"] == src]
        yoy_vals = s["yoy"].dropna()
        yoy_dict[src_label] = {
            "mean": float(yoy_vals.mean()),
            "std": float(yoy_vals.std()),
            "share_ge_5": float((yoy_vals >= 5).mean()),
            "by_year": {
                int(yr): float(v)
                for yr, v in s.groupby("year", observed=True)["yoy"].mean().dropna().items()
            },
        }
    (ui_dir / "eda_year_change.json").write_text(json.dumps(yoy_dict, indent=2), encoding="utf-8")

    # 5. Feature dictionary and importance
    (ui_dir / "feature_dictionary.json").write_text(json.dumps(FEATURE_DEFINITIONS, indent=2), encoding="utf-8")

    # Univariate association on train rows
    print("Computing feature importance preview on training rows...")
    feat_imp = []
    panel_pool = ROOT / cfg["paths"]["processed_dir"] / "panel_pooled.parquet"
    if panel_pool.exists():
        pdf = pd.read_parquet(panel_pool)
        train_rows = pdf[pdf["split"] == "train"]
        num_cols = [
            f["name"]
            for f in FEATURE_DEFINITIONS
            if f["name"] in train_rows.columns and pd.api.types.is_numeric_dtype(train_rows[f["name"]])
        ]
        for col in num_cols:
            s = train_rows[col].dropna()
            y_hr = train_rows.loc[s.index, "high_risk_next"]
            y_ris = train_rows.loc[s.index, "rising_next"]
            corr_hr = float(s.corr(y_hr)) if len(s) > 10 else 0.0
            corr_ris = float(s.corr(y_ris)) if len(s) > 10 else 0.0
            feat_imp.append({
                "feature": col,
                "corr_high_risk": corr_hr if not np.isnan(corr_hr) else 0.0,
                "corr_rising": corr_ris if not np.isnan(corr_ris) else 0.0,
                "abs_importance": max(abs(corr_hr), abs(corr_ris)),
            })
        feat_imp.sort(key=lambda x: x["abs_importance"], reverse=True)
    (ui_dir / "feature_importance.json").write_text(json.dumps(feat_imp, indent=2), encoding="utf-8")

    # 6. Model results, curves, segments, errors
    print("Exporting model curves, segments, and error analysis...")
    curves_data = {}
    segments_data = {}
    errors_data = {}
    results_comparison = {"validation": {}, "test": {}}

    for split_type in ["validation", "test"]:
        results_comparison[split_type] = {}
        for config_name in ["glass", "ecdc", "pooled"]:
            p_path = ROOT / cfg["paths"]["processed_dir"] / f"panel_{config_name}.parquet"
            if not p_path.exists():
                continue
            df_split = pd.read_parquet(p_path)
            split_df = df_split[df_split["split"] == split_type].reset_index(drop=True)
            if len(split_df) == 0:
                continue

            models_dir = ROOT / cfg["paths"]["models_dir"] / config_name
            results_comparison[split_type][config_name] = {}

            for target in ["high_risk_next", "rising_next"]:
                results_comparison[split_type][config_name][target] = []
                X_sp, y_sp = prepare_xy(split_df, target, config_name)
                b_prob = persistence_baseline_clf(split_df, T).astype(float) if target == "high_risk_next" else rising_delta_baseline(split_df).astype(float)
                b_met = classification_metrics(y_sp, b_prob, 0.5)
                b_met["model"] = "baseline"
                bootstrap_frame = split_df[["iso3"]].copy()
                bootstrap_frame["y"] = y_sp
                bootstrap_frame["baseline_prob"] = b_prob
                metric = lambda y, p: average_precision_score(y, p) if len(np.unique(y)) > 1 else float("nan")
                b_met["pr_auc_ci"] = list(country_bootstrap_ci(
                    bootstrap_frame.assign(prob=b_prob), metric, "y", "prob",
                    n_boot=int(cfg["tuning"].get("n_bootstrap", 1000)), seed=int(cfg["seed"]),
                ))
                results_comparison[split_type][config_name][target].append(b_met)

                for name in ["lr", "rf", "xgb", "voting", "stacking"]:
                    m_file = models_dir / f"{name}_{target}.joblib"
                    if not m_file.exists():
                        continue
                    m = joblib.load(m_file)
                    thr = 0.5
                    meta_path = models_dir / f"{name}_{target}_meta.json"
                    if meta_path.exists():
                        thr = json.loads(meta_path.read_text()).get("threshold", 0.5)

                    if name == "stacking":
                        lr_m = joblib.load(models_dir / f"lr_{target}.joblib")
                        rf_m = joblib.load(models_dir / f"rf_{target}.joblib")
                        xgb_m = joblib.load(models_dir / f"xgb_{target}.joblib")
                        val_meta = np.column_stack([
                            lr_m.predict_proba(X_sp)[:, 1],
                            rf_m.predict_proba(X_sp)[:, 1],
                            xgb_m.predict_proba(X_sp)[:, 1],
                        ])
                        prob = m["meta"].predict_proba(val_meta)[:, 1]
                    else:
                        prob = m.predict_proba(X_sp)[:, 1]

                    met = classification_metrics(y_sp, prob, thr)
                    met["model"] = name
                    met["threshold"] = thr
                    bootstrap_frame["model_prob"] = prob
                    met["pr_auc_ci"] = list(country_bootstrap_ci(
                        bootstrap_frame, metric, "y", "model_prob",
                        n_boot=int(cfg["tuning"].get("n_bootstrap", 1000)),
                        seed=int(cfg["seed"]),
                    ))
                    met["diff_ci"] = list(country_bootstrap_diff_ci(
                        bootstrap_frame, metric, "y", "model_prob", "baseline_prob",
                        n_boot=int(cfg["tuning"].get("n_bootstrap", 1000)),
                        seed=int(cfg["seed"]),
                    ))
                    results_comparison[split_type][config_name][target].append(met)

                    # Curves data for validation
                    if split_type == "validation":
                        curve_key = f"{config_name}_{target}_{name}"
                        curves_data[curve_key] = compute_curves_data(y_sp, prob, thr)

                    # Segments and error analysis for best model (xgb or lr)
                    if name in ["xgb", "lr"] and split_type == "validation":
                        split_df[f"prob_{target}"] = prob
                        seg_key = f"{config_name}_{target}"
                        segments_data[seg_key] = segment_analysis(split_df, target, f"prob_{target}", thr)

            # Companion regressors are part of the same served comparison contract.
            results_comparison[split_type][config_name]["y_reg"] = []
            X_reg, y_reg = prepare_xy(split_df, "y_reg", config_name)
            y_reg = np.asarray(y_reg, dtype=float)
            reg_candidates = [("persistence", split_df["lag_1"].to_numpy(dtype=float))]
            roll_col = "roll_mean_2"
            if roll_col in split_df:
                reg_candidates.append(("roll_mean_2", split_df[roll_col].to_numpy(dtype=float)))
            for reg_name, model_file in [("ridge", "ridge_y_reg.joblib"), ("xgb_reg", "xgb_y_reg.joblib")]:
                reg_path = models_dir / model_file
                if reg_path.exists():
                    reg_model = joblib.load(reg_path)
                    reg_candidates.append((reg_name, reg_model.predict(X_reg)))
            for reg_name, reg_pred in reg_candidates:
                reg_met = regression_metrics(y_reg, np.asarray(reg_pred, dtype=float))
                reg_met["model"] = reg_name
                reg_met["beat_persistence_share"] = float(np.mean(
                    np.abs(y_reg - np.asarray(reg_pred, dtype=float)) < np.abs(y_reg - split_df["lag_1"].to_numpy(dtype=float))
                ))
                results_comparison[split_type][config_name]["y_reg"].append(reg_met)

            # Regression errors
            ridge_file = models_dir / "ridge_y_reg.joblib"
            if ridge_file.exists() and split_type == "validation":
                ridge_m = joblib.load(ridge_file)
                X_reg, _ = prepare_xy(split_df, "y_reg", config_name)
                pred_reg = ridge_m.predict(X_reg)
                split_df["pred_reg"] = pred_reg
                target_clf = "high_risk_next"
                prob_col = f"prob_{target_clf}" if f"prob_{target_clf}" in split_df.columns else "lag_1"
                errors_data[config_name] = error_analysis_tables(
                    split_df, target_clf, prob_col, "y_reg", "pred_reg"
                )

    (ui_dir / "model_results_validation.json").write_text(
        json.dumps(results_comparison["validation"], indent=2), encoding="utf-8"
    )
    (ui_dir / "model_results_test.json").write_text(
        json.dumps(results_comparison["test"], indent=2), encoding="utf-8"
    )
    (ui_dir / "curves.json").write_text(json.dumps(curves_data, indent=2), encoding="utf-8")
    (ui_dir / "segments.json").write_text(json.dumps(segments_data, indent=2), encoding="utf-8")
    (ui_dir / "errors.json").write_text(json.dumps(errors_data, indent=2), encoding="utf-8")

    # 7. Watchlist table with latest observed year and predictions
    print("Generating surveillance watchlist table...")
    watchlist_rows = []
    # Load pooled models for generating next-year forecasts on latest year
    pooled_dir = ROOT / cfg["paths"]["models_dir"] / "pooled"
    has_models = (pooled_dir / "lr_high_risk_next.joblib").exists()

    if has_models:
        lr_hr = joblib.load(pooled_dir / "lr_high_risk_next.joblib")
        lr_ris = joblib.load(pooled_dir / "lr_rising_next.joblib")
        ridge_reg = joblib.load(pooled_dir / "ridge_y_reg.joblib")
        thr_hr = 0.5
        thr_ris = 0.5
        m_hr = pooled_dir / "lr_high_risk_next_meta.json"
        m_ris = pooled_dir / "lr_rising_next_meta.json"
        if m_hr.exists():
            thr_hr = json.loads(m_hr.read_text()).get("threshold", 0.5)
        if m_ris.exists():
            thr_ris = json.loads(m_ris.read_text()).get("threshold", 0.5)

    # Use panel_pooled for latest year
    panel_p = pd.read_parquet(ROOT / cfg["paths"]["processed_dir"] / "panel_pooled.parquet")
    for key, g in panel_p.groupby(SERIES_COLS, observed=True):
        g = g.sort_values("year")
        last_row = g.iloc[-1]
        source_val, iso3_val, path_val, ab_val = key

        fc_pct = float(last_row["pct_resistant"])
        hr_prob = 0.0
        ris_prob = 0.0
        if has_models:
            X_row, _ = prepare_xy(pd.DataFrame([last_row]), "high_risk_next", "pooled")
            hr_prob = float(lr_hr.predict_proba(X_row)[0, 1])
            ris_prob = float(lr_ris.predict_proba(X_row)[0, 1])
            fc_pct = float(ridge_reg.predict(X_row)[0])

        n_tested = float(last_row.get("number_tested_prev", last_row.get("number_tested", 50)))
        low_sample = bool(n_tested < 30)

        watchlist_rows.append({
            "source": str(source_val),
            "iso3": str(iso3_val),
            "country": str(last_row.get("country", iso3_val)),
            "pathogen": str(path_val),
            "antibiotic": str(ab_val),
            "latest_year": int(last_row["year"]),
            "latest_resistance_pct": float(last_row["pct_resistant"]),
            "number_tested": float(last_row["number_tested"]),
            "forecast_pct": round(float(fc_pct), 1),
            "high_risk_probability": round(float(hr_prob), 3),
            "rising_probability": round(float(ris_prob), 3),
            "exceeds_high_risk": bool(hr_prob >= thr_hr),
            "exceeds_rising": bool(ris_prob >= thr_ris),
            "low_sample_flag": low_sample,
            "data_quality_flag": "Low Sample (<30)" if low_sample else "OK",
        })

    wl_df = pd.DataFrame(watchlist_rows)
    wl_df.to_parquet(ui_dir / "watchlist.parquet", index=False)

    # 8. Limitations & Methods
    limitations = [
        "Six-year GLASS history only (2018-2023), limiting depth of longitudinal features.",
        "GLASS countries reflect a reporting filter (better-reporting countries overrepresented).",
        "Thresholds for 'high risk' (30%) and 'rising' (>=5 pp, z-test p<0.05) are project-defined, not clinical cure guidelines.",
        "Measurement definition mismatch: ECDC uses I+R; GLASS uses R as reported — levels must not be compared directly.",
        "Small held-out test sets (especially GLASS 2023 single-year slice) increase metric variance; paired country bootstrap CIs are provided.",
        "Mild temporal overlap between pooled training (GLASS 2019-2021) and held-out ECDC test (2018-2019).",
    ]
    (ui_dir / "limitations.json").write_text(json.dumps(limitations, indent=2), encoding="utf-8")

    methods_doc = {
        "definitions": {
            "high_risk_next": "1 if next-year resistance >= 30% (project-defined threshold, sensitivity at 20% and 50%).",
            "rising_next": "1 if next-year resistance rises >= 5 pp AND one-sided 2-proportion z-test p < 0.05 AND sample >= 30 in both years.",
            "y_reg": "Continuous next-year resistance percentage.",
        },
        "thresholds": cfg["thresholds"],
        "splits": cfg["splits"],
        "limitations": limitations,
        "phase2_roadmap": [
            "SHAP value explanations for feature attribution",
            "Conformal prediction intervals with formal coverage guarantees",
            "Spatial clustering and transfer learning experiments",
            "Isolation Forest multivariate anomaly detection",
            "CUSUM and change-point surveillance alerts",
            "Automated feature group ablation studies",
        ],
    }
    (ui_dir / "methods.json").write_text(json.dumps(methods_doc, indent=2), encoding="utf-8")

    print(f"UI data export complete! All files saved in {ui_dir}")


def main() -> None:
    export_ui_data()


if __name__ == "__main__":
    main()
