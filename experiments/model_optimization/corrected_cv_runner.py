"""
Phase 7B-C: Corrected Cross-Validation Pipeline with Strict Fold-Level Preprocessing Isolation.
Guarantees:
- Zero job overlap between training and validation folds (GroupKFold).
- Fresh TfidfVectorizer fitted inside each training fold only.
- Fresh TruncatedSVD (128 components) fitted inside each training fold only.
- Fresh RobustScaler fitted on domain features inside each training fold only.
- Zero learned parameters shared across folds.
- Zero access to validation labels or official held-out test data.
Evaluates:
1. Optimized Logistic Regression (C=0.0656)
2. Optimized Linear SVM (C=0.10)
3. Optimized LightGBM (num_leaves=29, max_depth=5, n_estimators=70)
4. GPU-Accelerated XGBoost (NVIDIA RTX 4050, tree_method='hist', device='cuda')
"""

import time
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
from src.utils.split_manager import get_unseen_jobs_split

RESULTS_DIR = Path("experiments/model_optimization/results")
CACHE_DIR = Path("experiments/model_optimization/data_cache")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LABEL_ORDER = ["No Fit", "Good Fit", "Potential Fit"]
LABEL_TO_INT = {l: i for i, l in enumerate(LABEL_ORDER)}
INT_TO_LABEL = {i: l for i, l in enumerate(LABEL_ORDER)}


def build_fold_features(
    train_resumes: List[str],
    train_jobs: List[str],
    val_resumes: List[str],
    val_jobs: List[str],
    train_dom_raw: np.ndarray,
    val_dom_raw: np.ndarray,
    max_tfidf_features: int = 2500,
    svd_components: int = 128
) -> Tuple[sparse.csr_matrix, sparse.csr_matrix, Dict[str, Any]]:
    """
    Constructs feature matrices with STRICT zero-leakage fold-level fitting.
    Vectorizers, SVD, and Scalers are instantiated and fitted on training data only.
    """
    clean_r_tr = [clean_text(t) for t in train_resumes]
    clean_j_tr = [clean_text(t) for t in train_jobs]
    clean_r_va = [clean_text(t) for t in val_resumes]
    clean_j_va = [clean_text(t) for t in val_jobs]

    # 1. Fresh TF-IDF fitted ONLY on fold training corpus
    corpus_tr = clean_r_tr + clean_j_tr
    min_doc_freq = min(3, max(1, len(corpus_tr)))
    vectorizer = TfidfVectorizer(
        max_features=max_tfidf_features,
        ngram_range=(1, 2),
        min_df=min_doc_freq,
        sublinear_tf=True,
        norm="l2",
        token_pattern=r"(?u)\b[a-zA-Z0-9_\.\#\+\-]+\b"
    )
    vectorizer.fit(corpus_tr)

    V_r_tr = vectorizer.transform(clean_r_tr)
    V_j_tr = vectorizer.transform(clean_j_tr)
    V_r_va = vectorizer.transform(clean_r_va)
    V_j_va = vectorizer.transform(clean_j_va)

    # Directional features
    V_diff_tr = abs(V_r_tr - V_j_tr)
    V_diff_va = abs(V_r_va - V_j_va)

    V_signed_tr = V_r_tr - V_j_tr
    V_signed_va = V_r_va - V_j_va

    V_dot_tr = V_r_tr.multiply(V_j_tr)
    V_dot_va = V_r_va.multiply(V_j_va)

    # Lexical interaction scalars
    cos_tr = np.asarray((V_r_tr.multiply(V_j_tr)).sum(axis=1)).reshape(-1, 1)
    cos_va = np.asarray((V_r_va.multiply(V_j_va)).sum(axis=1)).reshape(-1, 1)
    man_tr = np.asarray(V_diff_tr.sum(axis=1)).reshape(-1, 1)
    man_va = np.asarray(V_diff_va.sum(axis=1)).reshape(-1, 1)
    euc_tr = np.sqrt(np.asarray(V_diff_tr.power(2).sum(axis=1))).reshape(-1, 1)
    euc_va = np.sqrt(np.asarray(V_diff_va.power(2).sum(axis=1))).reshape(-1, 1)
    inter_tr = np.hstack([cos_tr, man_tr, euc_tr])
    inter_va = np.hstack([cos_va, man_va, euc_va])

    # 2. Fresh TruncatedSVD fitted ONLY on fold training TF-IDF
    V_corpus_tr = vectorizer.transform(corpus_tr)
    n_comp = min(svd_components, max(1, V_corpus_tr.shape[1] - 1))
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    svd.fit(V_corpus_tr)

    svd_r_tr = svd.transform(V_r_tr)
    svd_j_tr = svd.transform(V_j_tr)
    svd_r_va = svd.transform(V_r_va)
    svd_j_va = svd.transform(V_j_va)

    svd_diff_tr = abs(svd_r_tr - svd_j_tr)
    svd_diff_va = abs(svd_r_va - svd_j_va)
    svd_dot_tr = svd_r_tr * svd_j_tr
    svd_dot_va = svd_r_va * svd_j_va

    norm_r_tr = np.linalg.norm(svd_r_tr, axis=1, keepdims=True) + 1e-9
    norm_j_tr = np.linalg.norm(svd_j_tr, axis=1, keepdims=True) + 1e-9
    svd_cos_tr = np.sum((svd_r_tr / norm_r_tr) * (svd_j_tr / norm_j_tr), axis=1, keepdims=True)

    norm_r_va = np.linalg.norm(svd_r_va, axis=1, keepdims=True) + 1e-9
    norm_j_va = np.linalg.norm(svd_j_va, axis=1, keepdims=True) + 1e-9
    svd_cos_va = np.sum((svd_r_va / norm_r_va) * (svd_j_va / norm_j_va), axis=1, keepdims=True)

    svd_feats_tr = np.hstack([svd_diff_tr, svd_dot_tr, svd_cos_tr])
    svd_feats_va = np.hstack([svd_diff_va, svd_dot_va, svd_cos_va])

    # 3. Fresh RobustScaler fitted ONLY on fold training domain features
    scaler = RobustScaler()
    scaler.fit(train_dom_raw)
    dom_scaled_tr = scaler.transform(train_dom_raw)
    dom_scaled_va = scaler.transform(val_dom_raw)

    # 4. Assemble CSR matrices
    X_tr = sparse.hstack([
        V_diff_tr, V_signed_tr, V_dot_tr,
        sparse.csr_matrix(inter_tr),
        sparse.csr_matrix(svd_feats_tr),
        sparse.csr_matrix(dom_scaled_tr)
    ], format="csr")

    X_va = sparse.hstack([
        V_diff_va, V_signed_va, V_dot_va,
        sparse.csr_matrix(inter_va),
        sparse.csr_matrix(svd_feats_va),
        sparse.csr_matrix(dom_scaled_va)
    ], format="csr")

    metadata = {
        "vocab_size": len(vectorizer.vocabulary_),
        "n_svd_components": svd.n_components,
        "n_features_total": X_tr.shape[1]
    }
    return X_tr, X_va, metadata


