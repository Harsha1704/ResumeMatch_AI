"""
Tests for Phase 12I Benchmark Acquisition Protocol & Cluster Power Analysis.
"""

import json
import os
import pytest


@pytest.fixture(scope="module")
def dataset_count_data():
    with open("experiments/phase12i/results/dataset_count_reconciliation.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def power_analysis_data():
    with open("experiments/phase12i/results/cluster_adjusted_power_analysis.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def provenance_data():
    with open("experiments/phase12i/results/source_provenance_verification.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sampling_design_data():
    with open("experiments/phase12i/results/benchmark_sampling_design.json") as f:
        return json.load(f)


def test_dataset_count_reconciliation_total_8000(dataset_count_data):
    """Verifies that 6,241 train + 1,759 test sums to exactly 8,000 physical rows."""
    summary = dataset_count_data["reconciliation_summary"]
    assert summary["raw_train_rows"] == 6241
    assert summary["raw_test_rows"] == 1759
    assert summary["total_physical_rows"] == 8000
    assert summary["exact_pair_overlap_train_test"] == 0


def test_frozen_splits_inventory_includes_resume_disjoint(dataset_count_data):
    """Verifies all 7 frozen splits including resume_disjoint are documented."""
    splits = dataset_count_data["frozen_splits_inventory"]
    assert len(splits) == 7
    assert "resume_disjoint_train_v1" in splits
    assert "resume_disjoint_val_v1" in splits
    assert splits["resume_disjoint_train_v1"]["row_count"] == 5217
    assert splits["resume_disjoint_val_v1"]["row_count"] == 1023


def test_djinni_provenance_author_correction(provenance_data):
    """Verifies Djinni authorship corrected to Drushchak & Romanyshyn (UNLP @ LREC-COLING 2024)."""
    djinni = provenance_data["external_benchmarks_verified"]["djinni_dataset"]
    assert "Drushchak" in djinni["authors"]
    assert "Romanyshyn" in djinni["authors"]
    assert "CC BY 4.0" in djinni["license"]
    assert djinni["pairing_status"] == "UNPAIRED / DUAL-MODALITY ONLY"


def test_two_way_cluster_adjusted_power(power_analysis_data):
    """Verifies two-way design effect (DEFF=2.05) and recommended sample size (2,850 pairs)."""
    deff = power_analysis_data["provisional_design_evaluation"]["combined_two_way_deff"]
    assert deff == 2.05
    recs = power_analysis_data["cluster_adjusted_recommendations"]
    assert recs["recommended_nominal_pairs_N"] == 2816
    assert recs["sampling_topology_for_80_percent_power"]["total_pairs"] == 2850
    assert recs["sampling_topology_for_80_percent_power"]["minimum_unique_candidates"] >= 950
    assert recs["sampling_topology_for_80_percent_power"]["minimum_unique_jobs"] >= 380


def test_sampling_design_model_blind(sampling_design_data):
    """Verifies sampling design enforces model-blind selection and strict quarantine."""
    principles = sampling_design_data["sampling_architecture"]["sampling_principles"]
    assert any("MODEL-BLIND SAMPLING" in p for p in principles)
    quarantine = sampling_design_data["sampling_architecture"]["quarantine_and_isolation_rules"]
    assert "0% hash intersection" in quarantine["overlap_audit_with_internal_splits"]
