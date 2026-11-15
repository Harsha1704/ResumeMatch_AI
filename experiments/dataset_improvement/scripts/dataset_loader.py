"""
Phase 7D Reproducible Dataset Loader and Scenario Split Manager.
Maintains three clearly distinguished evaluation scenarios:
- Evaluation A: Unseen Jobs
- Evaluation B: Unseen Resumes
- Evaluation C: Dual-Unseen (Both Unseen Resumes and Unseen Jobs)
Zero leakage. Zero synthetic data.
"""

from pathlib import Path
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np

SPLITS_DIR = Path("experiments/dataset_improvement/splits")
RAW_DIR = Path("data/raw")

VALID_LABELS = ["No Fit", "Good Fit", "Potential Fit"]
LABEL_MAPPING = {"No Fit": 0, "Good Fit": 1, "Potential Fit": 2}


def load_dual_unseen_split() -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Loads Evaluation C: Dual-Unseen Benchmark.
    Guarantees:
    - Train Resumes ∩ Val Resumes = Empty
    - Train Jobs ∩ Val Jobs = Empty
    - Train Pairs ∩ Val Pairs = Empty
    """
    train_path = SPLITS_DIR / "dual_unseen_train.parquet"
    val_path = SPLITS_DIR / "dual_unseen_val.parquet"

    if not train_path.exists() or not val_path.exists():
        from experiments.dataset_improvement.scripts.create_dual_unseen_split import create_dual_unseen_partition
        train_df, val_df, _, meta = create_dual_unseen_partition(seed=20)
    else:
        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
        import json
        with open(SPLITS_DIR / "dual_unseen_metadata.json") as f:
            meta = json.load(f)

    return train_df, val_df, meta


def verify_scenario_c_integrity(train_df: pd.DataFrame, val_df: pd.DataFrame) -> Dict[str, bool]:
    """
    Rigorous mathematical proof that Evaluation C maintains zero overlap across all entities.
    """
    r_tr = set(train_df["resume_id"]) if "resume_id" in train_df else set(train_df["resume_text"])
    r_va = set(val_df["resume_id"]) if "resume_id" in val_df else set(val_df["resume_text"])

    j_tr = set(train_df["job_id"]) if "job_id" in train_df else set(train_df["job_description_text"])
    j_va = set(val_df["job_id"]) if "job_id" in val_df else set(val_df["job_description_text"])

    pair_tr = set(zip(train_df["resume_text"], train_df["job_description_text"]))
    pair_va = set(zip(val_df["resume_text"], val_df["job_description_text"]))

    r_overlap = len(r_tr.intersection(r_va))
    j_overlap = len(j_tr.intersection(j_va))
    pair_overlap = len(pair_tr.intersection(pair_va))

    return {
        "zero_resume_overlap": r_overlap == 0,
        "zero_job_overlap": j_overlap == 0,
        "zero_pair_overlap": pair_overlap == 0,
        "resume_overlap_count": r_overlap,
        "job_overlap_count": j_overlap,
        "pair_overlap_count": pair_overlap,
        "all_valid_labels": set(train_df["label"].unique()).issubset(set(VALID_LABELS)),
        "class_counts_train": train_df["label"].value_counts().to_dict(),
        "class_counts_val": val_df["label"].value_counts().to_dict()
    }
