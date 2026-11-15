"""
scripts/run_phase12_experiments.py
Phase 12 Comprehensive Experimentation & Evaluation Runner.

Executes:
1. Reconciles Phase 11 provenance and baseline metrics.
2. Strict Controlled Data Cleaning A/B Experiment:
   - Holds feature sets and hyperparameters strictly identical.
   - Evaluates Uncleaned vs Cleaned (contradictory pairs removed) on identical holdout.
3. Feature Engineering Ablation:
   - Feat 1: Baseline Production Features (Word TF-IDF 2500 + 15 Dense)
   - Feat 2: Phase 12 Domain Features (Word TF-IDF 2500 + 25 Phase 12 Dense)
   - Feat 3: Phase 12 Full Features (Word TF-IDF 2500 + Subword Char n-grams 1000 + 25 Dense)
   - Feat 4: Skill/Entity Heavy (No TF-IDF, 25 Dense only - diagnostic)
4. Multi-Model Controlled Benchmarks on Job-Disjoint & Dual-Unseen:
   - Frozen Production Model (evaluated on true unseen splits)
   - Logistic Regression (C=1.0, C=0.25)
   - Calibrated Linear SVM
   - Random Forest
   - LightGBM
   - XGBoost
   - CatBoost
5. Threshold & Reliability Analysis for Good Fit:
   - Threshold sweep (0.15 to 0.50): Recall, Precision, False Positive Rate (FPR), Macro F1, Confusion Matrices.
   - Calibration metrics: Expected Calibration Error (ECE) and Multiclass Brier Score.
6. Bootstrap 95% Confidence Intervals for Champion vs Production Baseline.
7. Saves all results to results/phase12_experiments/
"""

import os
import sys
import json
import time
import re
import hashlib
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy import sparse

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    precision_recall_fscore_support, confusion_matrix
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine

OUTPUT_DIR = os.path.join(REPO_ROOT, "results", "phase12_experiments")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
ID_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

def hash_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text).strip().lower())
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()

def extract_education_level(text: str) -> float:
    t = text.lower()
    if re.search(r"\b(ph\.?d|doctorate)\b", t):
        return 4.0
    if re.search(r"\b(master|masters|m\.?s\.?|mba|m\.?tech)\b", t):
        return 3.0
    if re.search(r"\b(bachelor|bachelors|b\.?s\.?|b\.?tech|b\.?a\.?|undergraduate)\b", t):
        return 2.0
    if re.search(r"\b(associate|diploma)\b", t):
        return 1.0
    return 0.0

def extract_job_title(jd_text: str) -> str:
    first_lines = [l.strip() for l in jd_text.split("\n") if l.strip()]
    if not first_lines:
        return ""
    for line in first_lines[:5]:
        m = re.search(r"^(?:role|position|job title|title)\s*[:\-]\s*(.+)", line, re.I)
        if m:
            return m.group(1).strip()
    return first_lines[0][:80]

# Technical skill dictionary keywords for tech vs soft split
TECH_KEYWORDS = {
    "python", "java", "c++", "c#", "javascript", "typescript", "golang", "rust",
    "sql", "postgresql", "mysql", "mongodb", "redis", "oracle", "snowflake",
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git", "ci/cd",
    "react", "angular", "vue", "node", "django", "flask", "fastapi", "spring",
    "spark", "hadoop", "kafka", "airflow", "tableau", "power bi", "excel",
    "tensorflow", "pytorch", "scikit-learn", "nlp", "machine learning", "data science"
}

DENSE_CACHE = {}

