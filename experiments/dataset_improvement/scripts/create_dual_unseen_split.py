"""
Phase 7D: Dual-Unseen Bipartite Partitioning Pipeline.
Constructs Evaluation C (Dual-Unseen Benchmark) strictly from genuine labeled pairs.
Guarantees:
- Train Resume IDs ∩ Val Resume IDs = Empty
- Train Job IDs ∩ Val Job IDs = Empty
- Train Pairs ∩ Val Pairs = Empty
- Official held-out test partition preserved strictly as Evaluation A (Unseen Jobs benchmark)
- Zero synthetic pairs. Zero label modifications.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd

SPLITS_DIR = Path("experiments/dataset_improvement/splits")
AUDITS_DIR = Path("experiments/dataset_improvement/audits")
SPLITS_DIR.mkdir(parents=True, exist_ok=True)
AUDITS_DIR.mkdir(parents=True, exist_ok=True)


def hash_text(text: str) -> str:
    """Deterministic 16-character SHA-256 hash for document identification."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def create_dual_unseen_partition(
    raw_train_path: str = "data/raw/resume_job_fit_train.csv",
    seed: int = 20,
    val_job_ratio: float = 0.20,
    val_resume_ratio: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Performs bipartite node holdout splitting on genuine resume-job pairs.
    """
    df = pd.read_csv(raw_train_path)

    # Document identification
    df["resume_id"] = "R_" + df["resume_text"].apply(hash_text)
    df["job_id"] = "J_" + df["job_description_text"].apply(hash_text)
    df["pair_id"] = df["resume_id"] + "__" + df["job_id"]

    all_resumes = np.sort(df["resume_id"].unique())
    all_jobs = np.sort(df["job_id"].unique())

    # Reproducible bipartite holdout
    rng = np.random.RandomState(seed)
    n_val_jobs = int(round(val_job_ratio * len(all_jobs)))
    n_val_resumes = int(round(val_resume_ratio * len(all_resumes)))

    val_jobs = set(rng.choice(all_jobs, size=n_val_jobs, replace=False))
    val_resumes = set(rng.choice(all_resumes, size=n_val_resumes, replace=False))

    train_jobs = set(all_jobs) - val_jobs
    train_resumes = set(all_resumes) - val_resumes

    # Partition pairs
    mask_val = df["resume_id"].isin(val_resumes) & df["job_id"].isin(val_jobs)
    mask_train = df["resume_id"].isin(train_resumes) & df["job_id"].isin(train_jobs)
    mask_cross = (~mask_val) & (~mask_train)

    val_df = df[mask_val].copy().reset_index(drop=True)
    train_df = df[mask_train].copy().reset_index(drop=True)
    cross_df = df[mask_cross].copy().reset_index(drop=True)

    # Invariant Verification
    r_overlap = set(train_df["resume_id"]).intersection(set(val_df["resume_id"]))
    j_overlap = set(train_df["job_id"]).intersection(set(val_df["job_id"]))
    pair_overlap = set(train_df["pair_id"]).intersection(set(val_df["pair_id"]))

    assert len(r_overlap) == 0, f"Violation: Resume overlap detected: {len(r_overlap)}"
    assert len(j_overlap) == 0, f"Violation: Job overlap detected: {len(j_overlap)}"
    assert len(pair_overlap) == 0, f"Violation: Pair overlap detected: {len(pair_overlap)}"

    metadata = {
        "split_name": "Evaluation C: Dual-Unseen Benchmark",
        "random_seed": seed,
        "total_source_pairs": len(df),
        "train_pairs": len(train_df),
        "val_pairs": len(val_df),
        "cross_boundary_excluded_pairs": len(cross_df),
        "exclusion_percentage": round(len(cross_df) / len(df) * 100, 2),
        "unique_resumes_total": len(all_resumes),
        "unique_jobs_total": len(all_jobs),
        "train_unique_resumes": train_df["resume_id"].nunique(),
        "train_unique_jobs": train_df["job_id"].nunique(),
        "val_unique_resumes": val_df["resume_id"].nunique(),
        "val_unique_jobs": val_df["job_id"].nunique(),
        "resume_overlap_count": len(r_overlap),
        "job_overlap_count": len(j_overlap),
        "pair_overlap_count": len(pair_overlap),
        "train_label_distribution": train_df["label"].value_counts().to_dict(),
        "val_label_distribution": val_df["label"].value_counts().to_dict(),
        "class_diversity_verified": all(val_df["label"].value_counts() >= 50)
    }

    # Save splits
    train_df.to_parquet(SPLITS_DIR / "dual_unseen_train.parquet", index=False)
    val_df.to_parquet(SPLITS_DIR / "dual_unseen_val.parquet", index=False)
    cross_df.to_parquet(SPLITS_DIR / "cross_boundary_excluded.parquet", index=False)
    train_df.to_csv(SPLITS_DIR / "dual_unseen_train.csv", index=False)
    val_df.to_csv(SPLITS_DIR / "dual_unseen_val.csv", index=False)

    with open(SPLITS_DIR / "dual_unseen_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return train_df, val_df, cross_df, metadata


if __name__ == "__main__":
    t_df, v_df, c_df, meta = create_dual_unseen_partition()
    print("Dual-Unseen Partitioning Successful!")
    print(f"Train Pairs: {len(t_df)} | Val Pairs: {len(v_df)} | Discarded Cross-boundary: {len(c_df)} ({meta['exclusion_percentage']}%)")
    print(f"Val Distribution: {meta['val_label_distribution']}")
    print(f"Resume Overlap: {meta['resume_overlap_count']} | Job Overlap: {meta['job_overlap_count']}")
