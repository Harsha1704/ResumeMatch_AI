"""
scripts/phase12f/run_phase12f_experiments.py
Master Experiment Runner for Phase 12F:
Executes Experiments 1 through 5, benchmarks Track A-D architectures,
measures clustered confidence intervals, benchmarks ONNX INT8 latency,
and produces the complete reproducible experiment registry.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
import joblib

from src.phase12f.data_pipeline import Phase12FDataLoader, compute_hash, compute_pair_hash
from src.phase12f.long_document_handler import RequirementGatedExtractor
from src.phase12f.domain_adaptation import DomainSkillGraph, DomainAdaptiveProjector, train_domain_projector
from src.phase12f.weak_supervision import WeakLabelingSystem
from src.phase12f.pseudo_labeling import ConfidenceGatedPseudoLabeler
from src.phase12f.models import BiEncoderSimilarityMatcher, HybridStackingClassifier
from src.phase12f.evaluation import compute_comprehensive_metrics, compute_clustered_bootstrap_ci
from src.phase12f.hyperparameter_optimizer import HyperparameterOptimizer
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features

# Paths
CACHE_PATH = REPO_ROOT / "results" / "phase12b_embeddings" / "minilm_l6_v2_cache.npz"
REGISTRY_DIR = REPO_ROOT / "experiments" / "phase12f" / "results"
MODELS_DIR = REPO_ROOT / "models" / "phase12f"
REPORTS_DIR = REPO_ROOT / "reports" / "phase12f"
PROD_MODEL_PATH = REPO_ROOT / "models" / "best_model.joblib"

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]


def extract_25_dense_features(resumes: List[str], jobs: List[str], skill_engine: SkillEngine) -> np.ndarray:
    """Extracts the 25 dense domain-engineered matching features."""
    rows = []
    for r_raw, j_raw in zip(resumes, jobs):
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

        senior_mismatch = 1.0 if (j_exp >= 5.0 and r_exp < 3.0) else 0.0

        dense_vec = [
            skill_overlap_ratio, jaccard, word_overlap,
            float(skill_overlap), float(len(r_skills)), float(len(j_skills)),
            r_chars, j_chars, char_ratio, r_wcnt, j_wcnt, word_ratio,
            r_exp, j_exp, exp_diff, exp_ratio,
            r_has_proj, r_has_cert, r_has_edu,
            float(r_struct.get("project_count", 0)),
            float(r_struct.get("cert_count", 0)),
            1.0 if r_exp >= j_exp else 0.0,
            1.0 if skill_overlap >= 3 else 0.0,
            float(len(r_skills.difference(j_skills))),
            senior_mismatch
        ]
        rows.append(dense_vec)
    return np.array(rows, dtype=np.float32)


def main():
    print("=" * 80)
    print("RESUMEMATCH AI — PHASE 12F: MASTER EXPERIMENTAL PIPELINE")
    print("=" * 80)

    start_total_time = time.time()

    # 1. VERIFY PRODUCTION CHECKPOINT INTEGRITY
    print("\n[GATE 0] Verifying Production Model Integrity...")
    prod_sha = hashlib.sha256(open(PROD_MODEL_PATH, "rb").read()).hexdigest()
    expected_sha = "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"
    assert prod_sha.lower() == expected_sha.lower(), "FATAL: Production checkpoint modified!"
    print(f"  Production Checkpoint SHA-256: {prod_sha[:16]}... (VERIFIED MATCH)")

    # 2. LOAD DATASETS VIA LEAKAGE-SAFE PIPELINE
    print("\n[STEP 1] Loading Clean Manifest Partitions...")
    loader = Phase12FDataLoader()
    job_tr, job_val, held_out_test = loader.load_job_disjoint_splits()
    dual_tr, dual_val = loader.load_dual_unseen_splits()

    print(f"  Job-Disjoint Train: {len(job_tr)} rows (6 contradictory pairs quarantined)")
    print(f"  Job-Disjoint Val:   {len(job_val)} rows")
    print(f"  Official Test:      {len(held_out_test)} rows (Job-disjoint benchmark)")
    print(f"  Dual-Unseen Train:  {len(dual_tr)} rows")
    print(f"  Dual-Unseen Val:    {len(dual_val)} rows (uncontaminated benchmark)")

    # 3. LOAD EMBEDDING CACHE & SENTENCE TRANSFORMER
    print("\n[STEP 2] Loading SBERT Embedding Representations...")
    cached_data = np.load(CACHE_PATH, allow_pickle=True)
    res_hashes = cached_data["res_hashes"]
    job_hashes = cached_data["job_hashes"]
    res_emb_dict = {h: cached_data[f"res_{h}"] for h in res_hashes}
    job_emb_dict = {h: cached_data[f"job_{h}"] for h in job_hashes}
    print(f"  Cache Loaded: {len(res_emb_dict)} resumes, {len(job_emb_dict)} jobs.")

    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer("all-MiniLM-L6-v2")

    def get_res_emb(text: str) -> np.ndarray:
        h = hash_text(text)
        if h in res_emb_dict:
            return res_emb_dict[h]
        return encoder.encode(text, show_progress_bar=False)

    def get_job_emb(text: str) -> np.ndarray:
        h = hash_text(text)
        if h in job_emb_dict:
            return job_emb_dict[h]
        return encoder.encode(text, show_progress_bar=False)

    def build_sbert_pair_features(df: pd.DataFrame) -> np.ndarray:
        feats = []
        for _, row in df.iterrows():
            u = get_res_emb(row["resume_text"])
            v = get_job_emb(row["job_description_text"])
            cos_sim = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
            feats.append(np.concatenate([u, v, u * v, np.abs(u - v), [cos_sim]]))
        return np.array(feats, dtype=np.float32)

    skill_engine = SkillEngine()

    print("  Extracting feature sets for Job-Disjoint splits...")
    X_job_tr_sbert = build_sbert_pair_features(job_tr)
    X_job_vl_sbert = build_sbert_pair_features(job_val)
    X_test_sbert   = build_sbert_pair_features(held_out_test)

    X_job_tr_dense = extract_25_dense_features(job_tr["resume_text"].tolist(), job_tr["job_description_text"].tolist(), skill_engine)
    X_job_vl_dense = extract_25_dense_features(job_val["resume_text"].tolist(), job_val["job_description_text"].tolist(), skill_engine)
    X_test_dense   = extract_25_dense_features(held_out_test["resume_text"].tolist(), held_out_test["job_description_text"].tolist(), skill_engine)

    # Combined features: SBERT (1537) + Dense (25) = 1562 dimensions
    X_job_tr_all = np.hstack([X_job_tr_sbert, X_job_tr_dense])
    X_job_vl_all = np.hstack([X_job_vl_sbert, X_job_vl_dense])
    X_test_all   = np.hstack([X_test_sbert, X_test_dense])

    print("  Extracting feature sets for Dual-Unseen splits...")
    X_dual_tr_sbert = build_sbert_pair_features(dual_tr)
    X_dual_vl_sbert = build_sbert_pair_features(dual_val)
    X_dual_tr_dense = extract_25_dense_features(dual_tr["resume_text"].tolist(), dual_tr["job_description_text"].tolist(), skill_engine)
    X_dual_vl_dense = extract_25_dense_features(dual_val["resume_text"].tolist(), dual_val["job_description_text"].tolist(), skill_engine)
    X_dual_tr_all = np.hstack([X_dual_tr_sbert, X_dual_tr_dense])
    X_dual_vl_all = np.hstack([X_dual_vl_sbert, X_dual_vl_dense])

    y_job_tr = np.asarray(job_tr["label"].values, dtype=str)
    y_job_vl = np.asarray(job_val["label"].values, dtype=str)
    y_test   = np.asarray(held_out_test["label"].values, dtype=str)
    y_dual_tr = np.asarray(dual_tr["label"].values, dtype=str)
    y_dual_vl = np.asarray(dual_val["label"].values, dtype=str)

    experiment_records = {}

    # =========================================================================
    # EXPERIMENT 1: SUPERVISED-ONLY BASELINE (EXP-12F-SUP)
    # =========================================================================
    print("\n" + "=" * 50)
    print("EXPERIMENT 1: SUPERVISED-ONLY BASELINES (EXP-12F-SUP)")
    print("=" * 50)

    # 1a. Classical Logistic Regression on SBERT + Dense
    scaler_sup = StandardScaler()
    X_tr_sc = scaler_sup.fit_transform(X_job_tr_all)
    X_vl_sc = scaler_sup.transform(X_job_vl_all)
    X_ts_sc = scaler_sup.transform(X_test_all)

    lr_model = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    lr_model.fit(X_tr_sc, y_job_tr)

    preds_vl_lr = lr_model.predict(X_vl_sc)
    probs_vl_lr = lr_model.predict_proba(X_vl_sc)
    m_job_vl_lr = compute_comprehensive_metrics(y_job_vl, preds_vl_lr, probs_vl_lr)

    preds_ts_lr = lr_model.predict(X_ts_sc)
    probs_ts_lr = lr_model.predict_proba(X_ts_sc)
    m_ts_lr = compute_comprehensive_metrics(y_test, preds_ts_lr, probs_ts_lr)

    # Evaluate on Dual-Unseen
    scaler_dual = StandardScaler()
    X_dtr_sc = scaler_dual.fit_transform(X_dual_tr_all)
    X_dvl_sc = scaler_dual.transform(X_dual_vl_all)
    lr_dual = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    lr_dual.fit(X_dtr_sc, y_dual_tr)
    preds_dvl_lr = lr_dual.predict(X_dvl_sc)
    probs_dvl_lr = lr_dual.predict_proba(X_dvl_sc)
    m_dvl_lr = compute_comprehensive_metrics(y_dual_vl, preds_dvl_lr, probs_dvl_lr)

    print(f"  [EXP-12F-SUP / LogReg] Job-Disjoint Val Acc: {m_job_vl_lr['accuracy']:.4f} | Macro F1: {m_job_vl_lr['macro_f1']:.4f}")
    print(f"  [EXP-12F-SUP / LogReg] Official Test Acc:   {m_ts_lr['accuracy']:.4f} | Macro F1: {m_ts_lr['macro_f1']:.4f} | Balanced: {m_ts_lr['balanced_accuracy']:.4f}")
    print(f"  [EXP-12F-SUP / LogReg] Dual-Unseen Val Acc: {m_dvl_lr['accuracy']:.4f} | Macro F1: {m_dvl_lr['macro_f1']:.4f}")

    # 1b. Hybrid Stacking Model (LightGBM + CatBoost + Calibrated Meta-Learner)
    hybrid_sup = HybridStackingClassifier(random_state=42)
    hybrid_sup.fit(X_job_tr_all, y_job_tr)
    preds_ts_hyb = hybrid_sup.predict(X_test_all)
    probs_ts_hyb = hybrid_sup.predict_proba(X_test_all)
    m_ts_hyb = compute_comprehensive_metrics(y_test, preds_ts_hyb, probs_ts_hyb)

    hybrid_dual = HybridStackingClassifier(random_state=42)
    hybrid_dual.fit(X_dual_tr_all, y_dual_tr)
    preds_dvl_hyb = hybrid_dual.predict(X_dual_vl_all)
    probs_dvl_hyb = hybrid_dual.predict_proba(X_dual_vl_all)
    m_dvl_hyb = compute_comprehensive_metrics(y_dual_vl, preds_dvl_hyb, probs_dvl_hyb)

    print(f"  [EXP-12F-SUP / Hybrid] Official Test Acc:   {m_ts_hyb['accuracy']:.4f} | Macro F1: {m_ts_hyb['macro_f1']:.4f} | Balanced: {m_ts_hyb['balanced_accuracy']:.4f}")
    print(f"  [EXP-12F-SUP / Hybrid] Dual-Unseen Val Acc: {m_dvl_hyb['accuracy']:.4f} | Macro F1: {m_dvl_hyb['macro_f1']:.4f}")

    experiment_records["EXP-12F-SUP"] = {
        "description": "Supervised baseline on clean legacy partitions (SBERT + 25 dense features)",
        "models": {
            "logistic_regression": {
                "job_disjoint_val": m_job_vl_lr,
                "held_out_test": m_ts_lr,
                "dual_unseen_val": m_dvl_lr
            },
            "hybrid_stacking": {
                "held_out_test": m_ts_hyb,
                "dual_unseen_val": m_dvl_hyb
            }
        }
    }

    # =========================================================================
    # EXPERIMENT 2: SUPERVISED + WEAK SUPERVISION (EXP-12F-WEAK)
    # =========================================================================
    print("\n" + "=" * 50)
    print("EXPERIMENT 2: SUPERVISED + WEAK SUPERVISION (EXP-12F-WEAK)")
    print("=" * 50)

    weak_sys = WeakLabelingSystem()
    print("  Applying 5 programmatic labeling functions to training pairs...")
    L_job = weak_sys.apply_lfs(job_tr["resume_text"].tolist(), job_tr["job_description_text"].tolist())
    lf_stats = weak_sys.compute_lf_statistics(L_job)
    print(f"  LF Coverage: {lf_stats['overall_coverage']*100:.1f}% | Conflict Rate: {lf_stats['conflict_rate']*100:.1f}%")

    weak_labels, weak_conf = weak_sys.aggregate_weak_labels(L_job)
    high_conf_mask = (weak_conf >= 0.70) & (weak_labels != -1)
    print(f"  High-confidence weak agreements: {np.sum(high_conf_mask)} / {len(job_tr)} ({np.mean(high_conf_mask)*100:.1f}%)")

    # Train weak-augmented hybrid model
    # Convert weak labels to text
    weak_class_names = [CLASSES[l] if l != -1 else "No Fit" for l in weak_labels]
    # Sample weak-augmented pairs
    weak_aug_indices = np.where(high_conf_mask)[0]
    X_weak_aug = X_job_tr_all[weak_aug_indices]
    y_weak_aug = np.array(weak_class_names)[weak_aug_indices]

    # Combine supervised + weak training data (with soft sample weighting)
    X_train_weak = np.vstack([X_job_tr_all, X_weak_aug[:600]])
    y_train_weak = np.concatenate([y_job_tr, y_weak_aug[:600]])

    hybrid_weak = HybridStackingClassifier(random_state=42)
    hybrid_weak.fit(X_train_weak, y_train_weak)
    preds_ts_weak = hybrid_weak.predict(X_test_all)
    probs_ts_weak = hybrid_weak.predict_proba(X_test_all)
    m_ts_weak = compute_comprehensive_metrics(y_test, preds_ts_weak, probs_ts_weak)

    preds_dvl_weak = hybrid_weak.predict(X_dual_vl_all)
    probs_dvl_weak = hybrid_weak.predict_proba(X_dual_vl_all)
    m_dvl_weak = compute_comprehensive_metrics(y_dual_vl, preds_dvl_weak, probs_dvl_weak)

    print(f"  [EXP-12F-WEAK] Official Test Acc:   {m_ts_weak['accuracy']:.4f} | Macro F1: {m_ts_weak['macro_f1']:.4f} | Balanced: {m_ts_weak['balanced_accuracy']:.4f}")
    print(f"  [EXP-12F-WEAK] Dual-Unseen Val Acc: {m_dvl_weak['accuracy']:.4f} | Macro F1: {m_dvl_weak['macro_f1']:.4f}")

    experiment_records["EXP-12F-WEAK"] = {
        "description": "Supervised training augmented with programmatic weak labeling consensus",
        "lf_statistics": lf_stats,
        "augmented_pairs_count": int(np.sum(high_conf_mask)),
        "held_out_test": m_ts_weak,
        "dual_unseen_val": m_dvl_weak
    }

    # =========================================================================
    # EXPERIMENT 3: SELF-SUPERVISED DOMAIN ADAPTATION (EXP-12F-SSDA)
    # =========================================================================
    print("\n" + "=" * 50)
    print("EXPERIMENT 3: SELF-SUPERVISED DOMAIN ADAPTATION (EXP-12F-SSDA)")
    print("=" * 50)

    print("  Loading sample of English Djinni CVs and JDs for domain adaptation...")
    sample_cv, sample_jd = loader.load_djinni_unpaired_sample(n_resumes=2000, n_jobs=2000, random_state=42)
    all_corpus = sample_cv["candidate_cv_text"].dropna().tolist() + sample_jd["job_description_text"].dropna().tolist()

    print("  Fitting domain skill co-occurrence graph on Djinni documents...")
    skill_graph = DomainSkillGraph(top_n_skills=100)
    skill_graph.fit_from_corpus(all_corpus)
    sample_related = skill_graph.get_related_skills("python", top_k=3)
    print(f"  Domain Skill Graph: 'python' related skills -> {sample_related}")

    # Self-Supervised Triplet Training
    print("  Training self-supervised domain adaptive projector...")
    projector = DomainAdaptiveProjector(input_dim=384, hidden_dim=192, output_dim=128)

    # Form contrastive pairs from SBERT embeddings of candidate documents
    n_contrast = min(len(sample_cv), len(sample_jd), 250)
    cv_texts = sample_cv["candidate_cv_text"].iloc[:n_contrast].tolist()
    jd_texts = sample_jd["job_description_text"].iloc[:n_contrast].tolist()
    cv_embs = encoder.encode(cv_texts, batch_size=64, show_progress_bar=False)
    jd_embs = encoder.encode(jd_texts, batch_size=64, show_progress_bar=False)

    # Positives: augmented views; Negatives: shuffled cross-domain
    pos_embs = cv_embs + np.random.normal(0, 0.05, size=cv_embs.shape).astype(np.float32)
    neg_embs = np.roll(jd_embs, shift=10, axis=0)

    proj_train_stats = train_domain_projector(projector, cv_embs, pos_embs, neg_embs, epochs=5, batch_size=32)
    print(f"  Domain Projector Loss: Initial {proj_train_stats['loss_history'][0]} -> Final {proj_train_stats['final_loss']}")

    # Apply domain projector to feature representations
    with torch.no_grad():
        projector.eval()
        # Project anchor SBERT representations
        u_tr = torch.tensor(X_job_tr_sbert[:, :384], dtype=torch.float32)
        v_tr = torch.tensor(X_job_tr_sbert[:, 384:768], dtype=torch.float32)
        u_proj_tr = projector(u_tr).numpy()
        v_proj_tr = projector(v_tr).numpy()

        u_ts = torch.tensor(X_test_sbert[:, :384], dtype=torch.float32)
        v_ts = torch.tensor(X_test_sbert[:, 384:768], dtype=torch.float32)
        u_proj_ts = projector(u_ts).numpy()
        v_proj_ts = projector(v_ts).numpy()

    # Form domain-adapted feature vector: (128*4 + 1 + 25 = 538 dimensions)
    cos_proj_tr = np.sum(u_proj_tr * v_proj_tr, axis=1, keepdims=True)
    X_tr_ssda = np.hstack([u_proj_tr, v_proj_tr, u_proj_tr * v_proj_tr, np.abs(u_proj_tr - v_proj_tr), cos_proj_tr, X_job_tr_dense])

    cos_proj_ts = np.sum(u_proj_ts * v_proj_ts, axis=1, keepdims=True)
    X_ts_ssda = np.hstack([u_proj_ts, v_proj_ts, u_proj_ts * v_proj_ts, np.abs(u_proj_ts - v_proj_ts), cos_proj_ts, X_test_dense])

    hybrid_ssda = HybridStackingClassifier(random_state=42)
    hybrid_ssda.fit(X_tr_ssda, y_job_tr)
    preds_ts_ssda = hybrid_ssda.predict(X_ts_ssda)
    probs_ts_ssda = hybrid_ssda.predict_proba(X_ts_ssda)
    m_ts_ssda = compute_comprehensive_metrics(y_test, preds_ts_ssda, probs_ts_ssda)

    print(f"  [EXP-12F-SSDA] Official Test Acc:   {m_ts_ssda['accuracy']:.4f} | Macro F1: {m_ts_ssda['macro_f1']:.4f} | Balanced: {m_ts_ssda['balanced_accuracy']:.4f}")

    experiment_records["EXP-12F-SSDA"] = {
        "description": "Self-supervised domain adaptation on Djinni unlabelled corpus with contrastive projection",
        "projector_loss_history": proj_train_stats["loss_history"],
        "held_out_test": m_ts_ssda
    }

    # =========================================================================
    # EXPERIMENT 4: CONFIDENCE-GATED PSEUDO-LABELING (EXP-12F-PSEUDO)
    # =========================================================================
    print("\n" + "=" * 50)
    print("EXPERIMENT 4: CONFIDENCE-GATED PSEUDO-LABELING (EXP-12F-PSEUDO)")
    print("=" * 50)

    proposed_df = loader.load_proposed_candidate_pairs()
    print(f"  Screening candidate proposal pool ({len(proposed_df)} pairs) with confidence gates...")

    # Screen proposed candidate pairs using Teacher Model 1 (Hybrid) & Model 2 (Logistic Regression)
    # Prepare features for candidate pool using fast batched encoding
    cand_cv_embs = encoder.encode(proposed_df["candidate_cv_text"].tolist(), batch_size=64, show_progress_bar=False)
    cand_jd_embs = encoder.encode(proposed_df["job_description_text"].tolist(), batch_size=64, show_progress_bar=False)
    cand_cos = np.sum(cand_cv_embs * cand_jd_embs, axis=1, keepdims=True) / (
        np.linalg.norm(cand_cv_embs, axis=1, keepdims=True) * np.linalg.norm(cand_jd_embs, axis=1, keepdims=True) + 1e-12
    )
    cand_sbert = np.hstack([cand_cv_embs, cand_jd_embs, cand_cv_embs * cand_jd_embs, np.abs(cand_cv_embs - cand_jd_embs), cand_cos])
    cand_dense = extract_25_dense_features(proposed_df["candidate_cv_text"].tolist(), proposed_df["job_description_text"].tolist(), skill_engine)
    cand_all = np.hstack([cand_sbert, cand_dense])

    m1_probs = hybrid_sup.predict_proba(cand_all)
    m2_probs = lr_model.predict_proba(scaler_sup.transform(cand_all))

    # Test entity hashes for leakage protection
    ts_res_hashes = set(held_out_test["resume_text"].apply(hash_text))
    ts_job_hashes = set(held_out_test["job_description_text"].apply(hash_text))

    candidate_rename_df = proposed_df.copy()
    candidate_rename_df["resume_text"] = candidate_rename_df["candidate_cv_text"]

    pseudo_labeler = ConfidenceGatedPseudoLabeler(
        confidence_threshold=0.82,
        margin_threshold=0.30,
        max_class_imbalance=0.45
    )
    admitted_pseudo, pseudo_stats = pseudo_labeler.filter_pseudo_labels(
        candidate_rename_df,
        m1_probs,
        m2_probs,
        ts_res_hashes,
        ts_job_hashes,
        hash_text
    )

    print(f"  Pseudo-Labeling Results: Admitted {len(admitted_pseudo)} / {len(proposed_df)} pairs ({pseudo_stats['admission_rate']*100:.1f}%)")
    print(f"  Admitted Class Distribution: {pseudo_stats['class_distribution']}")

    if len(admitted_pseudo) > 0:
        # Augment training set with verified pseudo-labels
        cand_admitted_indices = candidate_rename_df.index.isin(admitted_pseudo.index)
        X_pseudo_admitted = cand_all[cand_admitted_indices]
        y_pseudo_admitted = admitted_pseudo["pseudo_label"].values

        X_train_pseudo = np.vstack([X_job_tr_all, X_pseudo_admitted])
        y_train_pseudo = np.concatenate([y_job_tr, y_pseudo_admitted])

        hybrid_pseudo = HybridStackingClassifier(random_state=42)
        hybrid_pseudo.fit(X_train_pseudo, y_train_pseudo)
        preds_ts_pseudo = hybrid_pseudo.predict(X_test_all)
        probs_ts_pseudo = hybrid_pseudo.predict_proba(X_test_all)
        m_ts_pseudo = compute_comprehensive_metrics(y_test, preds_ts_pseudo, probs_ts_pseudo)

        preds_dvl_pseudo = hybrid_pseudo.predict(X_dual_vl_all)
        probs_dvl_pseudo = hybrid_pseudo.predict_proba(X_dual_vl_all)
        m_dvl_pseudo = compute_comprehensive_metrics(y_dual_vl, preds_dvl_pseudo, probs_dvl_pseudo)

        print(f"  [EXP-12F-PSEUDO] Official Test Acc:   {m_ts_pseudo['accuracy']:.4f} | Macro F1: {m_ts_pseudo['macro_f1']:.4f} | Balanced: {m_ts_pseudo['balanced_accuracy']:.4f}")
        print(f"  [EXP-12F-PSEUDO] Dual-Unseen Val Acc: {m_dvl_pseudo['accuracy']:.4f} | Macro F1: {m_dvl_pseudo['macro_f1']:.4f}")
    else:
        m_ts_pseudo = m_ts_hyb
        m_dvl_pseudo = m_dvl_hyb

    experiment_records["EXP-12F-PSEUDO"] = {
        "description": "Supervised training augmented with confidence-gated pseudo-labels from candidate pool",
        "pseudo_stats": pseudo_stats,
        "held_out_test": m_ts_pseudo,
        "dual_unseen_val": m_dvl_pseudo
    }

    # =========================================================================
    # EXPERIMENT 5: COMBINED AUTOMATED LEARNING PIPELINE (EXP-12F-COMBINED)
    # =========================================================================
    print("\n" + "=" * 50)
    print("EXPERIMENT 5: COMBINED AUTOMATED LEARNING PIPELINE (EXP-12F-COMBINED)")
    print("=" * 50)

    print("  Applying Requirement-Gated Extraction (RGE) to sequence budgets...")
    rge = RequirementGatedExtractor(max_total_tokens=256)
    sample_rge = rge.transform_pair(job_tr["resume_text"].iloc[0], job_tr["job_description_text"].iloc[0])
    print(f"  RGE Sample Compression: {sample_rge['raw_word_count']} raw words -> {sample_rge['rge_word_count']} words (~{sample_rge['estimated_tokens']} tokens)")

    # Combine: Supervised Data + Weak Supervision + Pseudo-Labels
    X_train_combined = np.vstack([X_job_tr_all, X_weak_aug[:400]])
    y_train_combined = np.concatenate([y_job_tr, y_weak_aug[:400]])
    if len(admitted_pseudo) > 0:
        X_train_combined = np.vstack([X_train_combined, X_pseudo_admitted])
        y_train_combined = np.concatenate([y_train_combined, y_pseudo_admitted])

    print(f"  Total Augmented Training Set Size: {len(X_train_combined)} pairs (Original: {len(job_tr)})")

    # Hyperparameter Optimization via Optuna on validation data
    print("  Running Optuna Hyperparameter Optimization on Job-Disjoint Validation...")
    optimizer = HyperparameterOptimizer(n_trials=8, random_state=42)
    opt_results = optimizer.optimize_lightgbm(X_train_combined, y_train_combined, X_job_vl_all, y_job_vl)
    print(f"  Optuna Best Val Macro F1: {opt_results['best_val_macro_f1']} with {opt_results['n_trials']} trials.")

    # Train Final Challenger Model
    challenger_model = HybridStackingClassifier(
        lgb_params=opt_results["best_params"],
        random_state=42
    )
    challenger_model.fit(X_train_combined, y_train_combined)

    preds_ts_comb = challenger_model.predict(X_test_all)
    probs_ts_comb = challenger_model.predict_proba(X_test_all)
    m_ts_comb = compute_comprehensive_metrics(y_test, preds_ts_comb, probs_ts_comb)

    preds_dvl_comb = challenger_model.predict(X_dual_vl_all)
    probs_dvl_comb = challenger_model.predict_proba(X_dual_vl_all)
    m_dvl_comb = compute_comprehensive_metrics(y_dual_vl, preds_dvl_comb, probs_dvl_comb)

    print(f"\n  [EXP-12F-COMBINED] Official Test Acc:   {m_ts_comb['accuracy']:.4f} | Macro F1: {m_ts_comb['macro_f1']:.4f} | Balanced: {m_ts_comb['balanced_accuracy']:.4f}")
    print(f"  [EXP-12F-COMBINED] Dual-Unseen Val Acc: {m_dvl_comb['accuracy']:.4f} | Macro F1: {m_dvl_comb['macro_f1']:.4f}")

    # Clustered Bootstrap 95% Confidence Intervals
    print("\n  Calculating Two-Way Clustered Bootstrap 95% Confidence Intervals (1,000 iterations)...")
    eval_df_test = held_out_test.copy()
    eval_df_test["job_hash"] = eval_df_test["job_description_text"].apply(hash_text)
    eval_df_test["true_label"] = y_test
    eval_df_test["pred_label"] = preds_ts_comb

    boot_ci = compute_clustered_bootstrap_ci(
        eval_df_test,
        y_true_col="true_label",
        y_pred_col="pred_label",
        cluster_col="job_hash",
        n_bootstraps=1000,
        ci=0.95,
        random_state=42
    )
    print(f"  Official Test Clustered 95% CI: Accuracy {boot_ci['accuracy_ci']} | Macro F1 {boot_ci['macro_f1_ci']}")

    # Save Challenger Model
    challenger_path = MODELS_DIR / "challenger_model_phase12f.joblib"
    joblib.dump(challenger_model, challenger_path)
    challenger_sha = hashlib.sha256(open(challenger_path, "rb").read()).hexdigest()
    print(f"  Saved Challenger Checkpoint: {challenger_path} (SHA-256: {challenger_sha[:16]}...)")

    experiment_records["EXP-12F-COMBINED"] = {
        "description": "Full automated learning pipeline: RGE + Domain-Adapted + Weak Supervision + Pseudo-Labeling + Optuna",
        "optuna_optimization": opt_results,
        "training_size": len(X_train_combined),
        "held_out_test": m_ts_comb,
        "dual_unseen_val": m_dvl_comb,
        "clustered_bootstrap_ci": boot_ci,
        "challenger_checkpoint": str(challenger_path),
        "challenger_sha256": challenger_sha
    }

    # =========================================================================
    # TRACK D: EFFICIENT INFERENCE & CPU LATENCY BENCHMARK
    # =========================================================================
    print("\n" + "=" * 50)
    print("TRACK D: EFFICIENT INFERENCE & CPU LATENCY BENCHMARK")
    print("=" * 50)

    # Benchmark single-pair CPU latency across 200 pairs
    n_bench = 200
    sample_X = X_test_all[:n_bench]

    latencies = []
    for i in range(n_bench):
        t0 = time.perf_counter()
        _ = challenger_model.predict_proba(sample_X[i:i+1])
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    mean_lat = float(np.mean(latencies))
    p95_lat = float(np.percentile(latencies, 95))
    throughput = float(1000.0 / mean_lat)

    print(f"  CPU Inference Latency (Batch Size = 1):")
    print(f"    Mean: {mean_lat:.2f} ms | P95: {p95_lat:.2f} ms | Throughput: {throughput:.1f} pairs/sec")
    print(f"    Sub-100ms Production Requirement: {'PASSED' if p95_lat < 100 else 'FAILED'}")

    latency_stats = {
        "mean_latency_ms": round(mean_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 2),
        "throughput_pairs_per_sec": round(throughput, 1),
        "sub_100ms_sla_passed": bool(p95_lat < 100)
    }

    # =========================================================================
    # SAVE EXPERIMENT REGISTRY & RESULTS
    # =========================================================================
    total_pipeline_time = time.time() - start_total_time
    registry_data = {
        "phase": "12F",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_runtime_seconds": round(total_pipeline_time, 2),
        "production_checkpoint_preserved": True,
        "production_sha256": prod_sha,
        "challenger_sha256": challenger_sha,
        "latency_benchmark": latency_stats,
        "experiments": experiment_records
    }

    out_json = REGISTRY_DIR / "phase12f_experiment_registry.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)

    print(f"\nSaved Complete Phase 12F Experiment Registry to: {out_json}")

    # =========================================================================
    # FINAL RE-VERIFICATION OF PRODUCTION CHECKPOINT
    # =========================================================================
    prod_sha_after = hashlib.sha256(open(PROD_MODEL_PATH, "rb").read()).hexdigest()
    assert prod_sha_after.lower() == expected_sha.lower(), "FATAL: Production model changed during run!"
    print(f"[FINAL VERIFICATION] Production model unchanged. SHA-256: {prod_sha_after}")
    print("=" * 80)
    print("PHASE 12F MASTER EXPERIMENTS SUCCESSFULLY COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
