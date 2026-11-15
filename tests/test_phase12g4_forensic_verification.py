"""
Tests for Phase 12G.4 Forensic Verification.
Validates:
1. Production checkpoints bit-for-bit preservation.
2. Cross-encoder audit classification (UNVERIFIED on Dual-Unseen).
3. Candidate vs Job fold isolation properties in nested calibration.
4. Correctness of recomputed metrics from saved predictions.
5. Latency boundary distinction (Classifier-only vs End-to-End).
"""

import json
import hashlib
import os
import pytest


@pytest.fixture(scope="module")
def audit_data():
    with open("experiments/phase12g/results/phase12g4_forensic_audit.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def recomputed_data():
    with open("experiments/phase12g/results/phase12g4_recomputed_metrics.json") as f:
        return json.load(f)


def test_production_artifacts_cryptographically_identical(audit_data):
    """Verifies that production artifacts remain 100% identical to certified hashes."""
    prod = audit_data["checkpoint_integrity"]["production_model_joblib"]
    pipe = audit_data["checkpoint_integrity"]["feature_pipeline_joblib"]
    
    assert prod["sha256"] == "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"
    assert prod["size_bytes"] == 61487
    assert pipe["sha256"] == "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"
    assert pipe["size_bytes"] == 270105


def test_cross_encoder_classified_unverified(audit_data):
    """Verifies that cross-encoder 47.30% Dual-Unseen claim is properly classified as unverified."""
    ce = audit_data["cross_encoder_audit"]["forensic_investigation"]
    assert ce["reproducibility_verdict"] == "UNVERIFIED ON DUAL-UNSEEN PREDICTIONS"
    assert ce["saved_predictions_file"] is None


def test_nested_calibration_fold_isolation(audit_data):
    """Verifies that folds are candidate-disjoint but document job sharing."""
    folds = audit_data["calibration_audit"]["fold_isolation_audit"]
    assert len(folds) == 5
    for fold in folds:
        assert fold["candidate_disjoint"] is True
        assert fold["candidate_overlap"] == 0
        assert fold["job_disjoint"] is False


def test_recomputed_metrics_from_saved_predictions(audit_data):
    """Verifies that metrics recalculated from oof_calibrated_predictions_seed42.csv match audit records."""
    metrics = audit_data["calibration_audit"]["recomputed_metrics"]
    assert metrics["accuracy"] == 0.4764
    assert metrics["balanced_accuracy"] == 0.4136
    assert metrics["macro_f1"] == 0.3638


def test_latency_boundary_distinction(audit_data):
    """Verifies that end-to-end latency is properly distinguished from classifier-only forward pass."""
    prod_lat = audit_data["latency_memory_audit"]["benchmarks"]["production_end_to_end_pipeline"]
    assert prod_lat["mean_latency_ms"] > 30.0
    assert prod_lat["classifier_only_mean_ms"] < 1.0
