"""
Phase 7E: Supervised Model Training and Dual-Unseen Generalization Evaluation
Strict Protocols:
- Evaluates candidate models via 5-Fold GroupKFold CV on dual_unseen_train.parquet only.
- Preserves the 297-pair dual_unseen_val.parquet completely untouched until model freezing.
- Fits champion pipeline and model on full training partition.
- Evaluates frozen champion ONCE on the dual-unseen benchmark.
- Pre-registers baseline comparison on Evaluation C.
- Generates all required visualizations and logs.
"""

import os
import sys
import time
import math
import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import sparse
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)
import lightgbm as lgb
import xgboost as xgb

from src.preprocessing.text_cleaner import clean_text

SPLITS_DIR = Path("experiments/dataset_improvement/splits")
RESULTS_DIR = Path("experiments/dataset_improvement/results")
MODELS_DIR = Path("experiments/dataset_improvement/models")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

LABEL_ORDER = ["No Fit", "Good Fit", "Potential Fit"]
LABEL_TO_INT = {l: i for i, l in enumerate(LABEL_ORDER)}
INT_TO_LABEL = {i: l for i, l in enumerate(LABEL_ORDER)}


class FullFeaturePipeline:
    """
    Leakage-safe end-to-end feature pipeline.
    Fits TF-IDF, TruncatedSVD, and RobustScaler strictly on the training partition.
    """
    def __init__(self, max_tfidf_features: int = 2500, svd_components: int = 128):
        self.max_tfidf_features = max_tfidf_features
        self.svd_components = svd_components
        self.vectorizer = None
        self.svd = None
        self.scaler = None

    def fit(self, resumes: List[str], jobs: List[str], dom_raw: np.ndarray):
        clean_r = [clean_text(t) for t in resumes]
        clean_j = [clean_text(t) for t in jobs]
        corpus = clean_r + clean_j

        min_doc_freq = min(3, max(1, len(corpus)))
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_tfidf_features,
            ngram_range=(1, 2),
            min_df=min_doc_freq,
            sublinear_tf=True,
            norm="l2",
            token_pattern=r"(?u)\b[a-zA-Z0-9_\.\#\+\-]+\b"
        )
        self.vectorizer.fit(corpus)

        V_corpus = self.vectorizer.transform(corpus)
        n_comp = min(self.svd_components, max(1, V_corpus.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=n_comp, random_state=42)
        self.svd.fit(V_corpus)

        self.scaler = RobustScaler()
        self.scaler.fit(dom_raw)
        return self

    def transform(self, resumes: List[str], jobs: List[str], dom_raw: np.ndarray) -> sparse.csr_matrix:
        clean_r = [clean_text(t) for t in resumes]
        clean_j = [clean_text(t) for t in jobs]

        V_r = self.vectorizer.transform(clean_r)
        V_j = self.vectorizer.transform(clean_j)

        V_diff = abs(V_r - V_j)
        V_signed = V_r - V_j
        V_dot = V_r.multiply(V_j)

        cos_sim = np.asarray(V_dot.sum(axis=1)).reshape(-1, 1)
        man_sim = np.asarray(V_diff.sum(axis=1)).reshape(-1, 1)
        euc_sim = np.sqrt(np.asarray(V_diff.power(2).sum(axis=1))).reshape(-1, 1)
        inter = np.hstack([cos_sim, man_sim, euc_sim])

        svd_r = self.svd.transform(V_r)
        svd_j = self.svd.transform(V_j)
        svd_diff = abs(svd_r - svd_j)
        svd_dot = svd_r * svd_j

        norm_r = np.linalg.norm(svd_r, axis=1, keepdims=True) + 1e-9
        norm_j = np.linalg.norm(svd_j, axis=1, keepdims=True) + 1e-9
        svd_cos = np.sum((svd_r / norm_r) * (svd_j / norm_j), axis=1, keepdims=True)
        svd_feats = np.hstack([svd_diff, svd_dot, svd_cos])

        dom_scaled = self.scaler.transform(dom_raw)

        X = sparse.hstack([
            V_diff, V_signed, V_dot,
            sparse.csr_matrix(inter),
            sparse.csr_matrix(svd_feats),
            sparse.csr_matrix(dom_scaled)
        ], format="csr")
        return X

    def fit_transform(self, resumes: List[str], jobs: List[str], dom_raw: np.ndarray) -> sparse.csr_matrix:
        self.fit(resumes, jobs, dom_raw)
        return self.transform(resumes, jobs, dom_raw)


def compute_wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes Wilson score 95% confidence interval for proportion k/n."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    z = 1.959963984540054  # for 95%
    denominator = 1.0 + z * z / n
    centre_adjusted_probability = (p + z * z / (2 * n)) / denominator
    margin = (z / denominator) * math.sqrt(p * (1 - p) / n + (z * z) / (4 * n * n))
    lower = max(0.0, centre_adjusted_probability - margin)
    upper = min(1.0, centre_adjusted_probability + margin)
    return lower, upper


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    p_cls, r_cls, f1_cls, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABEL_ORDER, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER).tolist()

    k = int(np.sum(y_true == y_pred))
    n = len(y_true)
    ci_low, ci_high = compute_wilson_ci(k, n)

    return {
        "n_samples": n,
        "n_correct": k,
        "accuracy": acc,
        "accuracy_ci_95": [float(ci_low), float(ci_high)],
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
        "weighted_f1": float(f1_wt),
        "per_class": {
            label: {
                "precision": float(p_cls[i]),
                "recall": float(r_cls[i]),
                "f1": float(f1_cls[i])
            }
            for i, label in enumerate(LABEL_ORDER)
        },
        "confusion_matrix": cm,
        "label_order": LABEL_ORDER
    }