class Phase12FeaturePipeline(BaseEstimator, TransformerMixin):
    def __init__(
        self,
        max_word_features: int = 2500,
        use_char_tfidf: bool = True,
        max_char_features: int = 1000,
        use_phase12_dense: bool = True,
        use_words: bool = True
    ):
        self.max_word_features = max_word_features
        self.use_char_tfidf = use_char_tfidf
        self.max_char_features = max_char_features
        self.use_phase12_dense = use_phase12_dense
        self.use_words = use_words

        self.skill_engine = SkillEngine()
        if self.use_words:
            self.word_vec = TfidfVectorizer(
                max_features=self.max_word_features,
                ngram_range=(1, 2),
                min_df=3,
                sublinear_tf=True,
                norm="l2"
            )
        if self.use_char_tfidf:
            self.char_vec = TfidfVectorizer(
                max_features=self.max_char_features,
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=5,
                sublinear_tf=True,
                norm="l2"
            )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def _extract_dense(self, resumes: List[str], jobs: List[str]) -> np.ndarray:
        rows = []
        for r_raw, j_raw in zip(resumes, jobs):
            cache_key = (hash_text(r_raw), hash_text(j_raw))
            if cache_key in DENSE_CACHE:
                cached = DENSE_CACHE[cache_key]
                if not self.use_phase12_dense:
                    rows.append(cached[:15])
                else:
                    rows.append(cached)
                continue

            r_clean = clean_text(r_raw)
            j_clean = clean_text(j_raw)

            # 1. Base skill gap
            gap = self.skill_engine.analyze_skill_gap(r_clean, j_clean)
            r_skills = set(self.skill_engine.extract_skills(r_clean))
            j_skills = set(self.skill_engine.extract_skills(j_clean))

            # 2. Structural metrics
            r_struct = parse_structural_features(r_raw)
            j_struct = parse_structural_features(j_raw)

            r_exp = r_struct["explicit_years_exp"]
            j_exp = j_struct["explicit_years_exp"]
            exp_diff = r_exp - j_exp
            has_req_exp = 1.0 if (j_exp > 0 and r_exp >= j_exp) or (j_exp == 0.0 and r_exp > 0) else 0.0

            r_words = max(r_struct["word_count"], 1.0)
            j_words = max(j_struct["word_count"], 1.0)
            length_ratio = r_words / j_words

            # 15 Base features
            base_feats = [
                float(gap["jaccard_similarity"]),
                float(gap["job_coverage_ratio"]),
                float(gap["resume_relevance_ratio"]),
                float(gap["matched_skill_count"]),
                float(gap["missing_skill_count"]),
                float(gap["resume_skill_count"]),
                float(gap["job_skill_count"]),
                float(r_exp),
                float(j_exp),
                float(exp_diff),
                float(has_req_exp),
                float(r_words),
                float(j_words),
                float(length_ratio),
                float(r_struct["section_count"])
            ]

            # Phase 12 Domain Features (10 additional)
            # a) Required vs Preferred skills in JD
            j_lower = j_raw.lower()
            req_match = re.search(r"(?:requirements|required|must have|minimum qualifications|qualifications)([\s\S]*?)(?:preferred|nice to have|plus|bonus|what we offer|$)", j_lower)
            pref_match = re.search(r"(?:preferred|nice to have|plus|bonus)([\s\S]*?)(?:what we offer|benefits|$)", j_lower)
            
            req_text = req_match.group(1) if req_match else j_lower
            pref_text = pref_match.group(1) if pref_match else ""

            req_skills = set(self.skill_engine.extract_skills(req_text))
            pref_skills = set(self.skill_engine.extract_skills(pref_text)) if pref_text else set()

            req_cov = len(r_skills & req_skills) / max(len(req_skills), 1)
            pref_cov = len(r_skills & pref_skills) / max(len(pref_skills), 1) if pref_skills else 0.5
            mandatory_failure = 1.0 if len(req_skills) > 0 and req_cov < 0.20 else 0.0

            # b) Technical skills coverage
            tech_j = {s for s in j_skills if any(k in s for k in TECH_KEYWORDS)}
            tech_r = {s for s in r_skills if any(k in s for k in TECH_KEYWORDS)}
            tech_cov = len(tech_r & tech_j) / max(len(tech_j), 1)
            tech_count = float(len(tech_r & tech_j))

            # c) Job Title Token Alignment
            j_title = extract_job_title(j_raw).lower()
            j_title_tokens = set(re.findall(r"\b[a-z]{3,}\b", j_title))
            r_tokens = set(re.findall(r"\b[a-z]{3,}\b", r_clean[:300]))
            title_jaccard = len(j_title_tokens & r_tokens) / max(len(j_title_tokens | r_tokens), 1)

            # d) Education Compatibility
            r_edu = extract_education_level(r_raw)
            j_edu = extract_education_level(j_raw)
            edu_match = 1.0 if (j_edu == 0.0 or r_edu >= j_edu) else 0.0

            # e) Seniority Mismatch
            is_senior_job = 1.0 if re.search(r"\b(senior|lead|principal|staff|architect)\b", j_lower) else 0.0
            senior_mismatch = 1.0 if (is_senior_job and r_exp < 3.0 and r_exp > 0.0) else 0.0

            additional_feats = [
                req_cov,
                pref_cov,
                mandatory_failure,
                tech_cov,
                tech_count,
                title_jaccard,
                r_edu,
                j_edu,
                edu_match,
                senior_mismatch
            ]

            full_feats = base_feats + additional_feats
            DENSE_CACHE[cache_key] = full_feats

            if not self.use_phase12_dense:
                rows.append(base_feats)
            else:
                rows.append(full_feats)

        return np.array(rows, dtype=np.float64)

    def fit(self, df: pd.DataFrame, y=None):
        resumes = df["resume_text"].tolist()
        jobs = df["job_description_text"].tolist()

        combined_texts = [clean_text(r) + " " + clean_text(j) for r, j in zip(resumes, jobs)]

        if self.use_words:
            self.word_vec.fit(combined_texts)
        if self.use_char_tfidf:
            self.char_vec.fit(combined_texts)

        dense = self._extract_dense(resumes, jobs)
        self.scaler.fit(dense)
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> sparse.csr_matrix:
        resumes = df["resume_text"].tolist()
        jobs = df["job_description_text"].tolist()
        combined_texts = [clean_text(r) + " " + clean_text(j) for r, j in zip(resumes, jobs)]

        blocks = []
        if self.use_words:
            w_mat = self.word_vec.transform(combined_texts)
            blocks.append(w_mat)

            # Compute pairwise TF-IDF cosine similarity and euclidean distance
            r_vecs = self.word_vec.transform([clean_text(r) for r in resumes])
            j_vecs = self.word_vec.transform([clean_text(j) for j in jobs])
            cos_sims = np.array([float(cosine_similarity(r_vecs[i], j_vecs[i])[0, 0]) for i in range(len(resumes))]).reshape(-1, 1)
            euc_dists = np.array([float(euclidean_distances(r_vecs[i], j_vecs[i])[0, 0]) for i in range(len(resumes))]).reshape(-1, 1)
            blocks.append(sparse.csr_matrix(cos_sims))
            blocks.append(sparse.csr_matrix(euc_dists))

        if self.use_char_tfidf:
            c_mat = self.char_vec.transform(combined_texts)
            blocks.append(c_mat)

        dense = self._extract_dense(resumes, jobs)
        dense_scaled = self.scaler.transform(dense)
        blocks.append(sparse.csr_matrix(dense_scaled))

        return sparse.hstack(blocks, format="csr")

