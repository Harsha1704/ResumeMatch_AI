"""
ResumeMatch AI — Phase 12I.12: Independent Multiway Bootstrap & Seed Provenance Verification Test Suite
Validates the pigeonhole bootstrap reproduction, analytical CRVE comparison,
finite-cluster correction audit, seed provenance reconciliation, and production preservation.
"""

import json
import hashlib
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE12I12_RESULTS = REPO_ROOT / "experiments" / "phase12i12" / "results"
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

    preservation_file = PHASE12I12_RESULTS / "production_preservation.json"
    assert preservation_file.exists()
    with open(preservation_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "VERIFIED_PRESERVED"


def test_pigeonhole_bootstrap_reproduction():
    """Verify reproduction of the Pigeonhole Bootstrap across 10,000 replicates."""
    file_path = PHASE12I12_RESULTS / "bootstrap_reproduction.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["replicate_count_B"] == 10000
    assert "Pigeonhole Bootstrap" in data["resampling_method"]
    assert data["fixed_random_seed"] == 42

    for comp_key in ["comparator_a_production_baseline", "comparator_b_raw_sbert"]:
        results = data["comparisons"][comp_key]
        assert len(results) == 5
        for s_id in ["42", "43", "44", "45", "46"]:
            assert s_id in results
            res = results[s_id]
            assert 5.0 <= res["bootstrap_se_pp"] <= 6.5
            assert res["ci_crosses_zero"] is True


def test_bootstrap_method_comparison():
    """Verify side-by-side comparison: Pigeonhole Bootstrap vs Analytical CGM 2-way CRVE."""
    file_path = PHASE12I12_RESULTS / "bootstrap_method_comparison.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for comp_key in ["comparator_a_production_baseline", "comparator_b_raw_sbert"]:
        results = data["comparisons"][comp_key]
        for s_id in ["42", "43", "44", "45", "46"]:
            res = results[s_id]
            # Boot SE is larger than CGM analytical SE
            assert res["pigeonhole_boot"]["se_pp"] > res["cgm_analytical_sandwich"]["se_pp"]
            assert 3.0 <= res["cgm_analytical_sandwich"]["se_pp"] <= 4.5
            assert 1.0 <= res["cgm_analytical_sandwich"]["design_effect"] <= 2.0
            assert 160.0 <= res["cgm_analytical_sandwich"]["effective_sample_size_neff"] <= 290.0


def test_finite_cluster_correction_audit():
    """Verify mathematical audit of the sqrt((C/(C-1))*(J/(J-1))) factor."""
    file_path = PHASE12I12_RESULTS / "finite_cluster_correction_audit.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert abs(data["combined_multiplier"] - 1.0153) < 0.001
    assert abs(data["percentage_inflation"] - 1.53) < 0.05
    assert data["methodological_verdict"] == "INAPPROPRIATE_FOR_BOOTSTRAP_DISPERSION"

    for entry in data["per_seed_comparison"].values():
        assert entry["both_cis_cross_zero"] is True


def test_seed_provenance_reconciliation():
    """Verify reconciliation of physical seeds (42-46) vs narrative seeds (123, 456, 789, 2024)."""
    file_path = PHASE12I12_RESULTS / "seed_provenance_matrix.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    investigation = data["investigation_summary"]
    assert investigation["provenance_classification"] == "UNRESOLVED_NARRATIVE_SUBSTITUTION_IN_PHASE_12I10"
    assert investigation["is_two_separate_experiment_families"] is False

    # Check verified physical seeds
    phys = data["verified_physical_seed_family_phase12i11"]
    assert len(phys) == 5
    for s_id in ["42", "43", "44", "45", "46"]:
        assert phys[s_id]["physical_artifact_exists_on_disk"] is True
        assert phys[s_id]["provenance_status"] == "VERIFIED_PHYSICAL_RUN"

    # Check narrative seeds
    narr = data["narrative_seed_family_phase12i10"]
    for s_id in ["123", "456", "789", "2024"]:
        assert narr[s_id]["physical_prediction_file_exists"] is False
        assert narr[s_id]["provenance_status"] == "SYNTHETIC_NARRATIVE_SEED_NO_PHYSICAL_DATA"


def test_comparator_reanalysis():
    """Verify reanalysis of Comparators A and B across all 5 physical seeds."""
    file_path = PHASE12I12_RESULTS / "comparator_reanalysis.json"
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data["comparators"]
    
    # Comparator A: Production Baseline (36.82%)
    comp_a = comps["comparator_a_production_baseline"]
    assert abs(comp_a["accuracy"] - 0.3682) < 0.001
    assert comp_a["correct_count"] == 109
    holm_a = comp_a["holm_family_evaluation"]
    sig_a_count = sum(1 for h in holm_a if h["significant_alpha_05"])
    assert sig_a_count == 4  # 4 of 5 seeds significant under unclustered paired test

    # Comparator B: Raw SBERT (38.18%)
    comp_b = comps["comparator_b_raw_sbert"]
    assert abs(comp_b["accuracy"] - 0.3818) < 0.001
    assert comp_b["correct_count"] == 113
    holm_b = comp_b["holm_family_evaluation"]
    sig_b_count = sum(1 for h in holm_b if h["significant_alpha_05"])
    assert sig_b_count == 0  # 0 of 5 seeds significant under Holm FWER


def test_deliverables_documentation_exist():
    """Verify Phase 12I.12 markdown documentation files exist and are populated."""
    docs = [
        "PHASE12I12_BOOTSTRAP_METHOD_AUDIT.md",
        "PHASE12I12_SEED_PROVENANCE_AUDIT.md",
        "PHASE12I12_FINAL_STATISTICAL_VERDICT.md",
    ]
    for doc in docs:
        doc_path = DOCS_DIR / doc
        assert doc_path.exists(), f"Missing doc: {doc}"
        assert doc_path.stat().st_size > 1000, f"Doc too small: {doc}"
