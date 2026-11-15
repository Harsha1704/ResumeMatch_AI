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


def test_seed_significance_audit():
    """Verify 5-seed audit, McNemar chi-squared and binomial values, and Fisher limitation statement."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "seed_significance_audit.json")
    assert os.path.exists(path), "seed_significance_audit.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["validation_dataset"]["evaluated_rows"] == 296
    assert data["validation_dataset"]["unique_candidates"] == 91
    assert data["validation_dataset"]["unique_jobs"] == 52

    seeds = {s["seed"]: s for s in data["per_seed_evaluations"]}
    assert 42 in seeds
    assert 43 in seeds
    assert 44 in seeds
    assert 45 in seeds
    assert 46 in seeds

    s42 = seeds[42]
    assert s42["contingency_table"]["n10_raw_only_correct_b"] == 30
    assert s42["contingency_table"]["n01_contrastive_only_correct_c"] == 53
    assert pytest.approx(s42["mcnemar_chi2_corrected"], abs=1e-3) == 5.8313
    assert pytest.approx(s42["exact_binomial_p_value"], abs=1e-3) == 0.0152

    fisher_inv = data["fisher_combined_pvalue_investigation"]
    assert "INVALID_INDEPENDENCE_ASSUMPTION" in fisher_inv["methodological_flaw"]


def test_bayes_bound_audit_invalidation():
    """Verify that Cover-Hart Bayes error bound claim is officially invalidated."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "bayes_bound_audit.json")
    assert os.path.exists(path), "bayes_bound_audit.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        data = json.loads(raw_text)

    assert data["audit_verdict"] == "CLAIM_INVALIDATED_AND_RETRACTED"
    assert "category error" in raw_text.lower()
    assert "80%+" in data["certified_scientific_corrections"]["scientifically_defensible_limitations_statement"]


def test_architecture_attribution_audit():
    """Verify that 47.64% and 50.26% results are properly attributed to their true architectures."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "architecture_attribution_audit.json")
    assert os.path.exists(path), "architecture_attribution_audit.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    attributions = {a["metric_value"]: a for a in data["audited_attributions"]}
    assert "47.64% Accuracy (Dual-Unseen Validation)" in attributions
    assert "50.26% Accuracy (Official Held-Out Test)" in attributions

    attr_47 = attributions["47.64% Accuracy (Dual-Unseen Validation)"]
    assert "threshold" in attr_47["actual_producing_architecture"].lower()
    assert attr_47["physical_checkpoint_audit"]["standalone_cross_encoder_weights_exist"] is False

    attr_50 = attributions["50.26% Accuracy (Official Held-Out Test)"]
    assert "pseudo-label" in attr_50["actual_producing_architecture"].lower()


def test_four_protocol_reconciliation():
    """Verify all 4 evaluation protocols match certified manifest hashes and entity isolation."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "four_protocol_reconciliation.json")
    assert os.path.exists(path), "four_protocol_reconciliation.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    inventory = {m["protocol"]: m for m in data["manifest_inventory"]}
    assert "job_disjoint" in inventory
    assert "resume_disjoint" in inventory
    assert "dual_unseen" in inventory
    assert "held_out_test" in inventory

    assert inventory["held_out_test"]["record_count"] == 1759
    assert inventory["held_out_test"]["sha256"] == "d4319c1fb86f7708ece03ddb361514940f7416b22958ec6d9c94dc09f367d39b"
    assert pytest.approx(inventory["held_out_test"]["baseline_production_accuracy"], abs=1e-3) == 0.4861

    assert inventory["dual_unseen"]["clean_evaluated_records"] == 296
    assert inventory["dual_unseen"]["sha256"] == "1b31ae0c5d05ddccdaf351f58742e86ea89d1923050377efa335844e07c22321"


def test_threshold_leakage_audit():
    """Verify that test label leakage is false across all threshold workflows."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "threshold_leakage_audit.json")
    assert os.path.exists(path), "threshold_leakage_audit.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for wf in data["audited_threshold_workflows"]:
        assert wf["test_label_leakage_detected"] is False


def test_latency_reconciliation():
    """Verify standardized latency results distinguish end-to-end from classifier-only."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i9", "results", "latency_reconciliation.json")
    assert os.path.exists(path), "latency_reconciliation.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pipe_bk = data["standardized_benchmark_results"]["production_pipeline_breakdown"]
    assert pipe_bk["end_to_end_pipeline"]["mean_latency_ms"] > 10.0
    assert pipe_bk["stage_2_classifier_predict"]["mean_latency_ms"] < 1.0


def test_documentation_and_verdict():
    """Verify that all Phase 12I.9 research documents exist and report the official verdict."""
    rep_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I9_INDEPENDENT_AUDIT_REPORT.md")
    reg_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I9_CORRECTION_REGISTER.md")
    stat_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I9_STATISTICAL_REANALYSIS.md")

    assert os.path.exists(rep_path), "PHASE12I9_INDEPENDENT_AUDIT_REPORT.md missing!"
    assert os.path.exists(reg_path), "PHASE12I9_CORRECTION_REGISTER.md missing!"
    assert os.path.exists(stat_path), "PHASE12I9_STATISTICAL_REANALYSIS.md missing!"

    with open(rep_path, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "AUDIT CONDITIONALLY PASSED — CORRECTIONS REQUIRED" in rep_content
    assert "promotion" in rep_content.lower() and "withheld" in rep_content.lower()