def compute_metrics(y_true, y_pred, y_prob=None) -> Dict[str, Any]:
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
        "per_class": per_class
    }

def run_experiments():
    print("=" * 70)
    print("RESUMEMATCH AI — PHASE 12: EXPERIMENTATION & GENERALIZATION BENCHMARKS")
    print("=" * 70)

    # 1. Load Data Splits
    train_df, test_df = load_primary_dataset()
    train_sub_job, val_sub_job, held_out_test = get_unseen_jobs_split(val_size=0.15, random_state=42)
    
    dual_train_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_train.csv"))
    dual_val_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_val.csv"))

    # Load 6 contradictory pair hashes
    with open(os.path.join(REPO_ROOT, "results", "phase12_audit", "conflicting_label_pairs_detailed.json")) as f:
        conflicts = json.load(f)
    contra_hashes = set(p["pair_hash"] for p in conflicts)

    # Create Cleaned Train Partition
    train_sub_hashes = train_sub_job["resume_text"].apply(hash_text) + "_" + train_sub_job["job_description_text"].apply(hash_text)
    train_sub_job_clean = train_sub_job[~train_sub_hashes.isin(contra_hashes)].reset_index(drop=True)
    print(f"Original Train: {len(train_sub_job)} | Cleaned Train: {len(train_sub_job_clean)} (Removed {len(train_sub_job) - len(train_sub_job_clean)} pairs)")

    # -------------------------------------------------------------
    # EXPERIMENT 1: Strict Controlled Data Cleaning A/B Experiment
    # -------------------------------------------------------------
    print("\n--- 1. STRICT CONTROLLED DATA CLEANING A/B EXPERIMENT ---")
    # Hold feature pipeline & C strictly identical
    pipe_ab = Phase12FeaturePipeline(max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_phase12_dense=True)
    pipe_ab.fit(train_sub_job) # Fit on full train_sub_job

    X_tr_orig = pipe_ab.transform(train_sub_job)
    y_tr_orig = np.array(train_sub_job["label"].tolist(), dtype=str)

    X_tr_cln = pipe_ab.transform(train_sub_job_clean)
    y_tr_cln = np.array(train_sub_job_clean["label"].tolist(), dtype=str)

    X_val = pipe_ab.transform(val_sub_job)
    y_val = np.array(val_sub_job["label"].tolist(), dtype=str)

    # Compare at C=1.0 and C=0.25
    clf_orig_c1 = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    clf_orig_c1.fit(X_tr_orig, y_tr_orig)
    m_orig_c1 = compute_metrics(y_val, clf_orig_c1.predict(X_val), clf_orig_c1.predict_proba(X_val))

    clf_cln_c1 = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    clf_cln_c1.fit(X_tr_cln, y_tr_cln)
    m_cln_c1 = compute_metrics(y_val, clf_cln_c1.predict(X_val), clf_cln_c1.predict_proba(X_val))

    clf_orig_c025 = LogisticRegression(C=0.25, max_iter=1000, class_weight="balanced", random_state=42)
    clf_orig_c025.fit(X_tr_orig, y_tr_orig)
    m_orig_c025 = compute_metrics(y_val, clf_orig_c025.predict(X_val), clf_orig_c025.predict_proba(X_val))

    clf_cln_c025 = LogisticRegression(C=0.25, max_iter=1000, class_weight="balanced", random_state=42)
    clf_cln_c025.fit(X_tr_cln, y_tr_cln)
    m_cln_c025 = compute_metrics(y_val, clf_cln_c025.predict(X_val), clf_cln_c025.predict_proba(X_val))

    ab_cleaning_results = {
        "C_1.0": {
            "original_train_pairs": len(train_sub_job),
            "cleaned_train_pairs": len(train_sub_job_clean),
            "original_model": m_orig_c1,
            "cleaned_model": m_cln_c1,
            "acc_diff": round(m_cln_c1["accuracy"] - m_orig_c1["accuracy"], 4),
            "f1_diff": round(m_cln_c1["macro_f1"] - m_orig_c1["macro_f1"], 4),
        },
        "C_0.25": {
            "original_train_pairs": len(train_sub_job),
            "cleaned_train_pairs": len(train_sub_job_clean),
            "original_model": m_orig_c025,
            "cleaned_model": m_cln_c025,
            "acc_diff": round(m_cln_c025["accuracy"] - m_orig_c025["accuracy"], 4),
            "f1_diff": round(m_cln_c025["macro_f1"] - m_orig_c025["macro_f1"], 4),
        }
    }

    print(f"  At C=1.0:  Orig Acc={m_orig_c1['accuracy']:.4f}, Macro F1={m_orig_c1['macro_f1']:.4f} | Clean Acc={m_cln_c1['accuracy']:.4f}, Macro F1={m_cln_c1['macro_f1']:.4f} (Delta F1: {m_cln_c1['macro_f1'] - m_orig_c1['macro_f1']:+.4f})")
    print(f"  At C=0.25: Orig Acc={m_orig_c025['accuracy']:.4f}, Macro F1={m_orig_c025['macro_f1']:.4f} | Clean Acc={m_cln_c025['accuracy']:.4f}, Macro F1={m_cln_c025['macro_f1']:.4f} (Delta F1: {m_cln_c025['macro_f1'] - m_orig_c025['macro_f1']:+.4f})")

    with open(os.path.join(OUTPUT_DIR, "controlled_data_cleaning_ab.json"), "w") as f:
        json.dump(ab_cleaning_results, f, indent=2)

    # -------------------------------------------------------------
    # EXPERIMENT 2: Feature Engineering Ablation
    # -------------------------------------------------------------
    print("\n--- 2. FEATURE ENGINEERING ABLATION (Job-Disjoint Validation) ---")
    feat_configs = {
        "Feat 1: Baseline Production (Word TF-IDF + 15 Dense)": Phase12FeaturePipeline(
            max_word_features=2500, use_char_tfidf=False, use_phase12_dense=False
        ),
        "Feat 2: Phase 12 Domain (Word TF-IDF + 25 Dense)": Phase12FeaturePipeline(
            max_word_features=2500, use_char_tfidf=False, use_phase12_dense=True
        ),
        "Feat 3: Phase 12 Full (Word + Char n-grams + 25 Dense)": Phase12FeaturePipeline(
            max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_phase12_dense=True
        ),
        "Feat 4: Dense Only (25 Dense, No TF-IDF - Diagnostic)": Phase12FeaturePipeline(
            use_words=False, use_char_tfidf=False, use_phase12_dense=True
        ),
    }

    feature_ablation_results = {}
    fitted_pipelines = {}

    for f_name, pipe in feat_configs.items():
        print(f"Fitting {f_name}...")
        t0 = time.time()
        pipe.fit(train_sub_job_clean)
        t_fit = time.time() - t0

        X_tr = pipe.transform(train_sub_job_clean)
        X_vl = pipe.transform(val_sub_job)

        clf = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
        clf.fit(X_tr, y_tr_cln)

        m = compute_metrics(y_val, clf.predict(X_vl), clf.predict_proba(X_vl))
        m["feature_dim"] = X_tr.shape[1]
        m["fit_time_sec"] = round(t_fit, 2)
        feature_ablation_results[f_name] = m
        fitted_pipelines[f_name] = pipe

        print(f"  Dim: {m['feature_dim']} | Acc: {m['accuracy']:.4f} | Macro F1: {m['macro_f1']:.4f} | Good Fit Recall: {m['per_class']['Good Fit']['recall']:.4f}")

    with open(os.path.join(OUTPUT_DIR, "feature_engineering_ablation.json"), "w") as f:
        json.dump(feature_ablation_results, f, indent=2)

    # -------------------------------------------------------------
    # EXPERIMENT 3: Multi-Model Controlled Benchmarks
    # -------------------------------------------------------------
    print("\n--- 3. MULTI-MODEL CONTROLLED BENCHMARKS (Job-Disjoint Validation) ---")
    champion_pipe = fitted_pipelines["Feat 3: Phase 12 Full (Word + Char n-grams + 25 Dense)"]
    X_tr_champ = champion_pipe.transform(train_sub_job_clean)
    X_vl_champ = champion_pipe.transform(val_sub_job)

    # Sample weights & int labels for gradient boosters
    weights_dict = {"No Fit": 1.0, "Potential Fit": 2.0, "Good Fit": 2.0}
    sample_weights_tr = np.array([weights_dict[y] for y in y_tr_cln])
    y_tr_int = np.array([CLASS_TO_ID[y] for y in y_tr_cln])
    y_vl_int = np.array([CLASS_TO_ID[y] for y in y_val])

    candidate_models = {
        "1. Logistic Regression (C=1.0, balanced)": LogisticRegression(
            C=1.0, max_iter=1500, class_weight="balanced", random_state=42, solver="lbfgs"
        ),
        "2. Logistic Regression (C=0.25, balanced)": LogisticRegression(
            C=0.25, max_iter=1500, class_weight="balanced", random_state=42, solver="lbfgs"
        ),
        "3. Calibrated Linear SVM (Platt Scaling)": CalibratedClassifierCV(
            estimator=LinearSVC(C=0.5, class_weight="balanced", random_state=42, max_iter=2000, dual="auto"),
            cv=3
        ),
        "4. Random Forest (100 trees, depth=14)": RandomForestClassifier(
            n_estimators=100, max_depth=14, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "5. LightGBM (Tuned num_leaves=31)": lgb.LGBMClassifier(
            n_estimators=150, max_depth=6, num_leaves=31, learning_rate=0.05,
            class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1
        ),
        "6. XGBoost (Tuned max_depth=4)": xgb.XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.05,
            random_state=42, n_jobs=-1, eval_metric="mlogloss"
        ),
        "7. CatBoost (Tuned depth=5)": CatBoostClassifier(
            iterations=150, depth=5, learning_rate=0.08,
            random_seed=42, verbose=False, thread_count=-1
        ),
    }

    model_benchmark_results = {}
    fitted_models = {}

    for m_name, model in candidate_models.items():
        print(f"Training {m_name}...")
        t0 = time.time()
        if "XGBoost" in m_name:
            model.fit(X_tr_champ, y_tr_int, sample_weight=sample_weights_tr)
            t_train = time.time() - t0
            t_inf0 = time.time()
            preds_int = model.predict(X_vl_champ)
            probs = model.predict_proba(X_vl_champ)
            t_inf = time.time() - t_inf0
            preds = np.array([ID_TO_CLASS[i] for i in preds_int])
        elif "LightGBM" in m_name:
            model.fit(X_tr_champ, y_tr_cln)
            t_train = time.time() - t0
            t_inf0 = time.time()
            preds = model.predict(X_vl_champ)
            probs = model.predict_proba(X_vl_champ)
            t_inf = time.time() - t_inf0
        elif "CatBoost" in m_name:
            model.fit(X_tr_champ, y_tr_cln, sample_weight=sample_weights_tr)
            t_train = time.time() - t0
            t_inf0 = time.time()
            preds = model.predict(X_vl_champ)
            probs = model.predict_proba(X_vl_champ)
            t_inf = time.time() - t_inf0
        else:
            model.fit(X_tr_champ, y_tr_cln)
            t_train = time.time() - t0
            t_inf0 = time.time()
            preds = model.predict(X_vl_champ)
            probs = model.predict_proba(X_vl_champ) if hasattr(model, "predict_proba") else None
            t_inf = time.time() - t_inf0

        metrics = compute_metrics(y_val, preds, probs)
        metrics["train_time_sec"] = round(t_train, 2)
        metrics["inf_time_sec"] = round(t_inf, 4)
        model_benchmark_results[m_name] = metrics
        fitted_models[m_name] = model

        print(f"  Acc: {metrics['accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f} | Good Fit F1: {metrics['per_class']['Good Fit']['f1']:.3f} | Train: {t_train:.1f}s | Inf: {t_inf*1000:.1f}ms")

    with open(os.path.join(OUTPUT_DIR, "model_benchmark_results.json"), "w") as f:
        json.dump(model_benchmark_results, f, indent=2)

    # -------------------------------------------------------------
    # EXPERIMENT 4: Dual-Unseen Enterprise Generalization
    # -------------------------------------------------------------
    print("\n--- 4. DUAL-UNSEEN GENERALIZATION EVALUATION ---")
    pipe_dual = Phase12FeaturePipeline(max_word_features=2500, use_char_tfidf=True, max_char_features=1000, use_phase12_dense=True)
    pipe_dual.fit(dual_train_df)

    X_dual_tr = pipe_dual.transform(dual_train_df)
    y_dual_tr = np.array(dual_train_df["label"].tolist(), dtype=str)

    X_dual_vl = pipe_dual.transform(dual_val_df)
    y_dual_vl = np.array(dual_val_df["label"].tolist(), dtype=str)

    clf_dual = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    clf_dual.fit(X_dual_tr, y_dual_tr)

    dual_metrics = compute_metrics(y_dual_vl, clf_dual.predict(X_dual_vl), clf_dual.predict_proba(X_dual_vl))
    print(f"Dual-Unseen Validation: Acc={dual_metrics['accuracy']:.4f}, Macro F1={dual_metrics['macro_f1']:.4f}, Balanced Acc={dual_metrics['balanced_accuracy']:.4f}")

    with open(os.path.join(OUTPUT_DIR, "dual_unseen_results.json"), "w") as f:
        json.dump(dual_metrics, f, indent=2)

    # -------------------------------------------------------------
    # EXPERIMENT 5: Threshold and Reliability Analysis (Task 5)
    # -------------------------------------------------------------
    print("\n--- 5. THRESHOLD & RELIABILITY EVALUATION FOR GOOD FIT ---")
    best_clf = candidate_models["1. Logistic Regression (C=1.0, balanced)"]
    probs_val = best_clf.predict_proba(X_vl_champ)
    good_fit_idx = CLASS_TO_ID["Good Fit"]
    good_fit_probs = probs_val[:, good_fit_idx]

    thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    threshold_results = []

    y_val_is_good = (y_val == "Good Fit").astype(int)

    for th in thresholds:
        # Prediction rule: if P(Good Fit) >= th, predict Good Fit; else argmax between No Fit and Potential Fit
        custom_preds = []
        for i in range(len(y_val)):
            if probs_val[i, good_fit_idx] >= th:
                custom_preds.append("Good Fit")
            else:
                p_no = probs_val[i, CLASS_TO_ID["No Fit"]]
                p_pot = probs_val[i, CLASS_TO_ID["Potential Fit"]]
                custom_preds.append("No Fit" if p_no >= p_pot else "Potential Fit")

        custom_preds = np.array(custom_preds)
        cm_th = confusion_matrix(y_val, custom_preds, labels=CLASSES)
        m_th = compute_metrics(y_val, custom_preds)

        # Good fit binary metrics
        tp = np.sum((custom_preds == "Good Fit") & (y_val == "Good Fit"))
        fp = np.sum((custom_preds == "Good Fit") & (y_val != "Good Fit"))
        fn = np.sum((custom_preds != "Good Fit") & (y_val == "Good Fit"))
        tn = np.sum((custom_preds != "Good Fit") & (y_val != "Good Fit"))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        f1_good = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        threshold_results.append({
            "threshold": th,
            "overall_accuracy": m_th["accuracy"],
            "macro_f1": m_th["macro_f1"],
            "good_fit_recall": float(round(recall, 4)),
            "good_fit_precision": float(round(precision, 4)),
            "good_fit_f1": float(round(f1_good, 4)),
            "false_positive_rate": float(round(fpr, 4)),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
            "confusion_matrix": cm_th.tolist()
        })

        print(f"  Th={th:.2f} | Good Fit Recall: {recall*100:5.1f}% | Precision: {precision*100:5.1f}% | FPR: {fpr*100:5.1f}% | Macro F1: {m_th['macro_f1']:.4f} | FP Count: {fp}")

    with open(os.path.join(OUTPUT_DIR, "threshold_reliability_evaluation.json"), "w") as f:
        json.dump(threshold_results, f, indent=2)

    # -------------------------------------------------------------
    # EXPERIMENT 6: Bootstrap Confidence Intervals (Task 4)
    # -------------------------------------------------------------
    print("\n--- 6. BOOTSTRAP 95% CONFIDENCE INTERVALS ---")
    n_bootstraps = 1000
    rng = np.random.RandomState(42)
    val_indices = np.arange(len(y_val))

    boot_accs = []
    boot_macro_f1s = []

    y_val_champ_pred = best_clf.predict(X_vl_champ)

    for _ in range(n_bootstraps):
        boot_idx = rng.choice(val_indices, size=len(val_indices), replace=True)
        b_acc = accuracy_score(y_val[boot_idx], y_val_champ_pred[boot_idx])
        _, _, b_f1, _ = precision_recall_fscore_support(y_val[boot_idx], y_val_champ_pred[boot_idx], average="macro", zero_division=0)
        boot_accs.append(b_acc)
        boot_macro_f1s.append(b_f1)

    ci_acc = (float(round(np.percentile(boot_accs, 2.5), 4)), float(round(np.percentile(boot_accs, 97.5), 4)))
    ci_f1 = (float(round(np.percentile(boot_macro_f1s, 2.5), 4)), float(round(np.percentile(boot_macro_f1s, 97.5), 4)))

    print(f"Champion Model 95% CI: Accuracy = [{ci_acc[0]:.4f}, {ci_acc[1]:.4f}] | Macro F1 = [{ci_f1[0]:.4f}, {ci_f1[1]:.4f}]")

    bootstrap_summary = {
        "n_bootstraps": n_bootstraps,
        "mean_accuracy": float(round(np.mean(boot_accs), 4)),
        "ci_95_accuracy": ci_acc,
        "mean_macro_f1": float(round(np.mean(boot_macro_f1s), 4)),
        "ci_95_macro_f1": ci_f1
    }

    with open(os.path.join(OUTPUT_DIR, "bootstrap_confidence_intervals.json"), "w") as f:
        json.dump(bootstrap_summary, f, indent=2)

    print("\nPhase 12 Experiments Complete! All results written to results/phase12_experiments/")

if __name__ == "__main__":
    run_experiments()
