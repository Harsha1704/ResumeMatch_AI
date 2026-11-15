import json
import os
import hashlib
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_production_artifacts_unmodified():
    """Verify that models/best_model.joblib, feature_pipeline, and challenger have not been modified."""
    best_model_path = os.path.join(WORKSPACE_ROOT, "models", "best_model.joblib")
    pipeline_path = os.path.join(WORKSPACE_ROOT, "models", "feature_pipeline.joblib")
    challenger_path = os.path.join(WORKSPACE_ROOT, "models", "phase12f", "challenger_model_phase12f.joblib")

    assert os.path.exists(best_model_path), "Production model missing!"
    assert os.path.exists(pipeline_path), "Feature pipeline missing!"
    assert os.path.exists(challenger_path), "Challenger checkpoint missing!"

    with open(best_model_path, "rb") as f:
        best_data = f.read()
        assert len(best_data) == 61487
        assert hashlib.sha256(best_data).hexdigest().lower() == "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"

    with open(pipeline_path, "rb") as f:
        pipe_data = f.read()
        assert len(pipe_data) == 270105
        assert hashlib.sha256(pipe_data).hexdigest().lower() == "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"

    with open(challenger_path, "rb") as f:
        chal_data = f.read()
        assert len(chal_data) == 2330440
        assert hashlib.sha256(chal_data).hexdigest().lower() == "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766"

def test_power_discrepancy_reconciliation():
    """Verify the Phase 12I.4 power discrepancy correction artifact."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_power_discrepancy_correction.json")
    assert os.path.exists(json_path), "phase12i4_power_discrepancy_correction.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    math_data = data["discrepancy_investigation"]["mathematical_investigation"]
    assert pytest.approx(math_data["exact_manifest_icc_candidate"], 0.001) == 0.1426
    assert pytest.approx(math_data["exact_manifest_icc_job"], 0.001) == 0.0757
    assert pytest.approx(math_data["cluster_size_weighting"]["mj_star"], 0.001) == 7.5333
    assert pytest.approx(math_data["recalculated_deff_values"]["formula_with_exact_mj_star"], 0.01) == 1.7800

    iccs = data["distinction_of_three_icc_concepts"]
    assert "recruiter_rating_icc" in iccs
    assert "adjudicated_label_icc" in iccs
    assert "paired_correctness_difference_icc" in iccs
    assert "NEVER substitute" in iccs["cardinal_biostatistical_rule"]

    bound = data["power_bound_clarification"]
    assert bound["is_80_69_percent_a_guarantee"] is False

def test_pilot_sampling_manifest_topology():
    """Verify the frozen 200-pair pilot sampling manifest topology and constraints."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_pilot_sampling_manifest.json")
    assert os.path.exists(json_path), "phase12i4_pilot_sampling_manifest.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_pairs"] == 200
    assert data["total_unique_candidates"] == 120
    assert data["total_unique_jobs"] == 60

    stats = data["cluster_statistics"]
    assert stats["max_candidate_cluster"] <= 3
    assert stats["max_job_cluster"] <= 6

    dist = data["domain_distribution"]
    assert dist["Software Engineering / Full-Stack / Backend"] == 80
    assert dist["DevOps / SRE / Cloud Infrastructure"] == 40
    assert dist["Data Science / Machine Learning / Data Engineering"] == 40
    assert dist["Quality Assurance / Test Automation"] == 20
    assert dist["Technical Product / Project Management"] == 20

    pairs = data["pairs"]
    assert len(pairs) == 200
    c_counts = {}
    j_counts = {}
    for p in pairs:
        assert p["model_predictions_blinded"] is True
        assert p["peer_annotations_blinded"] is True
        c_counts[p["candidate_id"]] = c_counts.get(p["candidate_id"], 0) + 1
        j_counts[p["job_id"]] = j_counts.get(p["job_id"], 0) + 1

    assert max(c_counts.values()) <= 3
    assert max(j_counts.values()) <= 6

def test_annotator_reliability_schema():
    """Verify the annotator reliability specification and awaiting status."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_annotator_reliability.json")
    assert os.path.exists(json_path), "phase12i4_annotator_reliability.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["execution_status"] == "PILOT READY — AWAITING RECRUITERS"
    assert data["declaration_of_scientific_integrity"]["synthetic_data_fabricated"] is False

    formulas = data["pre_adjudication_reliability_pipeline"]["mathematical_formulas_verified"]
    assert "linear_weighted_kappa" in formulas
    assert "quadratic_weighted_kappa" in formulas
    assert "gwet_ac1" in formulas
    assert "specific_agreement" in formulas

    gates = data["pre_adjudication_reliability_pipeline"]["quality_gates"]
    assert gates["quadratic_weighted_kappa_gate"] == ">= 0.70"

def test_pilot_transport_analysis():
    """Verify the pilot-to-benchmark transportability analysis."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_pilot_transport_analysis.json")
    assert os.path.exists(json_path), "phase12i4_pilot_transport_analysis.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scaling = data["cluster_dimension_scaling"]
    assert scaling["pilot_topology"]["N"] == 200
    assert scaling["main_benchmark_topology"]["N"] == 2850

    matrix = data["conservative_transport_matrix"]
    assert len(matrix) >= 4
    for scenario in matrix:
        assert scenario["projected_benchmark_deff"] > scenario["pilot_deff"]

def test_onboarding_guide_and_operations_manual():
    """Verify the recruiter onboarding guide and annotation operations manual."""
    guide_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I4_ANNOTATOR_ONBOARDING_GUIDE.md")
    manual_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I4_ANNOTATION_OPERATIONS_MANUAL.md")

    assert os.path.exists(guide_path), "Onboarding guide missing!"
    assert os.path.exists(manual_path), "Operations manual missing!"

    with open(guide_path, "r", encoding="utf-8") as f:
        guide = f.read()

    assert "job_evidence_quote" in guide
    assert "mandatory_justification" in guide
    assert "resume_evidence_status" in guide
    assert "decision_rationale" in guide
    assert "Rule on Unstated Evidence" in guide
    assert "20.0% Boundary Rule" in guide

    with open(manual_path, "r", encoding="utf-8") as f:
        manual = f.read()

    assert "Double-Blind Independent Annotation with Senior Adjudication" in manual
    assert "Permanent Quarantine Policy" in manual

def test_quarantine_integrity():
    """Verify zero overlap with historical manifests and pilot quarantine."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_pilot_sampling_manifest.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["quarantine_and_blinding_status"]["historical_manifest_overlap_count"] == 0
    assert "permanently quarantined" in data["quarantine_and_blinding_status"]["quarantine_rule"]

def test_final_verdict_awaiting_recruiters():
    """Verify the execution report declares PILOT READY — AWAITING RECRUITERS."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I4_RECRUITER_PILOT_EXECUTION_REPORT.md")
    assert os.path.exists(report_path), "Execution report missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        report = f.read()

    assert "PILOT READY — AWAITING RECRUITERS" in report
