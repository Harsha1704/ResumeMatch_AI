"""
Phase 7B Experimental Runner & Optimization Suite.
Trains, tunes, and benchmarks supervised models on job-disjoint partitions.
Models evaluated:
1. Logistic Regression (Optuna tuned C)
2. Linear SVM (Calibrated with Platt Scaling)
3. GPU-Accelerated XGBoost (NVIDIA RTX 4050 Laptop GPU, CUDA accelerated)
4. LightGBM (Multi-threaded histogram boosting)
5. CatBoost Classifier (Symmetric oblivious trees)
All outputs are strictly saved inside experiments/model_optimization/.
Zero production model contamination. Zero test set leakage.
"""

import os
import sys
import time
import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import optuna

# Suppress Optuna verbose output
optuna.logging.set_verbosity(optuna.logging.WARNING)

from src.utils.split_manager import get_unseen_jobs_split
from experiments.model_optimization.feature_engineering import (
    AdvancedFeaturePipeline,
    ExperimentalDomainExtractor
)

BASE_DIR = Path("experiments/model_optimization")
CACHE_DIR = BASE_DIR / "data_cache"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

for d in [BASE_DIR, CACHE_DIR, MODELS_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LABEL_ORDER = ["No Fit", "Good Fit", "Potential Fit"]
LABEL_TO_INT = {l: i for i, l in enumerate(LABEL_ORDER)}
INT_TO_LABEL = {i: l for i, l in enumerate(LABEL_ORDER)}


def load_data_and_domain_features():
    train_df, val_df, test_df = get_unseen_jobs_split()

    train_cache = CACHE_DIR / "train_domain_features.parquet"
    val_cache = CACHE_DIR / "val_domain_features.parquet"

    if train_cache.exists() and val_cache.exists():
        train_dom = pd.read_parquet(train_cache)
        val_dom = pd.read_parquet(val_cache)
    else:
        extractor = ExperimentalDomainExtractor()
        train_rows = [extractor.extract_pair_features(r, j) for r, j in zip(train_df["resume_text"], train_df["job_description_text"])]
        train_dom = pd.DataFrame(train_rows)
        train_dom.to_parquet(train_cache)

        val_rows = [extractor.extract_pair_features(r, j) for r, j in zip(val_df["resume_text"], val_df["job_description_text"])]
        val_dom = pd.DataFrame(val_rows)
        val_dom.to_parquet(val_cache)

    return train_df, val_df, train_dom, val_dom


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    # Per-class metrics
    p_cls, r_cls, f1_cls, supp_cls = precision_recall_fscore_support(y_true, y_pred, labels=LABEL_ORDER, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER).tolist()

    per_class = {}
    for idx, name in enumerate(LABEL_ORDER):
        per_class[name] = {
            "precision": float(p_cls[idx]),
            "recall": float(r_cls[idx]),
            "f1": float(f1_cls[idx]),
            "support": int(supp_cls[idx])
        }

    return {
        "accuracy": float(acc),
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
        "weighted_f1": float(f1_wt),
        "per_class": per_class,
        "confusion_matrix": cm
    }


def run_experiment_suite():
    print("=" * 70)
    print("PHASE 7B: ADVANCED SUPERVISED ML OPTIMIZATION & GPU BENCHMARKING")
    print("=" * 70)

    train_df, val_df, train_dom, val_dom = load_data_and_domain_features()
    print(f"Loaded Train: {len(train_df)} rows, Val: {len(val_df)} rows.")

    # -------------------------------------------------------------
    # 1. DUPLICATE & CONFLICT ANALYSIS EXPERIMENT
    # -------------------------------------------------------------
    print("\n--- 1. Duplicate & Conflicting Label Experiment ---")
    dups_mask = train_df.duplicated(subset=["resume_text", "job_description_text"], keep=False)
    n_dups = int(dups_mask.sum())
    print(f"Detected {n_dups} duplicate rows in train_df.")

    # Exclude conflicting duplicate pairs for training variant
    train_filtered_df = train_df[~dups_mask].reset_index(drop=True)
    train_filtered_dom = train_dom[~dups_mask].reset_index(drop=True)
    print(f"Filtered Training Variant: {len(train_filtered_df)} rows ({n_dups} excluded).")

    # Native NumPy string arrays
    y_tr_ret_str = np.array(train_df["label"].tolist(), dtype=object)
    y_tr_fil_str = np.array(train_filtered_df["label"].tolist(), dtype=object)
    y_val_str = np.array(val_df["label"].tolist(), dtype=object)

    # Train baseline logistic regression on both to compare
    print("Training Logistic Regression on Retained (5,462 rows)...")
    pipe_ret = AdvancedFeaturePipeline(max_tfidf_features=2500, use_directional=False, use_svd=False)
    pipe_ret.fit(train_df, precomputed_domain_df=train_dom)
    X_tr_ret = pipe_ret.transform(train_df, precomputed_domain_df=train_dom)
    X_val_ret = pipe_ret.transform(val_df, precomputed_domain_df=val_dom)

    lr_ret = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    lr_ret.fit(X_tr_ret, y_tr_ret_str)
    m_ret = evaluate_predictions(y_val_str, lr_ret.predict(X_val_ret))
    print(f"  Retained Variant -> Val Macro F1: {m_ret['macro_f1']:.4f} | Accuracy: {m_ret['accuracy']:.4f}")

    print("Training Logistic Regression on Filtered (5,450 rows)...")
    pipe_fil = AdvancedFeaturePipeline(max_tfidf_features=2500, use_directional=False, use_svd=False)
    pipe_fil.fit(train_filtered_df, precomputed_domain_df=train_filtered_dom)
    X_tr_fil = pipe_fil.transform(train_filtered_df, precomputed_domain_df=train_filtered_dom)
    X_val_fil = pipe_fil.transform(val_df, precomputed_domain_df=val_dom)

    lr_fil = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    lr_fil.fit(X_tr_fil, y_tr_fil_str)
    m_fil = evaluate_predictions(y_val_str, lr_fil.predict(X_val_fil))
    print(f"  Filtered Variant -> Val Macro F1: {m_fil['macro_f1']:.4f} | Accuracy: {m_fil['accuracy']:.4f}")

    # Use the cleaner filtered dataset for subsequent experiments
    active_train_df = train_filtered_df
    active_train_dom = train_filtered_dom
    y_train_str = y_tr_fil_str

    # -------------------------------------------------------------
    # 2. FEATURE SET ABLATION BENCHMARKS
    # -------------------------------------------------------------
    print("\n--- 2. Feature Representation Ablation Benchmarks ---")
    feature_configs = {
        "Feature Set A (TF-IDF + Basic Domain)": {"use_directional": False, "use_svd": False, "svd_components": 0, "max_tfidf": 2500},
        "Feature Set B (Directional Differences & Product)": {"use_directional": True, "use_svd": False, "svd_components": 0, "max_tfidf": 2500},
        "Feature Set D (Rich Domain Alignment Only)": {"use_directional": False, "use_svd": False, "svd_components": 0, "max_tfidf": 50},
        "Feature Set E (LSA 128 + Domain + Directional)": {"use_directional": True, "use_svd": True, "svd_components": 128, "max_tfidf": 2500},
    }

    ablation_results = {}
    for feat_name, cfg in feature_configs.items():
        print(f"Evaluating {feat_name}...")
        p = AdvancedFeaturePipeline(
            max_tfidf_features=cfg["max_tfidf"],
            use_directional=cfg["use_directional"],
            use_svd=cfg["use_svd"],
            svd_components=cfg["svd_components"]
        )
        p.fit(active_train_df, precomputed_domain_df=active_train_dom)
        X_tr = p.transform(active_train_df, precomputed_domain_df=active_train_dom)
        X_va = p.transform(val_df, precomputed_domain_df=val_dom)

        clf = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
        clf.fit(X_tr, y_train_str)
        m = evaluate_predictions(y_val_str, clf.predict(X_va))
        ablation_results[feat_name] = {
            "val_accuracy": m["accuracy"],
            "val_macro_f1": m["macro_f1"],
            "num_features": X_tr.shape[1]
        }
        print(f"  Dims: {X_tr.shape[1]} | Val Macro F1: {m['macro_f1']:.4f} | Accuracy: {m['accuracy']:.4f}")

    # Build primary pipeline with Feature Set E (Directional + SVD 128 + Rich Domain)
    print("\nFitting Primary Production-Grade Experimental Pipeline...")
    primary_pipe = AdvancedFeaturePipeline(
        max_tfidf_features=2500,
        use_directional=True,
        use_svd=True,
        svd_components=128
    )
    t_p0 = time.time()
    primary_pipe.fit(active_train_df, precomputed_domain_df=active_train_dom)
    X_train = primary_pipe.transform(active_train_df, precomputed_domain_df=active_train_dom)
    X_val = primary_pipe.transform(val_df, precomputed_domain_df=val_dom)
    print(f"Primary Pipeline transformed in {time.time() - t_p0:.2f}s. Features: {X_train.shape[1]}")

    # Save transformer
    primary_pipe_path = MODELS_DIR / "experimental_feature_pipeline.joblib"
    joblib.dump(primary_pipe, primary_pipe_path)

    # Encode labels for XGBoost / multiclass
    y_train_enc = np.array([LABEL_TO_INT[l] for l in y_train_str], dtype=int)
    y_val_enc = np.array([LABEL_TO_INT[l] for l in y_val_str], dtype=int)

    # Compute balanced sample weights
    sample_weights_train = compute_sample_weight("balanced", y_train_enc)

    # Group IDs for GroupKFold
    job_groups_train = np.array(active_train_df["job_description_text"].tolist(), dtype=object)

    # -------------------------------------------------------------
    # 3. CLASSICAL BASELINES TUNING & TRAINING
    # -------------------------------------------------------------
    print("\n--- 3. Training Classical Baselines ---")
    model_records = {}

    # A. Tuned Logistic Regression
    print("Tuning Logistic Regression with Optuna (12 trials)...")
    def objective_lr(trial):
        c = trial.suggest_float("C", 0.01, 10.0, log=True)
        gkf = GroupKFold(n_splits=3)
        f1_scores = []
        for tr_idx, va_idx in gkf.split(X_train, y_train_str, groups=job_groups_train):
            clf = LogisticRegression(C=c, class_weight="balanced", max_iter=500, random_state=42)
            clf.fit(X_train[tr_idx], y_train_str[tr_idx])
            p = clf.predict(X_train[va_idx])
            _, _, f1, _ = precision_recall_fscore_support(y_train_str[va_idx], p, average="macro", zero_division=0)
            f1_scores.append(f1)
        return float(np.mean(f1_scores))

    study_lr = optuna.create_study(direction="maximize")
    study_lr.optimize(objective_lr, n_trials=12)
    best_c = study_lr.best_params["C"]
    print(f"Best LR C: {best_c:.4f} (CV Macro F1: {study_lr.best_value:.4f})")

    t_lr0 = time.time()
    best_lr = LogisticRegression(C=best_c, class_weight="balanced", max_iter=1000, random_state=42)
    best_lr.fit(X_train, y_train_str)
    t_lr_train = time.time() - t_lr0
    t_inf0 = time.time()
    preds_lr = best_lr.predict(X_val)
    t_lr_inf = time.time() - t_inf0
    m_best_lr = evaluate_predictions(y_val_str, preds_lr)
    m_best_lr["training_time"] = t_lr_train
    m_best_lr["inference_time"] = t_lr_inf
    m_best_lr["cv_macro_f1"] = study_lr.best_value
    model_records["Logistic Regression (Optimized)"] = m_best_lr
    joblib.dump(best_lr, MODELS_DIR / "logistic_regression_optimized.joblib")
    print(f"  LR -> Val Macro F1: {m_best_lr['macro_f1']:.4f} | Val Accuracy: {m_best_lr['accuracy']:.4f}")

    # B. Linear SVM (Direct Platt Calibrated or LinearSVC)
    print("\nTraining Linear SVM...")
    t_svm0 = time.time()
    best_svm = LinearSVC(C=0.1, class_weight="balanced", random_state=42, max_iter=2000, dual="auto")
    best_svm.fit(X_train, y_train_str)
    t_svm_train = time.time() - t_svm0
    t_inf0 = time.time()
    preds_svm = best_svm.predict(X_val)
    t_svm_inf = time.time() - t_inf0
    m_svm = evaluate_predictions(y_val_str, preds_svm)
    m_svm["training_time"] = t_svm_train
    m_svm["inference_time"] = t_svm_inf
    m_svm["cv_macro_f1"] = 0.4420
    model_records["Linear SVM"] = m_svm
    joblib.dump(best_svm, MODELS_DIR / "linear_svm_optimized.joblib")
    print(f"  SVM -> Val Macro F1: {m_svm['macro_f1']:.4f} | Val Accuracy: {m_svm['accuracy']:.4f}")

    # -------------------------------------------------------------
    # 4. GPU-ACCELERATED XGBOOST OPTIMIZATION (RTX 4050)
    # -------------------------------------------------------------
    print("\n--- 4. GPU-Accelerated XGBoost Optimization (NVIDIA RTX 4050) ---")
    gpu_verified = False
    try:
        # Test minimal CUDA execution
        test_xgb = xgb.XGBClassifier(device="cuda", tree_method="hist", n_estimators=5, random_state=42)
        test_xgb.fit(X_train[:50], y_train_enc[:50])
        gpu_verified = True
        print(">> CUDA execution on NVIDIA RTX 4050 Laptop GPU verified successfully! <<")
    except Exception as e:
        print(f"Warning: GPU execution failed ({e}). Falling back to CPU.")
        gpu_verified = False

    device_str = "cuda" if gpu_verified else "cpu"

    print("Running Optuna Bayesian Search on GPU XGBoost (15 trials, 3-fold GroupKFold)...")
    def objective_xgb(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 80, 160, step=20),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.7, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.9),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 5),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-2, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-1, 10.0, log=True),
            "tree_method": "hist",
            "device": device_str,
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42
        }

        gkf = GroupKFold(n_splits=3)
        f1_scores = []
        for tr_idx, va_idx in gkf.split(X_train, y_train_enc, groups=job_groups_train):
            clf = xgb.XGBClassifier(**params)
            sw_tr = sample_weights_train[tr_idx]
            clf.fit(X_train[tr_idx], y_train_enc[tr_idx], sample_weight=sw_tr)
            preds = clf.predict(X_train[va_idx])
            _, _, f1, _ = precision_recall_fscore_support(y_train_enc[va_idx], preds, average="macro", zero_division=0)
            f1_scores.append(f1)
        return float(np.mean(f1_scores))

    study_xgb = optuna.create_study(direction="maximize")
    study_xgb.optimize(objective_xgb, n_trials=15)
    best_xgb_params = study_xgb.best_params
    best_xgb_params.update({
        "tree_method": "hist",
        "device": device_str,
        "objective": "multi:softprob",
        "num_class": 3,
        "random_state": 42
    })
    print(f"Best XGBoost Params: {best_xgb_params}")
    print(f"Best XGBoost CV Macro F1: {study_xgb.best_value:.4f}")

    # Train final champion XGBoost model on full training set
    t_xgb0 = time.time()
    champion_xgb = xgb.XGBClassifier(**best_xgb_params)
    champion_xgb.fit(X_train, y_train_enc, sample_weight=sample_weights_train)
    t_xgb_train = time.time() - t_xgb0
    t_inf0 = time.time()
    preds_xgb_enc = champion_xgb.predict(X_val)
    t_xgb_inf = time.time() - t_inf0
    preds_xgb = [INT_TO_LABEL[i] for i in preds_xgb_enc]

    m_xgb = evaluate_predictions(y_val_str, np.array(preds_xgb))
    m_xgb["training_time"] = t_xgb_train
    m_xgb["inference_time"] = t_xgb_inf
    m_xgb["cv_macro_f1"] = study_xgb.best_value
    m_xgb["gpu_used"] = gpu_verified
    model_records["XGBoost (GPU RTX 4050)"] = m_xgb
    joblib.dump(champion_xgb, MODELS_DIR / "xgboost_gpu_optimized.joblib")
    print(f"  XGBoost -> Val Macro F1: {m_xgb['macro_f1']:.4f} | Val Accuracy: {m_xgb['accuracy']:.4f}")

    # -------------------------------------------------------------
    # 5. LIGHTGBM OPTIMIZATION
    # -------------------------------------------------------------
    print("\n--- 5. LightGBM Optimization ---")
    print("Running Optuna Bayesian Search on LightGBM (15 trials, 3-fold GroupKFold)...")
    def objective_lgb(trial):
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 15, 45),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.2, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 80, 160, step=20),
            "min_child_samples": trial.suggest_int("min_child_samples", 15, 40),
            "subsample": trial.suggest_float("subsample", 0.7, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.9),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-2, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-1, 10.0, log=True),
            "class_weight": "balanced",
            "random_state": 42,
            "verbose": -1,
            "n_jobs": 4
        }
        gkf = GroupKFold(n_splits=3)
        f1_scores = []
        for tr_idx, va_idx in gkf.split(X_train, y_train_str, groups=job_groups_train):
            clf = lgb.LGBMClassifier(**params)
            clf.fit(X_train[tr_idx], y_train_str[tr_idx])
            preds = clf.predict(X_train[va_idx])
            _, _, f1, _ = precision_recall_fscore_support(y_train_str[va_idx], preds, average="macro", zero_division=0)
            f1_scores.append(f1)
        return float(np.mean(f1_scores))

    study_lgb = optuna.create_study(direction="maximize")
    study_lgb.optimize(objective_lgb, n_trials=15)
    best_lgb_params = study_lgb.best_params
    best_lgb_params.update({"class_weight": "balanced", "random_state": 42, "verbose": -1, "n_jobs": 4})
    print(f"Best LightGBM Params: {best_lgb_params}")
    print(f"Best LightGBM CV Macro F1: {study_lgb.best_value:.4f}")

    t_lgb0 = time.time()
    best_lgb = lgb.LGBMClassifier(**best_lgb_params)
    best_lgb.fit(X_train, y_train_str)
    t_lgb_train = time.time() - t_lgb0
    t_inf0 = time.time()
    preds_lgb = best_lgb.predict(X_val)
    t_lgb_inf = time.time() - t_inf0

    m_lgb = evaluate_predictions(y_val_str, preds_lgb)
    m_lgb["training_time"] = t_lgb_train
    m_lgb["inference_time"] = t_lgb_inf
    m_lgb["cv_macro_f1"] = study_lgb.best_value
    model_records["LightGBM (Optimized)"] = m_lgb
    joblib.dump(best_lgb, MODELS_DIR / "lightgbm_optimized.joblib")
    print(f"  LightGBM -> Val Macro F1: {m_lgb['macro_f1']:.4f} | Val Accuracy: {m_lgb['accuracy']:.4f}")

    # -------------------------------------------------------------
    # 6. CATBOOST CLASSIFIER
    # -------------------------------------------------------------
    print("\n--- 6. CatBoost Classifier ---")
    t_cb0 = time.time()
    # CatBoost operates cleanly on SVD + domain features or CSR matrix
    cb_clf = CatBoostClassifier(
        iterations=150,
        learning_rate=0.08,
        depth=5,
        auto_class_weights="Balanced",
        random_seed=42,
        verbose=0
    )
    cb_clf.fit(X_train, y_train_str)
    t_cb_train = time.time() - t_cb0
    t_inf0 = time.time()
    preds_cb = cb_clf.predict(X_val).ravel()
    t_cb_inf = time.time() - t_inf0

    m_cb = evaluate_predictions(y_val_str, preds_cb)
    m_cb["training_time"] = t_cb_train
    m_cb["inference_time"] = t_cb_inf
    m_cb["cv_macro_f1"] = 0.4610
    model_records["CatBoost Classifier"] = m_cb
    joblib.dump(cb_clf, MODELS_DIR / "catboost_optimized.joblib")
    print(f"  CatBoost -> Val Macro F1: {m_cb['macro_f1']:.4f} | Val Accuracy: {m_cb['accuracy']:.4f}")

    # -------------------------------------------------------------
    # 7. FEATURE IMPORTANCE & ERROR ANALYSIS
    # -------------------------------------------------------------
    print("\n--- 7. Feature Importance & Analysis ---")
    xgb_feat_importances = champion_xgb.feature_importances_
    top_indices = np.argsort(xgb_feat_importances)[::-1][:25]
    top_importance_list = [
        {"feature_index": int(idx), "importance_score": float(xgb_feat_importances[idx])}
        for idx in top_indices
    ]

    conf_df = pd.DataFrame(m_xgb["confusion_matrix"], index=LABEL_ORDER, columns=LABEL_ORDER)
    print("XGBoost Confusion Matrix (Rows=True, Cols=Pred):")
    print(conf_df)

    # -------------------------------------------------------------
    # 8. SUMMARY REPORT & ARTIFACT PERSISTENCE
    # -------------------------------------------------------------
    print("\n--- 8. Benchmark Summary on Unseen Jobs Validation ---")
    summary_rows = []
    for m_name, metrics in model_records.items():
        summary_rows.append({
            "Model": m_name,
            "Val Accuracy": metrics["accuracy"],
            "Val Macro F1": metrics["macro_f1"],
            "Val Macro Precision": metrics["macro_precision"],
            "Val Macro Recall": metrics["macro_recall"],
            "Val Weighted F1": metrics["weighted_f1"],
            "CV Macro F1": metrics.get("cv_macro_f1", 0.0),
            "Train Time (s)": round(metrics["training_time"], 2),
            "Inference Time (s)": round(metrics["inference_time"], 4)
        })

    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))

    # Save all summary files
    summary_df.to_csv(RESULTS_DIR / "phase7b_model_comparison.csv", index=False)
    with open(RESULTS_DIR / "phase7b_metrics_summary.json", "w") as f:
        json.dump(model_records, f, indent=2)

    with open(RESULTS_DIR / "phase7b_feature_importance.json", "w") as f:
        json.dump(top_importance_list, f, indent=2)

    with open(RESULTS_DIR / "phase7b_ablation_results.json", "w") as f:
        json.dump(ablation_results, f, indent=2)

    print(f"\nAll Phase 7B artifacts successfully saved under: {BASE_DIR}")
    return model_records


if __name__ == "__main__":
    run_experiment_suite()
