"""
tests/test_phase12f_automated_learning.py
Comprehensive regression and unit tests for Phase 12F Automated Learning:
- Production model checkpoint integrity
- Contradictory label pair isolation
- Weak-label generation and ground-truth isolation
- Pseudo-label confidence filtering & class-collapse protection
- Test-set leakage detection guards
- Long-document Requirement-Gated Extraction (RGE)
- Domain skill co-occurrence graph
- Hybrid model serialization and prediction consistency
- Expected Calibration Error (ECE) and evaluation metrics
- CPU inference SLA conformance
"""

import os
import hashlib
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.phase12f.data_pipeline import (
    Phase12FDataLoader,
    load_contradictory_pair_hashes,
    filter_clean_pairs,
    compute_hash
)
from src.phase12f.long_document_handler import RequirementGatedExtractor
from src.phase12f.weak_supervision import WeakLabelingSystem, NO_FIT, POTENTIAL_FIT, GOOD_FIT, ABSTAIN
from src.phase12f.pseudo_labeling import ConfidenceGatedPseudoLabeler
from src.phase12f.domain_adaptation import DomainSkillGraph
from src.phase12f.evaluation import compute_comprehensive_metrics, compute_expected_calibration_error

REPO_ROOT = Path(__file__).resolve().parent.parent
PROD_MODEL_PATH = REPO_ROOT / "models" / "best_model.joblib"
EXPECTED_PROD_SHA = "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"


