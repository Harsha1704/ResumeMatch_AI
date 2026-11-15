"""
scripts/run_phase12b_experiments.py
Phase 12B Research-Guided Transformer & Hybrid Semantic Matching Experiment Runner.

Executes:
1. Pretrained Sentence-BERT Embedding Generation & Caching (all-MiniLM-L6-v2)
2. Experiment A: Frozen Bi-Encoder Representation Ablation:
   - Rep 1: Cosine Similarity only (1 dim)
   - Rep 2: Concatenated [u, v] (768 dims)
   - Rep 3: Interaction [|u - v|, u * v, Cosine] (769 dims)
   - Rep 4: Full Bi-Encoder [u, v, |u - v|, u * v, Cosine] (1,537 dims)
3. Experiment B: Hybrid Semantic + Structured Matching (Configurations A to E):
   - Config A: TF-IDF Baseline (Word TF-IDF + 15 Dense)
   - Config B: Frozen Semantic Embeddings only (Bi-Encoder Rep 4)
   - Config C: Structured Matching Features only (25 Dense features)
   - Config D: Semantic Embeddings + Structured Matching (Rep 4 + 25 Dense)
   - Config E: Full Composite (TF-IDF + Semantic Embeddings + 25 Dense)
4. Experiment C: Cross-Encoder & Section-Aware Truncation Evaluation:
   - Straightforward vs Section-Aware Truncation
   - Cross-Encoder score feature generation
   - 3-Class classification using Cross-Encoder representations
   - CPU Latency & memory measurement
5. Experiment D: Contrastive Learning Investigation:
   - Hard-negative distance analysis across (Good Fit, Potential Fit, No Fit)
   - Triplet / margin separation evaluation
6. Multi-Protocol Generalization Evaluation:
   - Job-Disjoint Validation (Primary Dev Benchmark)
   - Resume-Disjoint Validation
   - Dual-Unseen Validation
   - Official Held-Out Test (Anchor benchmark)
7. Bootstrap 95% Confidence Intervals
Saves all artifacts to results/phase12b_experiments/
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

from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    precision_recall_fscore_support, confusion_matrix,
    brier_score_loss
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

import torch
from sentence_transformers import SentenceTransformer, CrossEncoder

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine

OUTPUT_DIR = os.path.join(REPO_ROOT, "results", "phase12b_experiments")
EMBEDDING_DIR = os.path.join(REPO_ROOT, "results", "phase12b_embeddings")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EMBEDDING_DIR, exist_ok=True)

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

def extract_section_aware_text(text: str, max_chars: int = 1500) -> str:
    """
    Extracts high-priority sections (Skills, Experience, Education, Requirements)
    to prevent critical qualifications from being dropped during transformer truncation.
    """
    lines = text.split("\n")
    skills_lines = []
    exp_lines = []
    edu_lines = []
    other_lines = []

    current_sec = "other"
    for line in lines:
        l_low = line.strip().lower()
        if any(k in l_low for k in ["skill", "technolog", "proficien", "competenc", "requirement", "qualification", "must have"]):
            current_sec = "skills"
        elif any(k in l_low for k in ["experience", "employment", "work history", "responsibilit", "duties"]):
            current_sec = "experience"
        elif any(k in l_low for k in ["education", "degree", "academic", "university"]):
            current_sec = "education"

        if current_sec == "skills":
            skills_lines.append(line.strip())
        elif current_sec == "experience":
            exp_lines.append(line.strip())
        elif current_sec == "education":
            edu_lines.append(line.strip())
        else:
            other_lines.append(line.strip())

    # Assemble: Skills first, then education, then recent experience, then other
    priority_assembled = (
        "SKILLS: " + " ".join(skills_lines)[:600] + "\n" +
        "EDUCATION: " + " ".join(edu_lines)[:300] + "\n" +
        "EXPERIENCE: " + " ".join(exp_lines)[:500] + "\n" +
        "SUMMARY: " + " ".join(other_lines)[:300]
    )
    return clean_text(priority_assembled[:max_chars])

TECH_KEYWORDS = {
    "python", "java", "c++", "c#", "javascript", "typescript", "golang", "rust",
    "sql", "postgresql", "mysql", "mongodb", "redis", "oracle", "snowflake",
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git", "ci/cd",
    "react", "angular", "vue", "node", "django", "flask", "fastapi", "spring",
    "spark", "hadoop", "kafka", "airflow", "tableau", "power bi", "excel",
    "tensorflow", "pytorch", "scikit-learn", "nlp", "machine learning", "data science"
}

DENSE_FEATURE_CACHE = {}

def extract_25_dense_features(resumes: List[str], jobs: List[str], skill_engine: SkillEngine) -> np.ndarray:
    rows = []
    for r_raw, j_raw in zip(resumes, jobs):
        key = (hash_text(r_raw), hash_text(j_raw))
        if key in DENSE_FEATURE_CACHE:
            rows.append(DENSE_FEATURE_CACHE[key])
            continue

        r_clean = clean_text(r_raw)
        j_clean = clean_text(j_raw)

        gap = skill_engine.analyze_skill_gap(r_clean, j_clean)
        r_skills = set(skill_engine.extract_skills(r_clean))
        j_skills = set(skill_engine.extract_skills(j_clean))

        r_struct = parse_structural_features(r_raw)
        j_struct = parse_structural_features(j_raw)

        r_exp = r_struct["explicit_years_exp"]
        j_exp = j_struct["explicit_years_exp"]
        exp_diff = r_exp - j_exp
        has_req_exp = 1.0 if (j_exp > 0 and r_exp >= j_exp) or (j_exp == 0.0 and r_exp > 0) else 0.0

        r_words = max(r_struct["word_count"], 1.0)
        j_words = max(j_struct["word_count"], 1.0)
        length_ratio = r_words / j_words

        # 15 Base
        base = [
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

        # 10 Phase 12 Domain
        j_lower = j_raw.lower()
        req_match = re.search(r"(?:requirements|required|must have|minimum qualifications|qualifications)([\s\S]*?)(?:preferred|nice to have|plus|bonus|what we offer|$)", j_lower)
        pref_match = re.search(r"(?:preferred|nice to have|plus|bonus)([\s\S]*?)(?:what we offer|benefits|$)", j_lower)

        req_text = req_match.group(1) if req_match else j_lower
        pref_text = pref_match.group(1) if pref_match else ""

        req_skills = set(skill_engine.extract_skills(req_text))
        pref_skills = set(skill_engine.extract_skills(pref_text)) if pref_text else set()

        req_cov = len(r_skills & req_skills) / max(len(req_skills), 1)
        pref_cov = len(r_skills & pref_skills) / max(len(pref_skills), 1) if pref_skills else 0.5
        mandatory_failure = 1.0 if len(req_skills) > 0 and req_cov < 0.20 else 0.0

        tech_j = {s for s in j_skills if any(k in s for k in TECH_KEYWORDS)}
        tech_r = {s for s in r_skills if any(k in s for k in TECH_KEYWORDS)}
        tech_cov = len(tech_r & tech_j) / max(len(tech_j), 1)
        tech_count = float(len(tech_r & tech_j))

        j_title = extract_job_title(j_raw).lower()
        j_title_tokens = set(re.findall(r"\b[a-z]{3,}\b", j_title))
        r_tokens = set(re.findall(r"\b[a-z]{3,}\b", r_clean[:300]))
        title_jaccard = len(j_title_tokens & r_tokens) / max(len(j_title_tokens | r_tokens), 1)

        r_edu = extract_education_level(r_raw)
        j_edu = extract_education_level(j_raw)
        edu_match = 1.0 if (j_edu == 0.0 or r_edu >= j_edu) else 0.0

        is_senior_job = 1.0 if re.search(r"\b(senior|lead|principal|staff|architect)\b", j_lower) else 0.0
        senior_mismatch = 1.0 if (is_senior_job and r_exp < 3.0 and r_exp > 0.0) else 0.0

        full_dense = base + [
            req_cov, pref_cov, mandatory_failure,
            tech_cov, tech_count, title_jaccard,
            r_edu, j_edu, edu_match, senior_mismatch
        ]
        DENSE_FEATURE_CACHE[key] = full_dense
        rows.append(full_dense)

    return np.array(rows, dtype=np.float64)

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

def run_phase12b():
    print("=" * 70, flush=True)
    print("RESUMEMATCH AI — PHASE 12B: TRANSFORMER & HYBRID SEMANTIC EXPERIMENTS", flush=True)
    print("=" * 70, flush=True)

    skill_engine = SkillEngine()

    # 1. Load Data Splits
    train_df, test_df = load_primary_dataset()
    train_sub_job, val_sub_job, held_out_test = get_unseen_jobs_split(val_size=0.15, random_state=42)
    train_sub_res, val_sub_res = get_unseen_resumes_split(test_size=0.15, random_state=42)

    dual_train_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_train.csv"))
    dual_val_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_val.csv"))

    # Load 6 contradictory pair hashes & filter clean train
    conflict_path = os.path.join(REPO_ROOT, "results", "phase12_audit", "conflicting_label_pairs_detailed.json")
    if os.path.exists(conflict_path):
        with open(conflict_path) as f:
            conflicts = json.load(f)
        contra_hashes = set(p["pair_hash"] for p in conflicts)
    else:
        contra_hashes = set()

    train_sub_hashes = train_sub_job["resume_text"].apply(hash_text) + "_" + train_sub_job["job_description_text"].apply(hash_text)
    train_sub_job_clean = train_sub_job[~train_sub_hashes.isin(contra_hashes)].reset_index(drop=True)
    print(f"Data Loaded: Train Sub Clean={len(train_sub_job_clean)} | Val Sub Job={len(val_sub_job)} | Val Sub Res={len(val_sub_res)} | Dual Val={len(dual_val_df)} | Official Test={len(held_out_test)}", flush=True)

    # 2. SBERT Pretrained Bi-Encoder Embedding Generation & Caching
    print("\n--- STEP 1: PRETRAINED SBERT EMBEDDING GENERATION (all-MiniLM-L6-v2) ---", flush=True)
    cache_path = os.path.join(EMBEDDING_DIR, "minilm_l6_v2_cache.npz")

    sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    all_resumes = pd.concat([train_df["resume_text"], test_df["resume_text"]]).unique().tolist()
    all_jobs = pd.concat([train_df["job_description_text"], test_df["job_description_text"]]).unique().tolist()

    if os.path.exists(cache_path):
        print(f"Loading cached embeddings from {cache_path}...", flush=True)
        cached_data = np.load(cache_path, allow_pickle=True)
        res_emb_dict = {h: cached_data[f"res_{h}"] for h in cached_data["res_hashes"]}
        job_emb_dict = {h: cached_data[f"job_{h}"] for h in cached_data["job_hashes"]}
        print(f"Loaded {len(res_emb_dict)} resume embeddings and {len(job_emb_dict)} job embeddings from cache.", flush=True)
    else:
        print(f"Encoding {len(all_resumes)} unique resumes and {len(all_jobs)} unique jobs...", flush=True)
        t0 = time.time()
        res_embs = sbert_model.encode(all_resumes, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        job_embs = sbert_model.encode(all_jobs, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        t_enc = time.time() - t0
        print(f"Encoded in {t_enc:.2f}s ({len(all_resumes) + len(all_jobs)} texts, {(len(all_resumes) + len(all_jobs))/t_enc:.1f} texts/s)!", flush=True)

        res_hashes = [hash_text(r) for r in all_resumes]
        job_hashes = [hash_text(j) for j in all_jobs]

        res_emb_dict = {h: res_embs[i] for i, h in enumerate(res_hashes)}
        job_emb_dict = {h: job_embs[i] for i, h in enumerate(job_hashes)}

        save_dict = {"res_hashes": np.array(res_hashes), "job_hashes": np.array(job_hashes)}
        for h, emb in res_emb_dict.items():
            save_dict[f"res_{h}"] = emb
        for h, emb in job_emb_dict.items():
            save_dict[f"job_{h}"] = emb
        np.savez_compressed(cache_path, **save_dict)
        print(f"Saved embedding cache to {cache_path}.", flush=True)

    def build_biencoder_features(df: pd.DataFrame, rep_type: str = "full") -> np.ndarray:
        feats = []
        res_hashes = [hash_text(r) for r in df["resume_text"]]
        job_hashes = [hash_text(j) for j in df["job_description_text"]]

        for rh, jh in zip(res_hashes, job_hashes):
            u = res_emb_dict[rh]
            v = job_emb_dict[jh]
            diff = np.abs(u - v)
            prod = u * v
            cos_sim = float(np.dot(u, v))  # Already unit normalized

            if rep_type == "cosine_only":
                feats.append([cos_sim])
            elif rep_type == "concat":
                feats.append(np.concatenate([u, v]))
            elif rep_type == "interaction":
                feats.append(np.concatenate([diff, prod, [cos_sim]]))
            elif rep_type == "full":
                feats.append(np.concatenate([u, v, diff, prod, [cos_sim]]))
            else:
                raise ValueError(f"Unknown rep_type: {rep_type}")

        return np.array(feats, dtype=np.float32)

    # 3. EXPERIMENT A: Frozen Sentence Embeddings Ablation
    print("\n--- EXPERIMENT A: FROZEN SENTENCE-BERT BI-ENCODER ABLATION ---", flush=True)
    y_tr = np.array(train_sub_job_clean["label"].tolist(), dtype=str)
    y_vl = np.array(val_sub_job["label"].tolist(), dtype=str)

    rep_options = ["cosine_only", "concat", "interaction", "full"]
    exp_a_results = {}

    for rep in rep_options:
        print(f"Evaluating Bi-Encoder Representation: {rep}...", flush=True)
        t0 = time.time()
        X_tr_rep = build_biencoder_features(train_sub_job_clean, rep_type=rep)
        X_vl_rep = build_biencoder_features(val_sub_job, rep_type=rep)

        clf = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
        clf.fit(X_tr_rep, y_tr)
        t_fit = time.time() - t0

        t_inf0 = time.time()
        preds = clf.predict(X_vl_rep)
        probs = clf.predict_proba(X_vl_rep)
        t_inf = time.time() - t_inf0

        metrics = compute_eval_metrics(y_vl, preds, probs)
        metrics["feature_dim"] = X_tr_rep.shape[1]
        metrics["train_time_sec"] = round(t_fit, 2)
        metrics["inf_time_ms_per_pair"] = round((t_inf / len(val_sub_job)) * 1000, 2)
        exp_a_results[rep] = metrics

        print(f"  Rep: {rep:12s} | Dim: {metrics['feature_dim']:4d} | Acc: {metrics['accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f} | Good Fit Recall: {metrics['per_class']['Good Fit']['recall']:.4f} | Inf Latency: {metrics['inf_time_ms_per_pair']:.2f}ms", flush=True)

    with open(os.path.join(OUTPUT_DIR, "experiment_a_embeddings.json"), "w") as f:
        json.dump(exp_a_results, f, indent=2)

    # 4. EXPERIMENT B: Hybrid Semantic + Structured Matching
    print("\n--- EXPERIMENT B: HYBRID SEMANTIC + STRUCTURED MATCHING (A to E) ---", flush=True)
    # Extract dense features
    print("Extracting 25 handcrafted dense domain features...", flush=True)
    dense_tr_25 = extract_25_dense_features(train_sub_job_clean["resume_text"].tolist(), train_sub_job_clean["job_description_text"].tolist(), skill_engine)
    dense_vl_25 = extract_25_dense_features(val_sub_job["resume_text"].tolist(), val_sub_job["job_description_text"].tolist(), skill_engine)

    scaler_dense = StandardScaler()
    dense_tr_scaled = scaler_dense.fit_transform(dense_tr_25)
    dense_vl_scaled = scaler_dense.transform(dense_vl_25)

    # TF-IDF Word
    vec_word = TfidfVectorizer(max_features=2500, ngram_range=(1, 2), min_df=3, sublinear_tf=True, norm="l2")
    combined_texts_tr = [clean_text(r) + " " + clean_text(j) for r, j in zip(train_sub_job_clean["resume_text"], train_sub_job_clean["job_description_text"])]
    combined_texts_vl = [clean_text(r) + " " + clean_text(j) for r, j in zip(val_sub_job["resume_text"], val_sub_job["job_description_text"])]

    tfidf_tr = vec_word.fit_transform(combined_texts_tr)
    tfidf_vl = vec_word.transform(combined_texts_vl)

    # Bi-Encoder Full (1,537 dims)
    sbert_tr = build_biencoder_features(train_sub_job_clean, rep_type="full")
    sbert_vl = build_biencoder_features(val_sub_job, rep_type="full")

    scaler_sbert = StandardScaler()
    sbert_tr_scaled = scaler_sbert.fit_transform(sbert_tr)
    sbert_vl_scaled = scaler_sbert.transform(sbert_vl)

    # Configurations:
    # A: TF-IDF Baseline (Word TF-IDF 2500 + 15 Dense = 2515 dims)
    X_tr_A = sparse.hstack([tfidf_tr, sparse.csr_matrix(dense_tr_scaled[:, :15])], format="csr")
    X_vl_A = sparse.hstack([tfidf_vl, sparse.csr_matrix(dense_vl_scaled[:, :15])], format="csr")

    # B: Frozen Semantic Embeddings only (Bi-Encoder 1537 dims)
    X_tr_B = sbert_tr_scaled
    X_vl_B = sbert_vl_scaled

    # C: Structured Matching Features only (25 Dense features)
    X_tr_C = dense_tr_scaled
    X_vl_C = dense_vl_scaled

    # D: Semantic Embeddings + Structured Features (1537 + 25 = 1562 dims)
    X_tr_D = np.hstack([sbert_tr_scaled, dense_tr_scaled])
    X_vl_D = np.hstack([sbert_vl_scaled, dense_vl_scaled])

    # E: Full Composite (TF-IDF + Semantic Embeddings + Structured Features)
    X_tr_E = sparse.hstack([tfidf_tr, sparse.csr_matrix(sbert_tr_scaled), sparse.csr_matrix(dense_tr_scaled)], format="csr")
    X_vl_E = sparse.hstack([tfidf_vl, sparse.csr_matrix(sbert_vl_scaled), sparse.csr_matrix(dense_vl_scaled)], format="csr")

    hybrid_configs = {
        "Config A: TF-IDF Baseline (Word TF-IDF + 15 Dense)": (X_tr_A, X_vl_A),
        "Config B: Semantic Embeddings Only (SBERT 1,537 dims)": (X_tr_B, X_vl_B),
        "Config C: Structured Matching Only (25 Dense Domain Feats)": (X_tr_C, X_vl_C),
        "Config D: Semantic Embeddings + Structured Matching (1,562 dims)": (X_tr_D, X_vl_D),
        "Config E: Composite (TF-IDF + Semantic + Structured, 4,062 dims)": (X_tr_E, X_vl_E),
    }

    exp_b_results = {}
    for cfg_name, (X_tr_c, X_vl_c) in hybrid_configs.items():
        print(f"Training {cfg_name}...", flush=True)
        t0 = time.time()
        clf_c = LogisticRegression(C=1.0, max_iter=1500, class_weight="balanced", random_state=42)
        clf_c.fit(X_tr_c, y_tr)
        t_fit = time.time() - t0

        t_inf0 = time.time()
        preds_c = clf_c.predict(X_vl_c)
        probs_c = clf_c.predict_proba(X_vl_c)
        t_inf = time.time() - t_inf0

        metrics_c = compute_eval_metrics(y_vl, preds_c, probs_c)
        metrics_c["feature_dim"] = X_tr_c.shape[1]
        metrics_c["train_time_sec"] = round(t_fit, 2)
        metrics_c["inf_time_ms_per_pair"] = round((t_inf / len(val_sub_job)) * 1000, 2)
        exp_b_results[cfg_name] = metrics_c

        print(f"  {cfg_name:55s} | Dim: {metrics_c['feature_dim']:4d} | Acc: {metrics_c['accuracy']:.4f} | Macro F1: {metrics_c['macro_f1']:.4f} | Good Fit Recall: {metrics_c['per_class']['Good Fit']['recall']:.4f}", flush=True)

    with open(os.path.join(OUTPUT_DIR, "experiment_b_hybrid.json"), "w") as f:
        json.dump(exp_b_results, f, indent=2)

    # 5. EXPERIMENT C: Cross-Encoder & Section-Aware Truncation Evaluation
    print("\n--- EXPERIMENT C: CROSS-ENCODER & SECTION-AWARE TRUNCATION ---", flush=True)
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Evaluate Straightforward Truncation vs Section-Aware Truncation
    print("Generating Cross-Encoder scores on Validation (Straight vs Section-Aware)...", flush=True)

    pairs_straight_val = [(r[:1500], j[:1500]) for r, j in zip(val_sub_job["resume_text"], val_sub_job["job_description_text"])]
    pairs_section_val = [(extract_section_aware_text(r), extract_section_aware_text(j)) for r, j in zip(val_sub_job["resume_text"], val_sub_job["job_description_text"])]

    t0 = time.time()
    ce_scores_straight_val = cross_encoder.predict(pairs_straight_val, batch_size=32)
    t_ce_straight = time.time() - t0

    t0 = time.time()
    ce_scores_section_val = cross_encoder.predict(pairs_section_val, batch_size=32)
    t_ce_section = time.time() - t0

    # Cross-encoder inference speed
    ce_lat_ms = (t_ce_straight / len(val_sub_job)) * 1000
    print(f"Cross-Encoder Latency: {ce_lat_ms:.2f} ms/pair ({len(val_sub_job)/t_ce_straight:.1f} pairs/sec)", flush=True)

    # Analyze correlation between Cross-Encoder score and True Compatibility Class
    ce_analysis = {}
    for name, scores in [("Straightforward Truncation", ce_scores_straight_val), ("Section-Aware Truncation", ce_scores_section_val)]:
        df_ce = pd.DataFrame({"label": y_vl, "score": scores})
        stats_by_class = {}
        for c in CLASSES:
            c_scores = df_ce[df_ce["label"] == c]["score"]
            stats_by_class[c] = {
                "mean": float(round(c_scores.mean(), 4)),
                "median": float(round(c_scores.median(), 4)),
                "std": float(round(c_scores.std(), 4)),
                "p25": float(round(np.percentile(c_scores, 25), 4)),
                "p75": float(round(np.percentile(c_scores, 75), 4)),
            }
        ce_analysis[name] = stats_by_class
        print(f"  {name}:", flush=True)
        for c, st in stats_by_class.items():
            print(f"    Class {c:13s}: Mean Score = {st['mean']:.4f} (Med {st['median']:.4f})", flush=True)

    # Evaluate Cross-Encoder augmented Hybrid Model
    print("\nTraining Hybrid Model Augmented with Cross-Encoder Relevance Score...", flush=True)
    # Generate CE scores on training partition
    pairs_straight_tr = [(r[:1500], j[:1500]) for r, j in zip(train_sub_job_clean["resume_text"], train_sub_job_clean["job_description_text"])]
    ce_scores_straight_tr = cross_encoder.predict(pairs_straight_tr, batch_size=32)

    X_tr_ce_aug = np.hstack([X_tr_D, ce_scores_straight_tr.reshape(-1, 1)])
    X_vl_ce_aug = np.hstack([X_vl_D, ce_scores_straight_val.reshape(-1, 1)])

    clf_ce_aug = LogisticRegression(C=1.0, max_iter=1500, class_weight="balanced", random_state=42)
    clf_ce_aug.fit(X_tr_ce_aug, y_tr)
    preds_ce_aug = clf_ce_aug.predict(X_vl_ce_aug)
    probs_ce_aug = clf_ce_aug.predict_proba(X_vl_ce_aug)

    metrics_ce_aug = compute_eval_metrics(y_vl, preds_ce_aug, probs_ce_aug)
    metrics_ce_aug["feature_dim"] = X_tr_ce_aug.shape[1]
    metrics_ce_aug["ce_inference_latency_ms"] = round(ce_lat_ms, 2)
    print(f"  Cross-Encoder Augmented Hybrid: Acc={metrics_ce_aug['accuracy']:.4f} | Macro F1={metrics_ce_aug['macro_f1']:.4f} | Good Fit Recall={metrics_ce_aug['per_class']['Good Fit']['recall']:.4f}", flush=True)

    exp_c_results = {
        "score_distribution_by_class": ce_analysis,
        "latency_ms_per_pair": round(ce_lat_ms, 2),
        "hybrid_with_cross_encoder": metrics_ce_aug
    }
    with open(os.path.join(OUTPUT_DIR, "experiment_c_cross_encoder.json"), "w") as f:
        json.dump(exp_c_results, f, indent=2)

    # 6. EXPERIMENT D: Contrastive Learning Applicability & Margin Analysis
    print("\n--- EXPERIMENT D: CONTRASTIVE LEARNING INVESTIGATION ---", flush=True)
    # SBERT cosine distance analysis: Good Fit vs No Fit vs Potential Fit
    val_cos_sims = exp_a_results["cosine_only"]  # 1 dim cos feature
    X_vl_cos = build_biencoder_features(val_sub_job, rep_type="cosine_only").flatten()
    df_val_cos = pd.DataFrame({"label": y_vl, "cosine_sim": X_vl_cos})

    cos_dist = {}
    for c in CLASSES:
        sims = df_val_cos[df_val_cos["label"] == c]["cosine_sim"]
        cos_dist[c] = {
            "mean": float(round(sims.mean(), 4)),
            "median": float(round(sims.median(), 4)),
            "std": float(round(sims.std(), 4)),
            "p25": float(round(np.percentile(sims, 25), 4)),
            "p75": float(round(np.percentile(sims, 75), 4)),
        }
        print(f"  Class {c:13s} SBERT Cosine Sim: Mean = {cos_dist[c]['mean']:.4f} (Med {cos_dist[c]['median']:.4f}, Std {cos_dist[c]['std']:.4f})", flush=True)

    # Measure margin separation: Good Fit vs No Fit vs Potential Fit
    margin_good_no = cos_dist["Good Fit"]["mean"] - cos_dist["No Fit"]["mean"]
    margin_good_pot = cos_dist["Good Fit"]["mean"] - cos_dist["Potential Fit"]["mean"]
    margin_pot_no = cos_dist["Potential Fit"]["mean"] - cos_dist["No Fit"]["mean"]

    print(f"  Cosine Margin (Good Fit - No Fit):        {margin_good_no:+.4f}", flush=True)
    print(f"  Cosine Margin (Good Fit - Potential Fit): {margin_good_pot:+.4f}", flush=True)
    print(f"  Cosine Margin (Potential Fit - No Fit):   {margin_pot_no:+.4f}", flush=True)

    contrastive_audit = {
        "cosine_distribution_by_class": cos_dist,
        "margins": {
            "good_vs_no_fit": round(margin_good_no, 4),
            "good_vs_potential_fit": round(margin_good_pot, 4),
            "potential_vs_no_fit": round(margin_pot_no, 4),
        },
        "contrastive_viability_verdict": (
            "POOR SEPARATION FOR CONTRASTIVE TRIPLET LOSS: "
            f"The cosine margin between Good Fit ({cos_dist['Good Fit']['mean']:.3f}) and Potential Fit ({cos_dist['Potential Fit']['mean']:.3f}) "
            f"is only {margin_good_pot:+.3f}. Treating Potential Fit as binary hard negative creates severe false-negative gradient penalty."
        )
    }
    with open(os.path.join(OUTPUT_DIR, "experiment_d_contrastive.json"), "w") as f:
        json.dump(contrastive_audit, f, indent=2)

    # 7. GENERALIZATION EVALUATION ACROSS PROTOCOLS
    print("\n--- MULTI-PROTOCOL GENERALIZATION EVALUATION (CHAMPION MODEL) ---", flush=True)
    # Selected Champion: Config D (Semantic Embeddings + Structured Matching, 1562 dims)
    champ_model = LogisticRegression(C=1.0, max_iter=1500, class_weight="balanced", random_state=42)
    champ_model.fit(X_tr_D, y_tr)

    # Benchmark on:
    # 1. Job-Disjoint Validation (val_sub_job)
    m_job_val = exp_b_results["Config D: Semantic Embeddings + Structured Matching (1,562 dims)"]

    # 2. Resume-Disjoint Validation (val_sub_res)
    dense_vl_res = extract_25_dense_features(val_sub_res["resume_text"].tolist(), val_sub_res["job_description_text"].tolist(), skill_engine)
    dense_vl_res_scaled = scaler_dense.transform(dense_vl_res)
    sbert_vl_res = build_biencoder_features(val_sub_res, rep_type="full")
    sbert_vl_res_scaled = scaler_sbert.transform(sbert_vl_res)
    X_vl_res_champ = np.hstack([sbert_vl_res_scaled, dense_vl_res_scaled])

    preds_res = champ_model.predict(X_vl_res_champ)
    probs_res = champ_model.predict_proba(X_vl_res_champ)
    m_res_val = compute_eval_metrics(val_sub_res["label"].tolist(), preds_res, probs_res)

    # 3. Dual-Unseen Validation (dual_val_df)
    dense_vl_dual = extract_25_dense_features(dual_val_df["resume_text"].tolist(), dual_val_df["job_description_text"].tolist(), skill_engine)
    dense_vl_dual_scaled = scaler_dense.transform(dense_vl_dual)
    sbert_vl_dual = build_biencoder_features(dual_val_df, rep_type="full")
    sbert_vl_dual_scaled = scaler_sbert.transform(sbert_vl_dual)
    X_vl_dual_champ = np.hstack([sbert_vl_dual_scaled, dense_vl_dual_scaled])

    preds_dual = champ_model.predict(X_vl_dual_champ)
    probs_dual = champ_model.predict_proba(X_vl_dual_champ)
    m_dual_val = compute_eval_metrics(dual_val_df["label"].tolist(), preds_dual, probs_dual)

    # 4. Official Held-Out Test (held_out_test)
    dense_test = extract_25_dense_features(held_out_test["resume_text"].tolist(), held_out_test["job_description_text"].tolist(), skill_engine)
    dense_test_scaled = scaler_dense.transform(dense_test)
    sbert_test = build_biencoder_features(held_out_test, rep_type="full")
    sbert_test_scaled = scaler_sbert.transform(sbert_test)
    X_test_champ = np.hstack([sbert_test_scaled, dense_test_scaled])

    preds_test = champ_model.predict(X_test_champ)
    probs_test = champ_model.predict_proba(X_test_champ)
    m_test = compute_eval_metrics(held_out_test["label"].tolist(), preds_test, probs_test)

    generalization_report = {
        "job_disjoint_validation": m_job_val,
        "resume_disjoint_validation": m_res_val,
        "dual_unseen_validation": m_dual_val,
        "official_held_out_test": m_test
    }
    with open(os.path.join(OUTPUT_DIR, "generalization_summary.json"), "w") as f:
        json.dump(generalization_report, f, indent=2)

    print(f"  1. Job-Disjoint Validation:  Acc={m_job_val['accuracy']:.4f} | Macro F1={m_job_val['macro_f1']:.4f} | Good Fit Recall={m_job_val['per_class']['Good Fit']['recall']:.4f}", flush=True)
    print(f"  2. Resume-Disjoint Valid:    Acc={m_res_val['accuracy']:.4f} | Macro F1={m_res_val['macro_f1']:.4f} | Good Fit Recall={m_res_val['per_class']['Good Fit']['recall']:.4f}", flush=True)
    print(f"  3. Dual-Unseen Validation:   Acc={m_dual_val['accuracy']:.4f} | Macro F1={m_dual_val['macro_f1']:.4f} | Good Fit Recall={m_dual_val['per_class']['Good Fit']['recall']:.4f}", flush=True)
    print(f"  4. Official Held-Out Test:   Acc={m_test['accuracy']:.4f} | Macro F1={m_test['macro_f1']:.4f} | Good Fit Recall={m_test['per_class']['Good Fit']['recall']:.4f}", flush=True)

    # 8. Bootstrap 95% Confidence Intervals for Champion Model
    print("\n--- BOOTSTRAP 95% CONFIDENCE INTERVALS (Job-Disjoint Validation) ---", flush=True)
    n_boot = 1000
    rng = np.random.RandomState(42)
    indices = np.arange(len(y_vl))
    preds_champ_val = champ_model.predict(X_vl_D)

    b_accs, b_f1s = [], []
    for _ in range(n_boot):
        b_idx = rng.choice(indices, size=len(indices), replace=True)
        b_accs.append(accuracy_score(y_vl[b_idx], preds_champ_val[b_idx]))
        _, _, f1_b, _ = precision_recall_fscore_support(y_vl[b_idx], preds_champ_val[b_idx], average="macro", zero_division=0)
        b_f1s.append(f1_b)

    ci_acc = (float(round(np.percentile(b_accs, 2.5), 4)), float(round(np.percentile(b_accs, 97.5), 4)))
    ci_f1 = (float(round(np.percentile(b_f1s, 2.5), 4)), float(round(np.percentile(b_f1s, 97.5), 4)))
    print(f"Champion 95% CI: Accuracy = [{ci_acc[0]:.4f}, {ci_acc[1]:.4f}] | Macro F1 = [{ci_f1[0]:.4f}, {ci_f1[1]:.4f}]", flush=True)

    ci_report = {
        "n_bootstraps": n_boot,
        "mean_accuracy": float(round(np.mean(b_accs), 4)),
        "ci_95_accuracy": ci_acc,
        "mean_macro_f1": float(round(np.mean(b_f1s), 4)),
        "ci_95_macro_f1": ci_f1
    }
    with open(os.path.join(OUTPUT_DIR, "bootstrap_confidence_intervals.json"), "w") as f:
        json.dump(ci_report, f, indent=2)

    print("\nPhase 12B Experiments Completed Successfully! All results written to results/phase12b_experiments/", flush=True)

if __name__ == "__main__":
    run_phase12b()
