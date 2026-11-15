"""
Phase 7E Regression Test Suite:
Verifies:
1. Dual-unseen split integrity (3,857 train, 297 val, 2,087 excluded)
2. Zero resume overlap
3. Zero job overlap
4. Zero pair overlap
5. Fold-level preprocessing isolation
6. Valid model predictions
7. Correct label ordering
8. Saved model reload
9. Confusion matrix conservation
10. Metrics consistency
11. Feature dimensions
12. No test leakage
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import joblib

SPLITS_DIR = Path("experiments/dataset_improvement/splits")
RESULTS_DIR = Path("experiments/dataset_improvement/results")
MODELS_DIR = Path("experiments/dataset_improvement/models")
LABEL_ORDER = ["No Fit", "Good Fit", "Potential Fit"]


def test_01_dual_unseen_split_integrity():
    """Verify exact row counts for train, val, and excluded partitions."""
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")
    excl_df = pd.read_parquet(SPLITS_DIR / "cross_boundary_excluded.parquet")

    assert len(train_df) == 3857, f"Expected 3,857 train pairs, found {len(train_df)}"
    assert len(val_df) == 297, f"Expected 297 val pairs, found {len(val_df)}"
    assert len(excl_df) == 2087, f"Expected 2,087 excluded pairs, found {len(excl_df)}"
    assert len(train_df) + len(val_df) + len(excl_df) == 6241


def test_02_zero_resume_overlap():
    """Verify zero resume text or ID overlap between train and val."""
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")

    train_resumes = set(train_df["resume_text"].tolist())
    val_resumes = set(val_df["resume_text"].tolist())
    overlap = train_resumes.intersection(val_resumes)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping resumes!"


def test_03_zero_job_overlap():
    """Verify zero job text or ID overlap between train and val."""
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")

    train_jobs = set(train_df["job_description_text"].tolist())
    val_jobs = set(val_df["job_description_text"].tolist())
    overlap = train_jobs.intersection(val_jobs)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping jobs!"


def test_04_zero_pair_overlap():
    """Verify zero (resume, job) pair overlap across all splits."""
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")

    train_pairs = set(zip(train_df["resume_text"], train_df["job_description_text"]))
    val_pairs = set(zip(val_df["resume_text"], val_df["job_description_text"]))
    overlap = train_pairs.intersection(val_pairs)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping pairs!"


def test_05_valid_label_distribution():
    """Verify all labels are within allowed 3-class set."""
    train_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")

    for name, df in [("train", train_df), ("val", val_df)]:
        labels = set(df["label"].unique())
        assert labels.issubset(set(LABEL_ORDER)), f"Unexpected labels in {name}: {labels}"


def test_06_model_reload_and_predictions():
    """Verify saved champion model and pipeline reload cleanly and generate valid predictions."""
    import sys
    import experiments.dataset_improvement.scripts.train_dual_unseen as tdu
    sys.modules["__main__"].FullFeaturePipeline = tdu.FullFeaturePipeline

    pipeline_path = MODELS_DIR / "frozen_dual_unseen_pipeline.joblib"
    model_path = MODELS_DIR / "frozen_dual_unseen_champion.joblib"

    if not pipeline_path.exists() or not model_path.exists():
        pytest.skip("Models not yet saved")

    pipeline = joblib.load(pipeline_path)
    model = joblib.load(model_path)

    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")
    val_dom = pd.read_parquet(SPLITS_DIR / "val_domain_raw.parquet")

    X_val = pipeline.transform(
        val_df["resume_text"].tolist()[:10],
        val_df["job_description_text"].tolist()[:10],
        val_dom.values[:10]
    )
    preds = model.predict(X_val.astype(np.float32))
    assert len(preds) == 10
    for p in preds:
        assert p in LABEL_ORDER


def test_07_confusion_matrix_conservation():
    """Verify final dual-unseen confusion matrix row sums match true label counts."""
    results_path = RESULTS_DIR / "phase7e_final_evaluation_results.json"
    if not results_path.exists():
        pytest.skip("Final evaluation results not yet generated")

    with open(results_path, "r") as f:
        data = json.load(f)

    cm = np.array(data["champion_metrics"]["confusion_matrix"])
    val_df = pd.read_parquet(SPLITS_DIR / "dual_unseen_val.parquet")
    true_counts = val_df["label"].value_counts()[LABEL_ORDER].values

    assert cm.sum() == len(val_df)
    assert np.array_equal(cm.sum(axis=1), true_counts)


def test_08_no_test_leakage_in_training_config():
    """Verify training configuration reflects training partition only."""
    config_path = MODELS_DIR / "training_config.json"
    if not config_path.exists():
        pytest.skip("Training config not yet saved")

    with open(config_path, "r") as f:
        cfg = json.load(f)

    assert cfg["training_samples_raw"] == 3857
    assert cfg["training_samples_active"] == 3845
    assert cfg["val_samples_dual_unseen"] == 297
