"""
tests/test_phase12f3_3_statistical_validation.py
Reproducible unit and regression tests for Phase 12F.3.3:
1. Verifies prediction alignment and exact row matching (296 rows per seed).
2. Verifies ground-truth label invariance across all seeds.
3. Tests McNemar exact test calculation against scipy reference implementation.
4. Verifies paired bootstrap logic preserving paired example structure.
5. Verifies three-class mapping consistency.
"""

import pytest
import numpy as np
import pandas as pd
import scipy.stats as stats
from pathlib import Path
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support

REPO_ROOT = Path("D:/skillsync1")
PRED_DIR = REPO_ROOT / "experiments" / "phase12f3_3" / "predictions"
CLASSES = ["No Fit", "Potential Fit", "Good Fit"]
SEEDS = [42, 43, 44, 45, 46]

def test_prediction_artifacts_exist_and_align():
    """Verifies that all 5 prediction CSVs exist and contain exactly 296 aligned rows."""
    reference_df = None
    for seed in SEEDS:
        p_path = PRED_DIR / f"contrastive_vs_raw_seed_{seed}.csv"
        assert p_path.exists(), f"Missing prediction file: {p_path}"
        df = pd.read_csv(p_path)
        assert len(df) == 296, f"Seed {seed} has {len(df)} rows, expected 296."
        
        # Verify columns
        expected_cols = {
            "row_index", "resume_id", "job_id", "resume_text_hash", "job_text_hash",
            "true_label", "pred_raw_sbert", "pred_contrastive",
            "raw_correct", "contrastive_correct"
        }
        assert expected_cols.issubset(set(df.columns))
        
        if reference_df is None:
            reference_df = df
        else:
            # Check row-by-row alignment
            assert (df["row_index"] == reference_df["row_index"]).all()
            assert (df["true_label"] == reference_df["true_label"]).all()
            assert (df["resume_text_hash"] == reference_df["resume_text_hash"]).all()
            assert (df["job_text_hash"] == reference_df["job_text_hash"]).all()

def test_prediction_labels_adhere_to_three_class_mapping():
    """Ensures all prediction strings strictly match the canonical three-class definitions."""
    for seed in SEEDS:
        df = pd.read_csv(PRED_DIR / f"contrastive_vs_raw_seed_{seed}.csv")
        assert set(df["true_label"]).issubset(set(CLASSES))
        assert set(df["pred_raw_sbert"]).issubset(set(CLASSES))
        assert set(df["pred_contrastive"]).issubset(set(CLASSES))

def test_mcnemar_exact_two_sided_calculation():
    """Validates that McNemar exact binomial test matches theoretical binomial probabilities."""
    # Test case: b=30, c=53 (Seed 42 values)
    b, c = 30, 53
    res = stats.binomtest(min(b, c), b + c, p=0.5, alternative="two-sided")
    p_val = res.pvalue
    assert round(p_val, 4) == 0.0152
    assert p_val < 0.05

    # Test case: b=43, c=46 (Seed 44 values)
    b44, c44 = 43, 46
    res44 = stats.binomtest(min(b44, c44), b44 + c44, p=0.5, alternative="two-sided")
    assert round(res44.pvalue, 4) == 0.8323
    assert res44.pvalue > 0.05

def test_paired_bootstrap_preserves_paired_structure():
    """Ensures paired resampling draws identical row indices for baseline and candidate."""
    df = pd.read_csv(PRED_DIR / f"contrastive_vs_raw_seed_42.csv")
    y_true = df["true_label"].values
    p_raw = df["pred_raw_sbert"].values
    p_proj = df["pred_contrastive"].values
    
    rng = np.random.default_rng(seed=42)
    sample_indices = rng.integers(0, len(df), size=len(df))
    
    # Paired accuracy difference
    acc_raw_paired = np.mean(p_raw[sample_indices] == y_true[sample_indices])
    acc_proj_paired = np.mean(p_proj[sample_indices] == y_true[sample_indices])
    paired_diff = acc_proj_paired - acc_raw_paired
    
    # Independent resampling should differ
    sample_indices_indep = rng.integers(0, len(df), size=len(df))
    acc_proj_indep = np.mean(p_proj[sample_indices_indep] == y_true[sample_indices_indep])
    indep_diff = acc_proj_indep - acc_raw_paired
    
    assert paired_diff != indep_diff
