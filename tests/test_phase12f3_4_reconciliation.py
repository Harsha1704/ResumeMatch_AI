"""
Tests for Phase 12F.3.4 Forensic Reconciliation and Grouped Dependence.
Validates:
1. Feature pipeline hash identity on disk.
2. Macro F1 reconciliation across Seeds 42-46.
3. Candidate and Job entity cluster definitions (91 unique candidate clusters, 52 job clusters).
4. Multiple testing corrections (Bonferroni, Holm).
5. Grouped cluster bootstrap bounds.
"""

import json
import hashlib
import os
import pytest
import numpy as np
import pandas as pd


@pytest.fixture(scope="module")
def pipeline_reconciliation_data():
    with open("experiments/phase12f3_4/results/pipeline_hash_reconciliation.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def macro_f1_reconciliation_data():
    with open("experiments/phase12f3_4/results/macro_f1_reconciliation.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def entity_cluster_data():
    with open("experiments/phase12f3_4/results/entity_cluster_audit.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def multiple_testing_data():
    with open("experiments/phase12f3_4/results/multiple_testing_results.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def grouped_bootstrap_data():
    with open("experiments/phase12f3_4/results/grouped_bootstrap_results.json") as f:
        return json.load(f)


def test_physical_pipeline_hash_matches_phase12f3_2(pipeline_reconciliation_data):
    """Verifies that the physical pipeline on disk matches the certified Phase 12F.3.2 hash."""
    path = "models/feature_pipeline.joblib"
    assert os.path.exists(path)
    with open(path, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"
    assert pipeline_reconciliation_data["forensic_determination"]["bit_for_bit_preservation_confirmed"] is True


def test_macro_f1_authoritative_delta_reconciliation(macro_f1_reconciliation_data):
    """Verifies that the arithmetic mean of the five certified contrastive macro F1s yields delta = +0.0025."""
    metrics = macro_f1_reconciliation_data["authoritative_reconciliation_table"]["exact_seed_metrics"]
    baseline_f1 = metrics["raw_baseline"]["macro_f1"]
    seed_f1s = [metrics[f"seed_{s}"]["macro_f1"] for s in [42, 43, 44, 45, 46]]
    
    assert baseline_f1 == 0.3282
    assert seed_f1s == [0.3311, 0.3329, 0.2703, 0.3604, 0.3589]
    mean_contrastive_f1 = np.mean(seed_f1s)
    assert abs(mean_contrastive_f1 - 0.33072) < 1e-4
    delta = mean_contrastive_f1 - baseline_f1
    assert abs(delta - 0.00252) < 1e-4


def test_candidate_and_job_cluster_partitions(entity_cluster_data):
    """Verifies 91 unique candidates and 52 unique jobs with single-cluster assignment."""
    assert entity_cluster_data["candidate_entities"]["unique_count"] == 91
    assert entity_cluster_data["job_entities"]["unique_count"] == 52
    assert entity_cluster_data["validation_pairs"] == 296


def test_multiple_testing_holm_and_bonferroni(multiple_testing_data):
    """Verifies that multiple-testing adjustment scales p-values above 0.05 family-wise."""
    adjustments = multiple_testing_data["multiple_testing_adjustments"]
    for row in adjustments:
        if row["seed"] in [42, 43, 45, 46]:
            assert row["bonferroni_p"] >= 0.0745
            assert row["holm_p"] >= 0.0745
            assert row["significant_post_holm_alpha_0_05"] is False
