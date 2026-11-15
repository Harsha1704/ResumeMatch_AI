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

def test_cluster_transport_audit():
    """Verify the pilot vs main benchmark cluster transport audit."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i3_cluster_transport_audit.json")
    assert os.path.exists(json_path), "phase12i3_cluster_transport_audit.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pilot = data["design_comparison"]["pilot"]
    assert pilot["pairs_N"] == 200
    assert pilot["candidates_C"] == 120
    assert pilot["jobs_J"] == 60
    assert pytest.approx(pilot["design_effect_DEFF"], 0.01) == 1.37

    main = data["design_comparison"]["main_benchmark"]
    assert main["pairs_N"] == 2850
    assert main["candidates_C"] == 950
    assert main["jobs_J"] == 380
    assert pytest.approx(main["design_effect_DEFF"], 0.01) == 2.05

    transport = data["transportability_analysis"]
    assert "CANNOT BE DIRECTLY TRANSPORTED" in transport["core_finding"]
    assert len(transport["conservative_transport_protocol"]) >= 4

def test_null_calibration():
    """Verify empirical Type I error calibration under H0."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i3_null_calibration.json")
    assert os.path.exists(json_path), "phase12i3_null_calibration.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["null_hypothesis"] == "H0: Delta = 0.00"
    assert data["monte_carlo_iterations_B"] == 5000
    alpha = data["empirical_type_I_error"]
    assert 0.04 <= alpha <= 0.07, f"Empirical alpha {alpha} outside expected range [0.04, 0.07]!"
    ci = data["ci_95"]
    assert ci[0] <= 0.05 <= ci[1], "95% confidence interval must cover nominal alpha = 0.05!"
    assert data["calibration_verdict"] in ["WELL-CALIBRATED", "ACCEPTABLY_CALIBRATED"]

def test_power_discrepancy_resolution():
    """Verify the resolution of analytical vs simulated power discrepancy."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i3_power_validation.json")
    assert os.path.exists(json_path), "phase12i3_power_validation.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    res = data["discrepancy_resolution"]
    assert pytest.approx(res["analytical_latent_power"], 0.01) == 0.807
    assert pytest.approx(res["simulated_manifest_power"], 0.01) == 0.856
    assert "TETRACHORIC ATTENUATION" in res["mathematical_explanation"]
    assert "CONSERVATIVE lower bound" in res["auditor_recommendation"]

def test_kappa_verification_equivalence():
    """Verify kappa agreement vs disagreement weights equivalence and stress cases."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i3_kappa_verification.json")
    assert os.path.exists(json_path), "phase12i3_kappa_verification.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    proof = data["quadratic_weights_clarification"]["mathematical_equivalence_proof"]
    assert "mathematically identical" in proof

    cases = data["test_cases"]
    assert cases["perfect_agreement"]["unweighted_kappa"] == 1.0
    assert cases["perfect_agreement"]["quadratic_weighted_kappa"] == 1.0
    assert cases["complete_disagreement"]["unweighted_kappa"] < 0
    assert cases["skewed_prevalence_paradox"]["observed_agreement_P_o"] >= 0.95
    assert cases["skewed_prevalence_paradox"]["gwet_ac1"] >= 0.90

def test_rubric_v3_four_mandatory_fields():
    """Verify Annotation Rubric V3 Section 6.2 mandatory schema and unstated evidence protection."""
    rubric_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I2_ANNOTATION_RUBRIC_V3.md")
    assert os.path.exists(rubric_path), "PHASE12I2_ANNOTATION_RUBRIC_V3.md missing!"

    with open(rubric_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "job_evidence_quote" in content
    assert "mandatory_justification" in content
    assert "resume_evidence_status" in content
    assert "decision_rationale" in content
    assert "must not automatically be classified as confirmed absence" in content

def test_pilot_release_checklist():
    """Verify pilot release checklist and all operational safeguards."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i3_pilot_release_checklist.json")
    assert os.path.exists(json_path), "phase12i3_pilot_release_checklist.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    domain = data["domain_allocation_verified"]
    assert domain["total_pairs"] == 200
    assert domain["software_engineering"] == 80
    assert domain["devops_cloud"] == 40
    assert domain["data_ml"] == 40
    assert domain["qa_automation"] == 20
    assert domain["product_project_management"] == 20

    guards = data["safeguard_checks"]
    assert len(guards) == 6
    for g in guards:
        assert g["status"] == "PASS", f"Guard {g['guard_id']} failed!"

def test_final_verdict_certified():
    """Verify the formal certification report exists and declares PILOT READY."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I3_FINAL_STATISTICAL_VERIFICATION.md")
    assert os.path.exists(report_path), "PHASE12I3_FINAL_STATISTICAL_VERIFICATION.md missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "PILOT READY — SOURCE-CODE, MATHEMATICS & OPERATIONAL SAFEGUARDS FULLY CERTIFIED" in content
