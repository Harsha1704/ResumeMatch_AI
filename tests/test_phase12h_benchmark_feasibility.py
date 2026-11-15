"""
Tests for Phase 12H Dataset Provenance, Benchmark Feasibility, and Correction Register.
"""

import json
import os
import pytest


@pytest.fixture(scope="module")
def dataset_provenance_data():
    with open("experiments/phase12h/results/dataset_provenance_audit.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def benchmark_feasibility_data():
    with open("experiments/phase12h/results/benchmark_feasibility.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def correction_register_data():
    with open("experiments/phase12h/results/phase12g_correction_register.json") as f:
        return json.load(f)


def test_djinni_is_strictly_unpaired(dataset_provenance_data):
    """Verifies Djinni is documented as unpaired with 0 labelled pairs."""
    djinni = dataset_provenance_data["datasets"]["external_djinni_corpus"]
    assert djinni["pairing_status"] == "UNPAIRED / DUAL-MODALITY ONLY"
    assert djinni["labelled_pairs"] == 0
    assert djinni["supports_three_class"] is False


def test_primary_dataset_has_6_contradictions(dataset_provenance_data):
    """Verifies that primary dataset known contradictions and entity sparsity are recorded."""
    primary = dataset_provenance_data["datasets"]["primary_resumematch_corpus"]
    assert primary["total_pairs"] == 7999
    assert primary["unique_resumes"] == 643
    assert primary["unique_jobs"] == 351
    assert any("6 known exact-pair label contradictions" in issue for issue in primary["data_quality_issues"])


def test_power_calculation_sample_size(benchmark_feasibility_data):
    """Verifies that statistical power calculation establishes N >= 1,372 (1,500 recommended)."""
    power_calc = benchmark_feasibility_data["sample_size_power_calculation"]
    assert power_calc["calculated_minimum_sample_size_N"] == 1372
    assert power_calc["recommended_benchmark_size"] == 1500
    assert power_calc["power_target"] == 0.80
    assert power_calc["hypothesized_effect_size_delta"] == 0.04


def test_phase12g_corrections_registered(correction_register_data):
    """Verifies that all 6 required corrections are formally registered."""
    corrections = correction_register_data["corrections"]
    assert len(corrections) == 6
    corr_ids = [c["item_id"] for c in corrections]
    assert corr_ids == ["CORR-01", "CORR-02", "CORR-03", "CORR-04", "CORR-05", "CORR-06"]
    
    # Check latency correction
    latency_corr = next(c for c in corrections if c["item_id"] == "CORR-05")
    assert "39.23 ms" in latency_corr["corrected_statement"]
    
    # Check cross-encoder correction
    ce_corr = next(c for c in corrections if c["item_id"] == "CORR-01")
    assert "analytical projections" in ce_corr["corrected_statement"]
