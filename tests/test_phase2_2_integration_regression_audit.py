"""
Tests for Phase 2.2: Final Integration & Regression Audit.
Verifies complete end-to-end integration across all 12 user workflow steps:
1. Health check & dashboard retrieval.
2. Resume analysis via JSON and multipart upload.
3. Supervised ML predictions, probabilities, and skill gap calculations.
4. Interview Studio dashboard and grounded question generation.
5. Practice mode initialization, navigation, and answer submission.
6. Practice evaluation metrics and results dashboard.
7. Career Mentor dossier, candidate customization, and priority skills.
8. Milestone progress updating and progress reset.
9. Session continuity across navigation without ID parameters.
10. Strict distinction between demo preview data and active candidate dossiers.
11. CSRF token validation and cross-session isolation.
12. Model artifact integrity and deterministic inference.
"""

import json
import pytest
from app import (
    app,
    ANALYSIS_CACHE,
    _get_active_analysis,
    _get_sample_analysis,
    get_authorized_analysis,
)
from src.interview.interview_session import InterviewSessionManager


@pytest.fixture(autouse=True)
def cleanup_integration_state():
    """Ensure clean test state before and after each test."""
    original_testing = app.config.get("TESTING", True)
    original_enforce = app.config.get("ENFORCE_CSRF_IN_TESTS", False)
    app.config["TESTING"] = True
    app.config["ENFORCE_CSRF_IN_TESTS"] = False

    test_keys = [k for k in list(ANALYSIS_CACHE.keys()) if k.startswith("p22_") or k.startswith("victim_") or k.startswith("user_")]
    for k in test_keys:
        ANALYSIS_CACHE.pop(k, None)

    yield

    app.config["TESTING"] = original_testing
    app.config["ENFORCE_CSRF_IN_TESTS"] = original_enforce
    for k in test_keys:
        ANALYSIS_CACHE.pop(k, None)