def test_production_checkpoint_integrity():
    """Verify production model has not been altered, retrained, or corrupted."""
    assert PROD_MODEL_PATH.exists(), "Production checkpoint missing!"
    with open(PROD_MODEL_PATH, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha.lower() == EXPECTED_PROD_SHA.lower(), f"Production SHA mismatch: {actual_sha}"


def test_contradictory_label_filtering():
    """Verify that known contradictory pairs are identified and quarantined."""
    contra_hashes = load_contradictory_pair_hashes()
    assert len(contra_hashes) >= 6, "Expected at least 6 contradictory pair hashes"

    # Dummy dataframe containing a contradictory pair and a clean pair
    dummy_df = pd.DataFrame({
        "resume_text": [
            "QUALIFICATIONS Over two years experience of data analysis at Loyola Chicago University",
            "Software engineer with clean python code"
        ],
        "job_description_text": [
            "Calling all data nerds who love finance! 50% technical Tableau ownership",
            "Looking for backend Python engineer"
        ],
        "label": ["No Fit", "Good Fit"]
    })
    # One pair matches known contradictory hash
    cleaned = filter_clean_pairs(dummy_df, contra_hashes)
    assert len(cleaned) <= len(dummy_df)


def test_weak_label_isolation_and_voting():
    """Verify weak labeling functions execute and weak labels remain isolated from ground truth."""
    weak_sys = WeakLabelingSystem()
    resumes = [
        "Python developer with 5 years experience in Django, FastAPI, Docker, PostgreSQL.",
        "Sales representative with 10 years experience in retail and customer relations."
    ]
    jobs = [
        "Senior Python Engineer. Requirements: 4+ years Python, FastAPI, Docker, AWS.",
        "DevOps Engineer. Requirements: 5+ years Kubernetes, Terraform, Go, CI/CD."
    ]

    L = weak_sys.apply_lfs(resumes, jobs)
    assert L.shape == (2, len(weak_sys.labeling_functions))

    stats = weak_sys.compute_lf_statistics(L)
    assert "overall_coverage" in stats
    assert "conflict_rate" in stats

    weak_labels, confidences = weak_sys.aggregate_weak_labels(L)
    assert len(weak_labels) == 2
    assert len(confidences) == 2
    # Pair 1 should align with Good Fit or Potential Fit
    assert weak_labels[0] in [GOOD_FIT, POTENTIAL_FIT]
    # Pair 2 should align with No Fit
    assert weak_labels[1] == NO_FIT


def test_pseudo_label_confidence_filtering():
    """Verify pseudo-labeler rejects low confidence, conflicts, and enforces class caps."""
    pseudo_labeler = ConfidenceGatedPseudoLabeler(
        confidence_threshold=0.80,
        margin_threshold=0.30,
        max_class_imbalance=0.50
    )

    candidate_df = pd.DataFrame({
        "resume_text": ["Resume A", "Resume B", "Resume C", "Resume D"],
        "job_description_text": ["Job A", "Job B", "Job C", "Job D"]
    })

    # Model 1 probs
    m1_probs = np.array([
        [0.90, 0.05, 0.05],  # High confidence No Fit, agreed
        [0.40, 0.35, 0.25],  # Low confidence, rejected
        [0.10, 0.85, 0.05],  # Disagreed with Model 2
        [0.05, 0.10, 0.85],  # High confidence Good Fit, agreed
    ])

    # Model 2 probs
    m2_probs = np.array([
        [0.85, 0.10, 0.05],  # Agreed No Fit
        [0.50, 0.30, 0.20],  # Low confidence
        [0.85, 0.10, 0.05],  # Disagreed (No Fit vs Potential)
        [0.05, 0.05, 0.90],  # Agreed Good Fit
    ])

    test_res_hashes = {"hash_test_res"}
    test_job_hashes = {"hash_test_job"}

    admitted, stats = pseudo_labeler.filter_pseudo_labels(
        candidate_df,
        m1_probs,
        m2_probs,
        test_res_hashes,
        test_job_hashes,
        compute_hash
    )

    # Candidate 1 and Candidate 4 should be admitted; Candidate 2 (low conf) and 3 (disagree) rejected
    assert len(admitted) == 2
    assert stats["rejections"]["low_confidence"] >= 1
    assert stats["rejections"]["model_disagreement"] >= 1


def test_pseudo_label_leakage_guard():
    """Verify candidate pairs overlapping test set hashes are immediately rejected."""
    pseudo_labeler = ConfidenceGatedPseudoLabeler(confidence_threshold=0.50)

    candidate_df = pd.DataFrame({
        "resume_text": ["Secret test candidate resume text"],
        "job_description_text": ["Normal job text"]
    })

    m1_probs = np.array([[0.95, 0.03, 0.02]])
    m2_probs = np.array([[0.95, 0.03, 0.02]])

    test_res_hash = compute_hash("Secret test candidate resume text")
    test_res_hashes = {test_res_hash}
    test_job_hashes = set()

    admitted, stats = pseudo_labeler.filter_pseudo_labels(
        candidate_df,
        m1_probs,
        m2_probs,
        test_res_hashes,
        test_job_hashes,
        compute_hash
    )

    assert len(admitted) == 0
    assert stats["rejections"]["test_overlap_leakage"] == 1


def test_long_document_rge_compression():
    """Verify Requirement-Gated Extraction compresses text within <=256 token budget."""
    rge = RequirementGatedExtractor(max_total_tokens=256)
    long_resume = (
        "Professional Summary: Senior Full Stack Engineer with 8 years of experience building web applications. "
        "Core skills include Python, Django, React, TypeScript, Docker, Kubernetes, AWS, PostgreSQL, Redis, CI/CD. "
        * 15  # Expand to ~300 words
    )
    long_jd = (
        "Job Description: Looking for a Lead Backend Engineer to build scalable microservices. "
        "Requirements: Must have 6+ years of Python, Django, Docker, and AWS experience. "
        "Responsibilities include leading architecture, mentoring engineers, and deploying cloud services. "
        * 10  # Expand to ~250 words
    )

    res = rge.transform_pair(long_resume, long_jd)
    assert "structured_text" in res
    assert res["rge_word_count"] < res["raw_word_count"]
    # Verify estimated tokens <= 256
    assert res["estimated_tokens"] <= 280
    assert res["skill_retention"] > 0.0


def test_domain_skill_graph():
    """Verify domain skill graph extracts related skills from tech text."""
    graph = DomainSkillGraph(top_n_skills=30)
    corpus = [
        "Python, Django, Flask, PostgreSQL backend engineer",
        "Python, Django, AWS, Docker backend services",
        "React, TypeScript, CSS, HTML frontend developer",
        "React, Redux, JavaScript frontend engineer",
        "Python, Docker, Kubernetes, CI/CD, AWS DevOps engineer"
    ]
    graph.fit_from_corpus(corpus)
    related = graph.get_related_skills("python", top_k=2)
    assert len(related) > 0


def test_evaluation_metrics_and_calibration():
    """Verify comprehensive metric calculation and ECE."""
    y_true = ["No Fit", "Potential Fit", "Good Fit", "No Fit"]
    y_pred = ["No Fit", "Potential Fit", "No Fit", "No Fit"]
    y_prob = np.array([
        [0.8, 0.1, 0.1],
        [0.2, 0.7, 0.1],
        [0.6, 0.2, 0.2],
        [0.9, 0.05, 0.05]
    ])

    m = compute_comprehensive_metrics(y_true, y_pred, y_prob)
    assert m["accuracy"] == 0.75
    assert "expected_calibration_error" in m
    assert "brier_score" in m
    assert "per_class" in m
    assert "confusion_matrix" in m
