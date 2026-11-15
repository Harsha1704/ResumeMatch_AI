"""
tests/test_phase12f2_split_isolation.py
Unit tests verifying the Phase 12F.2 & 12F.3 Split Isolation & Anti-Leakage Guard.
Includes strict positive and negative tests.
"""

import pytest
import pandas as pd
import numpy as np

from src.phase12f2.split_guard import (
    ProtocolSplitGuard,
    load_guarded_dual_unseen_splits,
    load_guarded_job_disjoint_splits,
    SplitLeakageError
)


def test_dual_unseen_guard_passes_clean_splits():
    """Verify that legitimate dual-unseen splits pass without error."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    assert len(tr_df) > 0
    assert len(val_df) > 0
    res = ProtocolSplitGuard.validate_dual_unseen(tr_df, val_df)
    assert res["status"] == "VALID"
    assert res["metrics"]["resume_overlap_count"] == 0
    assert res["metrics"]["job_overlap_count"] == 0
    assert res["metrics"]["pair_overlap_count"] == 0


def test_dual_unseen_guard_catches_resume_leakage():
    """Verify that a single overlapping resume triggers SplitLeakageError."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    contaminated_val = val_df.copy()
    contaminated_val.loc[0, "resume_text"] = tr_df.loc[0, "resume_text"]

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_dual_unseen(tr_df, contaminated_val)
    assert "DUAL ENTITY LEAKAGE" in str(exc_info.value) or "leakage" in str(exc_info.value).lower()


def test_dual_unseen_guard_catches_job_leakage():
    """Verify that a single overlapping job triggers SplitLeakageError."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    contaminated_val = val_df.copy()
    contaminated_val.loc[0, "job_description_text"] = tr_df.loc[0, "job_description_text"]

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_dual_unseen(tr_df, contaminated_val)
    assert "DUAL ENTITY LEAKAGE" in str(exc_info.value) or "leakage" in str(exc_info.value).lower()


def test_dual_unseen_guard_catches_pair_leakage():
    """Verify that an exact pair overlap triggers SplitLeakageError."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    contaminated_val = val_df.copy()
    contaminated_val.loc[0, "resume_text"] = tr_df.loc[0, "resume_text"]
    contaminated_val.loc[0, "job_description_text"] = tr_df.loc[0, "job_description_text"]

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_dual_unseen(tr_df, contaminated_val)
    assert "PAIR LEAKAGE" in str(exc_info.value) or "leakage" in str(exc_info.value).lower()


def test_dual_unseen_guard_catches_normalized_resume_duplicate():
    """Verify that a resume differing ONLY by punctuation/symbols triggers SplitLeakageError."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    contaminated_val = val_df.copy()
    # Modify punctuation only: replace spaces with hyphens/pipes
    orig_text = tr_df.loc[0, "resume_text"]
    disguised_text = orig_text.replace(" ", " | ")
    contaminated_val.loc[0, "resume_text"] = disguised_text

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_dual_unseen(tr_df, contaminated_val)
    assert "NORMALIZED RESUME DUPLICATE LEAKAGE" in str(exc_info.value)


def test_dual_unseen_guard_catches_normalized_job_duplicate():
    """Verify that a job description differing ONLY by punctuation/symbols triggers SplitLeakageError."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    contaminated_val = val_df.copy()
    orig_job = tr_df.loc[0, "job_description_text"]
    disguised_job = orig_job.replace(" ", " -- ")
    contaminated_val.loc[0, "job_description_text"] = disguised_job

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_dual_unseen(tr_df, contaminated_val)
    assert "NORMALIZED JOB DUPLICATE LEAKAGE" in str(exc_info.value)


def test_job_disjoint_guard_passes_clean_splits():
    """Verify that job-disjoint train and validation pass without error."""
    tr_df, val_df, test_df = load_guarded_job_disjoint_splits()
    res_val = ProtocolSplitGuard.validate_job_disjoint(tr_df, val_df)
    assert res_val["status"] == "VALID"
    assert res_val["metrics"]["job_overlap_count"] == 0
    assert res_val["metrics"]["pair_overlap_count"] == 0

    res_test = ProtocolSplitGuard.validate_job_disjoint(tr_df, test_df)
    assert res_test["status"] == "VALID"
    assert res_test["metrics"]["job_overlap_count"] == 0
    assert res_test["metrics"]["pair_overlap_count"] == 0


def test_job_disjoint_guard_catches_normalized_job_leakage():
    """Verify that a job description in eval disguised with punctuation triggers SplitLeakageError."""
    tr_df, val_df, _ = load_guarded_job_disjoint_splits()
    contaminated_val = val_df.copy()
    orig_job = tr_df.loc[0, "job_description_text"]
    disguised_job = orig_job.replace(".", " ... ")
    contaminated_val.loc[0, "job_description_text"] = disguised_job

    with pytest.raises(SplitLeakageError) as exc_info:
        ProtocolSplitGuard.validate_job_disjoint(tr_df, contaminated_val)
    assert "NORMALIZED JOB DUPLICATE LEAKAGE" in str(exc_info.value)


def test_filter_external_pool():
    """Verify that external pool filtering purges overlapping entities."""
    tr_df, val_df = load_guarded_dual_unseen_splits()
    external_pool = pd.DataFrame({
        "resume_text": [val_df.loc[0, "resume_text"], "Completely unique novel candidate text 12345"],
        "job_description_text": ["Completely unique novel jd text 12345", "Completely unique novel jd text 67890"]
    })
    filtered = ProtocolSplitGuard.filter_external_pool(external_pool, [val_df])
    assert len(filtered) == 1
    assert filtered.iloc[0]["resume_text"] == "Completely unique novel candidate text 12345"
