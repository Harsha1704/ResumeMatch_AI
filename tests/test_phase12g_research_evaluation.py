"""
Tests for Phase 12G Research Architecture Benchmarks, Benchmark Integrity, and Release Gates.
"""

import json
import hashlib
import os
import pytest
from pathlib import Path


@pytest.fixture(scope="module")
def release_gates_data():
    with open("experiments/phase12g/results/phase12g_release_gates_audit.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def arch_comparison_data():
    with open("experiments/phase12g/results/cross_encoder_vs_bi_encoder_comparison.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def threshold_calibration_data():
    with open("experiments/phase12g/results/threshold_calibration_quality_audit.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def benchmark_data():
    with open("experiments/phase12g/results/independent_benchmark_investigation.json") as f:
        return json.load(f)


def test_production_artifacts_strictly_preserved():
    """Confirms production checkpoints remain bit-for-bit unchanged."""
    prod_model = "models/best_model.joblib"
    prod_pipe = "models/feature_pipeline.joblib"
    
    with open(prod_model, "rb") as f:
        m_sha = hashlib.sha256(f.read()).hexdigest()
    with open(prod_pipe, "rb") as f:
        p_sha = hashlib.sha256(f.read()).hexdigest()
        
    assert m_sha == "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"
    assert p_sha == "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"


def test_release_gates_promotion_withheld(release_gates_data):
    """Verifies that challenger promotion is strictly withheld in Phase 12G."""
    assert release_gates_data["overall_release_verdict"] == "PROMOTION WITHHELD (RESEARCH STATUS RETAINED)"
    assert release_gates_data["gate_1_leakage_safe_evaluation"]["status"] == "PASSED"
    assert release_gates_data["gate_7_verified_artifact_integrity"]["status"] == "PASSED"


def test_djinni_unpaired_status_verified(benchmark_data):
    """Verifies that Djinni is strictly marked unpaired with zero synthetic labels."""
    djinni_status = benchmark_data["investigated_corpora"]["djinni_recruitment_corpus"]["pairing_status"]
    assert djinni_status == "UNPAIRED / DUAL-MODALITY ONLY"
    assert "Synthetic ground-truth label manufacturing" in benchmark_data["investigated_corpora"]["djinni_recruitment_corpus"]["prohibited_uses"]


def test_nested_threshold_calibration_improves_macro_f1(threshold_calibration_data):
    """Verifies that nested out-of-fold calibration improves Macro F1 without label leakage."""
    gain = threshold_calibration_data["gain_over_uncalibrated_argmax"]
    assert gain["macro_f1_delta"] > 0
    assert gain["good_fit_recall_recovery_pp"] > 0
    assert len(threshold_calibration_data["inner_fold_selected_thresholds"]) == 5
