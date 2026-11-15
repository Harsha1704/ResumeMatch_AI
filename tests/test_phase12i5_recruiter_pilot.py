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

def test_mathematical_correction_mj_star_and_deff():
    """Verify the corrected size-weighted mean cluster size and DEFF calculation."""
    # Check exact formula arithmetic:
    # 190 jobs with 7 pairs, 190 jobs with 8 pairs = 2850 pairs
    sum_m2 = 190 * (7**2) + 190 * (8**2)
    assert sum_m2 == 21470
    mj_star = sum_m2 / 2850.0
    assert pytest.approx(mj_star, 1e-5) == 7.533333

    # DEFF = 1 + (mc - 1)*icc_c + (mj* - 1)*icc_j
    icc_c = 0.142610
    icc_j = 0.075726
    deff_calc = 1.0 + (3.0 - 1.0) * icc_c + (mj_star - 1.0) * icc_j
    assert pytest.approx(deff_calc, 1e-4) == 1.7800

    # Verify JSON artifact matches
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i4_power_discrepancy_correction.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    math_data = data["discrepancy_investigation"]["mathematical_investigation"]
    assert pytest.approx(math_data["cluster_size_weighting"]["mj_star"], 1e-4) == 7.5333
    assert pytest.approx(math_data["recalculated_deff_values"]["formula_with_exact_mj_star"], 1e-4) == 1.7800

def test_finite_sample_reconciliation_explanation():
    """Verify the finite-sample crossed sampling explanation in report."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I5_STATISTICAL_CORRECTION.md")
    assert os.path.exists(report_path), "PHASE12I5_STATISTICAL_CORRECTION.md missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "7.533333" in content
    assert "1.7800" in content
    assert "Finite-Sample Permutation Geometry" in content
    assert "1.7305" in content

def test_three_icc_concepts_distinguished():
    """Verify that Recruiter-rating ICC, Adjudicated-label ICC, and Paired Correctness-Difference ICC are separated."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I5_STATISTICAL_CORRECTION.md")
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Recruiter-Rating ICC" in content
    assert "Adjudicated-Label ICC" in content
    assert "Paired Correctness-Difference ICC" in content
    assert "never" in content.lower()
    assert "substituted" in content.lower()

def test_recruiter_participation_roster():
    """Verify the recruiter cohort roster, pseudonyms, and blinding status."""
    part_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i5_recruiter_participation.json")
    assert os.path.exists(part_path), "phase12i5_recruiter_participation.json missing!"

    with open(part_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cohort = data["recruiter_cohort"]
    ids = [c["pseudonymous_id"] for c in cohort]
    assert "REC_A_892" in ids
    assert "REC_B_314" in ids
    assert "LEAD_ADJ_001" in ids

    assert data["governance_verification"]["zero_synthetic_recruiter_guarantee"] is True
    assert data["governance_verification"]["independent_blinded_evaluation"] is True

def test_annotation_progress_tracking():
    """Verify annotation progress accounting across 200 pairs and 5 strata."""
    prog_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i5_annotation_progress.json")
    assert os.path.exists(prog_path), "phase12i5_annotation_progress.json missing!"

    with open(prog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["progress_summary"]
    assert summary["total_benchmark_pairs"] == 200
    assert summary["required_independent_evaluations_per_pair"] == 2
    assert summary["total_required_ratings"] == 400

    strata = data["strata_completion_tracking"]
    assert strata["Software Engineering / Full-Stack / Backend"]["target_pairs"] == 80
    assert strata["DevOps / SRE / Cloud Infrastructure"]["target_pairs"] == 40
    assert strata["Data Science / Machine Learning / Data Engineering"]["target_pairs"] == 40
    assert strata["Quality Assurance / Test Automation"]["target_pairs"] == 20
    assert strata["Technical Product / Project Management"]["target_pairs"] == 20

def test_reliability_results_pre_adjudication_specification():
    """Verify reliability schema and pending status."""
    rel_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i5_reliability_results.json")
    assert os.path.exists(rel_path), "phase12i5_reliability_results.json missing!"

    with open(rel_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "PENDING_HUMAN_ANNOTATION_COMPLETION"
    assert data["metrics"]["quadratic_weighted_cohen_kappa"] is None
    assert data["quality_gate_thresholds"]["quadratic_weighted_kappa_gate"] == ">= 0.70 (Target >= 0.75)"

def test_final_verdict_awaiting_recruiters():
    """Verify official report verdict is PILOT READY — AWAITING RECRUITERS."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I5_RECRUITER_PILOT_LAUNCH_REPORT.md")
    assert os.path.exists(report_path), "PHASE12I5_RECRUITER_PILOT_LAUNCH_REPORT.md missing!"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "PILOT READY — AWAITING RECRUITERS" in content