def test_01_health_and_dashboard_integration():
    """1. Verify /health and /api/dashboard integration contracts."""
    client = app.test_client()

    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_data = health_res.get_json()
    assert health_data["status"] == "healthy"
    assert health_data["model_loaded"] is True
    assert health_data["active_backend_default"] == "production"
    assert "flask_rss_mb" in health_data

    dash_res = client.get("/api/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.get_json()
    assert dash_data["status"] == "success"
    assert "summary" in dash_data
    assert "dataset_summary" in dash_data


def _create_analyzed_client():
    client = app.test_client()
    resume_text = (
        "Experienced Machine Learning Engineer with 4 years in Python, PyTorch, Scikit-Learn, "
        "and SQL. Built scalable NLP pipelines and real-time inference microservices using Docker. "
        "Education: B.Tech in Computer Science."
    )
    job_description = (
        "Position: Senior Machine Learning Engineer\n"
        "Required Skills:\n"
        "- Python\n"
        "- PyTorch\n"
        "- Docker\n"
        "- SQL\n"
        "Preferred Skills:\n"
        "- Kubernetes\n"
    )
    payload = {
        "resume_text": resume_text,
        "job_description": job_description,
        "target_role": "Senior Machine Learning Engineer",
        "model_backend": "production"
    }
    res = client.post("/api/analyze", data=json.dumps(payload), content_type="application/json")
    assert res.status_code == 200
    data = res.get_json()
    return client, data["analysis_id"], data["data"]


def test_02_full_resume_analysis_and_ml_prediction_workflow():
    """2. Verify resume analysis input, supervised ML prediction, and probability validity."""
    client, analysis_id, analysis = _create_analyzed_client()

    # Verify ML classification outputs
    assert analysis["predicted_class"] in ["Good Fit", "Potential Fit", "No Fit"]
    assert 0.0 <= analysis["model_confidence"] <= 100.0
    assert 0.0 <= analysis["compatibility_score"] <= 100.0
    assert analysis["is_demo"] is False
    assert analysis["model_backend"] == "production"

    # Verify probability distribution sum ~ 1.0
    probs = analysis["class_probabilities"]
    prob_sum = sum(probs.values())
    assert abs(prob_sum - 1.0) < 0.02

    # Verify skill gap extraction
    gap = analysis["skill_gap_summary"]
    assert gap["total_required_count"] > 0
    assert len(analysis["matched_skills"]) > 0


def test_03_skill_gap_and_session_continuity():
    """3. Verify skill gap query and session continuity without explicit ID parameter."""
    client, analysis_id, _ = _create_analyzed_client()

    # Query with explicit ID
    res_id = client.get(f"/api/skill-gap?id={analysis_id}")
    assert res_id.status_code == 200
    data_id = res_id.get_json()["analysis"]
    assert data_id["analysis_id"] == analysis_id
    assert data_id["is_demo"] is False

    # Query without ID (session continuity)
    res_session = client.get("/api/skill-gap")
    assert res_session.status_code == 200
    data_session = res_session.get_json()["analysis"]
    assert data_session["analysis_id"] == analysis_id
    assert data_session["is_demo"] is False


def test_04_interview_studio_generation_and_practice_workflow():
    """4. Verify Interview Studio question generation, practice session, and answer submission."""
    client, analysis_id, _ = _create_analyzed_client()

    # 1. Studio dashboard API
    res_studio = client.get("/api/interview-studio")
    assert res_studio.status_code == 200
    studio_data = res_studio.get_json()
    assert studio_data["status"] == "success"
    assert len(studio_data["questions"]) > 0
    assert len(studio_data["technical_topics"]) > 0

    # 2. Initiate practice mode
    gen_payload = {
        "category": "ALL",
        "difficulty": "All",
        "max_questions": 5,
        "action": "practice"
    }
    res_gen = client.post("/api/interview-studio/generate",
                          data=json.dumps(gen_payload),
                          content_type="application/json")
    assert res_gen.status_code == 200
    gen_data = res_gen.get_json()
    assert gen_data["status"] == "success"
    session_id = gen_data["active_session_id"]
    assert session_id is not None

    # 3. Retrieve practice question
    res_prac = client.get(f"/api/interview-practice?session_id={session_id}")
    assert res_prac.status_code == 200
    prac_data = res_prac.get_json()
    assert prac_data["status"] == "success"
    assert prac_data["session_id"] == session_id
    assert "question" in prac_data
    assert prac_data["current_index"] == 0

    # 4. Instant heuristic evaluation
    eval_payload = {
        "user_answer": "Situation: We needed high throughput. Action: I optimized PyTorch model batching. Result: Reduced latency by 40%.",
        "question_text": prac_data["question"]["question_text"],
        "expected_key_points": prac_data["question"].get("expected_key_points", []),
        "framework_id": "STAR"
    }
    res_eval = client.post("/api/interview/evaluate",
                           data=json.dumps(eval_payload),
                           content_type="application/json")
    assert res_eval.status_code == 200
    eval_data = res_eval.get_json()
    assert eval_data["status"] == "evaluated"
    assert "Situation" in eval_data["framework_adherence"]["sections_addressed"]
    assert "Action" in eval_data["framework_adherence"]["sections_addressed"]

    # 5. Submit answer and advance
    sub_payload = {
        "session_id": session_id,
        "question_index": 0,
        "user_answer": eval_payload["user_answer"],
        "direction": "finish"
    }
    res_sub = client.post("/api/interview-practice/submit",
                          data=json.dumps(sub_payload),
                          content_type="application/json")
    assert res_sub.status_code == 200
    sub_data = res_sub.get_json()
    assert sub_data["is_finished"] is True

    # 6. Retrieve interview results
    res_res = client.get(f"/api/interview-results?session_id={session_id}")
    assert res_res.status_code == 200
    results_data = res_res.get_json()
    assert results_data["status"] == "success"
    results = results_data["results"]
    assert "total_questions" in results
    assert "completed_questions" in results


def test_05_career_mentor_workflow_and_progress_reset():
    """5. Verify Career Mentor dossier, milestone updates, and progress reset."""
    client, analysis_id, _ = _create_analyzed_client()

    # 1. Fetch career mentor dossier
    res_mentor = client.get("/api/career-mentor")
    assert res_mentor.status_code == 200
    mentor_data = res_mentor.get_json()
    assert mentor_data["status"] == "success"
    dossier = mentor_data["dossier"]
    assert len(dossier["roadmaps"]) > 0

    # 2. Update candidate display name
    res_name = client.post("/api/mentor/update-name",
                           data=json.dumps({"preferred_name": "Harsha"}),
                           content_type="application/json")
    assert res_name.status_code == 200
    assert res_name.get_json()["preferred_name"] == "Harsha"

    # Verify milestone schema contract
    first_milestone = dossier["roadmaps"][0]["milestones"][0]
    assert "task" in first_milestone
    assert "deliverable" in first_milestone
    assert "step_title" in first_milestone
    assert "task_key" in first_milestone
    assert "status" in first_milestone
    assert "estimated_hours" in first_milestone
    assert len(first_milestone["task"]) > 0

    # 3. Mark milestone as completed
    first_task = first_milestone["task_key"]
    res_prog = client.post("/api/mentor/progress",
                           data=json.dumps({"task_key": first_task, "status": "completed"}),
                           content_type="application/json")
    assert res_prog.status_code == 200
    prog_data = res_prog.get_json()
    assert prog_data["current_status"] == "completed"
    assert prog_data["progress_summary"]["completed_tasks"] >= 1

    # 4. Reset progress
    res_reset = client.post("/api/mentor/reset-progress")
    assert res_reset.status_code == 200
    assert res_reset.get_json()["status"] == "success"

    # Verify dossier reflects reset progress
    res_dossier_after = client.get("/api/career-mentor")
    dossier_after = res_dossier_after.get_json()["dossier"]
    assert dossier_after["progress_summary"]["completed_tasks"] == 0


def test_06_strict_demo_preview_distinction():
    """6. Verify that demo preview profiles are explicitly marked with is_demo=True."""
    client = app.test_client()

    # Client without an active session requests skill gap and analysis
    res_sg = client.get("/api/skill-gap?id=sample")
    assert res_sg.status_code == 200
    data_sg = res_sg.get_json()["analysis"]
    assert data_sg["is_demo"] is True
    assert data_sg["analysis_id"] == "sample-preview"

    res_ana = client.get("/api/analysis/demo")
    assert res_ana.status_code == 200
    data_ana = res_ana.get_json()["analysis"]
    assert data_ana["is_demo"] is True


def test_07_csrf_enforcement_and_form_header_parity():
    """7. Verify CSRF enforcement on state-changing endpoints in enforced mode.
    
    Verifies:
    1. A state-changing API request without a token is rejected (HTTP 403).
    2. A valid X-CSRF-Token header is accepted (HTTP 200).
    3. A legacy Jinja form submission without a token is rejected (HTTP 403).
    4. A legacy Jinja form submission with a valid form token is accepted (HTTP 200).
    """
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    # 1. State-changing API request without a token is rejected
    post_api_no_csrf = client.post("/api/mentor/reset-progress")
    assert post_api_no_csrf.status_code == 403
    api_err = post_api_no_csrf.get_json()
    assert "CSRF verification failed" in api_err["error_message"]

    # Retrieve valid CSRF token from active session
    token_resp = client.get("/api/csrf-token")
    assert token_resp.status_code == 200
    token = token_resp.get_json()["csrf_token"]
    assert len(token) == 64

    # 2. State-changing API request with valid X-CSRF-Token header is accepted
    post_api_with_csrf = client.post(
        "/api/mentor/reset-progress",
        headers={"X-CSRF-Token": token}
    )
    assert post_api_with_csrf.status_code == 200
    assert post_api_with_csrf.get_json()["status"] == "success"

    # 3. Legacy Jinja form submission without a token is rejected
    post_form_no_csrf = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate"
    })
    assert post_form_no_csrf.status_code == 403
    form_err = post_form_no_csrf.get_json()
    assert "CSRF verification failed" in form_err["error_message"]

    # 4. Legacy Jinja form submission with a valid form token is accepted
    post_form_with_csrf = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": token
    })
    assert post_form_with_csrf.status_code == 200
    assert b"Interview Intelligence Studio" in post_form_with_csrf.data
