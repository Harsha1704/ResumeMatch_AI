"""
Tests for Phase 2.1.1: Final Security Fixes.
Verifies:
1. Legacy interview generation rejects missing CSRF.
2. Legacy interview submission rejects missing CSRF.
3. Invalid CSRF requests return 403.
4. Valid CSRF requests (via form data and request headers) succeed.
5. A browser with no analysis cannot retrieve another user's cached analysis.
6. A browser with its own analysis can still retrieve it.
7. Explicit demo preview still works.
8. Existing interview and analysis workflows remain fully functional.
"""

import json
import pytest
from app import (
    app,
    ANALYSIS_CACHE,
    _get_active_analysis,
    _get_sample_analysis,
    get_authorized_analysis,
    _get_browser_session_uid,
)
from src.interview.interview_session import InterviewSessionManager


@pytest.fixture(autouse=True)
def cleanup_cache_and_state():
    """Ensure clean test state before and after each test."""
    original_testing = app.config.get("TESTING", True)
    original_enforce = app.config.get("ENFORCE_CSRF_IN_TESTS", False)
    app.config["TESTING"] = True
    app.config["ENFORCE_CSRF_IN_TESTS"] = False

    test_keys = [k for k in list(ANALYSIS_CACHE.keys()) if k.startswith("test_") or k.startswith("victim_") or k.startswith("user_")]
    for k in test_keys:
        ANALYSIS_CACHE.pop(k, None)

    yield

    app.config["TESTING"] = original_testing
    app.config["ENFORCE_CSRF_IN_TESTS"] = original_enforce
    for k in test_keys:
        ANALYSIS_CACHE.pop(k, None)


def test_01_legacy_interview_generate_rejects_missing_csrf():
    """1. Legacy interview generation (/interview-studio/generate) rejects missing CSRF."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    resp = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate"
    })
    assert resp.status_code == 403
    data = resp.get_json()
    assert "CSRF verification failed" in data["error_message"]


def test_02_legacy_interview_submit_rejects_missing_csrf():
    """2. Legacy interview submission (/interview-practice/submit) rejects missing CSRF."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    resp = client.post("/interview-practice/submit", data={
        "session_id": "any-session-id",
        "question_index": "0",
        "user_answer": "My response",
        "direction": "next"
    })
    assert resp.status_code == 403
    data = resp.get_json()
    assert "CSRF verification failed" in data["error_message"]


def test_03_legacy_interview_invalid_csrf_returns_403():
    """3. Invalid CSRF tokens on legacy interview routes return HTTP 403."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    # Establish session and obtain legitimate CSRF token
    token_resp = client.get("/api/csrf-token")
    assert token_resp.status_code == 200

    # Submit forged token in form
    resp_gen = client.post("/interview-studio/generate", data={
        "category": "ALL",
        "action": "generate",
        "csrf_token": "forged_malicious_token_12345"
    })
    assert resp_gen.status_code == 403

    resp_sub = client.post("/interview-practice/submit", data={
        "session_id": "test-session",
        "question_index": "0",
        "user_answer": "My answer",
        "csrf_token": "forged_malicious_token_12345"
    })
    assert resp_sub.status_code == 403


def test_04_legacy_interview_valid_csrf_form_token_accepted():
    """4. Valid CSRF token in HTML form data allows interview generation and submission."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    # Get active session CSRF token
    token_resp = client.get("/api/csrf-token")
    csrf_token = token_resp.get_json()["csrf_token"]
    assert len(csrf_token) == 64

    # 1. Post to generate with valid form CSRF token
    resp_gen = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": csrf_token
    })
    assert resp_gen.status_code == 200
    assert b"Interview Intelligence Studio" in resp_gen.data

    # 2. Transition into practice session
    resp_practice = client.post("/interview-studio/generate", data={
        "category": "ALL",
        "difficulty": "Medium",
        "max_questions": "5",
        "action": "practice",
        "csrf_token": csrf_token
    }, follow_redirects=False)
    assert resp_practice.status_code == 302
    assert "/interview-practice" in resp_practice.headers["Location"]

    # 3. Retrieve practice page to get active session ID
    prac_page = client.get("/interview-practice")
    assert prac_page.status_code == 200

    # Extract session ID from session cookie context
    with client.session_transaction() as sess:
        sess_id = sess.get("active_interview_session_id")
    assert sess_id is not None

    # 4. Submit an answer with valid form CSRF token
    resp_sub = client.post("/interview-practice/submit", data={
        "session_id": sess_id,
        "question_index": "0",
        "user_answer": "Situation: I built a pipeline. Action: I used PyTorch. Result: Achieved 95% accuracy.",
        "direction": "next",
        "csrf_token": csrf_token
    }, follow_redirects=False)
    assert resp_sub.status_code == 302


