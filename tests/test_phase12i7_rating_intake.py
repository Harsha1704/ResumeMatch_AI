import json
import os
import hashlib
import tempfile
import pytest

from src.benchmark.rating_intake_validator import RatingIntakeValidator

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


def test_participation_status_audit():
    """Verify recruiter participation audit artifact and awaiting status."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i7_participation_status.json")
    assert os.path.exists(path), "phase12i7_participation_status.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == "12I.7"
    summary = data["participation_summary"]
    assert summary["actual_ratings_submitted"] == 0
    assert summary["remaining_ratings_required"] == 400
    assert summary["target_pairs"] == 200
    assert summary["overall_status"] == "PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS"

    roster = {r["pseudonymous_id"]: r for r in data["recruiter_roster"]}
    assert "REC_A_892" in roster
    assert "REC_B_314" in roster
    assert "LEAD_ADJ_001" in roster

    assert roster["REC_A_892"]["lifecycle_stage"]["ratings_submitted"]["submitted_count"] == 0
    assert roster["REC_B_314"]["lifecycle_stage"]["ratings_submitted"]["submitted_count"] == 0


def test_rating_intake_rules_and_validation():
    """Verify programmatic schema validation and business logic rules in validator."""
    validator = RatingIntakeValidator()
    assert len(validator.all_pair_ids) == 200

    # 1. Valid submission passes
    valid_sub = {
        "evaluator_id": "REC_A_892",
        "pair_id": "PILOT_P_0001",
        "rating": 1,
        "confidence": 2,
        "job_evidence_quote": "TROOPS is an all-in-one SaaS platform",
        "decision_rationale": "Candidate possesses strong database engineering fundamentals but lacks lead Angular background.",
        "mandatory_justification": "Missing primary frontend requirement specified in senior role description.",
        "resume_evidence_status": "UNSTATED_UNVERIFIED",
    }
    is_valid, errors = validator.validate_submission_payload(valid_sub)
    assert is_valid, f"Expected valid submission, got errors: {errors}"
    assert len(errors) == 0

    # 2. Unauthorized evaluator rejected
    bad_eval = dict(valid_sub, evaluator_id="UNAUTHORIZED_USER")
    is_valid, errors = validator.validate_submission_payload(bad_eval)
    assert not is_valid
    assert any("Unauthorized evaluator" in e for e in errors)

    # 3. Non-existent pair_id rejected
    bad_pair = dict(valid_sub, pair_id="PILOT_P_9999")
    is_valid, errors = validator.validate_submission_payload(bad_pair)
    assert not is_valid
    assert any("not in frozen pilot sampling manifest" in e for e in errors)

    # 4. Out-of-bounds rating rejected
    bad_rating = dict(valid_sub, rating=3)
    is_valid, errors = validator.validate_submission_payload(bad_rating)
    assert not is_valid
    assert any("Invalid rating" in e for e in errors)

    # 5. Invalid confidence rejected
    bad_conf = dict(valid_sub, confidence=0)
    is_valid, errors = validator.validate_submission_payload(bad_conf)
    assert not is_valid
    assert any("Invalid confidence" in e for e in errors)

    # 6. Unverified / non-existent job quote rejected
    bad_quote = dict(valid_sub, job_evidence_quote="This quote definitely does not exist in the text of Troops posting")
    is_valid, errors = validator.validate_submission_payload(bad_quote)
    assert not is_valid
    assert any("Job evidence quote" in e for e in errors)

    # 7. Brief decision rationale rejected
    bad_rationale = dict(valid_sub, decision_rationale="Too short")
    is_valid, errors = validator.validate_submission_payload(bad_rationale)
    assert not is_valid
    assert any("Decision rationale is too brief" in e for e in errors)

    # 8. Blinding violation rejected
    bad_blinding = dict(valid_sub, model_prediction=1)
    is_valid, errors = validator.validate_submission_payload(bad_blinding)
    assert not is_valid
    assert any("Blinding violation" in e for e in errors)


def test_duplicate_submission_rejection():
    """Verify that duplicate submissions for the same evaluator and pair are rejected."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        tmp_ledger = tmp.name

    try:
        validator = RatingIntakeValidator(ledger_path=tmp_ledger)
        sub = {
            "evaluator_id": "REC_A_892",
            "pair_id": "PILOT_P_0001",
            "rating": 1,
            "confidence": 2,
            "job_evidence_quote": "TROOPS is an all-in-one SaaS platform",
            "decision_rationale": "Candidate possesses strong database engineering fundamentals but lacks lead Angular background.",
            "mandatory_justification": "Missing primary frontend requirement specified in senior role description.",
            "resume_evidence_status": "UNSTATED_UNVERIFIED",
        }

        # First intake accepted
        res1 = validator.ingest_submission(sub)
        assert res1["status"] == "ACCEPTED"
        assert "intake_hash" in res1

        # Second intake for same evaluator and pair rejected
        res2 = validator.ingest_submission(sub)
        assert res2["status"] == "REJECTED"
        assert any("Duplicate submission rejected" in e for e in res2["errors"])
    finally:
        if os.path.exists(tmp_ledger):
            os.remove(tmp_ledger)


