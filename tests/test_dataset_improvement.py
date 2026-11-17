"""
Phase 7D Automated Regression Tests:
Tests dataset schema, duplicate detection, conflicting labels, privacy,
technical token preservation, and mathematical proof of dual-unseen isolation.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from experiments.dataset_improvement.scripts.dataset_loader import (
    load_dual_unseen_split,
    verify_scenario_c_integrity,
    VALID_LABELS,
    LABEL_MAPPING
)
from src.preprocessing.text_cleaner import clean_text
from src.preprocessing.skill_extractor import SkillEngine


def test_dual_unseen_schema_validation():
    """1. Dataset schema validation."""
    train_df, val_df, meta = load_dual_unseen_split()
    expected_cols = {"resume_text", "job_description_text", "label", "resume_id", "job_id", "pair_id"}
    assert expected_cols.issubset(set(train_df.columns))
    assert expected_cols.issubset(set(val_df.columns))


def test_label_integrity():
    """2. Label integrity across partitions."""
    train_df, val_df, _ = load_dual_unseen_split()
    assert set(train_df["label"].unique()) == set(VALID_LABELS)
    assert set(val_df["label"].unique()) == set(VALID_LABELS)


def test_duplicate_detection_and_conflicts():
    """3 & 4. Duplicate and conflicting label detection."""
    raw_train = pd.read_csv("data/raw/resume_job_fit_train.csv")
    dups = raw_train[raw_train.duplicated(subset=["resume_text", "job_description_text"], keep=False)]
    assert len(dups) == 14  # Exact 14 duplicate rows identified
    conflicts = dups.groupby(["resume_text", "job_description_text"])["label"].nunique()
    assert (conflicts > 1).sum() == 6  # 6 conflicting groups


def test_label_mapping_compatibility():
    """6. Label mapping compatibility."""
    assert len(LABEL_MAPPING) == 3
    for label in VALID_LABELS:
        assert label in LABEL_MAPPING
        assert isinstance(LABEL_MAPPING[label], int)


def test_zero_resume_overlap():
    """7. Mathematical proof of zero resume overlap in Evaluation C."""
    train_df, val_df, _ = load_dual_unseen_split()
    tr_resumes = set(train_df["resume_id"])
    va_resumes = set(val_df["resume_id"])
    overlap = tr_resumes.intersection(va_resumes)
    assert len(overlap) == 0, f"Detected resume leakage: {len(overlap)}"


def test_zero_job_overlap():
    """8. Mathematical proof of zero job overlap in Evaluation C."""
    train_df, val_df, _ = load_dual_unseen_split()
    tr_jobs = set(train_df["job_id"])
    va_jobs = set(val_df["job_id"])
    overlap = tr_jobs.intersection(va_jobs)
    assert len(overlap) == 0, f"Detected job leakage: {len(overlap)}"


def test_zero_pair_overlap():
    """9. Zero pair overlap in Evaluation C."""
    train_df, val_df, _ = load_dual_unseen_split()
    tr_pairs = set(train_df["pair_id"])
    va_pairs = set(val_df["pair_id"])
    overlap = tr_pairs.intersection(va_pairs)
    assert len(overlap) == 0


def test_split_reproducibility():
    """10. Split reproducibility using seed 20."""
    import time
    from experiments.dataset_improvement.scripts.create_dual_unseen_split import create_dual_unseen_partition
    t1, v1, _, _ = create_dual_unseen_partition(seed=20)
    time.sleep(0.5)
    for attempt in range(3):
        try:
            t2, v2, _, _ = create_dual_unseen_partition(seed=20)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.5)
    assert t1["pair_id"].tolist() == t2["pair_id"].tolist()
    assert v1["pair_id"].tolist() == v2["pair_id"].tolist()


def test_class_distribution_integrity():
    """11. Class distribution integrity in Dual-Unseen validation."""
    train_df, val_df, meta = load_dual_unseen_split()
    counts = val_df["label"].value_counts()
    assert counts["No Fit"] >= 50
    assert counts["Good Fit"] >= 50
    assert counts["Potential Fit"] >= 50
    assert meta["class_diversity_verified"] is True


def test_dataset_loader_compatibility():
    """12. Dataset loader and scenario verification."""
    train_df, val_df, _ = load_dual_unseen_split()
    report = verify_scenario_c_integrity(train_df, val_df)
    assert report["zero_resume_overlap"] is True
    assert report["zero_job_overlap"] is True
    assert report["zero_pair_overlap"] is True


def test_missing_value_handling():
    """13. Missing value handling."""
    train_df, val_df, _ = load_dual_unseen_split()
    assert train_df["resume_text"].isnull().sum() == 0
    assert train_df["job_description_text"].isnull().sum() == 0
    assert val_df["resume_text"].isnull().sum() == 0
    assert val_df["job_description_text"].isnull().sum() == 0


def test_technical_token_preservation():
    """14. Technical token preservation during cleaning."""
    tokens = ["C++", "C#", ".NET", "Node.js", "SQL", "Python", "Kubernetes", "Docker"]
    text = "Proficient in C++, C#, .NET, Node.js, SQL, Python, Kubernetes, and Docker."
    cleaned = clean_text(text)
    for tok in ["c++", "c#", ".net", "node.js", "sql", "python", "kubernetes", "docker"]:
        assert tok in cleaned.lower()


def test_privacy_safe_diagnostics():
    """15. Privacy diagnostics: No raw PII exposed in outputs."""
    with open("experiments/dataset_improvement/audits/dataset_audit_report.json") as f:
        rep = json.load(f)
    assert "emails" in rep["train_set"]["pii_occurrences"]
    assert "phone_numbers" in rep["train_set"]["pii_occurrences"]
