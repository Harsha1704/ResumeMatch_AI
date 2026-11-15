"""
scripts/run_phase12d_evaluation.py
Phase 12D Permanent ML Evaluation Repair & Leakage-Free Benchmark Runner.

Enforces:
1. Cryptographic manifest verification before loading data.
2. Mandatory entity and pair isolation validation prior to training.
3. Separate model training on the designated training partition for each protocol.
4. Complete pipeline transformation isolation (TF-IDF, Scalers fit strictly on train).
5. Comprehensive experiment metadata tracking and prediction logging.
"""

import os
import sys
import json
import time
import re
import hashlib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix, precision_recall_fscore_support
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine
from src.evaluation.split_validator import (
    SplitLeakageError,
    validate_split_isolation,
    compute_overlap_metrics,
    validate_manifest_integrity,
    validate_embedding_cache_keys,
    hash_text,
    hash_pair
)

MANIFEST_DIR = os.path.join(REPO_ROOT, "manifests", "v1")
MANIFEST_JSON = os.path.join(MANIFEST_DIR, "manifest_v1.json")
OUTPUT_DIR = os.path.join(REPO_ROOT, "results", "phase12d_experiments")
CACHE_PATH = os.path.join(REPO_ROOT, "results", "phase12b_embeddings", "minilm_l6_v2_cache.npz")
PREDICTIONS_DIR = os.path.join(OUTPUT_DIR, "predictions")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
ID_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

DENSE_FEATURE_CACHE = {}


def extract_education_level(text: str) -> float:
    t = text.lower()
    if any(k in t for k in ["phd", "ph.d", "doctorate"]):
        return 4.0
    if any(k in t for k in ["master", "m.s", "m.tech", "mba", "post graduate"]):
        return 3.0
    if any(k in t for k in ["bachelor", "b.s", "b.tech", "b.e", "undergraduate", "degree"]):
        return 2.0
    if any(k in t for k in ["diploma", "associate"]):
        return 1.0
    return 0.0


