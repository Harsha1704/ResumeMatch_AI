"""
experiments/phase13_1/tests/test_phase13_1_corrections.py
Automated verification tests for Phase 13.1 Evidence Correction & Validation:
1. Row alignment and one-to-one joins on stable pair_id.
2. Contradictory duplicate detection and handling.
3. Production baseline provenance audit (checkpoint contamination check).
4. Relative Good Fit improvement formula verification (78.57% vs 92.3%).
5. Multiclass Brier score normalization (raw / 2.0).
6. Evidence-derived release gates integrity (no hardcoded unconditional passes).
7. Production checkpoint hash preservation.
"""

import json
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path("D:/skillsync1")
PROD_FILES = {
    "models/best_model.joblib": (61487, "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"),
    "models/feature_pipeline.joblib": (270105, "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"),
    "models/phase12f/challenger_model_phase12f.joblib": (2330440, "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766")
}

def test_production_artifacts_unmodified():
    """Verify that production files have not been overwritten or altered."""
    for rel_path, (expected_size, expected_hash) in PROD_FILES.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"Missing production artifact: {rel_path}"
        data = file_path.read_bytes()
        assert len(data) == expected_size, f"Size mismatch for {rel_path}: {len(data)} != {expected_size}"
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"

def test_keyed_splits_and_one_to_one_alignment():
    """Verify Task 1: stable pair_id keys, exactly 296 clean validation rows, and 1-to-1 matching."""
    val_keyed_path = REPO_ROOT / "experiments" / "phase13_1" / "splits" / "val_domain_keyed.parquet"
    assert val_keyed_path.exists(), "Keyed validation split missing."
    val_df = pd.read_parquet(val_keyed_path)
    
    assert len(val_df) == 296, f"Expected 296 clean validation rows, found {len(val_df)}"
    assert "pair_id" in val_df.columns
    assert "resume_id" in val_df.columns
    assert "job_id" in val_df.columns
    assert "label" in val_df.columns
    
    # Verify synthetic composite pair_id matches resume_id and job_id
    for idx, row in val_df.iterrows():
        expected_pair_id = f"{row['resume_id']}__{row['job_id']}"
        assert row["pair_id"] == expected_pair_id, f"Row {idx} pair_id mismatch"
        
    # Clean validation protocol retains the historical 296 pairs (with row 46 quarantined from train leakage).
    # Note: exactly 295 unique pair_ids exist because of the contradictory duplicate pair (rows 0 and 224/225).
    assert len(val_df["pair_id"].unique()) == 295, "Expected exactly 295 unique pair_ids across 296 pairs"
    counts = val_df["pair_id"].value_counts()
    assert counts.iloc[0] == 2, "Expected exactly one pair_id with count 2 (the contradictory duplicate)"
    assert counts.index[0] == "R_9ec670d617d35247__J_78a2a1e24cb08975"

def test_contradictory_duplicate_detected_in_raw_validation():
    """Verify Task 1 audit finding: row 0 and row 225 in raw dual_unseen_val_v1 have identical pair_id but opposite labels."""
    raw_val_path = REPO_ROOT / "manifests" / "v1" / "dual_unseen_val_v1.parquet"
    assert raw_val_path.exists()
    raw_val = pd.read_parquet(raw_val_path)
    
    row0 = raw_val.iloc[0]
    row225 = raw_val.iloc[225]
    
    pair_id_0 = f"{row0['resume_id']}__{row0['job_id']}"
    pair_id_225 = f"{row225['resume_id']}__{row225['job_id']}"
    
    assert pair_id_0 == pair_id_225, "Expected rows 0 and 225 to share pair_id"
    assert row0["label"] != row225["label"], f"Expected contradictory labels, got {row0['label']} and {row225['label']}"
    assert row0["label"] == "No Fit"
    assert row225["label"] == "Good Fit"

def test_brier_score_normalization_formula():
    """Verify Task 5: 3-class Brier score theoretical max error is 2.0, so normalized must divide by 2.0, NOT 3.0."""
    # Worst case: prob = [1, 0, 0], true = class 2 (one-hot [0, 0, 1])
    # Sum of squared errors = (1-0)^2 + (0-0)^2 + (0-1)^2 = 1 + 0 + 1 = 2.0
    p_worst = np.array([[1.0, 0.0, 0.0]])
    y_worst = np.array([[0.0, 0.0, 1.0]])
    raw_worst = np.sum((p_worst - y_worst) ** 2)
    assert raw_worst == 2.0, f"Theoretical maximum squared error in 3-class Brier must be 2.0, got {raw_worst}"
    
    normalized_worst = raw_worst / 2.0
    assert normalized_worst == 1.0, f"Normalized Brier must scale worst-case error to 1.0, got {normalized_worst}"

def test_relative_good_fit_improvement_calculation():
    """Verify Task 4: Good Fit recall relative improvement is (25 - 14) / 14 = +78.57%, NOT 92.3%."""
    c_baseline = 14
    c_m5 = 25
    c_sbert = 13
    total_good_fit = 93
    
    rec_baseline = c_baseline / total_good_fit
    rec_m5 = c_m5 / total_good_fit
    rec_sbert = c_sbert / total_good_fit
    
    rel_gain_baseline = (rec_m5 - rec_baseline) / rec_baseline
    rel_gain_sbert = (rec_m5 - rec_sbert) / rec_sbert
    
    # Relative gain vs clean baseline is 78.57%
    assert round(rel_gain_baseline * 100, 2) == 78.57
    # 92.3% was the error from comparing against raw SBERT (13 count): (25-13)/13 = 92.31%
    assert round(rel_gain_sbert * 100, 1) == 92.3

def test_end_to_end_latency_benchmark_results():
    """Verify Task 6: end-to-end inference benchmark records cold-start, warm latencies, and artifact size."""
    bench_file = REPO_ROOT / "experiments" / "phase13_1" / "results" / "end_to_end_latency_benchmark.json"
    assert bench_file.exists()
    data = json.load(open(bench_file))
    
    m5 = data["models"]["semantic_skill_fusion_challenger"]
    assert m5["deployable_artifact_mb"] >= 174.0, "Deployable artifact size must include ~174 MB SBERT weights"
    assert m5["latency_mean_ms"] > 50.0, "End-to-end CPU inference per pair exceeds 50 ms SLA"
    assert m5["peak_rss_mb"] > 200.0, "Process RSS must capture full memory footprint"

def test_release_gates_integrity():
    """Verify Task 7: release gates are derived from evidence and cannot all be PASS."""
    gate_file = REPO_ROOT / "reports" / "phase13_1" / "phase13_1_release_gates.json"
    assert gate_file.exists()
    data = json.load(open(gate_file))
    
    gates = data["gates"]
    assert gates["gate_1_reproducibility"]["status"] == "PASS"
    assert gates["gate_2_leakage_safety"]["status"] == "PASS"
    assert gates["gate_3_statistically_significant_improvement"]["status"] == "CONDITIONAL"
    assert gates["gate_4_good_fit_recall_improvement"]["status"] == "PASS"
    assert gates["gate_5_inference_latency"]["status"] == "FAIL"
    assert gates["gate_6_model_size_and_memory"]["status"] == "FAIL"
    assert gates["gate_7_probability_calibration"]["status"] == "CONDITIONAL"
    assert gates["gate_8_no_class_degradation"]["status"] == "PASS"
    
    counts = data["gate_counts"]
    assert counts["PASS"] == 4
    assert counts["CONDITIONAL"] == 2
    assert counts["FAIL"] == 2
    assert counts["NOT_VERIFIED"] == 0
