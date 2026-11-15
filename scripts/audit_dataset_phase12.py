"""
scripts/audit_dataset_phase12.py
Phase 12 In-Depth Dataset Quality & Label Audit Engine.

Analyzes:
1. Exact duplicates in pairs, resumes, and jobs.
2. Near-duplicates (Cosine similarity > 0.95 on normalized TF-IDF) among resumes and job descriptions.
3. Conflicting label analysis: In-depth examination of the 6 contradictory pairs.
4. Ambiguous compatibility boundaries:
   - Analysis of pairs near class boundaries (e.g., Potential Fit vs Good Fit vs No Fit).
   - Skill overlap distribution per label class.
5. Class imbalance across train, validation splits, and test sets.
6. Entity graph topology and fan-in/fan-out (resumes per job, jobs per resume).
7. Cross-split data leakage analysis (Job-disjoint, Resume-disjoint, Dual-unseen, Official test).
8. Generates machine-readable audit report in results/phase12_audit/
"""

import os
import sys
import json
import re
import hashlib
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.preprocessing.skill_extractor import SkillEngine

OUTPUT_DIR = os.path.join(REPO_ROOT, "results", "phase12_audit")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def hash_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text).strip().lower())
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()

def normalize_text_for_sim(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", str(text).lower())
    return re.sub(r"\s+", " ", cleaned).strip()

def run_phase12_audit():
    print("=" * 70)
    print("RESUMEMATCH AI — PHASE 12: DATASET & LABEL QUALITY AUDIT")
    print("=" * 70)

    # 1. Load Raw Datasets
    raw_train_path = os.path.join(REPO_ROOT, "data", "raw", "resume_job_fit_train.csv")
    raw_test_path = os.path.join(REPO_ROOT, "data", "raw", "resume_job_fit_test.csv")
    raw_train_df = pd.read_csv(raw_train_path)
    raw_test_df = pd.read_csv(raw_test_path)

    print(f"Loaded raw datasets: Train={len(raw_train_df)} rows, Test={len(raw_test_df)} rows.")

    # 2. Exact Duplicates
    train_exact_dup_count = raw_train_df.duplicated().sum()
    test_exact_dup_count = raw_test_df.duplicated().sum()
    print(f"Exact Duplicate Rows in Train: {train_exact_dup_count}, Test: {test_exact_dup_count}")

    # Remove exact duplicate rows for subsequent pair-level analysis
    train_df = raw_train_df.drop_duplicates().reset_index(drop=True)
    test_df = raw_test_df.drop_duplicates().reset_index(drop=True)

    # 3. Conflicting Labels on Identical Text
    # Hash resume and job text
    train_df["resume_hash"] = train_df["resume_text"].apply(hash_text)
    train_df["job_hash"] = train_df["job_description_text"].apply(hash_text)
    train_df["pair_hash"] = train_df["resume_hash"] + "_" + train_df["job_hash"]

    pair_groups = train_df.groupby("pair_hash")
    conflicting_pairs = []
    
    skill_engine = SkillEngine()

    for p_hash, group in pair_groups:
        labels = group["label"].unique().tolist()
        if len(labels) > 1:
            sample = group.iloc[0]
            r_text = sample["resume_text"]
            j_text = sample["job_description_text"]
            r_skills = skill_engine.extract_skills(r_text)
            j_skills = skill_engine.extract_skills(j_text)
            overlap = sorted(list(set(r_skills) & set(j_skills)))
            
            conflicting_pairs.append({
                "pair_hash": p_hash,
                "count": len(group),
                "labels": labels,
                "row_indices": group.index.tolist(),
                "resume_char_len": len(r_text),
                "job_char_len": len(j_text),
                "resume_skills_count": len(r_skills),
                "job_skills_count": len(j_skills),
                "skill_overlap_count": len(overlap),
                "skill_overlap": overlap[:10],
                "resume_snippet": r_text[:250].replace("\n", " "),
                "job_snippet": j_text[:250].replace("\n", " ")
            })

    print(f"Found {len(conflicting_pairs)} conflicting text pairs in train (affecting {sum(p['count'] for p in conflicting_pairs)} rows).")

    # Save detailed conflicting pairs
    with open(os.path.join(OUTPUT_DIR, "conflicting_label_pairs_detailed.json"), "w", encoding="utf-8") as f:
        json.dump(conflicting_pairs, f, indent=2)

    # 4. Near-Duplicate Analysis among Resumes and Jobs
    print("\nAuditing Near-Duplicates (TF-IDF Cosine Similarity > 0.95)...")
    
    # Unique resumes across all 8000 pairs
    all_resumes = pd.concat([train_df["resume_text"], test_df["resume_text"]]).unique()
    all_jobs = pd.concat([train_df["job_description_text"], test_df["job_description_text"]]).unique()
    print(f"Unique Resumes: {len(all_resumes)} | Unique Jobs: {len(all_jobs)}")

    # Vectorize Resumes
    tfidf_res = TfidfVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2))
    res_matrix = tfidf_res.fit_transform(all_resumes)
    
    # Efficient pairwise cosine similarity for near-duplicates
    # Calculate batch-wise to keep memory small
    near_dup_resumes = []
    chunk_size = 200
    for i in range(0, len(all_resumes), chunk_size):
        sim_chunk = cosine_similarity(res_matrix[i:i+chunk_size], res_matrix)
        for r_idx in range(sim_chunk.shape[0]):
            global_r_idx = i + r_idx
            # Check upper triangle only
            high_sim_cols = np.where(sim_chunk[r_idx, global_r_idx+1:] > 0.95)[0] + (global_r_idx + 1)
            for c_idx in high_sim_cols:
                near_dup_resumes.append({
                    "resume_idx_1": int(global_r_idx),
                    "resume_idx_2": int(c_idx),
                    "similarity": float(round(sim_chunk[r_idx, c_idx], 4)),
                    "snippet_1": all_resumes[global_r_idx][:150].replace("\n", " "),
                    "snippet_2": all_resumes[c_idx][:150].replace("\n", " ")
                })

    print(f"Near-Duplicate Resumes (Cosine Sim > 0.95): {len(near_dup_resumes)} pairs.")

    # Vectorize Jobs
    tfidf_jobs = TfidfVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2))
    job_matrix = tfidf_jobs.fit_transform(all_jobs)
    
    near_dup_jobs = []
    for i in range(0, len(all_jobs), chunk_size):
        sim_chunk = cosine_similarity(job_matrix[i:i+chunk_size], job_matrix)
        for r_idx in range(sim_chunk.shape[0]):
            global_j_idx = i + r_idx
            high_sim_cols = np.where(sim_chunk[r_idx, global_j_idx+1:] > 0.95)[0] + (global_j_idx + 1)
            for c_idx in high_sim_cols:
                near_dup_jobs.append({
                    "job_idx_1": int(global_j_idx),
                    "job_idx_2": int(c_idx),
                    "similarity": float(round(sim_chunk[r_idx, c_idx], 4)),
                    "snippet_1": all_jobs[global_j_idx][:150].replace("\n", " "),
                    "snippet_2": all_jobs[c_idx][:150].replace("\n", " ")
                })

    print(f"Near-Duplicate Jobs (Cosine Sim > 0.95): {len(near_dup_jobs)} pairs.")

    # 5. Ambiguous Compatibility Boundaries Analysis
    print("\nAuditing Class Boundary Ambiguity & Skill Overlaps...")
    # Sample 1,000 pairs from train to inspect skill coverage & text similarity per class
    sample_df = train_df.sample(n=min(1200, len(train_df)), random_state=42).copy()
    
    boundary_stats = {"No Fit": [], "Potential Fit": [], "Good Fit": []}
    
    for _, row in sample_df.iterrows():
        r_txt = row["resume_text"]
        j_txt = row["job_description_text"]
        lbl = row["label"]
        
        r_sk = set(skill_engine.extract_skills(r_txt))
        j_sk = set(skill_engine.extract_skills(j_txt))
        
        j_count = len(j_sk)
        overlap = len(r_sk & j_sk)
        jaccard = (overlap / len(r_sk | j_sk)) if (r_sk or j_sk) else 0.0
        recall = (overlap / j_count) if j_count > 0 else 0.0
        
        boundary_stats[lbl].append({
            "job_skills": j_count,
            "resume_skills": len(r_sk),
            "overlap_skills": overlap,
            "skill_recall": recall,
            "skill_jaccard": jaccard
        })
        
    class_boundary_summary = {}
    for lbl in ["No Fit", "Potential Fit", "Good Fit"]:
        recs = [item["skill_recall"] for item in boundary_stats[lbl]]
        jacs = [item["skill_jaccard"] for item in boundary_stats[lbl]]
        ovs = [item["overlap_skills"] for item in boundary_stats[lbl]]
        class_boundary_summary[lbl] = {
            "n_samples": len(recs),
            "skill_recall_mean": float(round(np.mean(recs), 4)),
            "skill_recall_median": float(round(np.median(recs), 4)),
            "skill_recall_p25": float(round(np.percentile(recs, 25), 4)),
            "skill_recall_p75": float(round(np.percentile(recs, 75), 4)),
            "skill_jaccard_mean": float(round(np.mean(jacs), 4)),
            "skill_overlap_count_mean": float(round(np.mean(ovs), 2)),
            "skill_overlap_count_median": float(round(np.median(ovs), 2)),
        }
        print(f"  Class '{lbl:13s}': Recall Mean={class_boundary_summary[lbl]['skill_recall_mean']:.3f} (Med {class_boundary_summary[lbl]['skill_recall_median']:.3f}), Overlap Mean={class_boundary_summary[lbl]['skill_overlap_count_mean']:.1f}")

    # 6. Entity Overlap & Graph Topology Across Splits
    print("\nAuditing Graph Topology Across Splits...")
    train_sub_job, val_sub_job, held_out_test = get_unseen_jobs_split(val_size=0.15, random_state=42)
    train_sub_res, val_sub_res = get_unseen_resumes_split(test_size=0.15, random_state=42)
    
    dual_train_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_train.csv"))
    dual_val_df = pd.read_csv(os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_val.csv"))

    def analyze_graph(tr, te, name):
        tr_r = set(tr["resume_text"].unique())
        tr_j = set(tr["job_description_text"].unique())
        te_r = set(te["resume_text"].unique())
        te_j = set(te["job_description_text"].unique())
        
        r_overlap = len(tr_r & te_r)
        j_overlap = len(tr_j & te_j)
        
        return {
            "split_name": name,
            "train_pairs": len(tr),
            "test_pairs": len(te),
            "train_unique_resumes": len(tr_r),
            "test_unique_resumes": len(te_r),
            "train_unique_jobs": len(tr_j),
            "test_unique_jobs": len(te_j),
            "overlapping_resumes": r_overlap,
            "overlapping_resumes_pct": float(round(r_overlap / len(te_r) * 100, 2)) if te_r else 0,
            "overlapping_jobs": j_overlap,
            "overlapping_jobs_pct": float(round(j_overlap / len(te_j) * 100, 2)) if te_j else 0
        }

    graph_splits = [
        analyze_graph(train_sub_job, val_sub_job, "Protocol 2: Job-Disjoint Validation"),
        analyze_graph(train_sub_res, val_sub_res, "Protocol 3: Resume-Disjoint Validation"),
        analyze_graph(dual_train_df, dual_val_df, "Protocol 4: Dual-Unseen Validation"),
        analyze_graph(train_df, test_df, "Official Held-Out Test")
    ]

    for g in graph_splits:
        print(f"  {g['split_name']:35s} | Test Resumes Seen: {g['overlapping_resumes_pct']:5.1f}% | Test Jobs Seen: {g['overlapping_jobs_pct']:5.1f}%")

    # 7. Compile Final Audit Report
    audit_report = {
        "raw_counts": {
            "train": len(raw_train_df),
            "test": len(raw_test_df),
            "total": len(raw_train_df) + len(raw_test_df)
        },
        "exact_duplicates": {
            "train_duplicates": int(train_exact_dup_count),
            "test_duplicates": int(test_exact_dup_count)
        },
        "contradictory_label_pairs": {
            "count_conflicting_pairs": len(conflicting_pairs),
            "count_conflicting_rows": sum(p["count"] for p in conflicting_pairs),
            "pairs": conflicting_pairs
        },
        "near_duplicates": {
            "near_dup_resumes_count": len(near_dup_resumes),
            "near_dup_jobs_count": len(near_dup_jobs),
            "sample_near_dup_resumes": near_dup_resumes[:5],
            "sample_near_dup_jobs": near_dup_jobs[:5]
        },
        "class_boundary_overlap": class_boundary_summary,
        "graph_splits": graph_splits
    }

    report_path = os.path.join(OUTPUT_DIR, "phase12_dataset_audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    print(f"\nAudit complete! Saved detailed report to {report_path}")

if __name__ == "__main__":
    run_phase12_audit()
