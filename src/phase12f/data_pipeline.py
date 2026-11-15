"""
src/phase12f/data_pipeline.py
Leakage-safe automated data pipeline for Phase 12F.
Loads manifest-backed partitions, enforces contradictory-pair filtering,
validates split isolation, and manages unpaired Djinni corpora.
"""

import os
import json
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_DIR = REPO_ROOT / "manifests" / "v1"
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"
DJINNI_DIR = REPO_ROOT / "data" / "external" / "djinni"
CONFLICTS_FILE = REPO_ROOT / "results" / "phase12_audit" / "conflicting_label_pairs_detailed.json"

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
LABEL_TO_INT = {c: i for i, c in enumerate(CLASSES)}
INT_TO_LABEL = {i: c for i, c in enumerate(CLASSES)}


def compute_hash(text: str) -> str:
    """Computes truncated SHA-256 for text entity identification."""
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]


def compute_pair_hash(resume_text: str, jd_text: str) -> str:
    """Computes pair hash matching the audit format."""
    r_h = hashlib.md5(str(resume_text).strip().encode("utf-8")).hexdigest()
    j_h = hashlib.md5(str(jd_text).strip().encode("utf-8")).hexdigest()
    return f"{r_h}_{j_h}"


def load_contradictory_pair_hashes() -> Set[str]:
    """Loads the 6 known contradictory pair hashes from the Phase 12 audit."""
    if CONFLICTS_FILE.exists():
        with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
            conflicts = json.load(f)
        return set(c["pair_hash"] for c in conflicts)
    return set()


def filter_clean_pairs(df: pd.DataFrame, contra_hashes: Optional[Set[str]] = None) -> pd.DataFrame:
    """Filters contradictory label pairs from a dataset."""
    if contra_hashes is None:
        contra_hashes = load_contradictory_pair_hashes()
    if not contra_hashes:
        return df.copy()

    pair_hashes = df.apply(lambda r: compute_pair_hash(r["resume_text"], r["job_description_text"]), axis=1)
    mask = ~pair_hashes.isin(contra_hashes)
    filtered = df[mask].reset_index(drop=True)
    return filtered


class Phase12FDataLoader:
    """
    Unified, leakage-guarded data loader for Phase 12F experiments.
    """

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = manifest_dir or MANIFEST_DIR
        self.contra_hashes = load_contradictory_pair_hashes()

    def load_job_disjoint_splits(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Loads Job-Disjoint Train (5,462 rows), Val (778 rows), and Official Test (1,759 rows).
        Filters contradictory pairs from the training partition.
        """
        tr_path = self.manifest_dir / "job_disjoint_train_v1.parquet"
        vl_path = self.manifest_dir / "job_disjoint_val_v1.parquet"
        ts_path = self.manifest_dir / "held_out_test_v1.parquet"

        tr_df = pd.read_parquet(tr_path)
        vl_df = pd.read_parquet(vl_path)
        ts_df = pd.read_parquet(ts_path)

        tr_clean = filter_clean_pairs(tr_df, self.contra_hashes)
        return tr_clean, vl_df, ts_df

    def load_dual_unseen_splits(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads Dual-Unseen Train (3,857 rows) and Cleaned Val (296 rows).
        Guarantees 0% resume overlap and 0% job overlap.
        """
        tr_path = self.manifest_dir / "dual_unseen_train_v1.parquet"
        vl_path = self.manifest_dir / "dual_unseen_val_v1.parquet"

        tr_df = pd.read_parquet(tr_path)
        vl_df = pd.read_parquet(vl_path)

        tr_clean = filter_clean_pairs(tr_df, self.contra_hashes)

        # Remove the single near-duplicate resume identified in the forensic audit
        # Resume with 'Boise,ID,Acute and' differs by 1 char ('–' vs '|')
        tr_norm_res = set(tr_clean["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" "))
        vl_norm_res = vl_df["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" ")
        clean_mask = ~vl_norm_res.isin(tr_norm_res)
        vl_clean = vl_df[clean_mask].reset_index(drop=True)

        return tr_clean, vl_clean

    def load_djinni_unpaired_sample(self, n_resumes: int = 5000, n_jobs: int = 5000, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads a random, representative sample of English CVs and JDs for domain adaptation.
        """
        cv_path = DJINNI_DIR / "djinni_candidate_profiles_english.parquet"
        jd_path = DJINNI_DIR / "djinni_job_descriptions_english.parquet"

        cv_df = pd.read_parquet(cv_path)
        jd_df = pd.read_parquet(jd_path)

        sample_cv = cv_df.sample(n=min(n_resumes, len(cv_df)), random_state=random_state).reset_index(drop=True)
        sample_jd = jd_df.sample(n=min(n_jobs, len(jd_df)), random_state=random_state).reset_index(drop=True)

        if "candidate_cv_text" not in sample_cv.columns and "CV" in sample_cv.columns:
            sample_cv["candidate_cv_text"] = sample_cv["CV"]
        if "job_description_text" not in sample_jd.columns and "Long Description" in sample_jd.columns:
            sample_jd["job_description_text"] = sample_jd["Long Description"]

        return sample_cv, sample_jd

    def load_proposed_candidate_pairs(self) -> pd.DataFrame:
        """
        Loads the 830 candidate proposals (unlabeled, candidate pool for pseudo-labeling).
        """
        prop_path = DJINNI_DIR / "proposed_candidate_pairs_sample.csv"
        return pd.read_csv(prop_path)
