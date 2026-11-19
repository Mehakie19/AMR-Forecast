#!/usr/bin/env python
"""Generate report figures from the saved GLASS models and temporal data split."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import joblib

from amr_sense.config import load_config
from amr_sense.models import (
    make_preprocessor,
    prepare_xy,
)

TARGET = "high_risk_next"
CONFIG = "glass"
RANDOM_STATE = 42
COEFFICIENT_TOLERANCE = 1e-5
REGULARIZATION_C_VALUES = [0.01, 0.1, 1.0, 10.0]
TREE_DEPTHS: list[int | None] = [1, 2, 3, 5, 8, 12, None]
FIGURE_DIR = ROOT / "reports" / "figures" / "report"


def load_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = ROOT / "data" / "processed" / f"panel_{CONFIG}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing processed panel: {path}. Run scripts/run_features.py first.")
    panel = pd.read_parquet(path)
    splits = {
        name: panel.loc[panel["split"] == name].reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    if any(frame.empty for frame in splits.values()):
        raise ValueError(f"Expected non-empty train, validation, and test splits in {path}.")
    return splits["train"], splits["validation"], splits["test"]


def validate_binary_target(*frames: pd.DataFrame) -> None:
    for frame in frames:
        if TARGET not in frame or frame[TARGET].nunique() != 2:
            raise ValueError(f"{TARGET} must contain both classes in each evaluation split.")


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        fig.savefig(FIGURE_DIR / f"{stem}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_pr_roc(
    test_df: pd.DataFrame,
    x_test: pd.DataFrame,
    y_test: np.ndarray,
    resistance_threshold: float,
) -> None:
    model_dir = ROOT / "models" / CONFIG
    predictions: dict[str, np.ndarray] = {}

    for name in ("lr", "rf", "xgb", "voting"):
        model_path = model_dir / f"{name}_{TARGET}.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"Missing trained model: {model_path}")
        model = joblib.load(model_path)
        predictions[name.upper()] = model.predict_proba(x_test)[:, 1]

    stack_path = model_dir / f"stacking_{TARGET}.joblib"
    if stack_path.exists():
        stack_artifact = joblib.load(stack_path)
        base_probabilities = np.column_stack(
            [predictions["LR"], predictions["RF"], predictions["XGB"]]
        )
        predictions["STACKING"] = stack_artifact["meta"].predict_proba(base_probabilities)[:, 1]

    predictions["Persistence"] = (
        test_df["lag_1"].to_numpy() >= resistance_threshold
    ).astype(float)

    colors = {
        "LR": "#1f77b4",
        "RF": "#ff7f0e",
        "XGB": "#2ca02c",
        "VOTING": "#9467bd",
        "STACKING": "#d62728",
        "Persistence": "#555555",
    }
    fig, (pr_ax, roc_ax) = plt.subplots(1, 2, figsize=(13, 5.2))

    for name, probabilities in predictions.items():
        ap = average_precision_score(y_test, probabilities)
        precision, recall, _ = precision_recall_curve(y_test, probabilities)
        pr_ax.plot(recall, precision, color=colors[name], lw=2, label=f"{name} (AP={ap:.3f})")

        fpr, tpr, _ = roc_curve(y_test, probabilities)
        auc = roc_auc_score(y_test, probabilities)
        roc_ax.plot(fpr, tpr, color=colors[name], lw=2, label=f"{name} (AUC={auc:.3f})")

    prevalence = float(y_test.mean())
    pr_ax.axhline(prevalence, color="grey", linestyle=":", label=f"Prevalence={prevalence:.3f}")
    roc_ax.plot([0, 1], [0, 1], color="grey", linestyle=":")
    pr_ax.set(title="Precision–Recall Curves (GLASS Test Set)", xlabel="Recall", ylabel="Precision")
    roc_ax.set(title="ROC Curves (GLASS Test Set)", xlabel="False Positive Rate", ylabel="True Positive Rate")
    for ax in (pr_ax, roc_ax):
        ax.grid(alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    fig.suptitle("Figure 7.6: PR-AUC and ROC-AUC Model Comparison", fontsize=14)
    fig.tight_layout()
    save_figure(fig, "figure_7_6_pr_roc")


def plot_tree_depth_and_sparsity(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_validation: pd.DataFrame,
    y_validation: np.ndarray,
) -> None:
    depth_rows = []
    for depth in TREE_DEPTHS:
        model = Pipeline(
            [
                ("prep", make_preprocessor(CONFIG, scale=False)),
                (
                    "clf",
                    DecisionTreeClassifier(
                        max_depth=depth,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        )
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_validation)[:, 1]
        depth_rows.append(
            (
                "unlimited" if depth is None else str(depth),
                average_precision_score(y_validation, probabilities),
                roc_auc_score(y_validation, probabilities),
            )
        )

    sparsity_rows: dict[str, list[int]] = {"L1 (Lasso)": [], "L2 (Ridge)": []}
    for l1_ratio, label in ((1.0, "L1 (Lasso)"), (0.0, "L2 (Ridge)")):
        for c_value in REGULARIZATION_C_VALUES:
            model = Pipeline(
                [
                    ("prep", make_preprocessor(CONFIG, scale=True)),
                    (
                        "clf",
                        LogisticRegression(
                            C=c_value,
                            l1_ratio=l1_ratio,
                            solver="saga",
                            class_weight="balanced",
                            max_iter=5000,
                            random_state=RANDOM_STATE,
                        ),
                    ),
                ]
            )
            model.fit(x_train, y_train)
            coefficients = model.named_steps["clf"].coef_.ravel()
            nonzero = int(np.count_nonzero(np.abs(coefficients) > COEFFICIENT_TOLERANCE))
            sparsity_rows[label].append(nonzero)

    fig, (tree_ax, sparse_ax) = plt.subplots(1, 2, figsize=(12, 4.8))
    depth_labels = [row[0] for row in depth_rows]
    tree_ax.plot(depth_labels, [row[1] for row in depth_rows], marker="o", label="Validation PR-AUC")
    tree_ax.plot(depth_labels, [row[2] for row in depth_rows], marker="s", label="Validation ROC-AUC")
    tree_ax.set(
        title="Decision Tree Depth Sensitivity",
        xlabel="Maximum tree depth",
        ylabel="Validation score",
        ylim=(0, 1.02),
    )
    tree_ax.grid(alpha=0.25)
    tree_ax.legend()

    for label, counts in sparsity_rows.items():
        sparse_ax.plot(REGULARIZATION_C_VALUES, counts, marker="o", lw=2, label=label)
    sparse_ax.set_xscale("log")
    sparse_ax.set_xticks(REGULARIZATION_C_VALUES, labels=["0.01", "0.1", "1", "10"])
    sparse_ax.set(
        title="Logistic Regression Coefficient Sparsity",
        xlabel="C (smaller C means stronger regularization)",
        ylabel=f"Non-zero coefficients (|coef| > {COEFFICIENT_TOLERANCE:g})",
    )
    sparse_ax.grid(alpha=0.25)
    sparse_ax.legend()
    fig.suptitle("Figure 7.7: Decision Tree Depth and L1/L2 Sparsity", fontsize=14)
    fig.tight_layout()
    save_figure(fig, "figure_7_7_tree_depth_lasso_sparsity")

    rows = [
        "| Maximum depth | Validation PR-AUC | Validation ROC-AUC |",
        "|---:|---:|---:|",
    ]
    rows.extend(f"| {depth} | {pr_auc:.4f} | {roc_auc:.4f} |" for depth, pr_auc, roc_auc in depth_rows)
    rows.extend(
        [
            "",
            f"Coefficient counts use absolute-value tolerance `{COEFFICIENT_TOLERANCE:g}`.",
            "L1 is the Lasso penalty; L2 is Ridge-type regularization, not Lasso.",
            "Tree depth is a supplementary single-tree diagnostic; the project also compares Random Forest models.",
            "PR/ROC and probability-threshold plots use the held-out GLASS test split. The LR cutoff is selected from validation data.",
            "",
            "| C | L1 non-zero coefficients | L2 non-zero coefficients |",
            "|---:|---:|---:|",
        ]
    )
    rows.extend(
        f"| {c_value:g} | {sparsity_rows['L1 (Lasso)'][index]} | {sparsity_rows['L2 (Ridge)'][index]} |"
        for index, c_value in enumerate(REGULARIZATION_C_VALUES)
    )
    (FIGURE_DIR / "figure_7_7_values.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def plot_probability_threshold_curve(
    y_test: np.ndarray,
    lr_probabilities: np.ndarray,
    selected_threshold: float,
    false_alert_rate_cap: float,
) -> None:
    thresholds = np.linspace(0.01, 0.99, 99)
    precision_values, recall_values, f1_values, far_values = [], [], [], []

    for threshold in thresholds:
        predicted = (lr_probabilities >= threshold).astype(int)
        fp = int(np.sum((predicted == 1) & (y_test == 0)))
        tn = int(np.sum((predicted == 0) & (y_test == 0)))
        precision_values.append(precision_score(y_test, predicted, zero_division=0))
        recall_values.append(recall_score(y_test, predicted, zero_division=0))
        f1_values.append(f1_score(y_test, predicted, zero_division=0))
        far_values.append(fp / (fp + tn) if fp + tn else 0.0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, precision_values, label="Precision", lw=2)
    ax.plot(thresholds, recall_values, label="Recall", lw=2)
    ax.plot(thresholds, f1_values, label="F1-score", lw=2)
    ax.plot(thresholds, far_values, label="False-alert rate", lw=2)
    ax.axhline(
        false_alert_rate_cap,
        color="grey",
        linestyle=":",
        label=f"False-alert-rate cap ({false_alert_rate_cap:.2f})",
    )
    ax.axvline(
        selected_threshold,
        color="#d62728",
        linestyle="--",
        label=f"Validation-selected LR cutoff ({selected_threshold:.2f})",
    )
    ax.set(
        title="Figure 7.8: Probability Decision-Threshold Curve (GLASS Test Set)",
        xlabel="Predicted probability cutoff",
        ylabel="Metric",
        xlim=(0, 1),
        ylim=(0, 1.02),
    )
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    save_figure(fig, "figure_7_8_threshold_curve")


def main() -> None:
    cfg = load_config()
    train_df, validation_df, test_df = load_panel()
    validate_binary_target(train_df, validation_df, test_df)
    x_train, y_train = prepare_xy(train_df, TARGET, CONFIG)
    x_validation, y_validation = prepare_xy(validation_df, TARGET, CONFIG)
    x_test, y_test = prepare_xy(test_df, TARGET, CONFIG)

    plot_pr_roc(test_df, x_test, y_test, float(cfg["thresholds"]["high_risk_T"]))
    plot_tree_depth_and_sparsity(
        x_train,
        y_train,
        x_validation,
        y_validation,
    )

    model_dir = ROOT / "models" / CONFIG
    lr_model = joblib.load(model_dir / f"lr_{TARGET}.joblib")
    lr_probabilities = lr_model.predict_proba(x_test)[:, 1]
    meta_path = model_dir / f"lr_{TARGET}_meta.json"
    selected_threshold = float(json.loads(meta_path.read_text(encoding="utf-8"))["threshold"])
    plot_probability_threshold_curve(
        y_test,
        lr_probabilities,
        selected_threshold,
        float(cfg["thresholds"]["false_alert_rate_cap"]),
    )

    print(f"Report figures written to {FIGURE_DIR}")
    print("Figures: 7.6 PR/ROC, 7.7 tree-depth and L1/L2 sparsity, 7.8 probability threshold.")
    print(f"GLASS LR cutoff selected on validation: {selected_threshold:.2f}")


if __name__ == "__main__":
    main()
