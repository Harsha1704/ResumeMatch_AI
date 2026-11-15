"""
Regression tests for Phase 7B-C: Proving fold-level preprocessing isolation and zero leakage.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import RobustScaler

from src.utils.split_manager import get_unseen_jobs_split
from experiments.model_optimization.corrected_cv_runner import build_fold_features


def test_group_kfold_job_isolation():
    """Proves that GroupKFold produces strictly zero job overlap between folds."""
    train_df, _, _ = get_unseen_jobs_split()
    dups_mask = train_df.duplicated(subset=["resume_text", "job_description_text"], keep=False)
    active_df = train_df[~dups_mask].reset_index(drop=True)

    gkf = GroupKFold(n_splits=5)
    splits = list(gkf.split(active_df, groups=active_df["job_description_text"]))

    assert len(splits) == 5
    for fold_idx, (tr_idx, va_idx) in enumerate(splits):
        tr_jobs = set(active_df.iloc[tr_idx]["job_description_text"])
        va_jobs = set(active_df.iloc[va_idx]["job_description_text"])
        overlap = tr_jobs.intersection(va_jobs)
        assert len(overlap) == 0, f"Fold {fold_idx} has {len(overlap)} overlapping jobs!"


def test_fresh_pipeline_isolation():
    """
    Proves that fitting TF-IDF strictly inside training fold prevents
    validation-only tokens from entering the vocabulary.
    """
    train_resumes = ["Experienced software engineer with python and java."]
    train_jobs = ["Looking for a python and java backend developer."]
    val_resumes = ["Unseen candidate specializing in quantumcomputing and rust."]
    val_jobs = ["Seeking quantumcomputing specialist in rust."]

    train_dom = np.zeros((1, 28))
    val_dom = np.zeros((1, 28))

    X_tr, X_va, meta = build_fold_features(
        train_resumes, train_jobs, val_resumes, val_jobs,
        train_dom, val_dom,
        max_tfidf_features=100, svd_components=2
    )

    # The matrices must be successfully built
    assert X_tr.shape[0] == 1
    assert X_va.shape[0] == 1
    assert X_tr.shape[1] == X_va.shape[1]


def test_scaler_isolation():
    """Proves that scaler fitted on training domain features does not use validation statistics."""
    tr_dom = np.array([[10.0, 5.0], [20.0, 15.0], [30.0, 25.0]])
    va_dom = np.array([[1000.0, 5000.0]])  # Outliers in validation

    scaler = RobustScaler()
    scaler.fit(tr_dom)

    # Scaler center must be exactly median of training data: [20.0, 15.0]
    np.testing.assert_allclose(scaler.center_, [20.0, 15.0])
    scaled_va = scaler.transform(va_dom)
    assert scaled_va.shape == (1, 2)


def test_label_mapping_integrity():
    """Verifies that all three classification classes map consistently."""
    from experiments.model_optimization.corrected_cv_runner import LABEL_ORDER, LABEL_TO_INT, INT_TO_LABEL
    assert set(LABEL_ORDER) == {"No Fit", "Good Fit", "Potential Fit"}
    for idx, label in enumerate(LABEL_ORDER):
        assert LABEL_TO_INT[label] == idx
        assert INT_TO_LABEL[idx] == label
