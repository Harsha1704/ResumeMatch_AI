"""
ResumeMatch AI — Phase 12I.10: Final Evidence Audit & Benchmark Certification Test Suite
Validates the statistical corrections, split provenance audit, bootstrap estimates,
pseudo-label leakage classification, and production preservation.
"""

import json
import hashlib
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE12I10_RESULTS = REPO_ROOT / "experiments" / "phase12i10" / "results"
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


def test_production_artifacts_preserved():
    """Verify production and challenger models are strictly unmodified."""
    for rel_path, expected in EXPECTED_PRODUCTION_HASHES.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.exists(), f"Missing file: {rel_path}"
        assert full_path.stat().st_size == expected["size"], f"Size mismatch for {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected["sha256"], f"Hash mismatch for {rel_path}"

    preservation_file = PHASE12I10_RESULTS / "production_preservation.json"
    assert preservation_file.exists()
    with open(preservation_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["verification_verdict"] == "VERIFIED_PERFECT_PRESERVATION"
    assert data["production_governance"]["promotion_permitted"] is False


def test_seed_significance_corrected():
    """Verify McNemar paired tests, Holm-Bonferroni correction, and Fisher rejection."""
    file_path = PHASE12I10_RESULTS / "seed_significance_corrected.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evaluation_dataset"]["evaluated_rows"] == 296
    assert len(data["per_seed_paired_evaluations"]) == 5

    # Check Holm adjustment narrative and values
    method = data["methodological_corrections"]
    holm_text = method["holm_multiple_testing_correction"]
    assert "0.0743" in holm_text
    assert "alpha=0.05" in holm_text
    assert "none pass strict family-wise error rate control" in holm_text

    # Check Fisher combined rejection
    assert method["fisher_combined_pvalue_status"] == "PERMANENTLY_INVALIDATED"


def test_paired_two_way_bootstrap():
    """Verify Cameron-Gelbach-Miller two-way cluster bootstrap results."""
    file_path = PHASE12I10_RESULTS / "paired_two_way_bootstrap.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    methodology = data["methodology"]
    assert methodology["replicate_count_B"] == 10000
    assert methodology["candidate_clusters_C"] == 91
    assert methodology["job_clusters_J"] == 52

    # Verify SE and 95% CIs cross zero for all seeds
    for res in data["per_seed_bootstrap_results"]:
        assert 4.0 <= res["bootstrap_standard_error_pp"] <= 7.0, f"Bootstrap SE out of expected bounds: {res}"
        ci_lower, ci_upper = res["ci_95_percentile_percentage_points"]
        assert ci_lower < 0.0 < ci_upper, f"95% CI does not cross zero: [{ci_lower}, {ci_upper}]"
        assert res["zero_included_in_ci"] is True


def test_official_test_entity_provenance():
    """Verify 476/477 resume overlap reconciliation and job-disjoint classification."""
    file_path = PHASE12I10_RESULTS / "official_test_entity_provenance.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    held_out = data["held_out_test_provenance"]
    assert held_out["record_count"] == 1759
    assert held_out["unique_resumes"] == 477
    assert held_out["unique_jobs"] == 71

    overlap = data["exact_overlap_quantification"]
    assert overlap["job_description_hashes"]["overlapping_jobs_count"] == 0
    assert overlap["job_description_hashes"]["overlapping_jobs_percentage"] == 0.0
    assert overlap["resume_text_hashes"]["overlapping_resumes_count"] == 476
    assert overlap["resume_text_hashes"]["overlapping_resumes_percentage"] == 99.79
    assert overlap["exact_resume_job_pair_hashes"]["overlapping_pairs_count"] == 0
    assert overlap["exact_resume_job_pair_hashes"]["overlapping_pairs_percentage"] == 0.0

    verdict = data["protocol_classification_verdict"]
    desig = verdict["protocol_designation"].lower().replace("_", "-")
    assert "job-disjoint" in desig
    assert verdict["is_dual_unseen"] is False
    assert verdict["is_job_disjoint"] is True


def test_architecture_and_4764_attribution():
    """Verify 47.64% attribution and withdrawal of deep cross-encoder claim."""
    file_path = PHASE12I10_RESULTS / "architecture_and_4764_attribution.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "47.64%" in data["audited_metric"]["metric_value"]

    rec = data["reconstructed_evaluation_procedure"]
    assert rec["mean_selected_tau"] == 0.15

    disjoint = data["fold_disjointness_forensic_audit"]
    assert disjoint["is_candidate_disjoint"] is True
    assert disjoint["is_job_disjoint_across_folds"] is False
    assert "candidate_disjoint_oof" in disjoint["disjointness_verdict"].lower()

    arch = data["architecture_attribution_verdict"]
    assert arch["standalone_cross_encoder_checkpoint_exists"] is False
    assert "withdrawn" in arch["deep_cross_encoder_attribution"].lower()


def test_pseudo_label_test_leakage_audit():
    """Verify EXP-12F-PSEUDO audit and exploratory classification."""
    file_path = PHASE12I10_RESULTS / "pseudo_label_test_leakage_audit.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["reported_held_out_test_accuracy"] == 0.5026
    assert data["direct_leakage_audit"]["direct_test_label_leakage"] is False
    assert data["direct_leakage_audit"]["test_entity_overlap"] == 0
    assert data["indirect_leakage_audit"]["adaptive_test_reuse"] is True
    assert data["scientific_classification"] == "EXPLORATORY PSEUDO-LABELING RESEARCH"
    assert data["certified_status"] == "WITHDRAWN_AS_BENCHMARK_ESTIMATE"


def test_canonical_benchmark_reconciliation():
    """Verify canonical reconciliation of all 4 protocols and overall verdict."""
    file_path = PHASE12I10_RESULTS / "canonical_benchmark_reconciliation.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    benchmarks = data["benchmarks"]
    assert "held_out_test" in benchmarks
    assert "dual_unseen_val" in benchmarks
    assert "job_disjoint_val" in benchmarks
    assert "resume_disjoint_val" in benchmarks

    # Baseline accuracies
    assert benchmarks["held_out_test"]["baseline_metrics"]["accuracy"] == 0.4861
    assert benchmarks["dual_unseen_val"]["baseline_metrics"]["accuracy"] == 0.3682
    assert benchmarks["job_disjoint_val"]["baseline_metrics"]["accuracy"] == 0.7416
    assert benchmarks["resume_disjoint_val"]["baseline_metrics"]["accuracy"] == 0.7771

    # Overall verdict
    assert data["overall_verdict"] == "CONDITIONALLY CERTIFIED — SPECIFIC CLAIMS REQUIRE CORRECTION"


def test_documentation_deliverables_exist():
    """Verify that all Phase 12I.10 markdown documentation files exist and are populated."""
    docs = [
        "PHASE12I10_FINAL_EVIDENCE_AUDIT.md",
        "PHASE12I10_CORRECTION_REGISTER.md",
        "PHASE12I10_BENCHMARK_CERTIFICATION.md",
    ]
    for doc in docs:
        doc_path = DOCS_DIR / doc
        assert doc_path.exists(), f"Missing doc: {doc}"
        assert doc_path.stat().st_size > 500, f"Doc too small: {doc}"