def test_05_legacy_interview_valid_csrf_request_header_accepted():
    """5. Valid CSRF token via request headers (X-CSRF-Token) allows generation."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    client = app.test_client()

    token_resp = client.get("/api/csrf-token")
    csrf_token = token_resp.get_json()["csrf_token"]

    resp = client.post(
        "/interview-studio/generate",
        data={
            "category": "ALL",
            "action": "generate"
        },
        headers={"X-CSRF-Token": csrf_token}
    )
    assert resp.status_code == 200
    assert b"Interview Intelligence Studio" in resp.data


def test_06_no_analysis_browser_cannot_retrieve_other_user_cached_analysis():
    """6. A browser session with no analysis cannot retrieve another user's cached analysis."""
    # User A uploads and caches an analysis
    victim_analysis_id = "victim_confidential_999"
    victim_data = {
        "analysis_id": victim_analysis_id,
        "is_demo": False,
        "filename": "Confidential_Executive_Resume.pdf",
        "job_title": "Chief Technology Officer",
        "detected_job_title": "Executive CTO",
        "target_role_source": "resume",
        "predicted_class": "Good Fit",
        "model_confidence": 99.1,
        "compatibility_score": 98.5,
        "model_used": "Production Baseline (TF-IDF + Logistic Regression)",
        "model_backend": "production",
        "is_challenger": False,
        "inference_latency_ms": 12.0,
        "cache_status": "hit",
        "class_probabilities": {"Good Fit": 0.991, "Potential Fit": 0.007, "No Fit": 0.002},
        "skill_gap_summary": {
            "total_required_count": 5,
            "matched_required_count": 5,
            "fully_matched_required_count": 5,
            "partially_evidenced_required_count": 0,
            "missing_required_count": 0,
            "total_preferred_count": 2,
            "matched_preferred_count": 2,
            "missing_preferred_count": 0,
            "total_resume_skills_count": 10,
            "full_coverage_pct": 100.0,
            "any_coverage_pct": 100.0,
            "full_coverage_display": "100.0%",
            "any_coverage_display": "100.0%",
            "coverage_status": "Strong Match"
        },
        "projects": [
            {
                "title": "Secret Enterprise Microservice Architecture",
                "technologies": ["Go", "Kubernetes", "gRPC"],
                "description": "Proprietary enterprise infrastructure."
            }
        ],
        "internships": [],
        "resume_skills": ["Go", "Kubernetes", "gRPC", "Executive Strategy"],
        "matched_skills": ["Go", "Kubernetes"],
        "missing_skills": [],
        "required_skills": ["Go", "Kubernetes"],
        "preferred_skills": [],
        "education_analysis": {"notes": "Ph.D. in Computer Science"},
        "experience_summary": {"total_years": 15.0, "display_summary": "15 Years Experience"},
        "experience_analysis": {"total_years_estimate": 15.0, "display_summary": "15 Years"},
        "recommendations": [],
        "learning_resources": []
    }
    ANALYSIS_CACHE[victim_analysis_id] = victim_data

    # Client B represents a new user with an empty browser session
    with app.test_client() as client_b:
        # A. Direct internal call to _get_active_analysis() from Client B's request context
        with app.test_request_context():
            active_for_b = _get_active_analysis()
            assert active_for_b["analysis_id"] == "sample-preview"
            assert active_for_b["filename"] != "Confidential_Executive_Resume.pdf"
            assert active_for_b["job_title"] != "Chief Technology Officer"
            assert active_for_b["is_demo"] is True

        # B. Client B visits HTML views without an ID parameter
        resp_sg = client_b.get("/skill-gap")
        assert resp_sg.status_code == 200
        html_sg = resp_sg.data.decode("utf-8")
        assert "Confidential_Executive_Resume.pdf" not in html_sg
        assert "Chief Technology Officer" not in html_sg

        resp_studio = client_b.get("/interview-studio")
        assert resp_studio.status_code == 200
        html_studio = resp_studio.data.decode("utf-8")
        assert "Confidential_Executive_Resume.pdf" not in html_studio
        assert "Secret Enterprise Microservice Architecture" not in html_studio

        resp_mentor = client_b.get("/career-mentor")
        assert resp_mentor.status_code == 200
        html_mentor = resp_mentor.data.decode("utf-8")
        assert "Confidential_Executive_Resume.pdf" not in html_mentor
        assert "Chief Technology Officer" not in html_mentor

        # C. Client B attempts to fetch API companion endpoints without ID
        api_sg = client_b.get("/api/skill-gap")
        assert api_sg.status_code == 200
        sg_data = api_sg.get_json()["analysis"]
        assert sg_data["analysis_id"] == "sample-preview"
        assert sg_data["filename"] != "Confidential_Executive_Resume.pdf"

        # D. Client B directly targets User A's ID via API
        api_intruder = client_b.get(f"/api/analysis/{victim_analysis_id}")
        assert api_intruder.status_code == 403

        api_intruder_sg = client_b.get(f"/api/skill-gap?id={victim_analysis_id}")
        assert api_intruder_sg.status_code == 403


