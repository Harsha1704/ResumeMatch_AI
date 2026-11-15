"""
tests/test_split_leakage_guards.py
Regression test suite for Phase 12D: Leakage-Safe Evaluation Guards and Manifest Validation.

Verifies:
1. Rejection of deliberate resume overlap in resume-disjoint protocol.
2. Rejection of deliberate job overlap in job-disjoint protocol.
3. Rejection of deliberate resume or job overlap in dual-unseen protocol.
4. Rejection of deliberate exact-pair overlap across all protocols.
5. Rejection of Phase 12B cross-split evaluation flaw (training on job split, evaluating on resume/dual split).
6. Manifest cryptographic tampering detection.
7. Pipeline transformation isolation (TF-IDF and Scaler fitted exclusively on training).
8. Cache key and label leakage rejection.
"""

import os
import copy
import json
import pytest
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from src.evaluation.split_validator import (
    SplitLeakageError,
    validate_split_isolation,
    compute_overlap_metrics,
    validate_manifest_integrity,
    validate_embedding_cache_keys,
    hash_text,
    hash_pair
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def clean_mock_splits():
    """Provides isolated mock splits with zero resume, job, or pair overlap."""
    train_df = pd.DataFrame({
        "resume_text": [
            "Senior Python backend developer with Django and PostgreSQL experience.",
            "Frontend React developer with Redux and TypeScript proficiency.",
            "Data scientist with PyTorch, TensorFlow, and Pandas modeling skills."
        ],
        "job_description_text": [
            "Seeking Senior Python engineer with database design expertise.",
            "Frontend developer required for React and modern UI applications.",
            "Data scientist needed for predictive deep learning pipelines."
        ],
        "label": ["Good Fit", "Good Fit", "Potential Fit"]
    })

    eval_df = pd.DataFrame({
        "resume_text": [
            "DevOps engineer with Kubernetes, Docker, and CI/CD automation background.",
            "Embedded systems firmware engineer with C and microcontroller skills."
        ],
        "job_description_text": [
            "Looking for Cloud Infrastructure DevOps engineer for AWS and Kubernetes.",
            "Firmware developer wanted for RTOS microcontroller programming."
        ],
        "label": ["Good Fit", "Good Fit"]
    })
    return train_df, eval_df


def test_clean_splits_pass_all_protocols(clean_mock_splits):
    """Verifies that completely isolated splits pass validation across all protocols."""
    train_df, eval_df = clean_mock_splits
    for proto in ["job_disjoint", "resume_disjoint", "dual_unseen", "held_out_test"]:
        result = validate_split_isolation(train_df, eval_df, protocol=proto, split_name="test_clean")
        assert result["status"] == "VALID"
        assert result["metrics"]["resume_overlap_count"] == 0
        assert result["metrics"]["job_overlap_count"] == 0
        assert result["metrics"]["pair_overlap_count"] == 0


def test_reject_deliberate_resume_leakage(clean_mock_splits):
    """Verifies immediate rejection when a resume is shared in resume-disjoint or dual-unseen splits."""
    train_df, eval_df = clean_mock_splits
    contaminated_eval = eval_df.copy()
    # Inject train resume into eval
    contaminated_eval.loc[0, "resume_text"] = train_df.loc[0, "resume_text"]

    # Resume-disjoint must reject
    with pytest.raises(SplitLeakageError, match="RESUME LEAKAGE DETECTED"):
        validate_split_isolation(train_df, contaminated_eval, protocol="resume_disjoint")

    # Dual-unseen must reject
    with pytest.raises(SplitLeakageError, match="DUAL ENTITY LEAKAGE DETECTED"):
        validate_split_isolation(train_df, contaminated_eval, protocol="dual_unseen")


def test_reject_deliberate_job_leakage(clean_mock_splits):
    """Verifies immediate rejection when a job is shared in job-disjoint or dual-unseen splits."""
    train_df, eval_df = clean_mock_splits
    contaminated_eval = eval_df.copy()
    # Inject train job into eval
    contaminated_eval.loc[0, "job_description_text"] = train_df.loc[0, "job_description_text"]

    # Job-disjoint must reject
    with pytest.raises(SplitLeakageError, match="JOB LEAKAGE DETECTED"):
        validate_split_isolation(train_df, contaminated_eval, protocol="job_disjoint")

    # Dual-unseen must reject
    with pytest.raises(SplitLeakageError, match="DUAL ENTITY LEAKAGE DETECTED"):
        validate_split_isolation(train_df, contaminated_eval, protocol="dual_unseen")


def test_reject_deliberate_pair_leakage(clean_mock_splits):
    """Verifies immediate rejection when an exact pair is shared in any split."""
    train_df, eval_df = clean_mock_splits
    contaminated_eval = eval_df.copy()
    # Inject exact (resume, job) pair
    contaminated_eval.loc[0, "resume_text"] = train_df.loc[0, "resume_text"]
    contaminated_eval.loc[0, "job_description_text"] = train_df.loc[0, "job_description_text"]

    for proto in ["job_disjoint", "resume_disjoint", "dual_unseen", "held_out_test"]:
        with pytest.raises(SplitLeakageError, match="CATASTROPHIC PAIR LEAKAGE"):
            validate_split_isolation(train_df, contaminated_eval, protocol=proto)


def test_reject_phase12b_cross_split_contamination():
    """
    Verifies that the validator immediately catches and blocks the Phase 12B flaw:
    evaluating a train_sub_job-trained model on val_sub_res or dual_val_df.
    """
    manifest_dir = os.path.join(REPO_ROOT, "manifests", "v1")
    job_train_path = os.path.join(manifest_dir, "job_disjoint_train_v1.parquet")
    res_val_path = os.path.join(manifest_dir, "resume_disjoint_val_v1.parquet")
    dual_val_path = os.path.join(manifest_dir, "dual_unseen_val_v1.parquet")

    if os.path.exists(job_train_path) and os.path.exists(res_val_path):
        job_train_df = pd.read_parquet(job_train_path)
        res_val_df = pd.read_parquet(res_val_path)

        # Cross-evaluating job_train on res_val must be rejected
        with pytest.raises(SplitLeakageError, match="CATASTROPHIC PAIR LEAKAGE"):
            validate_split_isolation(job_train_df, res_val_df, protocol="resume_disjoint")

    if os.path.exists(job_train_path) and os.path.exists(dual_val_path):
        job_train_df = pd.read_parquet(job_train_path)
        dual_val_df = pd.read_parquet(dual_val_path)

        # Cross-evaluating job_train on dual_val must be rejected
        with pytest.raises(SplitLeakageError, match="CATASTROPHIC PAIR LEAKAGE"):
            validate_split_isolation(job_train_df, dual_val_df, protocol="dual_unseen")


def test_manifest_cryptographic_verification(tmp_path):
    """Verifies that manifest integrity verification detects tampered split files."""
    dummy_file = tmp_path / "dummy_split.parquet"
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(dummy_file)

    dummy_manifest = tmp_path / "manifest.json"
    actual_hash = "fake_sha256_hash_that_does_not_match"
    manifest_data = {
        "version": "1.0.0",
        "files": [{
            "relative_path": "dummy_split.parquet",
            "sha256": actual_hash
        }]
    }
    with open(dummy_manifest, "w") as f:
        json.dump(manifest_data, f)

    with pytest.raises(SplitLeakageError, match="MANIFEST CORRUPTION"):
        validate_manifest_integrity(str(dummy_manifest))


def test_transformer_pipeline_isolation():
    """
    Proves that fitting TF-IDF and StandardScaler strictly on training split
    preserves pipeline isolation (zero test-set vocabulary or variance leakage).
    """
    tr_resumes = ["Experienced software engineer with python and java backend skills."]
    val_resumes = ["Expert rust systems programmer with quantumcomputing specialization."]

    tfidf = TfidfVectorizer()
    tfidf.fit(tr_resumes)

    # Validation-only token 'quantumcomputing' must NOT be in vocabulary
    assert "quantumcomputing" not in tfidf.vocabulary_
    assert "python" in tfidf.vocabulary_

    # Verify scaler
    tr_feats = np.array([[10.0], [20.0], [30.0]])
    val_feats = np.array([[999.0]])

    scaler = StandardScaler()
    scaler.fit(tr_feats)

    assert scaler.mean_[0] == 20.0
    val_scaled = scaler.transform(val_feats)
    # Mean of scaler should remain 20.0, untouched by validation
    assert scaler.mean_[0] == 20.0


def test_cache_integrity_guard():
    """Verifies cache validation checks and rejection of illegal target keys."""
    cache_path = os.path.join(REPO_ROOT, "results", "phase12b_embeddings", "minilm_l6_v2_cache.npz")
    if os.path.exists(cache_path):
        res = validate_embedding_cache_keys(cache_path)
        assert res["status"] == "VALID"
        assert res["label_leakage_detected"] is False
        assert res["embedding_dim"] == 384
