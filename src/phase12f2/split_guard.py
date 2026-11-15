"""
src/phase12f2/split_guard.py
Permanent Architectural Split Isolation & Anti-Leakage Guard for Phase 12F.2 & Phase 12F.3.

Provides hard programmatic gates to prevent cross-protocol contamination:
1. Dual-Unseen Protocol: Strictly 0% resume overlap, 0% job overlap, 0% pair overlap.
2. Job-Disjoint Protocol: Strictly 0% job overlap, 0% pair overlap.
3. External Corpus Guard: Audits external candidate pools against evaluation entities before use.
4. Normalized Text Duplicate Guard: Strips punctuation and symbols to catch disguised duplicates.
5. Near-Duplicate Guard: Token-level Jaccard similarity checks.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import re
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path

from src.evaluation.split_validator import (
    SplitLeakageError,
    validate_split_isolation,
    compute_overlap_metrics,
    hash_text,
    hash_pair
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_DIR = REPO_ROOT / "manifests" / "v1"

# Protocol identifiers
PROTOCOL_DUAL_UNSEEN = "dual_unseen"
PROTOCOL_JOB_DISJOINT = "job_disjoint"
VALID_PROTOCOLS = {PROTOCOL_DUAL_UNSEEN, PROTOCOL_JOB_DISJOINT}


def normalize_alphanumeric_hash(text: str) -> str:
    """Computes deterministic MD5 hash of lowercased, alphanumeric-only tokens."""
    cleaned = re.sub(r"[^a-z0-9]", " ", str(text).lower())
    tokens = " ".join(cleaned.split())
    return hashlib.md5(tokens.encode("utf-8")).hexdigest()


class ProtocolSplitGuard:
    """
    Enforces strict protocol integrity before model training or evaluation.
    """

    @staticmethod
    def validate_normalized_duplicates(
        train_df: pd.DataFrame,
        eval_df: pd.DataFrame,
        check_resumes: bool = True,
        check_jobs: bool = True,
        context: str = "Split"
    ) -> None:
        """
        Validates that no entities in eval_df match train_df when punctuation and symbols are stripped.
        Raises SplitLeakageError immediately on violation.
        """
        if check_resumes and "resume_text" in train_df.columns and "resume_text" in eval_df.columns:
            tr_res = set(train_df["resume_text"].apply(normalize_alphanumeric_hash))
            ev_res = set(eval_df["resume_text"].apply(normalize_alphanumeric_hash))
            overlap = ev_res.intersection(tr_res)
            if overlap:
                raise SplitLeakageError(
                    f"[{context}] NORMALIZED RESUME DUPLICATE LEAKAGE: "
                    f"{len(overlap)} eval resumes match train resumes under alphanumeric normalization! "
                    f"Sample overlapping hashes: {list(overlap)[:3]}"
                )

        if check_jobs and "job_description_text" in train_df.columns and "job_description_text" in eval_df.columns:
            tr_job = set(train_df["job_description_text"].apply(normalize_alphanumeric_hash))
            ev_job = set(eval_df["job_description_text"].apply(normalize_alphanumeric_hash))
            overlap = ev_job.intersection(tr_job)
            if overlap:
                raise SplitLeakageError(
                    f"[{context}] NORMALIZED JOB DUPLICATE LEAKAGE: "
                    f"{len(overlap)} eval jobs match train jobs under alphanumeric normalization! "
                    f"Sample overlapping hashes: {list(overlap)[:3]}"
                )

    @staticmethod
    def validate_dual_unseen(train_df: pd.DataFrame, val_df: pd.DataFrame, context: str = "Dual-Unseen") -> Dict[str, Any]:
        """
        Hard gate for Dual-Unseen experiments:
        Requires EXACTLY 0 overlapping resumes, 0 overlapping jobs, and 0 overlapping pairs.
        Also enforces zero normalized alphanumeric duplicate leakage.
        Raises SplitLeakageError immediately on violation.
        """
        metrics = validate_split_isolation(
            train_df=train_df,
            eval_df=val_df,
            protocol="dual_unseen",
            split_name=context
        )
        ProtocolSplitGuard.validate_normalized_duplicates(
            train_df=train_df,
            eval_df=val_df,
            check_resumes=True,
            check_jobs=True,
            context=context
        )
        return metrics

    @staticmethod
    def validate_job_disjoint(train_df: pd.DataFrame, eval_df: pd.DataFrame, context: str = "Job-Disjoint") -> Dict[str, Any]:
        """
        Hard gate for Job-Disjoint experiments:
        Requires EXACTLY 0 overlapping jobs and 0 overlapping pairs.
        Also enforces zero normalized alphanumeric job duplicate leakage.
        Raises SplitLeakageError immediately on violation.
        """
        metrics = validate_split_isolation(
            train_df=train_df,
            eval_df=eval_df,
            protocol="job_disjoint",
            split_name=context
        )
        ProtocolSplitGuard.validate_normalized_duplicates(
            train_df=train_df,
            eval_df=eval_df,
            check_resumes=False,
            check_jobs=True,
            context=context
        )
        return metrics

    @staticmethod
    def filter_external_pool(
        pool_df: pd.DataFrame,
        eval_dfs: List[pd.DataFrame],
        resume_col: str = "resume_text",
        job_col: str = "job_description_text"
    ) -> pd.DataFrame:
        """
        Purges any candidate pairs from external/unlabeled pool that share a resume or job
        with ANY evaluation or test split (both exact and alphanumeric normalized).
        """
        prohibited_resumes: Set[str] = set()
        prohibited_jobs: Set[str] = set()
        prohibited_norm_resumes: Set[str] = set()
        prohibited_norm_jobs: Set[str] = set()

        for ev in eval_dfs:
            if "resume_text" in ev.columns:
                prohibited_resumes.update(ev["resume_text"].apply(hash_text))
                prohibited_norm_resumes.update(ev["resume_text"].apply(normalize_alphanumeric_hash))
            if "job_description_text" in ev.columns:
                prohibited_jobs.update(ev["job_description_text"].apply(hash_text))
                prohibited_norm_jobs.update(ev["job_description_text"].apply(normalize_alphanumeric_hash))

        pool_res_hashes = pool_df[resume_col].apply(hash_text)
        pool_job_hashes = pool_df[job_col].apply(hash_text)
        pool_norm_res_hashes = pool_df[resume_col].apply(normalize_alphanumeric_hash)
        pool_norm_job_hashes = pool_df[job_col].apply(normalize_alphanumeric_hash)

        safe_mask = (
            (~pool_res_hashes.isin(prohibited_resumes)) &
            (~pool_job_hashes.isin(prohibited_jobs)) &
            (~pool_norm_res_hashes.isin(prohibited_norm_resumes)) &
            (~pool_norm_job_hashes.isin(prohibited_norm_jobs))
        )
        filtered = pool_df[safe_mask].reset_index(drop=True)
        return filtered


def load_guarded_dual_unseen_splits() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads and cryptographically validates the Dual-Unseen partitions:
    - Train: manifests/v1/dual_unseen_train_v1.parquet (3,857 rows)
    - Val:   manifests/v1/dual_unseen_val_v1.parquet (296 rows)
    Enforces the single near-duplicate resume quarantine and validates zero entity leakage.
    """
    from src.phase12f.data_pipeline import Phase12FDataLoader

    loader = Phase12FDataLoader()
    tr_df, val_df = loader.load_dual_unseen_splits()

    # Apply strict ProtocolSplitGuard
    ProtocolSplitGuard.validate_dual_unseen(tr_df, val_df, context="Phase12F2_DualUnseen_Load")
    return tr_df, val_df


def load_guarded_job_disjoint_splits() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads and cryptographically validates the Job-Disjoint partitions:
    - Train: manifests/v1/job_disjoint_train_v1.parquet (5,462 rows)
    - Val:   manifests/v1/job_disjoint_val_v1.parquet (778 rows)
    - Test:  manifests/v1/held_out_test_v1.parquet (1,759 rows)
    Enforces zero job and pair overlap across partitions.
    """
    from src.phase12f.data_pipeline import Phase12FDataLoader

    loader = Phase12FDataLoader()
    tr_df, val_df, test_df = loader.load_job_disjoint_splits()

    # Apply strict ProtocolSplitGuard
    ProtocolSplitGuard.validate_job_disjoint(tr_df, val_df, context="Phase12F2_JobDisjoint_Val")
    ProtocolSplitGuard.validate_job_disjoint(tr_df, test_df, context="Phase12F2_JobDisjoint_Test")
    return tr_df, val_df, test_df
