"""
Comprehensive Evaluation Metrics & Visualization Module for Supervised Classification.
Computes genuine metrics: Accuracy, Macro/Weighted F1, Precision, Recall,
Confusion Matrices, Normalized Confusion Matrices, ROC Curves, and PR Curves.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    auc,
    precision_recall_curve
)
from sklearn.preprocessing import label_binarize


CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


def compute_metrics(
    y_true: Union[List, np.ndarray],
    y_pred: Union[List, np.ndarray],
    y_prob: Optional[np.ndarray] = None,
    classes: List[str] = CLASSES
) -> Dict:
    """
    Computes genuine multi-class classification metrics.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    acc = float(accuracy_score(y_true, y_pred))
    macro_p = float(precision_score(y_true, y_pred, labels=classes, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, labels=classes, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, labels=classes, average="weighted", zero_division=0))

    # Per-class metrics
    p_per = precision_score(y_true, y_pred, labels=classes, average=None, zero_division=0)
    r_per = recall_score(y_true, y_pred, labels=classes, average=None, zero_division=0)
    f1_per = f1_score(y_true, y_pred, labels=classes, average=None, zero_division=0)

    per_class = {}
    for idx, cls_name in enumerate(classes):
        per_class[cls_name] = {
            "precision": float(p_per[idx]),
            "recall": float(r_per[idx]),
            "f1": float(f1_per[idx]),
            "support": int(np.sum(y_true == cls_name))
        }

    # Confusion matrices
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    cm_norm = cm.astype("float") / np.maximum(cm.sum(axis=1)[:, np.newaxis], 1e-9)

    metrics = {
        "accuracy": round(acc, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "normalized_confusion_matrix": np.round(cm_norm, 4).tolist(),
        "total_samples": int(len(y_true))
    }

    # Multiclass ROC-AUC if probabilities available
    if y_prob is not None and y_prob.shape[1] == len(classes):
        try:
            y_bin = label_binarize(y_true, classes=classes)
            roc_aucs = {}
            for i, cls_name in enumerate(classes):
                fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
                roc_aucs[cls_name] = float(auc(fpr, tpr))
            metrics["roc_auc_per_class"] = roc_aucs
            metrics["macro_roc_auc"] = round(float(np.mean(list(roc_aucs.values()))), 4)
        except Exception:
            metrics["macro_roc_auc"] = None

    return metrics


def plot_model_comparison(
    comparison_df: pd.DataFrame,
    save_path: Union[str, Path]
) -> str:
    """
    Plots a multi-bar comparison chart across models for Accuracy, Macro Precision, Recall, and Macro F1.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Melt dataframe for grouped bar plotting
    metric_cols = ["Accuracy", "Macro Precision", "Macro Recall", "Macro F1"]
    melted = comparison_df.melt(id_vars=["Model"], value_vars=metric_cols, var_name="Metric", value_name="Score")

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

    palette = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    sns.barplot(data=melted, x="Model", y="Score", hue="Metric", palette=palette, ax=ax, edgecolor="#222222", linewidth=0.7)

    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            ax.annotate(f"{h:.3f}", (p.get_x() + p.get_width() / 2., h + 0.015),
                        ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#111111")

    ax.set_title("Supervised Model Performance Comparison (Validation)", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score (0.0 to 1.0)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Model Architecture", fontsize=11, fontweight="bold")
    ax.legend(title="Metric", frameon=True, facecolor="white", loc="lower right")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_confusion_matrices(
    cm: np.ndarray,
    cm_norm: np.ndarray,
    classes: List[str],
    title: str,
    save_path: Union[str, Path]
) -> str:
    """
    Generates side-by-side Raw and Normalized Confusion Matrices.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)

    # Raw counts
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=classes, yticklabels=classes,
                ax=ax1, cbar=False, annot_kws={"size": 11, "fontweight": "bold"})
    ax1.set_title("Raw Confusion Matrix", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Actual Label", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Predicted Label", fontsize=10, fontweight="bold")

    # Normalized percentages
    sns.heatmap(cm_norm, annot=True, fmt=".1%", cmap="Blues", xticklabels=classes, yticklabels=classes,
                ax=ax2, cbar=False, annot_kws={"size": 11, "fontweight": "bold"})
    ax2.set_title("Normalized Confusion Matrix (Recall)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Actual Label", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Predicted Label", fontsize=10, fontweight="bold")

    plt.suptitle(title, fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_per_class_performance(
    per_class_dict: Dict,
    classes: List[str],
    model_name: str,
    save_path: Union[str, Path]
) -> str:
    """
    Plots Precision, Recall, and F1 across each fit class.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for cls_name in classes:
        info = per_class_dict[cls_name]
        rows.append({"Class": cls_name, "Metric": "Precision", "Score": info["precision"]})
        rows.append({"Class": cls_name, "Metric": "Recall", "Score": info["recall"]})
        rows.append({"Class": cls_name, "Metric": "F1-Score", "Score": info["f1"]})

    df = pd.DataFrame(rows)

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=300)

    sns.barplot(data=df, x="Class", y="Score", hue="Metric", palette="viridis", ax=ax, edgecolor="#222222", linewidth=0.7)

    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            ax.annotate(f"{h:.2f}", (p.get_x() + p.get_width() / 2., h + 0.015),
                        ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_title(f"Per-Class Performance — {model_name}", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=10, fontweight="bold")
    ax.set_xlabel("Ground Truth Compatibility Class", fontsize=10, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", loc="lower right")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_roc_curves(
    y_true: Union[List, np.ndarray],
    y_prob: np.ndarray,
    classes: List[str],
    model_name: str,
    save_path: Union[str, Path]
) -> str:
    """
    Plots genuine one-vs-rest Multiclass ROC curves with AUC for each class.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    y_bin = label_binarize(y_true, classes=classes)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, ax = plt.subplots(figsize=(7.5, 6), dpi=300)

    for i, cls_name in enumerate(classes):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=colors[i % len(colors)], lw=2,
                label=f"{cls_name} (AUC = {roc_auc:.3f})")

    ax.plot([0, 1], [0, 1], color="#888888", linestyle="--", lw=1.5, label="Random Guess (AUC = 0.500)")
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("False Positive Rate", fontsize=10, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Recall)", fontsize=10, fontweight="bold")
    ax.set_title(f"Multiclass ROC Curves — {model_name}", fontsize=12, fontweight="bold", pad=10)
    ax.legend(loc="lower right", frameon=True, facecolor="white")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_precision_recall_curves(
    y_true: Union[List, np.ndarray],
    y_prob: np.ndarray,
    classes: List[str],
    model_name: str,
    save_path: Union[str, Path]
) -> str:
    """
    Plots genuine Precision-Recall curves for each class.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    y_bin = label_binarize(y_true, classes=classes)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, ax = plt.subplots(figsize=(7.5, 6), dpi=300)

    for i, cls_name in enumerate(classes):
        precision, recall, _ = precision_recall_curve(y_bin[:, i], y_prob[:, i])
        pr_auc = auc(recall, precision)
        ax.plot(recall, precision, color=colors[i % len(colors)], lw=2,
                label=f"{cls_name} (PR-AUC = {pr_auc:.3f})")

    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("Recall", fontsize=10, fontweight="bold")
    ax.set_ylabel("Precision", fontsize=10, fontweight="bold")
    ax.set_title(f"Precision-Recall Curves — {model_name}", fontsize=12, fontweight="bold", pad=10)
    ax.legend(loc="lower left", frameon=True, facecolor="white")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_train_vs_val(
    models: List[str],
    train_f1s: List[float],
    val_f1s: List[float],
    save_path: Union[str, Path]
) -> str:
    """
    Plots Training vs Validation Macro F1 score to visualize generalization gaps.
    """
    out_file = Path(save_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=300)
    b1 = ax.bar(x - width/2, train_f1s, width, label="Training Macro F1", color="#1f77b4", edgecolor="#222")
    b2 = ax.bar(x + width/2, val_f1s, width, label="Validation Macro F1", color="#2ca02c", edgecolor="#222")

    for bar in list(b1) + list(b2):
        h = bar.get_height()
        ax.annotate(f"{h:.3f}", (bar.get_x() + bar.get_width() / 2., h + 0.015),
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_ylabel("Macro F1-Score", fontsize=10, fontweight="bold")
    ax.set_title("Training vs Validation Performance Comparison", fontsize=12, fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=True, facecolor="white")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)