def test_07_browser_with_own_analysis_retrieves_it():
    """7. A browser with its own active analysis successfully retrieves its own data."""
    my_id = "user_own_analysis_789"
    my_data = {
        "analysis_id": my_id,
        "is_demo": False,
        "filename": "Harsha_ML_Specialist.pdf",
        "job_title": "Lead Machine Learning Engineer",
        "detected_job_title": "Senior ML Engineer",
        "target_role_source": "job_description",
        "predicted_class": "Good Fit",
        "model_confidence": 94.5,
        "compatibility_score": 92.0,
        "model_used": "Production Baseline (TF-IDF + Logistic Regression)",
        "model_backend": "production",
        "is_challenger": False,
        "inference_latency_ms": 11.2,
        "cache_status": "hit",
        "class_probabilities": {"Good Fit": 0.945, "Potential Fit": 0.045, "No Fit": 0.010},
        "skill_gap_summary": {
            "total_required_count": 3,
            "matched_required_count": 3,
            "fully_matched_required_count": 3,
            "partially_evidenced_required_count": 0,
            "missing_required_count": 0,
            "total_preferred_count": 1,
            "matched_preferred_count": 1,
            "missing_preferred_count": 0,
            "total_resume_skills_count": 8,
            "full_coverage_pct": 100.0,
            "any_coverage_pct": 100.0,
            "full_coverage_display": "100.0%",
            "any_coverage_display": "100.0%",
            "coverage_status": "Strong Match"
        },
        "projects": [
            {
                "title": "ResumeMatch Intelligent Core",
                "technologies": ["Python", "PyTorch", "Flask"],
                "description": "High performance NLP matching engine."
            }
        ],
        "internships": [],
        "resume_skills": ["Python", "PyTorch", "Flask", "Docker"],
        "matched_skills": ["Python", "PyTorch"],
        "missing_skills": [],
        "required_skills": ["Python", "PyTorch"],
        "preferred_skills": ["Flask"],
        "education_analysis": {"notes": "B.Tech in Computer Science"},
        "experience_summary": {"total_years": 4.0, "display_summary": "4 Years Experience"},
        "experience_analysis": {"total_years_estimate": 4.0, "display_summary": "4 Years"},
        "recommendations": [],
        "learning_resources": []
    }
    ANALYSIS_CACHE[my_id] = my_data

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["active_analysis_id"] = my_id
            sess["allowed_analyses"] = [my_id]

        # 1. API analysis query
        res = client.get(f"/api/analysis/{my_id}")
        assert res.status_code == 200
        data = res.get_json()["analysis"]
        assert data["analysis_id"] == my_id
        assert data["filename"] == "Harsha_ML_Specialist.pdf"
        assert data["job_title"] == "Lead Machine Learning Engineer"

        # 2. API skill-gap query without explicit id (session continuity)
        res_sg = client.get("/api/skill-gap")
        assert res_sg.status_code == 200
        sg_data = res_sg.get_json()["analysis"]
        assert sg_data["analysis_id"] == my_id
        assert sg_data["filename"] == "Harsha_ML_Specialist.pdf"

        # 3. Direct _get_active_analysis() call
        with client.session_transaction() as sess:
            with app.test_request_context():
                from flask import session as flask_session
                flask_session["active_analysis_id"] = my_id
                flask_session["allowed_analyses"] = [my_id]
                active = _get_active_analysis()
                assert active["analysis_id"] == my_id
                assert active["filename"] == "Harsha_ML_Specialist.pdf"


def test_08_explicit_demo_preview_endpoints():
    """8. Explicit demo previews return standard demo data with is_demo=True."""
    client = app.test_client()

    # Query with ?id=sample
    resp_sample = client.get("/api/skill-gap?id=sample")
    assert resp_sample.status_code == 200
    data_sample = resp_sample.get_json()["analysis"]
    assert data_sample["is_demo"] is True
    assert data_sample["analysis_id"] == "sample-preview"

    # Query with ?id=demo
    resp_demo = client.get("/api/analysis/demo")
    assert resp_demo.status_code == 200
    data_demo = resp_demo.get_json()["analysis"]
    assert data_demo["is_demo"] is True

    # Direct helper call
    with app.test_request_context():
        sample = _get_sample_analysis()
        assert sample["is_demo"] is True
        assert sample["analysis_id"] == "sample-preview"
        assert "Python" in sample["resume_skills"]
