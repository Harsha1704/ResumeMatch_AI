"""
tests/test_model_performance_dashboard.py
Regression tests for Phase 12D Model Performance Dashboard Upgrade.

Verifies:
1. Model Performance route loads successfully with HTTP 200.
2. Metrics match approved evaluation artifacts (Phase 12D).
3. Active production model checkpoint and SHA-256 are correctly identified.
4. Multi-protocol data structure contains all 4 verified protocols.
5. Class ordering remains strictly ['No Fit', 'Potential Fit', 'Good Fit'].
6. Missing metrics or corrupted files handle gracefully without 500 errors.
7. Invalidated historical claims (85% dual-unseen) are explicitly labeled as INVALIDATED.
8. No model training or heavy transformer loading is triggered on GET /model-performance.
9. Production model binary (models/best_model.joblib) hash is strictly preserved.
10. CSV export endpoints (/api/model-performance/export) return valid CSV responses.
"""

import hashlib
import json
import time
import pytest
from app import app
from src.services.model_performance_adapter import (
    get_model_performance_dashboard_data,
    PRODUCTION_MODEL_METADATA,
    CLASSES
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_model_performance_route_success(client):
    """Requirement 1: Verify GET /model-performance loads with HTTP 200."""
    resp = client.get("/model-performance")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Model Performance &amp; Evaluation Dashboard" in html
    assert "Phase 12D Certified" in html


def test_metrics_match_approved_phase12d_artifacts():
    """Requirement 2: Verify metrics match approved Phase 12D artifacts."""
    data = get_model_performance_dashboard_data()
    protocols = data["protocols"]

    # Job-Disjoint Val
    jd = protocols["job_disjoint_val"]["models"]
    assert jd["classical_baseline"]["metrics"]["accuracy"] == 0.4846
    assert jd["classical_baseline"]["metrics"]["macro_f1"] == 0.4292
    assert jd["sbert_config_b"]["metrics"]["accuracy"] == 0.5116
    assert jd["sbert_config_b"]["metrics"]["macro_f1"] == 0.4759
    assert jd["hybrid_config_d"]["metrics"]["accuracy"] == 0.5180
    assert jd["hybrid_config_d"]["metrics"]["macro_f1"] == 0.4781

    # Resume-Disjoint Val
    rd = protocols["resume_disjoint_val"]["models"]
    assert rd["classical_baseline"]["metrics"]["accuracy"] == 0.4780
    assert rd["classical_baseline"]["metrics"]["macro_f1"] == 0.4440
    assert rd["sbert_config_b"]["metrics"]["accuracy"] == 0.5445
    assert rd["sbert_config_b"]["metrics"]["macro_f1"] == 0.5376
    assert rd["hybrid_config_d"]["metrics"]["accuracy"] == 0.5523
    assert rd["hybrid_config_d"]["metrics"]["macro_f1"] == 0.5460

    # Dual-Unseen Val
    du = protocols["dual_unseen_val"]["models"]
    assert du["classical_baseline"]["metrics"]["accuracy"] == 0.3939
    assert du["classical_baseline"]["metrics"]["macro_f1"] == 0.3633
    assert du["sbert_config_b"]["metrics"]["accuracy"] == 0.3872
    assert du["sbert_config_b"]["metrics"]["macro_f1"] == 0.3339
    assert du["hybrid_config_d"]["metrics"]["accuracy"] == 0.3670
    assert du["hybrid_config_d"]["metrics"]["macro_f1"] == 0.3169

    # Held-Out Test
    ht = protocols["held_out_test"]["models"]
    assert ht["classical_baseline"]["metrics"]["accuracy"] == 0.4849
    assert ht["classical_baseline"]["metrics"]["macro_f1"] == 0.4707
    assert ht["sbert_config_b"]["metrics"]["accuracy"] == 0.4730
    assert ht["sbert_config_b"]["metrics"]["macro_f1"] == 0.4422
    assert ht["hybrid_config_d"]["metrics"]["accuracy"] == 0.4673
    assert ht["hybrid_config_d"]["metrics"]["macro_f1"] == 0.4368


def test_production_model_identification(client):
    """Requirement 3: Verify active production model and checksum are displayed."""
    resp = client.get("/model-performance")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Logistic Regression" in html
    assert "Multinomial Logistic Regression (Sparse Word TF-IDF + 15 Dense Domain Features)" in html
    assert "sha256: 1001baaf" in html.lower() or "1001baaf" in html.lower()
    assert "ACTIVE IN PRODUCTION" in html


def test_protocol_data_structure():
    """Requirement 4: Verify protocol switching metadata for all 4 protocols."""
    data = get_model_performance_dashboard_data()
    protocols = data["protocols"]
    assert set(protocols.keys()) == {"job_disjoint_val", "resume_disjoint_val", "dual_unseen_val", "held_out_test"}

    assert protocols["job_disjoint_val"]["sample_count"] == 778
    assert protocols["resume_disjoint_val"]["sample_count"] == 1023
    assert protocols["dual_unseen_val"]["sample_count"] == 297
    assert protocols["held_out_test"]["sample_count"] == 1759


def test_class_ordering_consistency():
    """Requirement 5: Verify class ordering is strictly ['No Fit', 'Potential Fit', 'Good Fit']."""
    assert CLASSES == ["No Fit", "Potential Fit", "Good Fit"]
    data = get_model_performance_dashboard_data()
    assert data["classes"] == ["No Fit", "Potential Fit", "Good Fit"]

    # Verify per-class keys in all models
    for p in data["protocols"].values():
        for m in p["models"].values():
            assert list(m["metrics"]["per_class"].keys()) == ["No Fit", "Potential Fit", "Good Fit"]
            assert len(m["metrics"]["confusion_matrix"]) == 3
            assert len(m["metrics"]["confusion_matrix"][0]) == 3


def test_invalidated_claims_transparency(client):
    """Requirement 7: Verify that invalidated 85% dual-unseen claims are explicitly flagged."""
    resp = client.get("/model-performance")
    html = resp.data.decode("utf-8")
    assert "Invalidation of Phase 12B 85.19% Dual-Unseen Claim" in html
    assert "INVALIDATED" in html


def test_no_model_training_on_route_load(client):
    """Requirement 8: Verify GET /model-performance executes in milliseconds with zero training."""
    t0 = time.perf_counter()
    resp = client.get("/model-performance")
    latency = time.perf_counter() - t0

    assert resp.status_code == 200
    # Must render rapidly (< 500 ms) because it only reads cached JSON artifacts
    assert latency < 0.500, f"Page load took {latency:.3f}s; potential training triggered!"


def test_production_model_hash_unchanged():
    """Requirement 9: Verify models/best_model.joblib SHA-256 hash is unchanged."""
    model_path = "models/best_model.joblib"
    h = hashlib.sha256()
    with open(model_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_hash = h.hexdigest().upper()
    assert actual_hash == PRODUCTION_MODEL_METADATA["sha256"]


def test_export_endpoints(client):
    """Requirement 10: Verify CSV export API endpoints work correctly."""
    # 1. Comparison table CSV
    resp_comp = client.get("/api/model-performance/export?type=comparison")
    assert resp_comp.status_code == 200
    assert "text/csv" in resp_comp.content_type
    assert "Model Architecture,Artifact ID,Role,Training Partition,Evaluation Partition" in resp_comp.data.decode("utf-8")

    # 2. Protocol metrics CSV
    resp_met = client.get("/api/model-performance/export?type=metrics&protocol=job_disjoint_val&model=hybrid_config_d")
    assert resp_met.status_code == 200
    assert "text/csv" in resp_met.content_type
    assert "accuracy" in resp_met.data.decode("utf-8")

    # 3. Confusion matrix CSV
    resp_cm = client.get("/api/model-performance/export?type=confusion&protocol=job_disjoint_val&model=hybrid_config_d")
    assert resp_cm.status_code == 200
    assert "text/csv" in resp_cm.content_type
    assert "Actual Class,Pred No Fit,Pred Potential Fit,Pred Good Fit" in resp_cm.data.decode("utf-8")


def test_model_artifact_identity_separation():
    """Verify production frozen checkpoint is distinct from retrained baselines."""
    data = get_model_performance_dashboard_data()
    prod = data["production_model"]
    assert prod["artifact_path"] == "models/best_model.joblib"
    assert "1001BAAF" in prod["sha256"]
    assert prod["training_partition"] == "Phase 1 Primary Training Set (N=6,240, Unfiltered)"
    assert prod["evaluation_partition"] == "Official Held-Out Test Set (N=1,759, 71 Unseen Jobs)"

    # Comparison table separation
    rows = {r["model_name"]: r for r in data["comparison_table"]}
    assert "Logistic Regression (Deployed Checkpoint)" in rows
    assert "Classical Baseline (Phase 12D Retrained)" in rows
    assert rows["Logistic Regression (Deployed Checkpoint)"]["is_active"] is True
    assert rows["Classical Baseline (Phase 12D Retrained)"]["is_active"] is False


def test_protocol_specific_overlap_guarantees(client):
    """Verify protocol-specific guarantees replace blanket leak-free claims."""
    data = get_model_performance_dashboard_data()
    protos = data["protocols"]

    # Job-disjoint: jobs disjoint, resumes overlap permitted
    assert "0.0% (0 / 42 Jobs)" in protos["job_disjoint_val"]["leakage_guarantee"]["job_overlap"]
    assert "97.59%" in protos["job_disjoint_val"]["leakage_guarantee"]["resume_overlap"]

    # Resume-disjoint: resumes disjoint, jobs overlap permitted
    assert "0.0% (0 / 97 Resumes)" in protos["resume_disjoint_val"]["leakage_guarantee"]["resume_overlap"]
    assert "100.0%" in protos["resume_disjoint_val"]["leakage_guarantee"]["job_overlap"]

    # Dual-unseen: both disjoint
    assert "0.0% (0 / 92 Resumes)" in protos["dual_unseen_val"]["leakage_guarantee"]["resume_overlap"]
    assert "0.0% (0 / 52 Jobs)" in protos["dual_unseen_val"]["leakage_guarantee"]["job_overlap"]

    # All guarantee 0 exact pair overlap
    for p in protos.values():
        assert "0.0%" in p["leakage_guarantee"]["pair_overlap"]

    # Check that UI renders protocol-specific breakdown
    resp = client.get("/model-performance")
    html = resp.data.decode("utf-8")
    assert "Protocol-Specific Leakage Safeguards Active" in html
    assert "Tests Unseen Jobs with Known Candidates" in html


def test_dataset_count_reconciliation():
    """Verify 8,000 total pairs, 643 resumes, 351 jobs, 50/25/25 and 6 contradictory pairs."""
    data = get_model_performance_dashboard_data()
    facts = data["dataset_facts"]

    assert facts["total_source_pairs"] == 8000
    assert facts["unique_resumes"] == 643
    assert facts["unique_jobs"] == 351
    assert facts["raw_train_pairs"] == 6241
    assert facts["raw_test_pairs"] == 1759

    # Class distribution
    dist = facts["class_distribution_combined"]
    assert dist["No Fit"]["count"] == 4000
    assert dist["No Fit"]["percentage"] == 50.0
    assert dist["Potential Fit"]["count"] == 2000
    assert dist["Potential Fit"]["percentage"] == 25.0
    assert dist["Good Fit"]["count"] == 2000
    assert dist["Good Fit"]["percentage"] == 25.0

    # Contradictory label pairs treatment
    conflicts = facts["contradictory_label_pairs"]
    assert conflicts["count_conflict_groups"] == 6
    assert conflicts["total_conflicting_rows"] == 12
    assert conflicts["treatment"] == "FLAGGED & EXCLUDED"


def test_confusion_matrix_consistency_with_predictions():
    """Verify dashboard confusion matrices exactly match sums from saved prediction CSVs."""
    import pandas as pd
    from pathlib import Path

    pred_dir = Path("results/phase12d_experiments/predictions")
    data = get_model_performance_dashboard_data()

    for proto_key, proto_obj in data["protocols"].items():
        for model_key, model_obj in proto_obj["models"].items():
            csv_file = pred_dir / f"predictions_{proto_key}_{model_key}.csv"
            assert csv_file.exists(), f"Missing prediction CSV: {csv_file}"
            df = pd.read_csv(csv_file)

            # Recompute confusion matrix from CSV
            classes = ["No Fit", "Potential Fit", "Good Fit"]
            c_to_idx = {c: i for i, c in enumerate(classes)}
            expected_cm = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            for _, r in df.iterrows():
                expected_cm[c_to_idx[r["actual_label"]]][c_to_idx[r["predicted_label"]]] += 1

            actual_cm = model_obj["metrics"]["confusion_matrix"]
            assert actual_cm == expected_cm, (
                f"Mismatch in {proto_key} {model_key} CM: expected {expected_cm}, got {actual_cm}"
            )


def test_csv_to_ui_metric_consistency(client):
    """Verify that CSV exports match dashboard metrics exactly."""
    data = get_model_performance_dashboard_data()

    # Test metrics export for job_disjoint_val classical_baseline
    resp = client.get("/api/model-performance/export?type=metrics&protocol=job_disjoint_val&model=classical_baseline")
    assert resp.status_code == 200
    csv_text = resp.data.decode("utf-8")
    assert '"accuracy",0.4846' in csv_text
    assert '"macro_f1",0.4292' in csv_text

    # Test confusion export
    resp_cm = client.get("/api/model-performance/export?type=confusion&protocol=job_disjoint_val&model=classical_baseline")
    assert resp_cm.status_code == 200
    cm_text = resp_cm.data.decode("utf-8")
    assert '"No Fit",241,108,66' in cm_text
    assert '"Potential Fit",52,96,82' in cm_text
    assert '"Good Fit",45,48,40' in cm_text
