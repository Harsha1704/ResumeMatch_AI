"""
src/phase12f/evaluation.py
Comprehensive ML Evaluation & Clustered Statistical Verification Suite.
Calculates Accuracy, Balanced Accuracy, Macro F1, Weighted F1, Per-Class metrics,
Expected Calibration Error (ECE), Brier Score, and Clustered Bootstrap 95% Confidence Intervals.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    brier_score_loss
)

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


def compute_expected_calibration_error(y_true_indices: np.ndarray, y_probs: np.ndarray, n_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE) across multi-class predictions.
    """
    confidences = np.max(y_probs, axis=1)
    predictions = np.argmax(y_probs, axis=1)
    accuracies = (predictions == y_true_indices)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def compute_comprehensive_metrics(
    y_true: List[str],
    y_pred: List[str],
    y_prob: Optional[np.ndarray] = None,
    classes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Computes all standard and scientific evaluation metrics.
    """
    classes = classes or CLASSES
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    macro_f1 = float(f1_score(y_true_arr, y_pred_arr, average="macro", labels=classes, zero_division=0))
    weighted_f1 = float(f1_score(y_true_arr, y_pred_arr, average="weighted", labels=classes, zero_division=0))
    macro_prec = float(precision_score(y_true_arr, y_pred_arr, average="macro", labels=classes, zero_division=0))
    macro_rec = float(recall_score(y_true_arr, y_pred_arr, average="macro", labels=classes, zero_division=0))

    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=classes).tolist()

    per_class = {}
    for c in classes:
        mask_true = (y_true_arr == c)
        mask_pred = (y_pred_arr == c)
        p = float(precision_score(mask_true, mask_pred, zero_division=0))
        r = float(recall_score(mask_true, mask_pred, zero_division=0))
        f = float(f1_score(mask_true, mask_pred, zero_division=0))
        sup = int(np.sum(mask_true))
        per_class[c] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
            "support": sup
        }

    metrics: Dict[str, Any] = {
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "confusion_matrix": cm,
        "per_class": per_class
    }

    if y_prob is not None:
        y_int = np.array([classes.index(y) for y in y_true])
        ece = compute_expected_calibration_error(y_int, y_prob)
        metrics["expected_calibration_error"] = round(ece, 4)

        # Multi-class Brier score
        one_hot = np.zeros_like(y_prob)
        for i, idx in enumerate(y_int):
            one_hot[i, idx] = 1.0
        brier = float(np.mean(np.sum((y_prob - one_hot) ** 2, axis=1)))
        metrics["brier_score"] = round(brier, 4)

    return metrics


def compute_clustered_bootstrap_ci(
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    cluster_col: str = "job_hash",
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    random_state: int = 42
) -> Dict[str, Tuple[float, float]]:
    """
    Computes two-way clustered bootstrap confidence intervals by resampling entire clusters
    with replacement to properly account for intra-cluster correlation.
    """
    unique_clusters = df[cluster_col].unique()
    n_clusters = len(unique_clusters)
    rng = np.random.RandomState(random_state)

    boot_accs = []
    boot_macro_f1s = []
    boot_bal_accs = []

    # Precompute cluster-to-indices mapping for fast bootstrapping
    cluster_series = df[cluster_col]
    cluster_to_indices = {c: np.where(cluster_series == c)[0] for c in unique_clusters}
    y_t_arr = df[y_true_col].values
    y_p_arr = df[y_pred_col].values

    for _ in range(n_bootstraps):
        sampled_clusters = rng.choice(unique_clusters, size=n_clusters, replace=True)
        selected_indices = np.concatenate([cluster_to_indices[c] for c in sampled_clusters])

        y_t = y_t_arr[selected_indices]
        y_p = y_p_arr[selected_indices]

        boot_accs.append(accuracy_score(y_t, y_p))
        boot_macro_f1s.append(f1_score(y_t, y_p, average="macro", labels=CLASSES, zero_division=0))
        boot_bal_accs.append(balanced_accuracy_score(y_t, y_p))

    alpha = (1.0 - ci) / 2.0
    lower_idx = int(n_bootstraps * alpha)
    upper_idx = int(n_bootstraps * (1.0 - alpha))

    acc_ci = (round(float(np.percentile(boot_accs, 100 * alpha)), 4), round(float(np.percentile(boot_accs, 100 * (1.0 - alpha))), 4))
    f1_ci = (round(float(np.percentile(boot_macro_f1s, 100 * alpha)), 4), round(float(np.percentile(boot_macro_f1s, 100 * (1.0 - alpha))), 4))
    bal_ci = (round(float(np.percentile(boot_bal_accs, 100 * alpha)), 4), round(float(np.percentile(boot_bal_accs, 100 * (1.0 - alpha))), 4))

    return {
        "accuracy_ci": acc_ci,
        "macro_f1_ci": f1_ci,
        "balanced_accuracy_ci": bal_ci
    }
