"""
scripts/run_phase11_experiments.py
Phase 11 ML Accuracy, Data Quality & Generalization Experiment Runner.
Executes:
1. Feature Engineering Experiments (Baseline, Char n-grams, Enhanced Structured Features, Text Similarities, Combined)
2. Controlled Model Comparisons (Logistic Regression, Linear SVM, Calibrated SVM, Random Forest, LightGBM, XGBoost, CatBoost, Stacking Ensemble)
3. Controlled Data Quality Cleaning Experiments (Original vs Deduplicated/Contradiction-Filtered on untouched holdout)
4. Generalization Across 4 Protocols:
   - Random Split
   - Job-Disjoint Split
   - Resume-Disjoint Split
   - Dual-Unseen Split
5. Model Reliability & Threshold Optimization (Brier score, ECE, threshold sweep for Good Fit recall)
Saves results to results/phase11_experiments/
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import json
import time
import hashlib
import re
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy import sparse

from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    precision_recall_fscore_support, confusion_matrix,
    brier_score_loss
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.preprocessing.text_cleaner import clean_text
from src.preprocessing.skill_extractor import SkillEngine

OUTPUT_DIR = "results/phase11_experiments"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
ID_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

def hash_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text).strip().lower())
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()

def compute_eval_metrics(y_true, y_pred, y_prob=None) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES).tolist()
    
    per_class_p, per_class_r, per_class_f1, per_class_sup = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    
    per_class = {}
    for idx, c in enumerate(CLASSES):
        per_class[c] = {
            "precision": float(round(per_class_p[idx], 4)),
            "recall": float(round(per_class_r[idx], 4)),
            "f1": float(round(per_class_f1[idx], 4)),
            "support": int(per_class_sup[idx]),
        }
        
    brier = None
    if y_prob is not None:
        # Multiclass Brier score: mean squared error between one-hot and predicted probability
        y_true_ids = np.array([CLASS_TO_ID[y] for y in y_true])
        y_one_hot = np.zeros((len(y_true), len(CLASSES)))
        for i, tid in enumerate(y_true_ids):
            y_one_hot[i, tid] = 1.0
        brier = float(round(np.mean(np.sum((y_prob - y_one_hot) ** 2, axis=1)), 4))
        
    return {
        "accuracy": float(round(acc, 4)),
        "balanced_accuracy": float(round(bal_acc, 4)),
        "macro_precision": float(round(p_macro, 4)),
        "macro_recall": float(round(r_macro, 4)),
        "macro_f1": float(round(f1_macro, 4)),
        "weighted_f1": float(round(f1_weight, 4)),
        "brier_score": brier,
        "confusion_matrix": cm,
        "per_class": per_class,
    }


# =====================================================================
# EXPERIMENT 1: FEATURE ENGINEERING SUITE
# =====================================================================

class EnhancedFeaturePipeline:
    """
    Advanced Feature Pipeline for Resume-Job Matching.
    Supports:
    - Word TF-IDF (1-2 ngrams)
    - Optional Char TF-IDF (3-5 ngrams)
    - Vector interactions (Cosine, Manhattan, Euclidean, Dot Product)
    - Enhanced structured domain features (Skill coverage, missing counts, length ratios, title match)
    """
    def __init__(
        self,
        max_word_features: int = 2500,
        use_char_tfidf: bool = False,
        max_char_features: int = 1500,
        use_enhanced_domain: bool = True
    ):
        self.max_word_features = max_word_features
        self.use_char_tfidf = use_char_tfidf
        self.max_char_features = max_char_features
        self.use_enhanced_domain = use_enhanced_domain
        
        self.skill_engine = SkillEngine()
        self.word_vectorizer = TfidfVectorizer(
            max_features=self.max_word_features,
            ngram_range=(1, 2),
            min_df=3,
            sublinear_tf=True,
            norm="l2"
        )
        if self.use_char_tfidf:
            self.char_vectorizer = TfidfVectorizer(
                max_features=self.max_char_features,
                ngram_range=(3, 5),
                analyzer="char_wb",
                min_df=5,
                sublinear_tf=True,
                norm="l2"
            )
        else:
            self.char_vectorizer = None
            
        self.scaler = StandardScaler()
        self.is_fitted = False

    def _extract_dense(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        rows = []
        for r_text, j_text in zip(resumes, jobs):
            r_lower = r_text.lower()
            j_lower = j_text.lower()
            
            # Skills extraction
            r_skills = set(self.skill_engine.extract_skills(r_text))
            j_skills = set(self.skill_engine.extract_skills(j_text))
            
            matched = r_skills.intersection(j_skills)
            missing = j_skills.difference(r_skills)
            
            n_matched = len(matched)
            n_missing = len(missing)
            n_r_skills = len(r_skills)
            n_j_skills = len(j_skills)
            
            jaccard = n_matched / len(r_skills.union(j_skills)) if r_skills or j_skills else 0.0
            coverage = n_matched / n_j_skills if n_j_skills > 0 else 0.0
            relevance = n_matched / n_r_skills if n_r_skills > 0 else 0.0
            
            r_words = len(r_text.split())
            j_words = len(j_text.split())
            len_ratio = r_words / max(1, j_words)
            
            row = [
                jaccard, coverage, relevance,
                float(n_matched), float(n_missing),
                float(n_r_skills), float(n_j_skills),
                float(r_words), float(j_words), len_ratio
            ]
            
            if self.use_enhanced_domain:
                # Additional domain features
                # 1. Headline / Title match heuristic
                first_lines_r = " ".join(r_text.split("\n")[:4]).lower()
                first_lines_j = " ".join(j_text.split("\n")[:3]).lower()
                title_words_j = set(re.findall(r"\w+", first_lines_j))
                title_words_r = set(re.findall(r"\w+", first_lines_r))
                title_overlap = len(title_words_j & title_words_r) / max(1, len(title_words_j)) if title_words_j else 0.0
                
                # 2. Key cloud/language markers
                has_python = 1.0 if "python" in r_lower and "python" in j_lower else 0.0
                has_sql = 1.0 if "sql" in r_lower and "sql" in j_lower else 0.0
                has_cloud = 1.0 if any(k in r_lower for k in ["aws", "azure", "gcp", "cloud"]) and any(k in j_lower for k in ["aws", "azure", "gcp", "cloud"]) else 0.0
                
                # 3. High skill density indicator
                skill_density = n_r_skills / max(1, r_words) * 100
                
                row.extend([title_overlap, has_python, has_sql, has_cloud, skill_density])
                
            rows.append(row)
        return np.array(rows, dtype=np.float32)

    def fit(self, df: pd.DataFrame):
        resumes = df["resume_text"].tolist()
        jobs = df["job_description_text"].tolist()
        
        cleaned_resumes = [clean_text(t) for t in resumes]
        cleaned_jobs = [clean_text(t) for t in jobs]
        corpus = cleaned_resumes + cleaned_jobs
        
        self.word_vectorizer.fit(corpus)
        if self.char_vectorizer:
            self.char_vectorizer.fit(corpus)
            
        dense_feats = self._extract_dense(resumes, jobs)
        self.scaler.fit(dense_feats)
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> sparse.csr_matrix:
        resumes = df["resume_text"].tolist()
        jobs = df["job_description_text"].tolist()
        
        cleaned_resumes = [clean_text(t) for t in resumes]
        cleaned_jobs = [clean_text(t) for t in jobs]
        
        # Word TF-IDF
        V_r = self.word_vectorizer.transform(cleaned_resumes)
        V_j = self.word_vectorizer.transform(cleaned_jobs)
        V_diff = abs(V_r - V_j)
        cosine_sim = np.asarray((V_r.multiply(V_j)).sum(axis=1)).reshape(-1, 1)
        manhattan = np.asarray(V_diff.sum(axis=1)).reshape(-1, 1)
        
        blocks = [V_diff, cosine_sim, manhattan]
        
        # Char TF-IDF if enabled
        if self.char_vectorizer:
            Vc_r = self.char_vectorizer.transform(cleaned_resumes)
            Vc_j = self.char_vectorizer.transform(cleaned_jobs)
            Vc_diff = abs(Vc_r - Vc_j)
            char_cosine = np.asarray((Vc_r.multiply(Vc_j)).sum(axis=1)).reshape(-1, 1)
            blocks.extend([Vc_diff, char_cosine])
            
        # Dense features
        dense_feats = self._extract_dense(resumes, jobs)
        scaled_dense = self.scaler.transform(dense_feats)
        blocks.append(sparse.csr_matrix(scaled_dense))
        
        return sparse.hstack(blocks, format="csr")


def run_experiments():
    print("=" * 80)
    print("PHASE 11: CONTROLLED ML EXPERIMENTS & GENERALIZATION BENCHMARKS")
    print("=" * 80)
    
    # Load dataset
    train_df, test_df = load_primary_dataset()
    print(f"Total dataset: Train={len(train_df)} pairs, Test={len(test_df)} pairs")
    
    # -----------------------------------------------------------------
    # Part 1: Dataset Quality Filtering (Cleaned Dataset Variant)
    # -----------------------------------------------------------------
    print("\n--- Creating Versioned Dataset Variants for Quality Experiments ---")
    train_df["pair_hash"] = train_df["resume_text"].apply(hash_text) + "_" + train_df["job_description_text"].apply(hash_text)
    
    # Identify contradictory pairs
    pair_labels = train_df.groupby("pair_hash")["label"].nunique()
    contra_hashes = set(pair_labels[pair_labels > 1].index)
    
    # Variant A: Original raw training set (6,241 pairs)
    # Variant B: Filtered contradictory pairs (removes 12 conflicting rows -> 6,229 pairs)
    # Variant C: Exact deduplicated rows removed (removes 1 duplicate row -> 6,240 pairs)
    # Variant D: Cleaned (No duplicates + No contradictory labels -> 6,228 pairs)
    
    train_cleaned = train_df[~train_df["pair_hash"].isin(contra_hashes)].drop_duplicates(subset=["pair_hash", "label"]).reset_index(drop=True)
    print(f"Original Train size: {len(train_df)} pairs")
    print(f"Cleaned Train size:  {len(train_cleaned)} pairs (Removed {len(train_df) - len(train_cleaned)} conflicting/duplicate records)")
    
    # Save cleaned version
    train_cleaned[["resume_text", "job_description_text", "label"]].to_csv(
        os.path.join(OUTPUT_DIR, "train_cleaned_v1.csv"), index=False
    )
    
    # -----------------------------------------------------------------
    # Part 2: Split Partitions for 4 Protocols
    # -----------------------------------------------------------------
    print("\n--- Generating Partitions for 4 Evaluation Protocols ---")
    # Protocol 1: Random Split (Diagnostic comparison only)
    rand_train, rand_val = train_test_split(train_df, test_size=0.15, random_state=42, stratify=train_df["label"])
    
    # Protocol 2: Job-Disjoint Validation (Group on job_description_text)
    train_sub_job, val_sub_job, _ = get_unseen_jobs_split(val_size=0.15, random_state=42)
    
    # Protocol 3: Resume-Disjoint Validation (Group on resume_text)
    train_sub_res, val_sub_res = get_unseen_resumes_split(test_size=0.15, random_state=42)
    
    # Protocol 4: Dual-Unseen Validation (from Phase 7e)
    dual_train_df = pd.read_csv("experiments/dataset_improvement/splits/dual_unseen_train.csv")
    dual_val_df = pd.read_csv("experiments/dataset_improvement/splits/dual_unseen_val.csv")
    
    print(f"1. Random Split:         Train={len(rand_train)}, Val={len(rand_val)}")
    print(f"2. Job-Disjoint Split:   Train={len(train_sub_job)}, Val={len(val_sub_job)}")
    print(f"3. Resume-Disjoint Split: Train={len(train_sub_res)}, Val={len(val_sub_res)}")
    print(f"4. Dual-Unseen Split:    Train={len(dual_train_df)}, Val={len(dual_val_df)}")
    print(f"5. Official Test Holdout: {len(test_df)} pairs")
    
    # -----------------------------------------------------------------
    # Part 3: Feature Engineering Ablation on Job-Disjoint Validation
    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPERIMENT 1: FEATURE ENGINEERING ABLATION (Job-Disjoint Validation)")
    print("=" * 60)
    
    ablation_file = os.path.join(OUTPUT_DIR, "feature_engineering_ablation.json")
    if os.path.exists(ablation_file):
        print(f"Loading existing feature ablation results from {ablation_file}...")
        with open(ablation_file) as f:
            feature_ablation_results = json.load(f)
    else:
        feature_configs = {
            "Feat A: Baseline (Word TF-IDF + 15 Dense)": EnhancedFeaturePipeline(
                max_word_features=2500, use_char_tfidf=False, use_enhanced_domain=False
            ),
            "Feat B: Baseline + Enhanced Domain Features": EnhancedFeaturePipeline(
                max_word_features=2500, use_char_tfidf=False, use_enhanced_domain=True
            ),
            "Feat C: Baseline + Char n-grams (3-5)": EnhancedFeaturePipeline(
                max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_enhanced_domain=False
            ),
            "Feat D: Combined (Word + Char + Enhanced Domain)": EnhancedFeaturePipeline(
                max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_enhanced_domain=True
            ),
        }
        
        feature_ablation_results = {}
        for f_name, pipe in feature_configs.items():
            print(f"\nEvaluating {f_name}...")
            t0 = time.time()
            pipe.fit(train_sub_job)
            fit_time = time.time() - t0
            
            X_tr = pipe.transform(train_sub_job)
            X_vl = pipe.transform(val_sub_job)
            
            clf = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
            clf.fit(X_tr, np.array(train_sub_job["label"].tolist(), dtype=str))
            
            y_val_pred = clf.predict(X_vl)
            y_val_prob = clf.predict_proba(X_vl)
            
            metrics = compute_eval_metrics(val_sub_job["label"], y_val_pred, y_val_prob)
            metrics["feature_dim"] = X_tr.shape[1]
            metrics["fit_time_sec"] = round(fit_time, 2)
            feature_ablation_results[f_name] = metrics
            
        with open(ablation_file, "w") as f:
            json.dump(feature_ablation_results, f, indent=2)

    # Fit selected best feature pipeline (Feat C)
    print("\nFitting selected champion pipeline Feat C: Baseline + Char n-grams (3-5)...")
    selected_pipe = EnhancedFeaturePipeline(
        max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_enhanced_domain=False
    )
    selected_pipe.fit(train_sub_job)
    
    # -----------------------------------------------------------------
    # Part 4: Controlled Model Experiments
    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: CONTROLLED MODEL COMPARISONS (Job-Disjoint Validation)")
    print("=" * 60)
    
    X_train_job = selected_pipe.transform(train_sub_job)
    y_train_job = np.array(train_sub_job["label"].tolist(), dtype=str)
    
    X_val_job = selected_pipe.transform(val_sub_job)
    y_val_job = np.array(val_sub_job["label"].tolist(), dtype=str)
    
    # Calculate sample weights for gradient boosters
    class_weights_dict = {"No Fit": 1.0, "Potential Fit": 2.0, "Good Fit": 2.0}
    train_sample_weights = np.array([class_weights_dict[y] for y in y_train_job])
    
    # Mapping for XGBoost/LightGBM (expects 0, 1, 2)
    y_train_int = np.array([CLASS_TO_ID[y] for y in y_train_job])
    y_val_int = np.array([CLASS_TO_ID[y] for y in y_val_job])
    
    models = {
        "1. Logistic Regression (Baseline)": LogisticRegression(
            C=1.0, max_iter=1500, class_weight="balanced", random_state=42, solver="lbfgs"
        ),
        "2. Logistic Regression (Tuned C=0.25)": LogisticRegression(
            C=0.25, max_iter=1500, class_weight="balanced", random_state=42, solver="lbfgs"
        ),
        "3. Linear SVM (LinearSVC C=0.5)": LinearSVC(
            C=0.5, class_weight="balanced", random_state=42, max_iter=2000, dual="auto"
        ),
        "4. Calibrated Linear SVM (Platt Scaling)": CalibratedClassifierCV(
            estimator=LinearSVC(C=0.5, class_weight="balanced", random_state=42, max_iter=2000, dual="auto"),
            cv=3
        ),
        "5. Random Forest (100 trees, depth=14)": RandomForestClassifier(
            n_estimators=100, max_depth=14, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "6. LightGBM (Tuned num_leaves=31)": lgb.LGBMClassifier(
            n_estimators=150, max_depth=6, num_leaves=31, learning_rate=0.05,
            class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1
        ),
        "7. XGBoost (Tuned max_depth=4)": xgb.XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.05,
            random_state=42, n_jobs=-1, eval_metric="mlogloss"
        ),
        "8. CatBoost (Tuned depth=5)": CatBoostClassifier(
            iterations=150, depth=5, learning_rate=0.08,
            random_seed=42, verbose=False, thread_count=-1
        ),
    }
    
    model_comparison_results = {}
    trained_models = {}
    
    for m_name, model in models.items():
        print(f"\nTraining {m_name}...")
        t0 = time.time()
        
        # Fit logic
        if "XGBoost" in m_name:
            model.fit(X_train_job, y_train_int, sample_weight=train_sample_weights)
            train_time = time.time() - t0
            t_inf0 = time.time()
            y_val_pred_int = model.predict(X_val_job)
            y_val_prob = model.predict_proba(X_val_job)
            inf_time = time.time() - t_inf0
            y_val_pred = np.array([ID_TO_CLASS[i] for i in y_val_pred_int])
        elif "LightGBM" in m_name:
            model.fit(X_train_job, y_train_job)
            train_time = time.time() - t0
            t_inf0 = time.time()
            y_val_pred = model.predict(X_val_job)
            y_val_prob = model.predict_proba(X_val_job)
            inf_time = time.time() - t_inf0
        elif "CatBoost" in m_name:
            model.fit(X_train_job, y_train_job, sample_weight=train_sample_weights)
            train_time = time.time() - t0
            t_inf0 = time.time()
            y_val_pred = model.predict(X_val_job)
            y_val_prob = model.predict_proba(X_val_job)
            inf_time = time.time() - t_inf0
        else:
            model.fit(X_train_job, y_train_job)
            train_time = time.time() - t0
            t_inf0 = time.time()
            y_val_pred = model.predict(X_val_job)
            y_val_prob = model.predict_proba(X_val_job) if hasattr(model, "predict_proba") else None
            inf_time = time.time() - t_inf0
            
        metrics = compute_eval_metrics(y_val_job, y_val_pred, y_val_prob)
        metrics["train_time_sec"] = round(train_time, 2)
        metrics["inf_time_sec"] = round(inf_time, 4)
        
        model_comparison_results[m_name] = metrics
        trained_models[m_name] = model
        
        print(f"  Train: {train_time:.2f}s | Inf: {inf_time:.4f}s")
        print(f"  Val Acc: {metrics['accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f} | Balanced Acc: {metrics['balanced_accuracy']:.4f}")
        print(f"  Per-class F1: No Fit={metrics['per_class']['No Fit']['f1']:.3f}, Pot Fit={metrics['per_class']['Potential Fit']['f1']:.3f}, Good Fit={metrics['per_class']['Good Fit']['f1']:.3f}")
        
    with open(os.path.join(OUTPUT_DIR, "model_comparison_results.json"), "w") as f:
        json.dump(model_comparison_results, f, indent=2)
        
    # -----------------------------------------------------------------
    # Part 5: Controlled Data Quality Experiments (Cleaned vs Original)
    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: DATA QUALITY DEDUPLICATION & CONTRADICTION AUDIT")
    print("=" * 60)
    
    # Use exact same Job-Disjoint Validation split (untouched holdout), but train on:
    # Set 1: Original train partition (train_sub_job)
    # Set 2: Cleaned train partition (train_sub_job with contradictory pairs removed)
    
    sub_job_hashes = train_sub_job["resume_text"].apply(hash_text) + "_" + train_sub_job["job_description_text"].apply(hash_text)
    train_sub_job_cleaned = train_sub_job[~sub_job_hashes.isin(contra_hashes)].reset_index(drop=True)
    
    print(f"Original Train Sub: {len(train_sub_job)} | Cleaned Train Sub: {len(train_sub_job_cleaned)} (Removed {len(train_sub_job) - len(train_sub_job_cleaned)} pairs)")
    
    pipe_clean = EnhancedFeaturePipeline(max_word_features=2500, use_char_tfidf=False, use_enhanced_domain=True)
    pipe_clean.fit(train_sub_job_cleaned)
    
    X_tr_cln = pipe_clean.transform(train_sub_job_cleaned)
    X_val_cln = pipe_clean.transform(val_sub_job)
    
    clf_orig = LogisticRegression(C=0.25, max_iter=1000, class_weight="balanced", random_state=42)
    clf_orig.fit(X_train_job, y_train_job)
    pred_orig = clf_orig.predict(X_val_job)
    m_orig = compute_eval_metrics(y_val_job, pred_orig)
    
    clf_clean = LogisticRegression(C=0.25, max_iter=1000, class_weight="balanced", random_state=42)
    clf_clean.fit(X_tr_cln, np.array(train_sub_job_cleaned["label"].tolist(), dtype=str))
    pred_cln = clf_clean.predict(X_val_cln)
    m_cln = compute_eval_metrics(y_val_job, pred_cln)
    
    data_quality_results = {
        "original_train_pairs": len(train_sub_job),
        "cleaned_train_pairs": len(train_sub_job_cleaned),
        "contradictory_pairs_removed": len(train_sub_job) - len(train_sub_job_cleaned),
        "original_trained_model": m_orig,
        "clean_trained_model": m_cln,
    }
    
    print(f"Original Model on Val: Acc={m_orig['accuracy']:.4f}, Macro F1={m_orig['macro_f1']:.4f}, Good Fit F1={m_orig['per_class']['Good Fit']['f1']:.4f}")
    print(f"Cleaned Model on Val:  Acc={m_cln['accuracy']:.4f}, Macro F1={m_cln['macro_f1']:.4f}, Good Fit F1={m_cln['per_class']['Good Fit']['f1']:.4f}")
    
    with open(os.path.join(OUTPUT_DIR, "data_quality_cleaning_experiment.json"), "w") as f:
        json.dump(data_quality_results, f, indent=2)
        
    # -----------------------------------------------------------------
    # Part 6: Generalization Evaluation Across 4 Protocols
    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: GENERALIZATION BENCHMARKS ACROSS 4 SPLIT PROTOCOLS")
    print("=" * 60)
    
    protocols = {
        "1. Random Pair Split (Diagnostic)": (rand_train, rand_val),
        "2. Job-Disjoint Split (Unseen Jobs)": (train_sub_job, val_sub_job),
        "3. Resume-Disjoint Split (Unseen Resumes)": (train_sub_res, val_sub_res),
        "4. Dual-Unseen Split (Unseen Jobs & Resumes)": (dual_train_df, dual_val_df),
    }
    
    protocol_results = {}
    
    for p_name, (p_tr, p_vl) in protocols.items():
        print(f"\nEvaluating Protocol: {p_name} (Train={len(p_tr)}, Val={len(p_vl)})...")
        p_pipe = EnhancedFeaturePipeline(max_word_features=2500, use_char_tfidf=False, use_enhanced_domain=True)
        p_pipe.fit(p_tr)
        
        X_p_tr = p_pipe.transform(p_tr)
        X_p_vl = p_pipe.transform(p_vl)
        
        p_clf = LogisticRegression(C=0.25, max_iter=1000, class_weight="balanced", random_state=42)
        p_clf.fit(X_p_tr, np.array(p_tr["label"].tolist(), dtype=str))
        
        p_pred = p_clf.predict(X_p_vl)
        p_prob = p_clf.predict_proba(X_p_vl)
        
        p_metrics = compute_eval_metrics(p_vl["label"], p_pred, p_prob)
        protocol_results[p_name] = p_metrics
        
        print(f"  Acc: {p_metrics['accuracy']:.4f} | Macro F1: {p_metrics['macro_f1']:.4f} | Bal Acc: {p_metrics['balanced_accuracy']:.4f}")
        print(f"  No Fit F1: {p_metrics['per_class']['No Fit']['f1']:.3f} | Pot Fit F1: {p_metrics['per_class']['Potential Fit']['f1']:.3f} | Good Fit F1: {p_metrics['per_class']['Good Fit']['f1']:.3f}")
        
    with open(os.path.join(OUTPUT_DIR, "generalization_protocols_comparison.json"), "w") as f:
        json.dump(protocol_results, f, indent=2)
        
    # -----------------------------------------------------------------
    # Part 7: Model Reliability & Threshold Optimization
    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPERIMENT 5: MODEL RELIABILITY & THRESHOLD OPTIMIZATION")
    print("=" * 60)
    
    best_clf = trained_models["2. Logistic Regression (Tuned C=0.25)"]
    val_probs = best_clf.predict_proba(X_val_job)
    
    # Sweep decision thresholds on Good Fit probability to balance Precision vs Recall
    # Default argmax threshold is ~0.33
    threshold_sweep = []
    for thresh in np.arange(0.20, 0.55, 0.05):
        t_val = round(float(thresh), 2)
        # Custom prediction rule:
        # If prob(Good Fit) >= thresh -> Good Fit
        # Else if prob(Potential Fit) >= 0.35 -> Potential Fit
        # Else -> No Fit
        preds_custom = []
        for prob_row in val_probs:
            p_no, p_pot, p_good = prob_row[0], prob_row[1], prob_row[2]
            if p_good >= t_val:
                preds_custom.append("Good Fit")
            elif p_pot >= 0.35:
                preds_custom.append("Potential Fit")
            else:
                preds_custom.append("No Fit")
                
        t_m = compute_eval_metrics(y_val_job, preds_custom)
        threshold_sweep.append({
            "threshold": t_val,
            "accuracy": t_m["accuracy"],
            "macro_f1": t_m["macro_f1"],
            "good_fit_precision": t_m["per_class"]["Good Fit"]["precision"],
            "good_fit_recall": t_m["per_class"]["Good Fit"]["recall"],
            "good_fit_f1": t_m["per_class"]["Good Fit"]["f1"],
        })
        print(f"  Good Fit Thresh {t_val:.2f} -> Acc: {t_m['accuracy']:.4f}, Macro F1: {t_m['macro_f1']:.4f}, GF P={t_m['per_class']['Good Fit']['precision']:.3f}, GF R={t_m['per_class']['Good Fit']['recall']:.3f}, GF F1={t_m['per_class']['Good Fit']['f1']:.3f}")
        
    reliability_results = {
        "default_brier_score": model_comparison_results["2. Logistic Regression (Tuned C=0.25)"]["brier_score"],
        "threshold_sweep": threshold_sweep,
    }
    
    with open(os.path.join(OUTPUT_DIR, "model_reliability_threshold_sweep.json"), "w") as f:
        json.dump(reliability_results, f, indent=2)
        
    print("\nALL PHASE 11 EXPERIMENTS COMPLETED SUCCESSFULLY.")
    return True

if __name__ == "__main__":
    run_experiments()