def test_reliability_results_null_state():
    """Verify that reliability metrics are strictly null-initialized while pending real ratings."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i7_reliability_results.json")
    assert os.path.exists(path), "phase12i7_reliability_results.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "PENDING_RECRUITER_RATINGS"
    metrics = data["measured_reliability_metrics"]
    assert metrics["raw_percentage_agreement"] is None
    assert metrics["cohen_kappa_unweighted"] is None
    assert metrics["quadratic_weighted_kappa"] is None
    assert metrics["gwet_ac1"] is None
    assert metrics["specific_agreement"]["0_no_fit"] is None
    assert metrics["specific_agreement"]["1_potential_fit"] is None
    assert metrics["specific_agreement"]["2_good_fit"] is None

    gates = data["pre_specified_quality_acceptance_gates"]
    assert ">= 0.70" in gates["primary_reliability_gate"]["target_threshold"]
    assert "<= 5.0%" in gates["severe_discordance_gate"]["maximum_tolerated"]


def test_quarantine_and_blinding_audit():
    """Verify zero leakage between pilot pairs and training/validation/test parquet splits."""
    path = os.path.join(WORKSPACE_ROOT, "experiments", "phase12i", "results", "phase12i7_quarantine_audit.json")
    assert os.path.exists(path), "phase12i7_quarantine_audit.json missing!"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    audit = data["cross_split_contamination_audit"]
    assert audit["total_leakage_events"] == 0
    assert audit["quarantine_isolation_verdict"] == "VERIFIED_PERFECT_ISOLATION"

    for split in audit["evaluated_splits"]:
        assert split["candidate_overlap"] == 0
        assert split["job_overlap"] == 0
        assert split["leakage_detected"] is False

    # Check that deployed queues are blinded
    queue_a_path = os.path.join(WORKSPACE_ROOT, "data", "benchmark_vault", "queues", "queue_REC_A_892.json")
    queue_b_path = os.path.join(WORKSPACE_ROOT, "data", "benchmark_vault", "queues", "queue_REC_B_314.json")

    assert os.path.exists(queue_a_path)
    assert os.path.exists(queue_b_path)

    with open(queue_a_path, "r", encoding="utf-8") as f:
        qa = json.load(f)
    assert qa["pair_count"] == 200
    for p in qa["pairs"]:
        assert p["blinding"]["model_predictions_exposed"] is False
        assert p["blinding"]["peer_ratings_exposed"] is False
        assert "model_prediction" not in p


def test_documentation_and_verdict():
    """Verify Phase 12I.7 documentation deliverables exist with the official verdict."""
    rep_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I7_PILOT_EXECUTION_REPORT.md")
    guide_path = os.path.join(WORKSPACE_ROOT, "docs", "research", "PHASE12I7_RATING_INTAKE_GUIDE.md")

    assert os.path.exists(rep_path), "PHASE12I7_PILOT_EXECUTION_REPORT.md missing!"
    assert os.path.exists(guide_path), "PHASE12I7_RATING_INTAKE_GUIDE.md missing!"

    with open(rep_path, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS" in rep_content
    assert "0 out of 400" in rep_content