def extract_25_dense_features(resumes: List[str], jobs: List[str], skill_engine: SkillEngine) -> np.ndarray:
    rows = []
    for r_raw, j_raw in zip(resumes, jobs):
        key = (hash_text(r_raw), hash_text(j_raw))
        if key in DENSE_FEATURE_CACHE:
            rows.append(DENSE_FEATURE_CACHE[key])
            continue

        r_clean = clean_text(r_raw)
        j_clean = clean_text(j_raw)

        r_struct = parse_structural_features(r_raw)
        j_struct = parse_structural_features(j_raw)

        r_skills = set(skill_engine.extract_skills(r_clean))
        j_skills = set(skill_engine.extract_skills(j_clean))

        n_j_skills = max(len(j_skills), 1)
        skill_overlap = len(r_skills.intersection(j_skills))
        skill_overlap_ratio = skill_overlap / n_j_skills
        jaccard = skill_overlap / max(len(r_skills.union(j_skills)), 1)

        r_words = set(r_clean.split())
        j_words = set(j_clean.split())
        word_overlap = len(r_words.intersection(j_words)) / max(len(j_words), 1)

        r_chars = float(len(r_raw))
        j_chars = float(len(j_raw))
        r_wcnt = float(len(r_words))
        j_wcnt = float(len(j_words))
        char_ratio = r_chars / max(j_chars, 1.0)
        word_ratio = r_wcnt / max(j_wcnt, 1.0)

        r_exp = float(r_struct.get("experience_years", 0))
        j_exp = float(j_struct.get("experience_years", 0))
        exp_diff = r_exp - j_exp
        exp_ratio = r_exp / max(j_exp, 1.0)

        r_has_proj = 1.0 if r_struct.get("project_count", 0) > 0 else 0.0
        r_has_cert = 1.0 if r_struct.get("cert_count", 0) > 0 else 0.0
        r_has_edu = 1.0 if r_struct.get("has_education", False) else 0.0

        r_edu = extract_education_level(r_raw)
        j_edu = extract_education_level(j_raw)
        edu_match = 1.0 if r_edu >= j_edu else 0.0
        senior_mismatch = 1.0 if (j_exp >= 5.0 and r_exp < 3.0) else 0.0

        full_dense = [
            skill_overlap_ratio, jaccard, word_overlap,
            float(skill_overlap), float(len(r_skills)), float(len(j_skills)),
            r_chars, j_chars, char_ratio, r_wcnt, j_wcnt, word_ratio,
            r_exp, j_exp, exp_diff, exp_ratio,
            r_has_proj, r_has_cert, r_has_edu,
            float(r_struct.get("project_count", 0)),
            float(r_struct.get("cert_count", 0)),
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


def save_prediction_records(
    df: pd.DataFrame,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    protocol: str,
    model_name: str
) -> str:
    out_file = os.path.join(PREDICTIONS_DIR, f"predictions_{protocol}_{model_name}.csv")
    records = []
    for idx, row in df.iterrows():
        rh = hash_text(row["resume_text"])
        jh = hash_text(row["job_description_text"])
        ph = hash_pair(row["resume_text"], row["job_description_text"])
        records.append({
            "pair_hash": ph,
            "resume_hash": rh,
            "job_hash": jh,
            "actual_label": row["label"],
            "predicted_label": y_pred[idx],
            "prob_no_fit": round(float(y_prob[idx, 0]), 4),
            "prob_potential_fit": round(float(y_prob[idx, 1]), 4),
            "prob_good_fit": round(float(y_prob[idx, 2]), 4)
        })
    pred_df = pd.DataFrame(records)
    pred_df.to_csv(out_file, index=False)
    return out_file


def main():
    print("=" * 80)
    print("PHASE 12D: PERMANENT ML EVALUATION REPAIR & BENCHMARK")
    print("=" * 80)

    # 1. Cryptographic Manifest Verification
    print("\n[STEP 1] Validating Split Manifest V1 Integrity...")
    manifest_audit = validate_manifest_integrity(MANIFEST_JSON)
    print(f"  Manifest Version: {manifest_audit['manifest_version']}")
    print(f"  Verified Files: {len(manifest_audit['files_verified'])} files cryptographically verified.")

    # 2. Embedding Cache Key Verification
    print("\n[STEP 2] Validating Embedding Cache Keys & Integrity...")
    cache_audit = validate_embedding_cache_keys(CACHE_PATH)
    print(f"  Cache Status: {cache_audit['status']} | Resumes: {cache_audit['num_resumes']} | Jobs: {cache_audit['num_jobs']}")
    cached_data = np.load(CACHE_PATH, allow_pickle=True)
    res_hashes = cached_data["res_hashes"]
    job_hashes = cached_data["job_hashes"]
    res_emb_dict = {h: cached_data[f"res_{h}"] for h in res_hashes}
    job_emb_dict = {h: cached_data[f"job_{h}"] for h in job_hashes}

    skill_engine = SkillEngine()

    def build_sbert_features(df: pd.DataFrame) -> np.ndarray:
        feats = []
        for _, row in df.iterrows():
            rh = hash_text(row["resume_text"])
            jh = hash_text(row["job_description_text"])
            u = res_emb_dict[rh]
            v = job_emb_dict[jh]
            cos_sim = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
            feats.append(np.concatenate([u, v, u * v, np.abs(u - v), [cos_sim]]))
        return np.array(feats, dtype=np.float32)

    # Protocols to run
    protocols_config = [
        {
            "name": "job_disjoint_val",
            "protocol": "job_disjoint",
            "train_file": "job_disjoint_train_v1.parquet",
            "eval_file": "job_disjoint_val_v1.parquet",
            "description": "Validation on 42 unseen job descriptions (0% job, 0% pair overlap)"
        },
        {
            "name": "resume_disjoint_val",
            "protocol": "resume_disjoint",
            "train_file": "resume_disjoint_train_v1.parquet",
            "eval_file": "resume_disjoint_val_v1.parquet",
            "description": "Validation on 97 unseen candidate resumes (0% resume, 0% pair overlap)"
        },
        {
            "name": "dual_unseen_val",
            "protocol": "dual_unseen",
            "train_file": "dual_unseen_train_v1.parquet",
            "eval_file": "dual_unseen_val_v1.parquet",
            "description": "Validation on dual-unseen entities (0% resume, 0% job, 0% pair overlap)"
        },
        {
            "name": "held_out_test",
            "protocol": "held_out_test",
            "train_file": "job_disjoint_train_v1.parquet",
            "eval_file": "held_out_test_v1.parquet",
            "description": "Official held-out test on 71 unseen job descriptions (0% job, 0% pair overlap)"
        }
    ]

    all_benchmark_results = {}

    for proto_cfg in protocols_config:
        proto_name = proto_cfg["name"]
        proto_type = proto_cfg["protocol"]
        print("\n" + "=" * 60)
        print(f"BENCHMARK PROTOCOL: {proto_name.upper()} ({proto_type})")
        print(f"Description: {proto_cfg['description']}")
        print("=" * 60)

        train_path = os.path.join(MANIFEST_DIR, proto_cfg["train_file"])
        eval_path = os.path.join(MANIFEST_DIR, proto_cfg["eval_file"])

        train_df = pd.read_parquet(train_path)
        eval_df = pd.read_parquet(eval_path)

        # MANDATORY ENTITY AND PAIR ISOLATION VALIDATION
        print(f"Executing Pre-Evaluation Split Isolation Guard on {proto_name}...")
        v_res = validate_split_isolation(train_df, eval_df, protocol=proto_type, split_name=proto_name)
        print(f"  [PASS] Split Isolation Confirmed. Overlap metrics:")
        print(f"    Resumes Overlapping: {v_res['metrics']['resume_overlap_count']}/{v_res['metrics']['eval_resumes']} ({v_res['metrics']['resume_overlap_pct']}%)")
        print(f"    Jobs Overlapping: {v_res['metrics']['job_overlap_count']}/{v_res['metrics']['eval_jobs']} ({v_res['metrics']['job_overlap_pct']}%)")
        print(f"    Pairs Overlapping: {v_res['metrics']['pair_overlap_count']}/{v_res['metrics']['eval_pairs']} ({v_res['metrics']['pair_overlap_pct']}%)")

        y_train = train_df["label"].tolist()
        y_eval = eval_df["label"].tolist()

        # -------------------------------------------------------------
        # MODEL 1: FROZEN CLASSICAL BASELINE (Word TF-IDF + 15 Dense)
        # -------------------------------------------------------------
        print(f"\n--- Training Dedicated Classical Baseline on {proto_name} (N_tr={len(train_df)}) ---")
        t0 = time.time()
        r_tr_clean = [clean_text(t) for t in train_df["resume_text"]]
        j_tr_clean = [clean_text(t) for t in train_df["job_description_text"]]
        r_ev_clean = [clean_text(t) for t in eval_df["resume_text"]]
        j_ev_clean = [clean_text(t) for t in eval_df["job_description_text"]]

        # TF-IDF fit STRICTLY on training split
        tfidf = TfidfVectorizer(max_features=2500, stop_words="english", ngram_range=(1, 2))
        tfidf.fit(r_tr_clean + j_tr_clean)

        r_tr_tfidf = tfidf.transform(r_tr_clean)
        j_tr_tfidf = tfidf.transform(j_tr_clean)
        r_ev_tfidf = tfidf.transform(r_ev_clean)
        j_ev_tfidf = tfidf.transform(j_ev_clean)

        cos_tr = np.array([cosine_similarity(r_tr_tfidf[i], j_tr_tfidf[i])[0, 0] for i in range(len(train_df))]).reshape(-1, 1)
        cos_ev = np.array([cosine_similarity(r_ev_tfidf[i], j_ev_tfidf[i])[0, 0] for i in range(len(eval_df))]).reshape(-1, 1)

        dense_tr_25 = extract_25_dense_features(train_df["resume_text"].tolist(), train_df["job_description_text"].tolist(), skill_engine)
        dense_ev_25 = extract_25_dense_features(eval_df["resume_text"].tolist(), eval_df["job_description_text"].tolist(), skill_engine)

        # Scaler fit STRICTLY on training split
        scaler_dense15 = StandardScaler()
        dense15_tr_scaled = scaler_dense15.fit_transform(dense_tr_25[:, :14])
        dense15_ev_scaled = scaler_dense15.transform(dense_ev_25[:, :14])

        X_tr_A = np.hstack([r_tr_tfidf.toarray()[:len(train_df), :2500], cos_tr, dense15_tr_scaled])
        X_ev_A = np.hstack([r_ev_tfidf.toarray()[:len(eval_df), :2500], cos_ev, dense15_ev_scaled])

        model_A = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
        model_A.fit(X_tr_A, y_train)
        pred_A = model_A.predict(X_ev_A)
        prob_A = model_A.predict_proba(X_ev_A)
        t_A = time.time() - t0

        metrics_A = compute_eval_metrics(y_eval, pred_A, prob_A)
        metrics_A["train_time_sec"] = round(t_A, 2)
        metrics_A["feature_dim"] = X_tr_A.shape[1]

        pred_file_A = save_prediction_records(eval_df, pred_A, prob_A, proto_name, "classical_baseline")
        print(f"  Classical Baseline: Acc={metrics_A['accuracy']:.4f} | Macro F1={metrics_A['macro_f1']:.4f} | Good Fit Recall={metrics_A['per_class']['Good Fit']['recall']:.4f} | Preds: {os.path.basename(pred_file_A)}")

        # -------------------------------------------------------------
        # MODEL 2: SBERT CONFIG B (Pretrained Embeddings Only, 1537 dims)
        # -------------------------------------------------------------
        print(f"\n--- Training Dedicated SBERT Config B on {proto_name} (N_tr={len(train_df)}) ---")
        t0 = time.time()
        sbert_tr = build_sbert_features(train_df)
        sbert_ev = build_sbert_features(eval_df)

        # Scaler fit STRICTLY on training split
        scaler_sbert = StandardScaler()
        sbert_tr_scaled = scaler_sbert.fit_transform(sbert_tr)
        sbert_ev_scaled = scaler_sbert.transform(sbert_ev)

        model_B = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
        model_B.fit(sbert_tr_scaled, y_train)
        pred_B = model_B.predict(sbert_ev_scaled)
        prob_B = model_B.predict_proba(sbert_ev_scaled)
        t_B = time.time() - t0

        metrics_B = compute_eval_metrics(y_eval, pred_B, prob_B)
        metrics_B["train_time_sec"] = round(t_B, 2)
        metrics_B["feature_dim"] = sbert_tr.shape[1]

        pred_file_B = save_prediction_records(eval_df, pred_B, prob_B, proto_name, "sbert_config_b")
        print(f"  SBERT Config B:     Acc={metrics_B['accuracy']:.4f} | Macro F1={metrics_B['macro_f1']:.4f} | Good Fit Recall={metrics_B['per_class']['Good Fit']['recall']:.4f} | Preds: {os.path.basename(pred_file_B)}")

        # -------------------------------------------------------------
        # MODEL 3: HYBRID CONFIG D (SBERT 1537 + 25 Dense = 1562 dims)
        # -------------------------------------------------------------
        print(f"\n--- Training Dedicated Hybrid Config D on {proto_name} (N_tr={len(train_df)}) ---")
        t0 = time.time()
        scaler_dense25 = StandardScaler()
        dense25_tr_scaled = scaler_dense25.fit_transform(dense_tr_25)
        dense25_ev_scaled = scaler_dense25.transform(dense_ev_25)

        X_tr_D = np.hstack([sbert_tr_scaled, dense25_tr_scaled])
        X_ev_D = np.hstack([sbert_ev_scaled, dense25_ev_scaled])

        model_D = LogisticRegression(C=1.0, max_iter=1500, class_weight="balanced", random_state=42)
        model_D.fit(X_tr_D, y_train)
        pred_D = model_D.predict(X_ev_D)
        prob_D = model_D.predict_proba(X_ev_D)
        t_D = time.time() - t0

        metrics_D = compute_eval_metrics(y_eval, pred_D, prob_D)
        metrics_D["train_time_sec"] = round(t_D, 2)
        metrics_D["feature_dim"] = X_tr_D.shape[1]

        pred_file_D = save_prediction_records(eval_df, pred_D, prob_D, proto_name, "hybrid_config_d")
        print(f"  Hybrid Config D:    Acc={metrics_D['accuracy']:.4f} | Macro F1={metrics_D['macro_f1']:.4f} | Good Fit Recall={metrics_D['per_class']['Good Fit']['recall']:.4f} | Preds: {os.path.basename(pred_file_D)}")

        all_benchmark_results[proto_name] = {
            "protocol_type": proto_type,
            "train_record_count": len(train_df),
            "eval_record_count": len(eval_df),
            "isolation_audit": v_res["metrics"],
            "models": {
                "classical_baseline": metrics_A,
                "sbert_config_b": metrics_B,
                "hybrid_config_d": metrics_D
            }
        }

    # Save comprehensive evaluation results
    out_json = os.path.join(OUTPUT_DIR, "reproducible_evaluation_results.json")
    with open(out_json, "w") as f:
        json.dump(all_benchmark_results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PHASE 12D BENCHMARK COMPLETE. ALL ARTIFACTS WRITTEN TO: {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
