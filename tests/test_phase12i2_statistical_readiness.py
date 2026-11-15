import json
import os
import hashlib
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_production_artifacts_unmodified():
    """Verify that models/best_model.joblib and feature_pipeline have not been modified."""
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

def test_power_simulation_reproducibility():
    """Verify independent power reproduction artifact."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i2_power_reproduction.json")
    assert os.path.exists(json_path), "phase12i2_power_reproduction.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    params = data["simulation_parameters"]
    assert params["B"] == 2000
    assert params["alpha"] == 0.05
    assert "Two-way cluster-robust" in params["test_type"]

    scenarios = data["core_scenarios"]
    for s in ["Baseline", "Optimistic", "Pessimistic", "Low_Discordance", "High_Discordance"]:
        assert s in scenarios, f"Scenario {s} missing from reproduction!"

    baseline_2850 = scenarios["Baseline"]["N_2850"]
    assert baseline_2850["power_simulated"] >= 0.80, "Baseline at N=2850 must achieve at least 80% power!"
    assert baseline_2850["n_candidates"] == 950
    assert baseline_2850["n_jobs"] == 380

    assert "unequal_clusters_scenario" in data

def test_adaptive_sample_size_logic():
    """Verify the corrected simulation-based adaptive sample size plan."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i2_adaptive_sample_size.json")
    assert os.path.exists(json_path), "phase12i2_adaptive_sample_size.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    critique = data["critique_of_phase12i1_rule"]
    assert "3,500" in critique["previous_rule"]
    assert "flaw_identified" in critique

    recs = data["recommendation_summary"]
    assert recs["provisional_target"] == 2850
    assert recs["provisional_unique_candidates"] == 950
    assert recs["provisional_unique_jobs"] == 380
    assert recs["expansion_reserve_tier_2"] == 3800
    assert recs["stress_test_ceiling_tier_3"] == 5000

    scenarios = data["scenario_evaluations"]
    for s_name, s_data in scenarios.items():
        assert "requirements_for_80_percent_power" in s_data
        assert "requirements_for_90_percent_power" in s_data
        assert s_data["requirements_for_80_percent_power"]["total_pairs_N"] > 0
        assert s_data["requirements_for_90_percent_power"]["total_pairs_N"] > s_data["requirements_for_80_percent_power"]["total_pairs_N"]

def test_rubric_v3_hardened_boundaries():
    """Verify Annotation Rubric V3 definitions, seniority boundaries, and advisory weights."""
    rubric_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I2_ANNOTATION_RUBRIC_V3.md")
    assert os.path.exists(rubric_path), "PHASE12I2_ANNOTATION_RUBRIC_V3.md missing!"

    with open(rubric_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify no downstream hiring actions
    assert "advance to hiring manager interview" not in content.lower()
    assert "definite hire" not in content.lower()
    assert "fast-track to interview" not in content.lower()

    # Seniority boundary rules
    assert "20.0" in content
    assert "compensating seniority evidence" in content
    assert "Years of experience do NOT independently establish seniority" in content

    # Transferable skills advisory nature
    assert "advisory guidelines, NOT universal or automatic" in content

    # Check that 6 case examples exist
    assert "Example 1: Clear-Cut Good Fit" in content
    assert "Example 2: Borderline Good Fit" in content
    assert "Example 3: Borderline Potential Fit" in content
    assert "Example 4: Transferable Skill Potential Fit" in content
    assert "Example 5: Non-Transferable Disqualification" in content
    assert "Example 6: Ambiguous / Insufficient Evidence Case" in content

def test_reliability_audit_mathematics():
    """Verify reliability audit metrics, pre-adjudication calculation, and paradox disclosures."""
    audit_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i2_reliability_audit.json")
    assert os.path.exists(audit_path), "phase12i2_reliability_audit.json missing!"

    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Pre-adjudication rule
    rule = data["original_rating_preservation_architecture"]["cardinal_protocol_rule"]
    assert "raw_label" in rule
    assert "strictly prohibited" in rule.lower()

    # Quadratic kappa
    metrics = data["mathematical_metric_specifications"]
    assert "quadratic_weighted_cohen_kappa" in metrics
    w_mat = metrics["quadratic_weighted_cohen_kappa"]["weight_matrix"]
    assert w_mat[0][2] == 1.0
    assert w_mat[0][1] == 0.25

    # Paradoxes documented
    paradoxes = data["paradoxes_and_limitations_of_kappa"]
    assert "prevalence_paradox_feinstein_cicchetti_1" in paradoxes
    assert "bias_paradox_feinstein_cicchetti_2" in paradoxes

    # Remediation
    remed = data["remediation_protocols"]
    assert "scenario_low_weighted_kappa" in remed
    assert "scenario_excessive_severe_disagreement" in remed

def test_pilot_execution_plan_safeguards():
    """Verify pilot sample quotas, blinding safeguards, and quarantine."""
    plan_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i2_pilot_execution_plan.json")
    assert os.path.exists(plan_path), "phase12i2_pilot_execution_plan.json missing!"

    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["pilot_sample_design"]["total_pilot_pairs"] == 200
    alloc = data["pilot_sample_design"]["domain_allocation"]
    quota_dict = {a["stratum"]: a["quota"] for a in alloc}
    assert sum(quota_dict.values()) == 200
    assert quota_dict["Software Engineering / Full-Stack / Backend"] == 80
    assert quota_dict["DevOps / SRE / Cloud Infrastructure"] == 40
    assert quota_dict["Data Science / Machine Learning / Data Engineering"] == 40
    assert quota_dict["Quality Assurance / Test Automation"] == 20
    assert quota_dict["Technical Product / Project Management"] == 20

    # Permanent quarantine of pilot pairs
    isolation = data["pilot_quarantine_and_isolation_policy"]["cardinal_isolation_rule"]
    assert "PERMANENTLY QUARANTINED" in isolation

    # Awaiting annotators disclosure
    status = data["human_annotation_readiness_status"]
    assert status["execution_status"] == "AWAITING HUMAN ANNOTATOR ONBOARDING"

def test_contamination_privacy_framework():
    """Verify multi-layered contamination checks and privacy risk-reduction framing."""
    audit_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i2_contamination_privacy_audit.json")
    assert os.path.exists(audit_path), "phase12i2_contamination_privacy_audit.json missing!"

    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    layers = data["multi_layered_leakage_detection"]["detection_layers"]
    layer_names = [l["layer_name"] for l in layers]
    assert "Exact Pair Identifier Matching" in layer_names
    assert "Normalized Text SHA-256 Hashing" in layer_names
    assert "MinHash LSH Near-Duplicate Detection" in layer_names
    assert "Manual Review of Suspicious Matches" in layer_names

    framing = data["privacy_and_deidentification_framework"]["philosophical_framing"]
    assert "RISK REDUCTION" in framing

def test_final_verdict_certified():
    """Verify the formal certification report exists and declares PILOT READY."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I2_STATISTICAL_REPRODUCTION_REPORT.md")
    assert os.path.exists(report_path), "PHASE12I2_STATISTICAL_REPRODUCTION_REPORT.md missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "PILOT READY — PROTOCOL, STATISTICAL POWER & SAFEGUARDS RIGOROUSLY CERTIFIED" in content
