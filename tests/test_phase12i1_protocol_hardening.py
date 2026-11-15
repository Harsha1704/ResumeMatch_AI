import json
import os
import hashlib
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_production_artifacts_unmodified():
    """Verify that models/best_model.joblib and feature_pipeline have not been modified."""
    best_model_path = os.path.join(WORKSPACE_ROOT, "models", "best_model.joblib")
    pipeline_path = os.path.join(WORKSPACE_ROOT, "models", "feature_pipeline.joblib")

    assert os.path.exists(best_model_path), "Production model missing!"
    assert os.path.exists(pipeline_path), "Feature pipeline missing!"

    with open(best_model_path, "rb") as f:
        best_model_hash = hashlib.sha256(f.read()).hexdigest().lower()
    with open(pipeline_path, "rb") as f:
        pipeline_hash = hashlib.sha256(f.read()).hexdigest().lower()

    # Exact audited SHA-256 hashes
    assert best_model_hash == "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"
    assert pipeline_hash == "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"

def test_clustered_power_sensitivity():
    """Verify the clustered power sensitivity simulation artifact."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "clustered_power_sensitivity.json")
    assert os.path.exists(json_path), "clustered_power_sensitivity.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == "12I.1"
    scenarios = data["scenarios_evaluated"]
    expected_scenarios = ["baseline", "optimistic_low_icc", "pessimistic_high_icc", "low_discordance", "high_discordance"]
    for s in expected_scenarios:
        assert s in scenarios, f"Scenario {s} missing from sensitivity analysis!"

    baseline = scenarios["baseline"]
    assert baseline["candidate_icc"] == 0.20
    assert baseline["job_icc"] == 0.10
    assert baseline["discordance_rate_PD"] == 0.28
    assert baseline["design_effect"] == 2.05
    assert baseline["power_at_sample_sizes"]["N_2850"]["power_simulated"] >= 0.80, "Baseline power at N=2850 should achieve at least 80%!"
    assert baseline["sample_size_requirements"]["power_80_percent"]["nominal_N"] <= 2850, "Required N for 80% power should be <= 2850!"

def test_annotation_rubric_v2():
    """Verify that Rubric V2 meets all qualitative and protocol requirements."""
    rubric_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I1_ANNOTATION_RUBRIC_V2.md")
    assert os.path.exists(rubric_path), "PHASE12I1_ANNOTATION_RUBRIC_V2.md missing!"

    with open(rubric_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify removal of hiring-action jargon
    assert "advance to hiring manager interview" not in content.lower()
    assert "fast-track to interview" not in content.lower()
    assert "definite hire" not in content.lower()

    # Verify structural sections
    assert "Mandatory Requirements (Hard Prerequisites)" in content
    assert "Preferred Qualifications (Aspirational / Bonus)" in content
    assert "Transferable Skills & Tech Stack Equivalence Matrix" in content
    assert "Seniority & Experience Shortfall Rubric" in content
    assert "Evidence Documentation Protocol for Annotators" in content

    # Verify 3 classes present
    assert "No Fit" in content
    assert "Potential Fit" in content
    assert "Good Fit" in content

def test_annotation_reliability_protocol():
    """Verify the inter-annotator reliability and quality assurance protocol."""
    proto_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "annotation_reliability_protocol.json")
    assert os.path.exists(proto_path), "annotation_reliability_protocol.json missing!"

    with open(proto_path, "r", encoding="utf-8") as f:
        proto = json.load(f)

    metrics = proto["metrics_specification"]
    assert "quadratic_weighted_cohen_kappa" in metrics
    assert metrics["quadratic_weighted_cohen_kappa"]["threshold_rejection"] == "< 0.70"
    assert "unweighted_cohen_kappa" in metrics

    # Pre-adjudication rule
    rule = proto["independence_architecture"]["cardinal_rule"]
    assert "pre-adjudication" in rule.lower()

    # Remediation
    remediation = proto["remediation_protocol"]
    assert len(remediation["trigger_conditions"]) >= 3
    assert len(remediation["corrective_workflow"]) >= 4

def test_benchmark_governance_audit():
    """Verify the benchmark governance, sampling strata, and quarantine rules."""
    gov_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "benchmark_governance_audit.json")
    assert os.path.exists(gov_path), "benchmark_governance_audit.json missing!"

    with open(gov_path, "r", encoding="utf-8") as f:
        gov = json.load(f)

    strat = gov["domain_stratification"]
    assert strat["total_target_sample_size"] == 2850
    assert strat["pilot_sample_size"] == 200

    total_prop = sum(s["proportion"] for s in strat["strata_breakdown"])
    assert pytest.approx(total_prop, 0.001) == 1.0

    total_target = sum(s["target_pairs"] for s in strat["strata_breakdown"])
    assert total_target == 2850

    total_pilot = sum(s["pilot_pairs"] for s in strat["strata_breakdown"])
    assert total_pilot == 200

    dedup = gov["deduplication_and_leakage_controls"]
    assert "MinHash LSH" in dedup["near_duplicate_algorithm"]
    assert dedup["cross_corpus_quarantine_verification"]["contamination_tolerance"] == 0

def test_protocol_hardening_report():
    """Verify the comprehensive audit report and verdict."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I1_PROTOCOL_HARDENING_REPORT.md")
    assert os.path.exists(report_path), "PHASE12I1_PROTOCOL_HARDENING_REPORT.md missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        report = f.read()

    assert "PILOT READY — PROTOCOL AND STATISTICAL ASSUMPTIONS SUFFICIENTLY DOCUMENTED" in report
    assert "Baseline Scenario" in report
    assert "Quadratic-Weighted Cohen's" in report
