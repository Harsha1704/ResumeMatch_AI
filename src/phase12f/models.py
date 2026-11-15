"""
src/phase12f/models.py
Model Architecture Tracks for Phase 12F:
- Track A: Transformer Cross-Encoder with Requirement-Gated Extraction (RGE).
- Track B: Bi-Encoder Retrieval & Embedding Similarity Matcher.
- Track C: Hybrid Stacking Architecture with Out-of-Fold Calibration.
- Track D: ONNX Conversion and INT8 Dynamic Quantization for CPU inference.
"""

import os
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score
import lightgbm as lgb
from catboost import CatBoostClassifier

from src.phase12f.long_document_handler import RequirementGatedExtractor
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


class BiEncoderSimilarityMatcher:
    """
    Track B: Bi-encoder semantic retrieval and threshold-based matching.
    Evaluates Recall@K, nDCG, and 3-class classification separation.
    """

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.classes = CLASSES

    def compute_cosine_similarity(self, u: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Computes pairwise cosine similarity between normalized vectors."""
        u_norm = u / (np.linalg.norm(u, axis=1, keepdims=True) + 1e-12)
        v_norm = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
        return np.sum(u_norm * v_norm, axis=1)

    def evaluate_retrieval_ranking(self, u_embs: np.ndarray, v_embs: np.ndarray, labels: List[str], top_k: int = 5) -> Dict:
        """
        Evaluates retrieval quality: whether 'Good Fit' candidates rank higher
        than 'Potential Fit' and 'No Fit'.
        """
        sims = self.compute_cosine_similarity(u_embs, v_embs)
        # Binary target: Good Fit vs non-Good Fit
        binary_targets = np.array([1 if l == "Good Fit" else 0 for l in labels])
        
        # Sort by similarity
        sorted_indices = np.argsort(sims)[::-1]
        sorted_targets = binary_targets[sorted_indices]

        # Top-K Precision and Recall
        k = min(top_k, len(sorted_targets))
        total_positives = max(np.sum(binary_targets), 1)
        hits_at_k = np.sum(sorted_targets[:k])
        precision_at_k = hits_at_k / k
        recall_at_k = hits_at_k / total_positives

        # DCG@K
        dcg = np.sum(sorted_targets[:k] / np.log2(np.arange(2, k + 2)))
        ideal_targets = np.sort(binary_targets)[::-1][:k]
        idcg = np.sum(ideal_targets / np.log2(np.arange(2, k + 2)))
        ndcg = dcg / idcg if idcg > 0 else 0.0

        return {
            "mean_cosine_sim": round(float(np.mean(sims)), 4),
            "sim_by_class": {
                c: round(float(np.mean(sims[np.array(labels) == c])), 4)
                for c in self.classes if np.any(np.array(labels) == c)
            },
            f"precision_at_{top_k}": round(float(precision_at_k), 4),
            f"recall_at_{top_k}": round(float(recall_at_k), 4),
            f"ndcg_at_{top_k}": round(float(ndcg), 4)
        }


class HybridStackingClassifier(BaseEstimator, ClassifierMixin):
    """
    Track C: Hybrid Stacking Architecture combining:
    1. SBERT / Domain-Adapted Embedding Interaction Features
    2. Requirement-Gated Extraction (RGE) Text Features & Domain Engineered Features
    3. Multi-Model Stacking (LightGBM + CatBoost + Calibrated Logistic Regression)
    """

    def __init__(
        self,
        use_lightgbm: bool = True,
        use_catboost: bool = True,
        lgb_params: Optional[Dict] = None,
        cb_params: Optional[Dict] = None,
        random_state: int = 42
    ):
        self.use_lightgbm = use_lightgbm
        self.use_catboost = use_catboost
        self.random_state = random_state
        self.classes_ = np.array(CLASSES)
        
        self.scaler = StandardScaler()
        self.meta_learner = LogisticRegression(
            C=1.0, max_iter=1000, class_weight="balanced", random_state=random_state
        )

        default_lgb = {
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 5,
            "n_estimators": 80,
            "class_weight": "balanced",
            "n_jobs": 4,
            "verbose": -1,
            "random_state": random_state
        }
        self.lgb_params = lgb_params or default_lgb

        default_cb = {
            "iterations": 80,
            "learning_rate": 0.05,
            "depth": 5,
            "auto_class_weights": "Balanced",
            "thread_count": 4,
            "verbose": False,
            "random_seed": random_state
        }
        self.cb_params = cb_params or default_cb

        self.lgb_model = lgb.LGBMClassifier(**self.lgb_params) if use_lightgbm else None
        self.cb_model = CatBoostClassifier(**self.cb_params) if use_catboost else None

    def fit(self, X: np.ndarray, y: np.ndarray, cv_folds: int = 3) -> "HybridStackingClassifier":
        """
        Fits base gradient boosters and meta-learner using out-of-fold predictions
        to completely prevent stacking data leakage.
        """
        from sklearn.model_selection import StratifiedKFold
        y = np.asarray(y, dtype=str)
        X_scaled = self.scaler.fit_transform(X)
        N = len(X)

        meta_features = []
        oof_preds = np.zeros((N, 3 * (int(self.use_lightgbm) + int(self.use_catboost))), dtype=np.float32)

        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        for train_idx, val_idx in skf.split(X_scaled, y):
            X_tr, y_tr = X_scaled[train_idx], y[train_idx]
            X_val = X_scaled[val_idx]

            col_offset = 0
            if self.use_lightgbm:
                fold_lgb = lgb.LGBMClassifier(**self.lgb_params)
                fold_lgb.fit(X_tr, y_tr)
                oof_preds[val_idx, col_offset:col_offset + 3] = fold_lgb.predict_proba(X_val)
                col_offset += 3

            if self.use_catboost:
                fold_cb = CatBoostClassifier(**self.cb_params)
                fold_cb.fit(X_tr, y_tr)
                oof_preds[val_idx, col_offset:col_offset + 3] = fold_cb.predict_proba(X_val)

        # Train meta-learner on out-of-fold probabilities
        self.meta_learner.fit(oof_preds, y)

        # Re-fit base learners on all data
        if self.use_lightgbm:
            self.lgb_model.fit(X_scaled, y)
        if self.use_catboost:
            self.cb_model.fit(X_scaled, y)

        return self

    def _get_base_probs(self, X_scaled: np.ndarray) -> np.ndarray:
        base_probs = []
        if self.use_lightgbm:
            base_probs.append(self.lgb_model.predict_proba(X_scaled))
        if self.use_catboost:
            base_probs.append(self.cb_model.predict_proba(X_scaled))
        return np.hstack(base_probs)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        base_probs = self._get_base_probs(X_scaled)
        raw_probs = self.meta_learner.predict_proba(base_probs)
        # Align probabilities to self.classes_ ["No Fit", "Potential Fit", "Good Fit"]
        meta_classes = list(self.meta_learner.classes_)
        aligned_probs = np.zeros((len(raw_probs), len(self.classes_)), dtype=np.float32)
        for target_idx, c in enumerate(self.classes_):
            if c in meta_classes:
                src_idx = meta_classes.index(c)
                aligned_probs[:, target_idx] = raw_probs[:, src_idx]
        return aligned_probs

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        class_indices = np.argmax(probs, axis=1)
        return self.classes_[class_indices]


class TransformerCrossEncoderClassifier(nn.Module):
    """
    Track A: Lightweight Transformer Cross-Encoder with RGE Sequence Budgeting.
    Combines text pair representations with a deep classification head.
    """

    def __init__(self, hidden_dim: int = 384, num_classes: int = 3, dropout: float = 0.2):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.classifier(features)
