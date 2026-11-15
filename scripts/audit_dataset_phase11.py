"""
scripts/audit_dataset_phase11.py
Comprehensive Dataset Quality Audit for Phase 11.
Audits the 8,000 resume-job pairs across:
- Class distribution
- Missing values
- Exact duplicates (identical resume+job, same and contradictory labels)
- Group structure (unique resumes, unique jobs, pairings per entity)
- Length distributions and extreme outliers/truncations
- Text contamination / formatting issues
- Data leakage between train and test
"""

import os
import sys
import json
import hashlib
import re
from collections import Counter
import pandas as pd
import numpy as np

OUTPUT_DIR = "results/phase11_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def hash_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text).strip().lower())
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()

def audit():
    print("Loading raw train and test datasets...")
    train_path = "data/raw/resume_job_fit_train.csv"
    test_path = "data/raw/resume_job_fit_test.csv"
    
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    
    train["split"] = "train"
    test["split"] = "test"
    full_df = pd.concat([train, test], ignore_index=True)
    
    total_samples = len(full_df)
    train_count = len(train)
    test_count = len(test)
    
    print(f"Total samples: {total_samples} (Train: {train_count}, Test: {test_count})")
    
    # 1. Missing Values
    missing_analysis = {}
    for col in ["resume_text", "job_description_text", "label"]:
        train_null = int(train[col].isnull().sum())
        test_null = int(test[col].isnull().sum())
        train_empty = int((train[col].astype(str).str.strip() == "").sum())
        test_empty = int((test[col].astype(str).str.strip() == "").sum())
        missing_analysis[col] = {
            "train_null": train_null,
            "test_null": test_null,
            "train_empty": train_empty,
            "test_empty": test_empty,
        }
        
    # 2. Class Distributions
    train_classes = train["label"].value_counts().to_dict()
    test_classes = test["label"].value_counts().to_dict()
    full_classes = full_df["label"].value_counts().to_dict()
    
    train_pcts = {k: round(v / train_count * 100, 2) for k, v in train_classes.items()}
    test_pcts = {k: round(v / test_count * 100, 2) for k, v in test_classes.items()}
    
    # 3. Duplicate Analysis (Exact Text & Normalized Text)
    full_df["resume_hash"] = full_df["resume_text"].apply(hash_text)
    full_df["job_hash"] = full_df["job_description_text"].apply(hash_text)
    full_df["pair_hash"] = full_df["resume_hash"] + "_" + full_df["job_hash"]
    
    train["pair_hash"] = full_df.iloc[:train_count]["pair_hash"]
    test["pair_hash"] = full_df.iloc[train_count:]["pair_hash"]
    
    unique_resumes = full_df["resume_hash"].nunique()
    unique_jobs = full_df["job_hash"].nunique()
    unique_pairs = full_df["pair_hash"].nunique()
    
    train_unique_resumes = full_df.iloc[:train_count]["resume_hash"].nunique()
    train_unique_jobs = full_df.iloc[:train_count]["job_hash"].nunique()
    
    test_unique_resumes = full_df.iloc[train_count:]["resume_hash"].nunique()
    test_unique_jobs = full_df.iloc[train_count:]["job_hash"].nunique()
    
    # Cross-split overlap (Data Leakage!)
    train_resumes = set(full_df.iloc[:train_count]["resume_hash"])
    test_resumes = set(full_df.iloc[train_count:]["resume_hash"])
    overlap_resumes = train_resumes & test_resumes
    
    train_jobs = set(full_df.iloc[:train_count]["job_hash"])
    test_jobs = set(full_df.iloc[train_count:]["job_hash"])
    overlap_jobs = train_jobs & test_jobs
    
    train_pairs = set(full_df.iloc[:train_count]["pair_hash"])
    test_pairs = set(full_df.iloc[train_count:]["pair_hash"])
    overlap_pairs = train_pairs & test_pairs
    
    # Contradictory labels (same resume + same job, different label)
    pair_labels = full_df.groupby("pair_hash")["label"].nunique()
    contradictory_pairs_count = int((pair_labels > 1).sum())
    contradictory_samples = full_df[full_df["pair_hash"].isin(pair_labels[pair_labels > 1].index)]
    
    # Exact duplicate rows (identical resume + job + label)
    exact_duplicate_rows = int(full_df.duplicated(subset=["resume_hash", "job_hash", "label"]).sum())
    
    # Resumes per job and jobs per resume distribution
    resumes_per_job = full_df.groupby("job_hash")["resume_hash"].count()
    jobs_per_resume = full_df.groupby("resume_hash")["job_hash"].count()
    
    # 4. Length Distributions
    full_df["resume_char_len"] = full_df["resume_text"].astype(str).str.len()
    full_df["resume_word_len"] = full_df["resume_text"].astype(str).apply(lambda x: len(x.split()))
    full_df["job_char_len"] = full_df["job_description_text"].astype(str).str.len()
    full_df["job_word_len"] = full_df["job_description_text"].astype(str).apply(lambda x: len(x.split()))
    
    lengths_stats = {
        "resume_words": {
            "min": int(full_df["resume_word_len"].min()),
            "mean": float(round(full_df["resume_word_len"].mean(), 2)),
            "median": float(round(full_df["resume_word_len"].median(), 2)),
            "p25": float(round(full_df["resume_word_len"].quantile(0.25), 2)),
            "p75": float(round(full_df["resume_word_len"].quantile(0.75), 2)),
            "p95": float(round(full_df["resume_word_len"].quantile(0.95), 2)),
            "max": int(full_df["resume_word_len"].max()),
        },
        "job_words": {
            "min": int(full_df["job_word_len"].min()),
            "mean": float(round(full_df["job_word_len"].mean(), 2)),
            "median": float(round(full_df["job_word_len"].median(), 2)),
            "p25": float(round(full_df["job_word_len"].quantile(0.25), 2)),
            "p75": float(round(full_df["job_word_len"].quantile(0.75), 2)),
            "p95": float(round(full_df["job_word_len"].quantile(0.95), 2)),
            "max": int(full_df["job_word_len"].max()),
        }
    }
    
    # Outliers: Short resumes (<50 words) and short jobs (<30 words)
    short_resumes = int((full_df["resume_word_len"] < 50).sum())
    short_jobs = int((full_df["job_word_len"] < 30).sum())
    
    audit_summary = {
        "dataset_size": {
            "total_pairs": total_samples,
            "train_pairs": train_count,
            "test_pairs": test_count,
            "unique_resumes": unique_resumes,
            "unique_jobs": unique_jobs,
            "unique_pairs": unique_pairs,
        },
        "missing_values": missing_analysis,
        "class_distributions": {
            "train_counts": train_classes,
            "train_percentages": train_pcts,
            "test_counts": test_classes,
            "test_percentages": test_pcts,
            "full_counts": full_classes,
        },
        "entity_statistics": {
            "train_unique_resumes": train_unique_resumes,
            "train_unique_jobs": train_unique_jobs,
            "test_unique_resumes": test_unique_resumes,
            "test_unique_jobs": test_unique_jobs,
            "cross_split_leakage": {
                "overlapping_resumes_count": len(overlap_resumes),
                "overlapping_resumes_pct_of_test": round(len(overlap_resumes) / max(1, test_unique_resumes) * 100, 2),
                "overlapping_jobs_count": len(overlap_jobs),
                "overlapping_jobs_pct_of_test": round(len(overlap_jobs) / max(1, test_unique_jobs) * 100, 2),
                "overlapping_exact_pairs_count": len(overlap_pairs),
            },
            "exact_duplicate_rows": exact_duplicate_rows,
            "contradictory_label_pairs": contradictory_pairs_count,
            "jobs_per_resume": {
                "mean": float(round(jobs_per_resume.mean(), 2)),
                "max": int(jobs_per_resume.max()),
                "min": int(jobs_per_resume.min()),
            },
            "resumes_per_job": {
                "mean": float(round(resumes_per_job.mean(), 2)),
                "max": int(resumes_per_job.max()),
                "min": int(resumes_per_job.min()),
            }
        },
        "lengths": lengths_stats,
        "anomalies": {
            "short_resumes_lt_50_words": short_resumes,
            "short_jobs_lt_30_words": short_jobs,
        }
    }
    
    print("\n--- AUDIT SUMMARY ---")
    print(f"Total Pairs: {total_samples}")
    print(f"Unique Resumes: {unique_resumes} | Unique Jobs: {unique_jobs}")
    print(f"Missing Values: {missing_analysis}")
    print(f"Exact Duplicate Rows: {exact_duplicate_rows}")
    print(f"Contradictory Label Pairs: {contradictory_pairs_count}")
    print(f"Cross-Split Leaked Resumes: {len(overlap_resumes)} ({len(overlap_resumes)/test_unique_resumes*100:.1f}% of test resumes!)")
    print(f"Cross-Split Leaked Jobs: {len(overlap_jobs)} ({len(overlap_jobs)/test_unique_jobs*100:.1f}% of test jobs!)")
    print(f"Cross-Split Exact Pairs Leaked: {len(overlap_pairs)}")
    print(f"Resume Word Length: min={lengths_stats['resume_words']['min']}, median={lengths_stats['resume_words']['median']}, max={lengths_stats['resume_words']['max']}")
    print(f"Job Word Length: min={lengths_stats['job_words']['min']}, median={lengths_stats['job_words']['median']}, max={lengths_stats['job_words']['max']}")
    
    with open(os.path.join(OUTPUT_DIR, "dataset_audit_report.json"), "w") as f:
        json.dump(audit_summary, f, indent=2)
        
    return audit_summary, full_df

if __name__ == "__main__":
    audit()