def main():
    print("=" * 80)
    print("PHASE 7E: SUPERVISED MODEL TRAINING & DUAL-UNSEEN GENERALIZATION EVALUATION")
    print("=" * 80)
    total_start = time.time()

    # 1. Load Phase 7D splits and domain features
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")
    train_dom = pd.read_parquet(SPLITS_DIR / "train_domain_raw.parquet")
    val_dom = pd.read_parquet(SPLITS_DIR / "val_domain_raw.parquet")

    print(f"Loaded Train Pairs: {len(train_df):,} | Unique Resumes: {train_df['resume_text'].nunique()} | Unique Jobs: {train_df['job_description_text'].nunique()}")
    print(f"Loaded Val Pairs:   {len(val_df):,}   | Unique Resumes: {val_df['resume_text'].nunique()}   | Unique Jobs: {val_df['job_description_text'].nunique()}")

    # Check and remove conflicting duplicates in training
    dups_mask = train_df.duplicated(subset=["resume_text", "job_description_text"], keep=False)
    n_dups = dups_mask.sum()
    print(f"Training conflicting duplicate rows detected: {n_dups} (out of {len(train_df)}).")
    active_train_df = train_df[~dups_mask].reset_index(drop=True)
    active_train_dom = train_dom[~dups_mask].reset_index(drop=True)
    print(f"Active Clean Training Pairs: {len(active_train_df):,} across {active_train_df['job_description_text'].nunique()} jobs.")

    y_train_str = np.array(active_train_df["label"].tolist(), dtype=object)
    y_train_enc = np.array([LABEL_TO_INT[l] for l in y_train_str], dtype=int)
    job_groups = np.array(active_train_df["job_description_text"].tolist(), dtype=object)

    # 2. Setup 5-Fold GroupKFold CV on Training Set
    N_SPLITS = 5
    gkf = GroupKFold(n_splits=N_SPLITS)
    cv_splits = list(gkf.split(active_train_df, y_train_str, groups=job_groups))

    # Verify zero leakage across CV folds
    for f_i, (tr_idx, va_idx) in enumerate(cv_splits):
        tr_jobs = set(job_groups[tr_idx])
        va_jobs = set(job_groups[va_idx])
        assert len(tr_jobs.intersection(va_jobs)) == 0, f"Leakage detected in fold {f_i+1}!"
    print(f"Verified: Zero job leakage across all {N_SPLITS} GroupKFold splits.")

    # 3. Define candidate models
    models_to_evaluate = {
        "Optimized Linear SVM": {
            "type": "sklearn",
            "constructor": lambda: LinearSVC(C=0.10, class_weight="balanced", max_iter=3000, random_state=42, dual="auto")
        },
        "Optimized Logistic Regression": {
            "type": "sklearn",
            "constructor": lambda: LogisticRegression(C=0.0656, class_weight="balanced", max_iter=600, random_state=42)
        },
        "Optimized LightGBM": {
            "type": "lightgbm",
            "constructor": lambda: lgb.LGBMClassifier(
                num_leaves=29,
                max_depth=5,
                learning_rate=0.105,
                n_estimators=70,
                min_child_samples=30,
                subsample=0.82,
                colsample_bytree=0.65,
                reg_alpha=0.50,
                reg_lambda=1.32,
                class_weight="balanced",
                n_jobs=8,
                random_state=42,
                verbose=-1
            )
        },
        "GPU XGBoost": {
            "type": "xgboost",
            "constructor": lambda: xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.10,
                subsample=0.80,
                colsample_bytree=0.75,
                min_child_weight=2,
                reg_alpha=0.50,
                reg_lambda=1.50,
                tree_method="hist",
                device="cuda",
                objective="multi:softprob",
                num_class=3,
                random_state=42
            )
        },
        "Production Baseline Logistic Regression": {
            "type": "sklearn",
            "constructor": lambda: LogisticRegression(C=1.0, class_weight="balanced", max_iter=600, random_state=42)
        }
    }

    print("\n" + "=" * 80)
    print("RUNNING INTERNAL 5-FOLD JOB-DISJOINT CV ON TRAINING PARTITION")
    print("=" * 80)

    cv_results = {}
    model_oof_preds = {m: [None] * len(active_train_df) for m in models_to_evaluate}
    model_fit_times = {m: 0.0 for m in models_to_evaluate}

    for fold_idx, (tr_idx, va_idx) in enumerate(cv_splits):
        fold_num = fold_idx + 1
        t_f0 = time.time()
        print(f"\n--- Fold {fold_num}/{N_SPLITS} (Train: {len(tr_idx):,} rows | Val: {len(va_idx):,} rows) ---")

        r_tr = active_train_df.iloc[tr_idx]["resume_text"].tolist()
        j_tr = active_train_df.iloc[tr_idx]["job_description_text"].tolist()
        dom_tr = active_train_dom.iloc[tr_idx].values

        r_va = active_train_df.iloc[va_idx]["resume_text"].tolist()
        j_va = active_train_df.iloc[va_idx]["job_description_text"].tolist()
        dom_va = active_train_dom.iloc[va_idx].values

        y_tr_str = y_train_str[tr_idx]
        y_va_str = y_train_str[va_idx]
        y_tr_enc = y_train_enc[tr_idx]

        # Isolated fold pipeline
        pipeline = FullFeaturePipeline(max_tfidf_features=2500, svd_components=128)
        X_tr = pipeline.fit_transform(r_tr, j_tr, dom_tr)
        X_va = pipeline.transform(r_va, j_va, dom_va)
        print(f"  Feature pipeline fitted in {time.time() - t_f0:.2f}s | Feature dim: {X_tr.shape[1]:,}")

        # Train and evaluate each model on this fold
        for m_name, m_cfg in models_to_evaluate.items():
            t_m0 = time.time()
            clf = m_cfg["constructor"]()

            if m_cfg["type"] == "sklearn":
                clf.fit(X_tr, y_tr_str)
                preds = clf.predict(X_va)
            elif m_cfg["type"] == "lightgbm":
                clf.fit(X_tr.astype(np.float32), y_tr_str)
                preds = clf.predict(X_va.astype(np.float32))
            elif m_cfg["type"] == "xgboost":
                # Compute balanced sample weights for XGBoost
                sw_tr = compute_sample_weight("balanced", y_tr_enc)
                clf.fit(X_tr, y_tr_enc, sample_weight=sw_tr)
                p_enc = clf.predict(X_va)
                preds = np.array([INT_TO_LABEL[p] for p in p_enc], dtype=object)

            fit_time = time.time() - t_m0
            model_fit_times[m_name] += fit_time

            for idx_local, global_idx in enumerate(va_idx):
                model_oof_preds[m_name][global_idx] = preds[idx_local]

            f_acc = accuracy_score(y_va_str, preds)
            _, _, f_macro, _ = precision_recall_fscore_support(y_va_str, preds, average="macro", zero_division=0)
            if m_name not in cv_results:
                cv_results[m_name] = {"fold_macro_f1": [], "fold_acc": []}
            cv_results[m_name]["fold_macro_f1"].append(float(f_macro))
            cv_results[m_name]["fold_acc"].append(float(f_acc))
            print(f"  [{m_name}] Fold {fold_num} - Macro F1: {f_macro:.4f} | Acc: {f_acc*100:.2f}% ({fit_time:.2f}s)")

    print("\n" + "=" * 80)
    print("INTERNAL 5-FOLD CV SUMMARY (TRAINING PARTITION ONLY)")
    print("=" * 80)

    summary_records = []
    for m_name in models_to_evaluate:
        oof_preds = np.array(model_oof_preds[m_name], dtype=object)
        oof_metrics = evaluate_predictions(y_train_str, oof_preds)
        mean_cv_f1 = float(np.mean(cv_results[m_name]["fold_macro_f1"]))
        std_cv_f1 = float(np.std(cv_results[m_name]["fold_macro_f1"]))
        mean_cv_acc = float(np.mean(cv_results[m_name]["fold_acc"]))
        std_cv_acc = float(np.std(cv_results[m_name]["fold_acc"]))

        cv_results[m_name]["mean_macro_f1"] = mean_cv_f1
        cv_results[m_name]["std_macro_f1"] = std_cv_f1
        cv_results[m_name]["mean_acc"] = mean_cv_acc
        cv_results[m_name]["std_acc"] = std_cv_acc
        cv_results[m_name]["oof_metrics"] = oof_metrics
        cv_results[m_name]["total_train_time_sec"] = model_fit_times[m_name]

        summary_records.append({
            "model": m_name,
            "mean_cv_macro_f1": mean_cv_f1,
            "std_cv_macro_f1": std_cv_f1,
            "mean_cv_accuracy": mean_cv_acc,
            "std_cv_accuracy": std_cv_acc,
            "oof_accuracy": oof_metrics["accuracy"],
            "oof_macro_f1": oof_metrics["macro_f1"],
            "recall_good_fit": oof_metrics["per_class"]["Good Fit"]["recall"],
            "total_time_s": model_fit_times[m_name]
        })

        print(f"{m_name:42s} | Mean CV Macro F1: {mean_cv_f1:.4f} +/- {std_cv_f1:.4f} | Mean CV Acc: {mean_cv_acc*100:.2f}% | Good Fit Recall: {oof_metrics['per_class']['Good Fit']['recall']:.4f}")

    # Save CV results
    with open(RESULTS_DIR / "phase7e_cv_results.json", "w") as f:
        json.dump(cv_results, f, indent=2)

    # 4. Model Selection based strictly on Training CV Macro F1
    summary_df = pd.DataFrame(summary_records).sort_values("mean_cv_macro_f1", ascending=False).reset_index(drop=True)
    champion_name = summary_df.iloc[0]["model"]
    print("\n" + "=" * 80)
    print(f"CHAMPION MODEL SELECTED STRICTLY BY TRAINING-ONLY CV: {champion_name}")
    print(f"Selection Metric (Mean CV Macro F1): {summary_df.iloc[0]['mean_cv_macro_f1']:.4f}")
    print("=" * 80)

    # 5. Freeze Champion Pipeline and Model by Fitting on the Entire Active Training Partition
    print("\nFreezing Champion Pipeline & Model on full active training set...")
    t_freeze0 = time.time()
    frozen_pipeline = FullFeaturePipeline(max_tfidf_features=2500, svd_components=128)
    X_train_full = frozen_pipeline.fit_transform(
        active_train_df["resume_text"].tolist(),
        active_train_df["job_description_text"].tolist(),
        active_train_dom.values
    )
    print(f"Frozen pipeline fitted on {X_train_full.shape[0]:,} samples in {time.time() - t_freeze0:.2f}s (Features: {X_train_full.shape[1]:,}).")

    champion_clf = models_to_evaluate[champion_name]["constructor"]()
    if models_to_evaluate[champion_name]["type"] == "sklearn":
        champion_clf.fit(X_train_full, y_train_str)
    elif models_to_evaluate[champion_name]["type"] == "lightgbm":
        champion_clf.fit(X_train_full.astype(np.float32), y_train_str)
    elif models_to_evaluate[champion_name]["type"] == "xgboost":
        sw_full = compute_sample_weight("balanced", y_train_enc)
        champion_clf.fit(X_train_full, y_train_enc, sample_weight=sw_full)

    # Pre-registered Baseline model for Evaluation C comparison
    baseline_clf = models_to_evaluate["Production Baseline Logistic Regression"]["constructor"]()
    baseline_clf.fit(X_train_full, y_train_str)

    # Save artifacts
    joblib.dump(frozen_pipeline, MODELS_DIR / "frozen_dual_unseen_pipeline.joblib")
    joblib.dump(champion_clf, MODELS_DIR / "frozen_dual_unseen_champion.joblib")
    joblib.dump(baseline_clf, MODELS_DIR / "frozen_dual_unseen_baseline.joblib")

    training_config = {
        "selected_champion": champion_name,
        "champion_type": models_to_evaluate[champion_name]["type"],
        "training_samples_raw": len(train_df),
        "training_samples_active": len(active_train_df),
        "val_samples_dual_unseen": len(val_df),
        "n_tfidf_features": frozen_pipeline.max_tfidf_features,
        "n_svd_components": frozen_pipeline.svd.n_components,
        "n_features_total": X_train_full.shape[1],
        "label_order": LABEL_ORDER,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(MODELS_DIR / "training_config.json", "w") as f:
        json.dump(training_config, f, indent=2)
    print("Saved frozen pipeline and model artifacts.")

    # 6. ONE-TIME FINAL DUAL-UNSEEN EVALUATION (Evaluation Scenario C)
    print("\n" + "=" * 80)
    print("EXECUTING ONE-TIME FINAL DUAL-UNSEEN GENERALIZATION EVALUATION (297 PAIRS)")
    print("=" * 80)

    t_eval0 = time.time()
    X_val_dual = frozen_pipeline.transform(
        val_df["resume_text"].tolist(),
        val_df["job_description_text"].tolist(),
        val_dom.values
    )
    y_val_str = np.array(val_df["label"].tolist(), dtype=object)

    if models_to_evaluate[champion_name]["type"] == "sklearn":
        dual_unseen_preds = champion_clf.predict(X_val_dual)
    elif models_to_evaluate[champion_name]["type"] == "lightgbm":
        dual_unseen_preds = champion_clf.predict(X_val_dual.astype(np.float32))
    elif models_to_evaluate[champion_name]["type"] == "xgboost":
        p_enc = champion_clf.predict(X_val_dual)
        dual_unseen_preds = np.array([INT_TO_LABEL[p] for p in p_enc], dtype=object)

    champion_eval_metrics = evaluate_predictions(y_val_str, dual_unseen_preds)

    # Evaluate pre-registered baseline on the same dual-unseen set
    baseline_preds = baseline_clf.predict(X_val_dual)
    baseline_eval_metrics = evaluate_predictions(y_val_str, baseline_preds)

    eval_duration = time.time() - t_eval0

    final_eval_results = {
        "champion_model_name": champion_name,
        "dual_unseen_val_size": len(val_df),
        "evaluation_duration_sec": eval_duration,
        "champion_metrics": champion_eval_metrics,
        "baseline_metrics": baseline_eval_metrics,
        "historical_benchmarks": {
            "scenario_a_unseen_jobs": {
                "description": "Historical 1,759-pair held-out test set (unseen jobs only)",
                "baseline_lr_accuracy": 0.5121,
                "baseline_lr_macro_f1": 0.4666,
                "svm_phase7b_c_accuracy": 0.5319,
                "svm_phase7b_c_macro_f1": 0.4810
            },
            "scenario_b_unseen_resumes": {
                "description": "Historical 1,600-pair held-out resume split (unseen resumes only)",
                "reported_accuracy_range": "48.5% - 52.8%"
            },
            "scenario_c_dual_unseen": {
                "description": "Pristine 297-pair dual-unseen holdout (both resumes and jobs unseen)",
                "champion_model": champion_name,
                "champion_accuracy": champion_eval_metrics["accuracy"],
                "champion_accuracy_ci_95": champion_eval_metrics["accuracy_ci_95"],
                "champion_macro_f1": champion_eval_metrics["macro_f1"],
                "baseline_accuracy": baseline_eval_metrics["accuracy"],
                "baseline_macro_f1": baseline_eval_metrics["macro_f1"]
            }
        }
    }

    with open(RESULTS_DIR / "phase7e_final_evaluation_results.json", "w") as f:
        json.dump(final_eval_results, f, indent=2)

    print(f"\nFinal Dual-Unseen Evaluation Results (N = {len(val_df)}):")
    print(f"  Champion Model:         {champion_name}")
    print(f"  Accuracy:               {champion_eval_metrics['accuracy']*100:.2f}% (95% Wilson CI: [{champion_eval_metrics['accuracy_ci_95'][0]*100:.2f}%, {champion_eval_metrics['accuracy_ci_95'][1]*100:.2f}%])")
    print(f"  Macro Precision:        {champion_eval_metrics['macro_precision']:.4f}")
    print(f"  Macro Recall:           {champion_eval_metrics['macro_recall']:.4f}")
    print(f"  Macro F1:               {champion_eval_metrics['macro_f1']:.4f}")
    print(f"  Weighted F1:            {champion_eval_metrics['weighted_f1']:.4f}")
    print("\nPer-Class Metrics (Champion):")
    for lbl, m in champion_eval_metrics["per_class"].items():
        print(f"  {lbl:15s} | Prec: {m['precision']:.4f} | Recall: {m['recall']:.4f} | F1: {m['f1']:.4f}")

    print("\nPre-registered Baseline Logistic Regression Comparison:")
    print(f"  Baseline Accuracy:      {baseline_eval_metrics['accuracy']*100:.2f}% (95% Wilson CI: [{baseline_eval_metrics['accuracy_ci_95'][0]*100:.2f}%, {baseline_eval_metrics['accuracy_ci_95'][1]*100:.2f}%])")
    print(f"  Baseline Macro F1:      {baseline_eval_metrics['macro_f1']:.4f}")

    print("\nConfusion Matrix (Champion):")
    cm_arr = np.array(champion_eval_metrics["confusion_matrix"])
    print(f"Rows = True, Cols = Pred. Labels: {LABEL_ORDER}")
    for i, row in enumerate(cm_arr):
        print(f"  {LABEL_ORDER[i]:15s}: {row}")

    # 7. Generate Visualizations
    print("\n" + "=" * 80)
    print("GENERATING VISUALIZATION ARTIFACTS")
    print("=" * 80)

    # Plot 1: Internal CV Macro F1 and Accuracy Comparison
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    models_short = [m.replace("Optimized ", "").replace("Production Baseline ", "Baseline ") for m in summary_df["model"]]
    
    bars1 = ax1.bar(models_short, summary_df["mean_cv_macro_f1"], yerr=summary_df["std_cv_macro_f1"], capsize=5, color="#1976D2", alpha=0.85)
    ax1.set_title("Internal 5-Fold GroupKFold CV: Macro F1", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Macro F1-Score")
    ax1.set_ylim(0.0, 0.65)
    ax1.tick_params(axis="x", rotation=25)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f"{yval:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    bars2 = ax2.bar(models_short, summary_df["mean_cv_accuracy"] * 100, yerr=summary_df["std_cv_accuracy"] * 100, capsize=5, color="#388E3C", alpha=0.85)
    ax2.set_title("Internal 5-Fold GroupKFold CV: Accuracy (%)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Accuracy (%)")
    ax2.set_ylim(0.0, 75)
    ax2.tick_params(axis="x", rotation=25)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 2, f"{yval:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7e_internal_cv_comparison.png", dpi=300)
    plt.close()
    print("  Saved phase7e_internal_cv_comparison.png")

    # Plot 2: Confusion Matrix (Raw counts)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm_arr, annot=True, fmt="d", cmap="Blues", xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER, cbar=False, ax=ax)
    ax.set_title(f"Dual-Unseen Confusion Matrix (N = {len(val_df)})\n{champion_name}", fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Label", fontweight="bold")
    ax.set_ylabel("True Ground Truth Label", fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7e_dual_unseen_confusion_matrix.png", dpi=300)
    plt.close()
    print("  Saved phase7e_dual_unseen_confusion_matrix.png")

    # Plot 3: Normalized Confusion Matrix
    cm_norm = cm_arr.astype("float") / cm_arr.sum(axis=1)[:, np.newaxis]
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm_norm, annot=True, fmt=".2%", cmap="Greens", xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER, cbar=False, ax=ax)
    ax.set_title(f"Dual-Unseen Normalized Recall Matrix\n{champion_name}", fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Label", fontweight="bold")
    ax.set_ylabel("True Ground Truth Label", fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7e_dual_unseen_normalized_cm.png", dpi=300)
    plt.close()
    print("  Saved phase7e_dual_unseen_normalized_cm.png")

    # Plot 4: Per-Class Precision, Recall, F1
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = LABEL_ORDER
    x = np.arange(len(labels))
    width = 0.25
    precisions = [champion_eval_metrics["per_class"][l]["precision"] for l in labels]
    recalls = [champion_eval_metrics["per_class"][l]["recall"] for l in labels]
    f1s = [champion_eval_metrics["per_class"][l]["f1"] for l in labels]

    ax.bar(x - width, precisions, width, label="Precision", color="#1976D2")
    ax.bar(x, recalls, width, label="Recall", color="#388E3C")
    ax.bar(x + width, f1s, width, label="F1-Score", color="#F57C00")
    ax.set_ylabel("Score (0.0 - 1.0)")
    ax.set_title(f"Dual-Unseen Per-Class Performance ({champion_name})", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight="bold")
    ax.set_ylim(0.0, 1.0)
    ax.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7e_per_class_performance.png", dpi=300)
    plt.close()
    print("  Saved phase7e_per_class_performance.png")

    # Plot 5: Generalization Comparison Across Scenarios
    fig, ax = plt.subplots(figsize=(9, 5))
    scenarios = [
        "Scenario A:\nUnseen Jobs\n(Hist. Test 1,759 pairs)",
        "Scenario B:\nUnseen Resumes\n(Hist. Val 1,600 pairs)",
        "Scenario C:\nDual-Unseen (Baseline)\n(Val 297 pairs)",
        "Scenario C:\nDual-Unseen (Champion)\n(Val 297 pairs)"
    ]
    accuracies = [
        53.19,  # Phase 7B-C SVM on unseen jobs
        50.60,  # Midpoint of reported range
        baseline_eval_metrics["accuracy"] * 100,
        champion_eval_metrics["accuracy"] * 100
    ]
    colors = ["#78909C", "#90A4AE", "#FFA726", "#2E7D32"]
    bars = ax.bar(scenarios, accuracies, color=colors, width=0.55)
    ax.set_ylabel("Accuracy (%)", fontweight="bold")
    ax.set_title("Generalization Across Isolated Evaluation Scenarios", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 85)
    ax.axhline(80.0, color="#D32F2F", linestyle="--", linewidth=1.5, label="Target 80% Threshold")
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 1.5, f"{h:.2f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "phase7e_evaluation_scenarios_comparison.png", dpi=300)
    plt.close()
    print("  Saved phase7e_evaluation_scenarios_comparison.png")

    total_time = time.time() - total_start
    print(f"\nPhase 7E Execution Complete in {total_time:.2f}s ({total_time/60:.2f} min).")


if __name__ == "__main__":
    main()