def compute_fold_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    p_cls, r_cls, f1_cls, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABEL_ORDER, zero_division=0)
    return {
        "accuracy": acc,
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
        "weighted_f1": float(f1_wt),
        "recall_no_fit": float(r_cls[0]),
        "recall_good_fit": float(r_cls[1]),
        "recall_potential_fit": float(r_cls[2])
    }


def run_corrected_cv():
    print("=" * 80)
    print("PHASE 7B-C: CORRECTED CROSS-VALIDATION WITH FOLD-LEVEL PREPROCESSING ISOLATION")
    print("=" * 80)
    start_total_time = time.time()

    # Load data
    train_df, _, _ = get_unseen_jobs_split()
    train_dom = pd.read_parquet(CACHE_DIR / "train_domain_features.parquet")

    # Filter out the 12 conflicting duplicate rows
    dups_mask = train_df.duplicated(subset=["resume_text", "job_description_text"], keep=False)
    active_train_df = train_df[~dups_mask].reset_index(drop=True)
    active_train_dom = train_dom[~dups_mask].reset_index(drop=True)

    y_all_str = np.array(active_train_df["label"].tolist(), dtype=object)
    y_all_enc = np.array([LABEL_TO_INT[l] for l in y_all_str], dtype=int)
    job_groups = np.array(active_train_df["job_description_text"].tolist(), dtype=object)

    print(f"Total Active Training Records: {len(active_train_df):,} across {len(set(job_groups))} distinct jobs.")

    # 5-Fold GroupKFold
    N_SPLITS = 5
    gkf = GroupKFold(n_splits=N_SPLITS)
    splits = list(gkf.split(active_train_df, y_all_str, groups=job_groups))

    # Verify zero leakage across splits
    for fold_idx, (tr_idx, va_idx) in enumerate(splits):
        tr_jobs = set(job_groups[tr_idx])
        va_jobs = set(job_groups[va_idx])
        overlap = len(tr_jobs.intersection(va_jobs))
        assert overlap == 0, f"Error: Fold {fold_idx + 1} has {overlap} overlapping jobs!"
    print(f"Verified: Zero overlapping jobs across all {N_SPLITS} folds (GroupKFold).\n")

    # Models to evaluate
    models_to_test = {
        "Optimized Logistic Regression": {
            "type": "sklearn",
            "constructor": lambda: LogisticRegression(C=0.0656, class_weight="balanced", max_iter=600, random_state=42)
        },
        "Optimized Linear SVM": {
            "type": "sklearn",
            "constructor": lambda: LinearSVC(C=0.10, class_weight="balanced", max_iter=2500, random_state=42, dual="auto")
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
        }
    }

    # Tracking storage
    per_model_fold_metrics = {m_name: [] for m_name in models_to_test}
    per_model_oof_preds = {m_name: [None] * len(active_train_df) for m_name in models_to_test}
    per_model_train_times = {m_name: 0.0 for m_name in models_to_test}

    # Execute 5 Folds
    for fold_idx, (tr_idx, va_idx) in enumerate(splits):
        f_num = fold_idx + 1
        print(f"--- Processing Fold {f_num}/{N_SPLITS} (Train: {len(tr_idx):,} rows, Val: {len(va_idx):,} rows) ---")
        t_fold0 = time.time()

        r_tr = active_train_df.iloc[tr_idx]["resume_text"].tolist()
        j_tr = active_train_df.iloc[tr_idx]["job_description_text"].tolist()
        r_va = active_train_df.iloc[va_idx]["resume_text"].tolist()
        j_va = active_train_df.iloc[va_idx]["job_description_text"].tolist()

        dom_tr = active_train_dom.iloc[tr_idx].values
        dom_va = active_train_dom.iloc[va_idx].values

        # Build feature matrices strictly fitted on training fold
        X_tr, X_va, meta = build_fold_features(
            r_tr, j_tr, r_va, j_va, dom_tr, dom_va,
            max_tfidf_features=2500, svd_components=128
        )
        print(f"  [Fold {f_num} Features] Dimensions: {X_tr.shape[1]:,} | TF-IDF Vocab: {meta['vocab_size']:,} | Fitted in {time.time() - t_fold0:.2f}s")

        y_tr_str = y_all_str[tr_idx]
        y_va_str = y_all_str[va_idx]
        y_tr_enc = y_all_enc[tr_idx]
        y_va_enc = y_all_enc[va_idx]

        sw_tr = compute_sample_weight("balanced", y_tr_enc)

        # Train and evaluate each model on this fold
        for m_name, m_cfg in models_to_test.items():
            clf = m_cfg["constructor"]()
            t_m0 = time.time()

            if m_cfg["type"] == "xgboost":
                clf.fit(X_tr, y_tr_enc, sample_weight=sw_tr)
                t_fit = time.time() - t_m0
                preds_enc = clf.predict(X_va)
                preds_str = [INT_TO_LABEL[i] for i in preds_enc]
            elif m_cfg["type"] == "lightgbm":
                clf.fit(X_tr, y_tr_str)
                t_fit = time.time() - t_m0
                preds_str = clf.predict(X_va).tolist()
            else:  # sklearn (Logistic Regression, Linear SVM)
                clf.fit(X_tr, y_tr_str)
                t_fit = time.time() - t_m0
                preds_str = clf.predict(X_va).tolist()

            per_model_train_times[m_name] += t_fit

            # Store OOF predictions
            for local_i, global_i in enumerate(va_idx):
                per_model_oof_preds[m_name][global_i] = preds_str[local_i]

            f_metrics = compute_fold_metrics(y_va_str, np.array(preds_str))
            f_metrics["fold"] = f_num
            f_metrics["train_time"] = t_fit
            per_model_fold_metrics[m_name].append(f_metrics)

            print(f"    {m_name:32s} -> Acc: {f_metrics['accuracy']:.4f} | Macro F1: {f_metrics['macro_f1']:.4f} | Fit: {t_fit:.2f}s")

    print("\n" + "=" * 80)
    print("PHASE 7B-C: CORRECTED CROSS-VALIDATION SUMMARY RESULTS (5-FOLD GROUP-DISJOINT)")
    print("=" * 80)

    summary_rows = []
    overall_json = {}

    for m_name, f_list in per_model_fold_metrics.items():
        accs = [m["accuracy"] for m in f_list]
        f1s = [m["macro_f1"] for m in f_list]
        precs = [m["macro_precision"] for m in f_list]
        recs = [m["macro_recall"] for m in f_list]
        r_nofit = [m["recall_no_fit"] for m in f_list]
        r_goodfit = [m["recall_good_fit"] for m in f_list]
        r_potfit = [m["recall_potential_fit"] for m in f_list]

        # Aggregated OOF metrics
        oof_preds = np.array(per_model_oof_preds[m_name])
        oof_acc = float(accuracy_score(y_all_str, oof_preds))
        oof_p_macro, oof_r_macro, oof_f1_macro, _ = precision_recall_fscore_support(y_all_str, oof_preds, average="macro", zero_division=0)
        oof_cm = confusion_matrix(y_all_str, oof_preds, labels=LABEL_ORDER).tolist()

        row = {
            "Model": m_name,
            "Mean CV Accuracy": float(np.mean(accs)),
            "Std CV Accuracy": float(np.std(accs)),
            "Mean CV Macro F1": float(np.mean(f1s)),
            "Std CV Macro F1": float(np.std(f1s)),
            "OOF Macro F1": float(oof_f1_macro),
            "OOF Accuracy": float(oof_acc),
            "Mean Recall No Fit": float(np.mean(r_nofit)),
            "Mean Recall Good Fit": float(np.mean(r_goodfit)),
            "Mean Recall Potential Fit": float(np.mean(r_potfit)),
            "Total Fit Time (s)": round(per_model_train_times[m_name], 2)
        }
        summary_rows.append(row)

        overall_json[m_name] = {
            "per_fold": f_list,
            "aggregate_oof": {
                "accuracy": oof_acc,
                "macro_f1": oof_f1_macro,
                "macro_precision": float(oof_p_macro),
                "macro_recall": float(oof_r_macro),
                "confusion_matrix": oof_cm
            },
            "mean_cv_accuracy": float(np.mean(accs)),
            "std_cv_accuracy": float(np.std(accs)),
            "mean_cv_macro_f1": float(np.mean(f1s)),
            "std_cv_macro_f1": float(np.std(f1s)),
            "total_fit_time_seconds": round(per_model_train_times[m_name], 2)
        }

    summary_df = pd.DataFrame(summary_rows)
    # Sort strictly by Mean CV Macro F1 descending
    summary_df = summary_df.sort_values(by="Mean CV Macro F1", ascending=False).reset_index(drop=True)
    print(summary_df.to_string(index=False))

    # Save CSV and JSON
    summary_df.to_csv(RESULTS_DIR / "corrected_cv_metrics.csv", index=False)
    with open(RESULTS_DIR / "corrected_cv_summary.json", "w") as f:
        json.dump(overall_json, f, indent=2)

    # Generate Visualization Chart
    plt.figure(figsize=(11, 6))
    x = np.arange(len(summary_df))
    width = 0.35
    plt.bar(x - width/2, summary_df["Mean CV Accuracy"], width, yerr=summary_df["Std CV Accuracy"], capsize=5, label="Mean CV Accuracy", color="#2563eb")
    plt.bar(x + width/2, summary_df["Mean CV Macro F1"], width, yerr=summary_df["Std CV Macro F1"], capsize=5, label="Mean CV Macro F1", color="#10b981")
    plt.axhline(0.4442, color="#ef4444", linestyle="--", label="Phase 3 Production Baseline CV Macro F1 (0.4442)")
    plt.xlabel("Model Architecture")
    plt.ylabel("Cross-Validation Score")
    plt.title("Phase 7B-C: Corrected Zero-Leakage 5-Fold GroupKFold Cross-Validation")
    plt.xticks(x, summary_df["Model"], rotation=15, ha="right")
    plt.ylim(0.35, 0.60)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "corrected_cv_comparison.png", dpi=150)
    plt.close()

    # Generate Confusion Matrix for Champion
    champion_name = summary_df.iloc[0]["Model"]
    champ_cm = np.array(overall_json[champion_name]["aggregate_oof"]["confusion_matrix"])

    plt.figure(figsize=(7, 6))
    sns.heatmap(champ_cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER)
    plt.title(f"Aggregated OOF Confusion Matrix: {champion_name}\nMean CV Macro F1: {summary_df.iloc[0]['Mean CV Macro F1']:.4f}")
    plt.xlabel("Predicted Class")
    plt.ylabel("True Class")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "corrected_cv_champion_confusion_matrix.png", dpi=150)
    plt.close()

    total_time = time.time() - start_total_time
    print(f"\nCompleted Corrected 5-Fold Evaluation in {total_time:.2f} seconds.")
    print(f"\n>>> OFFICIALLY SELECTED CANDIDATE MODEL: {champion_name} <<<")
    print(f"Mean CV Macro F1: {summary_df.iloc[0]['Mean CV Macro F1']:.4f} +/- {summary_df.iloc[0]['Std CV Macro F1']:.4f}")
    print(f"Mean CV Accuracy: {summary_df.iloc[0]['Mean CV Accuracy']:.4f} +/- {summary_df.iloc[0]['Std CV Accuracy']:.4f}")
    print(f"Out-of-Fold Macro F1: {summary_df.iloc[0]['OOF Macro F1']:.4f} | Out-of-Fold Accuracy: {summary_df.iloc[0]['OOF Accuracy']:.4f}")

    return overall_json


if __name__ == "__main__":
    run_corrected_cv()
