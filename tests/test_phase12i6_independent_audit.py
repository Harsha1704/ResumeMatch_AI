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

def test_deff_reconciliation_mathematical_derivation():
    """Verify the exact crossed-cluster derivation, incidence structure, and theoretical DEFF."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i6_deff_reconciliation.json")
    assert os.path.exists(json_path), "phase12i6_deff_reconciliation.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    inc = data["exact_incidence_structure"]
    assert inc["total_pairs_N"] == 2850
    assert inc["total_candidates_C"] == 950
    assert inc["total_jobs_J"] == 380
    assert inc["candidate_size_weighted_mc_star"] == 3.0
    assert inc["job_allocation"]["jobs_with_7_pairs"] == 190
    assert inc["job_allocation"]["jobs_with_8_pairs"] == 190
    assert pytest.approx(inc["job_allocation"]["size_weighted_mj_star"], 1e-5) == 7.533333

    cov = data["exact_covariance_parameters"]
    assert cov["manifest_icc_candidate"] == 0.142610
    assert cov["manifest_icc_job"] == 0.075726
    assert cov["candidate_job_interaction_covariance"] == 0.0
    assert cov["unshared_pair_population_covariance"] == 0.0

    theo = data["theoretical_derivation"]
    assert pytest.approx(theo["exact_theoretical_deff"], 1e-4) == 1.7800
    assert theo["documented_formula_deff_rounded"] == 1.7800

def test_monte_carlo_uncertainty_reconciliation():
    """Verify that reported 1.7367 is consistent with Monte Carlo standard error."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i6_deff_reconciliation.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rec = data["empirical_reconciliation"]
    assert rec["reported_value_phase12i4"] == 1.7367
    assert pytest.approx(rec["standard_error_at_b5000"], 0.001) == 0.0356
    assert pytest.approx(rec["z_score"], 0.01) == -1.2152
    assert pytest.approx(rec["two_sided_p_value"], 0.01) == 0.2243
    assert "STATISTICAL RECONCILIATION PASSED" in rec["reconciliation_verdict"]

def test_high_precision_resimulation_convergence():
    """Verify B=10,000 resimulation coverage and confidence intervals."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i6_monte_carlo_uncertainty.json")
    assert os.path.exists(json_path), "phase12i6_monte_carlo_uncertainty.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sim = data["simulation_parameters"]
    assert sim["replications_B"] == 10000
    assert sim["sample_size_N"] == 2850

    dist = data["deff_sampling_distribution"]
    assert pytest.approx(dist["theoretical_deff"], 1e-4) == 1.7800
    assert pytest.approx(dist["empirical_deff"], 0.02) == 1.7800
    assert dist["contains_theoretical_deff"] is True
    ci95 = dist["ci_95"]
    assert ci95[0] <= dist["theoretical_deff"] <= ci95[1]

def test_three_separate_iccs_preserved():
    """Verify that three separate ICC concepts are tracked in reconciliation report."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I6_INDEPENDENT_STATISTICAL_RECONCILIATION.md")
    assert os.path.exists(report_path), "Reconciliation report missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Recruiter-Rating ICC" in content
    assert "Adjudicated-Label ICC" in content
    assert "Paired Correctness-Difference ICC" in content
    assert "used as a proxy" in content.lower()

def test_recruiter_participation_verification():
    """Verify recruiter roster verification, qualifications, and zero invention guarantee."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i6_recruiter_verification.json")
    assert os.path.exists(json_path), "phase12i6_recruiter_verification.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    roster = data["evaluator_roster"]
    r_map = {r["pseudonymous_id"]: r for r in roster}
    assert "REC_A_892" in r_map
    assert "REC_B_314" in r_map
    assert "LEAD_ADJ_001" in r_map

    assert r_map["REC_A_892"]["actual_submitted_annotations"] == 0
    assert r_map["REC_B_314"]["actual_submitted_annotations"] == 0
    assert data["verification_policy"]["zero_invention_rule"] is not None

def test_pilot_handoff_package_topology():
    """Verify pilot handoff package status and queue architecture."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i6_pilot_handoff_status.json")
    assert os.path.exists(json_path), "phase12i6_pilot_handoff_status.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["handoff_specification"]["total_pairs"] == 200
    assert data["handoff_specification"]["unique_candidates"] == 120
    assert data["handoff_specification"]["unique_jobs"] == 60
    assert data["handoff_specification"]["total_independent_ratings_target"] == 400
    assert data["handoff_status"] == "READY_FOR_DISTRIBUTION"

def test_final_verdict_reconciliation_passed():
    """Verify official report verdict is STATISTICAL RECONCILIATION PASSED — PILOT HANDOFF READY."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I6_RECRUITER_HANDOFF_REPORT.md")
    assert os.path.exists(report_path), "Handoff report missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "STATISTICAL RECONCILIATION PASSED — PILOT HANDOFF READY" in content
