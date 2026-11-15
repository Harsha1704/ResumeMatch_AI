"""
src/phase12f/pseudo_labeling.py
Confidence-Gated Pseudo-Labeling & Self-Training Manager.
Implements calibrated thresholding, multi-model consensus, uncertainty filtering,
class-balance caps, and strict test-set isolation guards.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator


class ConfidenceGatedPseudoLabeler:
    """
    Manages self-training and pseudo-labeling with strict quality and leakage gates.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.85,
        margin_threshold: float = 0.35,
        max_class_imbalance: float = 0.45,
        min_agreement_models: int = 2
    ):
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold
        self.max_class_imbalance = max_class_imbalance
        self.min_agreement_models = min_agreement_models
        self.classes = ["No Fit", "Potential Fit", "Good Fit"]

    def filter_pseudo_labels(
        self,
        candidate_df: pd.DataFrame,
        model_1_probs: np.ndarray,
        model_2_probs: np.ndarray,
        test_resume_hashes: set,
        test_job_hashes: set,
        hash_fn
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Filters pseudo-labels using:
        1. Multi-model consensus (Model 1 argmax == Model 2 argmax)
        2. High confidence threshold (prob >= confidence_threshold)
        3. Confidence margin (top1_prob - top2_prob >= margin_threshold)
        4. Test set entity isolation (0% resume or job overlap with test sets)
        5. Class balance cap (prevents single-class collapse)
        """
        N = len(candidate_df)
        assert len(model_1_probs) == N and len(model_2_probs) == N, "Probability lengths must match candidates!"

        m1_preds = np.argmax(model_1_probs, axis=1)
        m2_preds = np.argmax(model_2_probs, axis=1)

        # Average probabilities across the two models
        ensemble_probs = (model_1_probs + model_2_probs) / 2.0
        top_probs = np.max(ensemble_probs, axis=1)

        # Compute margin between top 1 and top 2
        sorted_probs = np.sort(ensemble_probs, axis=1)
        margins = sorted_probs[:, -1] - sorted_probs[:, -2]

        admitted_indices = []
        rejection_reasons = {
            "model_disagreement": 0,
            "low_confidence": 0,
            "low_margin": 0,
            "test_overlap_leakage": 0,
            "class_cap_exceeded": 0
        }

        # Track class admissions for class balance
        class_counts = {c: 0 for c in self.classes}

        for i in range(N):
            row = candidate_df.iloc[i]

            # 1. Consensus check
            if m1_preds[i] != m2_preds[i]:
                rejection_reasons["model_disagreement"] += 1
                continue

            pred_class = self.classes[m1_preds[i]]
            conf = top_probs[i]
            margin = margins[i]

            # 2. Confidence threshold
            if conf < self.confidence_threshold:
                rejection_reasons["low_confidence"] += 1
                continue

            # 3. Margin threshold
            if margin < self.margin_threshold:
                rejection_reasons["low_margin"] += 1
                continue

            # 4. Leakage check
            r_hash = hash_fn(row["resume_text"])
            j_hash = hash_fn(row["job_description_text"])
            if r_hash in test_resume_hashes or j_hash in test_job_hashes:
                rejection_reasons["test_overlap_leakage"] += 1
                continue

            admitted_indices.append((i, pred_class, float(conf), float(margin)))
            class_counts[pred_class] += 1

        # 5. Class balance capping: ensure no single class exceeds max_class_imbalance of admitted
        total_admitted = len(admitted_indices)
        if total_admitted > 0:
            max_allowed_per_class = max(int(total_admitted * self.max_class_imbalance), 1)
            final_admitted = []
            balanced_class_counts = {c: 0 for c in self.classes}

            for idx, p_class, conf, margin in admitted_indices:
                if balanced_class_counts[p_class] < max_allowed_per_class:
                    final_admitted.append((idx, p_class, conf, margin))
                    balanced_class_counts[p_class] += 1
                else:
                    rejection_reasons["class_cap_exceeded"] += 1
        else:
            final_admitted = []
            balanced_class_counts = {c: 0 for c in self.classes}

        # Build admitted DataFrame
        if final_admitted:
            sel_indices = [x[0] for x in final_admitted]
            admitted_df = candidate_df.iloc[sel_indices].copy().reset_index(drop=True)
            admitted_df["candidate_idx"] = sel_indices
            admitted_df["pseudo_label"] = [x[1] for x in final_admitted]
            admitted_df["pseudo_confidence"] = [x[2] for x in final_admitted]
            admitted_df["pseudo_margin"] = [x[3] for x in final_admitted]
            admitted_df["label"] = admitted_df["pseudo_label"]
        else:
            admitted_df = pd.DataFrame(columns=list(candidate_df.columns) + ["pseudo_label", "pseudo_confidence", "pseudo_margin"])

        stats = {
            "total_candidates_screened": N,
            "total_admitted": len(final_admitted),
            "admission_rate": round(len(final_admitted) / N, 4) if N > 0 else 0.0,
            "class_distribution": balanced_class_counts,
            "rejections": rejection_reasons
        }

        return admitted_df, stats
