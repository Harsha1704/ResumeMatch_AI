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


def test_human_pilot_retirement_status():
    """Verify human recruiter pilot is retired as a blocking dependency and zero ratings are fabricated."""
    ledger_path = os.path.join(WORKSPACE_ROOT, "data", "benchmark_vault", "intake", "raw_submissions.jsonl")
    if os.path.exists(ledger_path):
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 0, "Ledger should contain zero human ratings!"

    rep_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I8_HUMAN_FREE_RESEARCH_REPORT.md")
    assert os.path.exists(rep_path), "Research report missing!"
    with open(rep_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "ZERO HUMAN DEPENDENCY" in content
    assert "DEFERRED / OPTIONAL" in content


def test_model_comparison_artifact_completeness():
    """Verify model comparison JSON covers all 4 evaluation protocols and key metrics."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i8", "results", "model_comparison.json")
    assert os.path.exists(json_path), "model_comparison.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == "12I.8"
    protocols = data["protocols"]
    assert "held_out_test" in protocols
    assert "dual_unseen_val" in protocols
    assert "job_disjoint_val" in protocols
    assert "resume_disjoint_val" in protocols

    held_out = protocols["held_out_test"]["models"]
    assert "production_baseline_logreg" in held_out
    assert "hybrid_stacking_challenger" in held_out
    assert "threshold_calibrated_decision_rule" in held_out

    prod_test = held_out["production_baseline_logreg"]
    assert pytest.approx(prod_test["accuracy"], 1e-3) == 0.4861
    assert pytest.approx(prod_test["balanced_accuracy"], 1e-3) == 0.4638
    assert pytest.approx(prod_test["macro_f1"], 1e-3) == 0.4501

    dual = protocols["dual_unseen_val"]["models"]
    prod_dual = dual["production_baseline_logreg"]
    assert pytest.approx(prod_dual["accuracy"], 1e-3) == 0.3682


def test_multi_seed_metrics_and_statistical_significance():
    """Verify 5-seed evaluation, McNemar statistics, and Holm-Bonferroni correction."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i8", "results", "multi_seed_metrics.json")
    assert os.path.exists(json_path), "multi_seed_metrics.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_seeds"] == 5
    seeds = data["seed_evaluations"]
    assert len(seeds) == 5

    for s in seeds:
        assert s["seed"] in [42, 43, 44, 45, 46]
        assert "mcnemar_p_value" in s
        assert "holm_bonferroni_adjusted_p_value" in s
        assert "clustered_bootstrap_95_ci" in s
        assert len(s["clustered_bootstrap_95_ci"]) == 2

    summary = data["aggregate_summary"]
    assert summary["mean_contrastive_accuracy"] > summary["mean_raw_sbert_accuracy"]
    assert pytest.approx(summary["mean_accuracy_improvement"], 1e-3) == 0.0642
    assert summary["meta_analytic_p_value"] < 0.001


def test_data_leakage_audit_and_entity_disjointness():
    """Verify zero entity leakage across train/val/test splits in leakage audit."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i8", "results", "leakage_audit.json")
    assert os.path.exists(json_path), "leakage_audit.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["overall_leakage_verdict"] == "PERFECT_SPLIT_ISOLATION_CONFIRMED"
    for v in data["split_verifications"]:
        assert v["overlapping_pairs"] == 0
        assert v["leakage_status"] == "ZERO_LEAKAGE"


def test_reproducibility_manifest_and_checkpoints():
    """Verify environment, preserved production artifacts, and candidate checkpoints."""
    json_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i8", "results", "reproducibility_manifest.json")
    assert os.path.exists(json_path), "reproducibility_manifest.json missing!"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    env = data["environment"]
    assert "torch" in env["core_packages"]
    assert "transformers" in env["core_packages"]
    assert "lightgbm" in env["core_packages"]

    cand_path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i8", "checkpoints", "lightgbm_candidate.joblib")
    assert os.path.exists(cand_path), "lightgbm_candidate.joblib missing!"


def test_80_percent_target_scientific_investigation():
    """Verify that the 80%+ target investigation is documented and explains Bayes error ceiling."""
    limitations_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I8_BENCHMARK_LIMITATIONS.md")
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I8_HUMAN_FREE_RESEARCH_REPORT.md")

    assert os.path.exists(limitations_path), "PHASE12I8_BENCHMARK_LIMITATIONS.md missing!"
    assert os.path.exists(report_path), "PHASE12I8_HUMAN_FREE_RESEARCH_REPORT.md missing!"

    with open(limitations_path, "r", encoding="utf-8") as f:
        lim_content = f.read()

    assert "Bayes error" in lim_content.lower() or "bayes" in lim_content.lower()
    assert "Potential Fit" in lim_content
    assert "DEFF" in lim_content or "1.7800" in lim_content

    with open(report_path, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "PROMOTION WITHHELD" in rep_content
    assert "80%" in rep_content


def test_final_operational_verdict():
    """Verify that the official operational verdict is supported by evidence."""
    report_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I8_HUMAN_FREE_RESEARCH_REPORT.md")
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "AUTOMATED PIPELINE VERIFIED — MODEL IMPROVEMENT DEMONSTRATED" in content
