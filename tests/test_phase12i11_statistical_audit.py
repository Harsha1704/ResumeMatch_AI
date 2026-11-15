"""
ResumeMatch AI — Phase 12I.11: Statistical Audit & Comparator Verification Test Suite
Validates comparator separation, prediction provenance, Holm corrections,
multiway cluster bootstrap verification, official test quarantine, and checkpoint preservation.
"""

import json
import hashlib
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE12I11_RESULTS = REPO_ROOT / "experiments" / "phase12i11" / "results"
DOCS_DIR = REPO_ROOT / "docs" / "research"

EXPECTED_PRODUCTION_HASHES = {
    "models/best_model.joblib": {
        "size": 61487,
        "sha256": "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a",
    },
    "models/feature_pipeline.joblib": {
        "size": 270105,
        "sha256": "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6",
    },
    "models/phase12f/challenger_model_phase12f.joblib": {
        "size": 2330440,
        "sha256": "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766",
    },
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_production_checkpoints_preserved():
    """Verify production baseline and challenger models are strictly unmodified."""
    for rel_path, expected in EXPECTED_PRODUCTION_HASHES.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.exists(), f"Missing file: {rel_path}"
        assert full_path.stat().st_size == expected["size"], f"Size mismatch for {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected["sha256"], f"Hash mismatch for {rel_path}"

    preservation_file = PHASE12I11_RESULTS / "production_preservation.json"
    assert preservation_file.exists()
    with open(preservation_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "VERIFIED_PRESERVED"


def test_prediction_provenance_and_alignment():
    """Verify prediction file provenance, row alignment, and model identities."""
    file_path = PHASE12I11_RESULTS / "prediction_provenance.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evaluated_rows"] == 296
    align = data["alignment_verification"]
    assert align["pair_order_identical_across_all_files"] is True
    assert align["resume_text_hash_match"] is True
    assert align["job_text_hash_match"] is True
    assert align["ground_truth_labels_match"] is True

    # Check baseline and comparator metrics
    models = data["baseline_and_comparator_models"]
    assert models["production_baseline"]["correct_predictions"] == 109
    assert abs(models["production_baseline"]["accuracy"] - 0.3682) < 0.001

    assert models["raw_sbert"]["correct_predictions"] == 113
    assert abs(models["raw_sbert"]["accuracy"] - 0.3818) < 0.001

    assert models["hybrid_stacking"]["correct_predictions"] == 124
    assert abs(models["hybrid_stacking"]["accuracy"] - 0.4189) < 0.001

    # Check seeds count
    seeds = data["contrastive_seeds"]
    assert len(seeds) == 5
    for s_id in ["42", "43", "44", "45", "46"]:
        assert s_id in seeds
        assert seeds[s_id]["total_examples"] == 296


def test_production_comparator_analysis():
    """Verify Comparison A: Contrastive Seeds vs Production Baseline (36.82%)."""
    file_path = PHASE12I11_RESULTS / "production_comparator_analysis.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["comparator_accuracy"] == 0.3682
    assert data["comparator_correct_count"] == 109
    assert data["evaluation_pairs_N"] == 296

    results = data["per_seed_results"]
    assert len(results) == 5

    # Check Seed 42 vs Baseline: +9.12% (136 vs 109), b=29, c=56
    s42 = results["42"]
    assert s42["baseline_only_correct_b"] == 29
    assert s42["challenger_only_correct_c"] == 56
    assert s42["discordant_pairs"] == 85
    assert s42["paired_accuracy_difference_pp"] == 9.12
    assert abs(s42["mcnemar_chi2_corrected"] - 7.9529) < 0.01
    assert s42["mcnemar_exact_p_value_two_sided"] < 0.005

    # Check bootstrap CIs cross zero for all seeds
    for s_id, s_data in results.items():
        assert 0.04 <= s_data["bootstrap_standard_error"] <= 0.07
        assert s_data["ci_crosses_zero"] is True


def test_raw_sbert_comparator_analysis():
    """Verify Comparison B: Contrastive Seeds vs Raw SBERT (38.18%)."""
    file_path = PHASE12I11_RESULTS / "raw_sbert_comparator_analysis.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["comparator_accuracy"] == 0.3818
    assert data["comparator_correct_count"] == 113
    assert data["evaluation_pairs_N"] == 296

    results = data["per_seed_results"]
    assert len(results) == 5

    # Check Seed 42 vs Raw SBERT: +7.77% (136 vs 113), b=30, c=53
    s42 = results["42"]
    assert s42["raw_only_correct_b"] == 30
    assert s42["challenger_only_correct_c"] == 53
    assert s42["discordant_pairs"] == 83
    assert s42["paired_accuracy_difference_pp"] == 7.77
    assert abs(s42["mcnemar_chi2_corrected"] - 5.8313) < 0.01
    assert abs(s42["mcnemar_exact_p_value_two_sided"] - 0.015232) < 0.001

    # Check bootstrap CIs cross zero for all seeds
    for s_id, s_data in results.items():
        assert 0.04 <= s_data["bootstrap_standard_error"] <= 0.07
        assert s_data["ci_crosses_zero"] is True


def test_holm_correction_separate_families():
    """Verify Holm-Bonferroni correction on separate comparator families."""
    file_path = PHASE12I11_RESULTS / "holm_correction.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    families = data["families"]
    assert "family_a_production_baseline" in families
    assert "family_b_raw_sbert" in families

    fam_a = families["family_a_production_baseline"]
    assert fam_a["family_size_m"] == 5
    assert fam_a["fwer_pass_count"] == 4
    # Top rank in A has adjusted p < 0.05
    assert fam_a["sorted_hypotheses"][0]["holm_adjusted_p"] < 0.05

    fam_b = families["family_b_raw_sbert"]
    assert fam_b["family_size_m"] == 5
    assert fam_b["fwer_pass_count"] == 0
    # Top rank in B has adjusted p > 0.05 (0.0743)
    assert fam_b["sorted_hypotheses"][0]["holm_adjusted_p"] > 0.05


def test_bootstrap_method_verification():
    """Verify Cameron-Gelbach-Miller two-way cluster bootstrap audit findings."""
    file_path = PHASE12I11_RESULTS / "bootstrap_method_verification.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    audit = data["forensic_methodological_checks"]
    assert audit["crossed_cluster_resampling_verified"] is True
    assert audit["paired_prediction_alignment_preserved"] is True
    assert audit["candidate_job_incidence_structure_preserved"] is True
    assert audit["convergence_and_degenerate_replicates"]["degenerate_replicates_sum_w_zero"] == 0
    assert audit["convergence_and_degenerate_replicates"]["failed_replicates"] == 0

    assert data["verdict_on_bootstrap_integrity"] == "METHODOLOGICALLY_DEFENSIBLE_AND_REPRODUCED"


def test_official_test_quarantine_policy():
    """Verify official test quarantine rules and historical exposure records."""
    file_path = PHASE12I11_RESULTS / "official_test_quarantine.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["quarantine_policy"]["status"] == "PERMANENTLY_QUARANTINED"
    assert data["operational_classification"] == "HISTORICAL_DESCRIPTIVE_ONLY_NOT_CERTIFIED_BENCHMARK"

    # Verify 6 sequential configurations documented
    seq = data["historical_sequential_evaluations"]
    assert len(seq) == 6
    configs = [c["configuration_id"] for c in seq]
    assert "EXP-12F-SUP:logistic_regression" in configs
    assert "EXP-12F-SUP:hybrid_stacking" in configs
    assert "EXP-12F-WEAK" in configs
    assert "EXP-12F-SSDA" in configs
    assert "EXP-12F-PSEUDO" in configs
    assert "EXP-12F-COMBINED" in configs

    # Verify leakage differentiation
    leak = data["leakage_taxonomy_and_differentiation"]
    assert leak["direct_label_leakage"]["occurred"] is False
    assert leak["adaptive_test_reuse_bias"]["occurred"] is True


def test_documentation_deliverables_exist():
    """Verify Phase 12I.11 markdown documentation files exist and are populated."""
    docs = [
        "PHASE12I11_FINAL_STATISTICAL_AUDIT.md",
        "PHASE12I11_OFFICIAL_TEST_QUARANTINE.md",
        "PHASE12I11_FUTURE_EVALUATION_PROTOCOL.md",
    ]
    for doc in docs:
        doc_path = DOCS_DIR / doc
        assert doc_path.exists(), f"Missing doc: {doc}"
        assert doc_path.stat().st_size > 1000, f"Doc too small: {doc}"
