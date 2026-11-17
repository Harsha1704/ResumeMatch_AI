"""
tests/test_phase6_2_legacy_csrf.py
Phase 6.2 Legacy Routes CSRF Enforcement & Session Continuity Tests.

Verifies:
1. POST /analyze enforces fail-closed CSRF (missing, invalid, cross-session -> 403; valid -> 302).
2. POST /interview-studio/generate enforces fail-closed CSRF (missing, invalid, cross-session -> 403; valid -> 200/302).
3. POST /interview-practice/submit enforces fail-closed CSRF (missing, invalid, cross-session -> 403; valid -> 302).
4. Session continuity between token acquisition and form submission.
5. Cross-session forgery rejection on legacy endpoints.
"""

import io
import pytest
from app import app, ANALYSIS_CACHE
from src.interview.interview_session import InterviewSessionManager


@pytest.fixture(autouse=True)
def ensure_testing_mode():
    orig = app.config.get("TESTING")
    app.config["TESTING"] = True
    yield
    app.config["TESTING"] = orig


# =========================================================================
# 1. POST /analyze Legacy Form Route
# =========================================================================

def test_legacy_analyze_missing_csrf_returns_403():
    """Verify POST /analyze without CSRF token returns 403 Forbidden."""
    client = app.test_client()
    # Establish session without providing token in POST
    client.get("/api/csrf-token")

    form_data = {
        "resume_text": "Python Software Engineer with Docker and AWS experience.",
        "job_description": "Wanted: Python Engineer with cloud and container skills."
    }
    resp = client.post("/analyze", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_analyze_invalid_csrf_returns_403():
    """Verify POST /analyze with forged/invalid CSRF token returns 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    form_data = {
        "resume_text": "Python Software Engineer with Docker and AWS experience.",
        "job_description": "Wanted: Python Engineer with cloud and container skills.",
        "csrf_token": "attacker_forged_invalid_csrf_token"
    }
    resp = client.post("/analyze", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_analyze_cross_session_csrf_returns_403():
    """Verify POST /analyze using another session's CSRF token returns 403 Forbidden."""
    victim = app.test_client()
    attacker = app.test_client()

    v_tok = victim.get("/api/csrf-token").get_json()["csrf_token"]
    attacker.get("/api/csrf-token")

    form_data = {
        "resume_text": "Python Software Engineer with Docker and AWS experience.",
        "job_description": "Wanted: Python Engineer with cloud and container skills.",
        "csrf_token": v_tok
    }
    resp = attacker.post("/analyze", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_analyze_valid_csrf_succeeds_with_redirect():
    """Verify POST /analyze with valid session-bound CSRF token succeeds and redirects to /results."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    form_data = {
        "resume_text": "Experienced Python Software Engineer with Flask, Django, SQL, and Docker.",
        "job_description": "Wanted: Python Engineer with SQL and Flask experience.",
        "csrf_token": token
    }
    resp = client.post("/analyze", data=form_data, follow_redirects=False)
    assert resp.status_code == 302
    assert "/results?id=" in resp.headers["Location"]


# =========================================================================
# 2. POST /interview-studio/generate Legacy Form Route
# =========================================================================

def test_legacy_interview_studio_generate_missing_csrf_returns_403():
    """Verify POST /interview-studio/generate without CSRF token returns 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    form_data = {
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate"
    }
    resp = client.post("/interview-studio/generate", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_studio_generate_invalid_csrf_returns_403():
    """Verify POST /interview-studio/generate with invalid CSRF token returns 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    form_data = {
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": "forged_bad_csrf_token"
    }
    resp = client.post("/interview-studio/generate", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_studio_generate_cross_session_csrf_returns_403():
    """Verify POST /interview-studio/generate with cross-session CSRF token returns 403 Forbidden."""
    victim = app.test_client()
    attacker = app.test_client()

    v_tok = victim.get("/api/csrf-token").get_json()["csrf_token"]
    attacker.get("/api/csrf-token")

    form_data = {
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": v_tok
    }
    resp = attacker.post("/interview-studio/generate", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_studio_generate_valid_csrf_succeeds():
    """Verify POST /interview-studio/generate with valid CSRF token generates questions and creates session."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    # 1. Action: generate -> 200 OK rendering template
    form_data_gen = {
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": token
    }
    resp_gen = client.post("/interview-studio/generate", data=form_data_gen)
    assert resp_gen.status_code == 200
    assert b"Interview Intelligence Studio" in resp_gen.data

    # 2. Action: practice -> 302 Redirect to /interview-practice
    form_data_prac = {
        "category": "ALL",
        "difficulty": "Medium",
        "max_questions": "5",
        "action": "practice",
        "csrf_token": token
    }
    resp_prac = client.post("/interview-studio/generate", data=form_data_prac, follow_redirects=False)
    assert resp_prac.status_code == 302
    assert "/interview-practice" in resp_prac.headers["Location"]


# =========================================================================
# 3. POST /interview-practice/submit Legacy Form Route
# =========================================================================

def test_legacy_interview_practice_submit_missing_csrf_returns_403():
    """Verify POST /interview-practice/submit without CSRF token returns 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    form_data = {
        "session_id": "mock_sid",
        "question_index": 0,
        "user_answer": "Draft response without CSRF"
    }
    resp = client.post("/interview-practice/submit", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_practice_submit_invalid_csrf_returns_403():
    """Verify POST /interview-practice/submit with invalid CSRF token returns 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    form_data = {
        "session_id": "mock_sid",
        "question_index": 0,
        "user_answer": "Draft response with bad CSRF",
        "csrf_token": "invalid_forged_csrf_123"
    }
    resp = client.post("/interview-practice/submit", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_practice_submit_cross_session_csrf_returns_403():
    """Verify POST /interview-practice/submit with cross-session CSRF token returns 403 Forbidden."""
    victim = app.test_client()
    attacker = app.test_client()

    v_tok = victim.get("/api/csrf-token").get_json()["csrf_token"]
    attacker.get("/api/csrf-token")

    form_data = {
        "session_id": "mock_sid",
        "question_index": 0,
        "user_answer": "Draft response with stolen token",
        "csrf_token": v_tok
    }
    resp = attacker.post("/interview-practice/submit", data=form_data)
    assert resp.status_code == 403
    assert "CSRF token missing or invalid" in resp.get_json()["message"]


def test_legacy_interview_practice_submit_valid_csrf_succeeds():
    """Verify POST /interview-practice/submit with valid CSRF token records answer and navigates."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    # First, create a valid practice session
    gen_data = {
        "category": "ALL",
        "difficulty": "Easy",
        "max_questions": "3",
        "action": "practice",
        "csrf_token": token
    }
    resp_prac = client.post("/interview-studio/generate", data=gen_data, follow_redirects=False)
    assert resp_prac.status_code == 302

    # Get active session ID from session
    with client.session_transaction() as sess:
        sid = sess["active_interview_session_id"]

    # Submit answer with valid CSRF token
    submit_data = {
        "session_id": sid,
        "question_index": 0,
        "user_answer": "Situation: Implemented microservice. Task: Scale throughput. Action: Used Redis. Result: Latency reduced 50%.",
        "direction": "next",
        "csrf_token": token
    }
    resp_submit = client.post("/interview-practice/submit", data=submit_data, follow_redirects=False)
    assert resp_submit.status_code == 302
    assert "/interview-practice" in resp_submit.headers["Location"]


# =========================================================================
# 4. Session Continuity and Token Retention
# =========================================================================

def test_session_continuity_across_token_retrieval_and_mutations():
    """Verify session continuity: token acquired via /api/csrf-token remains valid across sequential mutations."""
    client = app.test_client()

    # Step 1: Client initializes session and retrieves CSRF token
    token = client.get("/api/csrf-token").get_json()["csrf_token"]
    assert token

    # Step 2: First mutation (POST /analyze) succeeds
    form_data = {
        "resume_text": "Senior ML Engineer with PyTorch, Scikit-learn, Docker, and Kubernetes.",
        "job_description": "Seeking ML Engineer with Python and Docker.",
        "csrf_token": token
    }
    r1 = client.post("/analyze", data=form_data, follow_redirects=False)
    assert r1.status_code == 302

    # Step 3: Second mutation (POST /interview-studio/generate) using the same session & token succeeds
    r2 = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "3",
        "action": "generate",
        "csrf_token": token
    })
    assert r2.status_code == 200

    # Step 4: Third mutation (POST /api/mentor/update-name) using the same session & token header succeeds
    r3 = client.post("/api/mentor/update-name", json={"preferred_name": "Dave"}, headers={"X-CSRF-Token": token})
    assert r3.status_code == 200
    assert r3.get_json()["preferred_name"] == "Dave"
