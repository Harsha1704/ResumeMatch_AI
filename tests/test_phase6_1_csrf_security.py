"""
tests/test_phase6_1_csrf_security.py
Comprehensive Phase 6.1 CSRF & API Security Test Suite.

Verifies:
1. GET /api/csrf-token returns session-bound cryptographic CSRF token.
2. Fail-closed CSRF enforcement across ALL environments (including TESTING=True).
3. Missing token -> 403 Forbidden across all protected state-changing endpoints.
4. Invalid token -> 403 Forbidden across all protected state-changing endpoints.
5. Cross-session token mismatch -> 403 Forbidden across all protected state-changing endpoints.
6. Legitimate token and session -> Success (200 / 201).
7. Cross-session ownership protections remain strictly enforced alongside CSRF.
8. Public unauthenticated ML endpoint (/api/match) operates without CSRF.
9. Credentialed CORS preflight and headers for cross-origin frontend-to-backend communication.
"""

import io
import json
import pytest
from app import app, ANALYSIS_CACHE


@pytest.fixture(autouse=True)
def ensure_testing_mode():
    """Ensure testing mode is active for test execution while verifying fail-closed CSRF."""
    orig = app.config.get("TESTING")
    app.config["TESTING"] = True
    yield
    app.config["TESTING"] = orig


# =========================================================================
# 1. CSRF Token Delivery Endpoint (GET /api/csrf-token)
# =========================================================================

def test_csrf_token_endpoint_delivery():
    """Verify GET /api/csrf-token generates and delivers a valid session-bound hex token."""
    client = app.test_client()

    resp = client.get("/api/csrf-token")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    token = data["csrf_token"]
    assert isinstance(token, str)
    assert len(token) == 64  # secrets.token_hex(32) produces 64 hex characters

    # Verify session cookie was set and contains the same token
    with client.session_transaction() as sess:
        assert sess.get("csrf_token") == token

    # Calling /api/csrf-token again within the same session returns the stable token
    resp2 = client.get("/api/csrf-token")
    assert resp2.status_code == 200
    assert resp2.get_json()["csrf_token"] == token


def test_csrf_token_separate_sessions_isolation():
    """Verify separate sessions receive cryptographically isolated, distinct tokens."""
    c1 = app.test_client()
    c2 = app.test_client()

    r1 = c1.get("/api/csrf-token")
    r2 = c2.get("/api/csrf-token")

    t1 = r1.get_json()["csrf_token"]
    t2 = r2.get_json()["csrf_token"]

    assert t1 != t2
    assert len(t1) == 64
    assert len(t2) == 64


# =========================================================================
# 2. Universal Fail-Closed CSRF Enforcement on All Mutation Endpoints
# =========================================================================

PROTECTED_MUTATION_ENDPOINTS = [
    # (method, endpoint, json_payload, form_data)
    ("POST", "/api/mentor/update-name", {"preferred_name": "DevCandidate"}, None),
    ("POST", "/api/mentor/progress", {"task_key": "pytest_task", "status": "In Progress"}, None),
    ("POST", "/api/mentor/reset-progress", {}, None),
    ("POST", "/api/candidate/update-role", {"target_role": "Platform Engineer"}, None),
    ("POST", "/api/candidate/confirm-education", {"education": "B.Tech Computer Science"}, None),
    ("POST", "/api/interview/confirm-activity", {"activity_key": "pytest_mocking", "confirmed": True}, None),
    ("POST", "/api/interview/reset", {}, None),
    ("POST", "/api/interview/evaluate", {"user_answer": "STAR formatted response demonstrating Flask architecture"}, None),
]


@pytest.mark.parametrize("method,endpoint,payload,form_data", PROTECTED_MUTATION_ENDPOINTS)
def test_mutation_missing_csrf_returns_403(method, endpoint, payload, form_data):
    """Verify state-changing mutations without CSRF token fail closed with 403 Forbidden."""
    client = app.test_client()
    # Establish a session without sending the CSRF token in the request
    client.get("/api/csrf-token")

    if method == "POST":
        resp = client.post(endpoint, json=payload)
    elif method == "DELETE":
        resp = client.delete(endpoint)

    assert resp.status_code == 403
    data = resp.get_json()
    assert data["status"] == "error"
    assert "CSRF token missing or invalid" in data["message"]


@pytest.mark.parametrize("method,endpoint,payload,form_data", PROTECTED_MUTATION_ENDPOINTS)
def test_mutation_invalid_csrf_returns_403(method, endpoint, payload, form_data):
    """Verify state-changing mutations with invalid CSRF token fail closed with 403 Forbidden."""
    client = app.test_client()
    client.get("/api/csrf-token")

    bad_headers = {"X-CSRF-Token": "invalid_forged_hex_token_0000000000000000000000000000000000000000"}

    if method == "POST":
        resp = client.post(endpoint, json=payload, headers=bad_headers)
    elif method == "DELETE":
        resp = client.delete(endpoint, headers=bad_headers)

    assert resp.status_code == 403
    data = resp.get_json()
    assert data["status"] == "error"
    assert "CSRF token missing or invalid" in data["message"]


@pytest.mark.parametrize("method,endpoint,payload,form_data", PROTECTED_MUTATION_ENDPOINTS)
def test_mutation_cross_session_csrf_returns_403(method, endpoint, payload, form_data):
    """Verify an attacker using Session A's CSRF token against Session B is rejected with 403 Forbidden."""
    victim = app.test_client()
    attacker = app.test_client()

    # Victim gets a valid token
    victim_tok = victim.get("/api/csrf-token").get_json()["csrf_token"]
    # Attacker has their own session
    attacker.get("/api/csrf-token")

    # Attacker tries to submit using victim's token
    cross_session_headers = {"X-CSRF-Token": victim_tok}

    if method == "POST":
        resp = attacker.post(endpoint, json=payload, headers=cross_session_headers)
    elif method == "DELETE":
        resp = attacker.delete(endpoint, headers=cross_session_headers)

    assert resp.status_code == 403
    data = resp.get_json()
    assert data["status"] == "error"
    assert "CSRF token missing or invalid" in data["message"]


@pytest.mark.parametrize("method,endpoint,payload,form_data", PROTECTED_MUTATION_ENDPOINTS)
def test_mutation_valid_csrf_succeeds(method, endpoint, payload, form_data):
    """Verify legitimate requests with matching session and header token succeed."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    headers = {"X-CSRF-Token": token}
    if method == "POST":
        resp = client.post(endpoint, json=payload, headers=headers)
    elif method == "DELETE":
        resp = client.delete(endpoint, headers=headers)

    assert resp.status_code == 200
    assert resp.get_json()["status"] in ["success", "reset", "evaluated"]


# =========================================================================
# 3. Endpoint-Specific Hardening: /api/analyze (JSON & Multipart Form)
# =========================================================================

def test_api_analyze_json_csrf_enforcement():
    """Verify /api/analyze JSON submissions require valid CSRF token."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    payload = {
        "resume_text": "Senior Python Backend Developer with 5 years experience in Docker and PostgreSQL.",
        "job_description": "Wanted: Senior Python Engineer with Docker and database experience."
    }

    # 1. Missing CSRF header -> 403
    r_no_csrf = client.post("/api/analyze", json=payload)
    assert r_no_csrf.status_code == 403
    assert "CSRF token missing or invalid" in r_no_csrf.get_json()["message"]

    # 2. Invalid CSRF header -> 403
    r_bad_csrf = client.post("/api/analyze", json=payload, headers={"X-CSRF-Token": "bad_token"})
    assert r_bad_csrf.status_code == 403

    # 3. Valid CSRF header -> 200
    r_ok = client.post("/api/analyze", json=payload, headers={"X-CSRF-Token": token})
    assert r_ok.status_code == 200
    assert r_ok.get_json()["status"] == "success"


def test_api_analyze_multipart_csrf_enforcement():
    """Verify /api/analyze multipart form uploads require valid CSRF token in header or form field."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    # 1. Missing CSRF -> 403
    data1 = {
        "resume_file": (io.BytesIO(b"Candidate Python Engineer resume text content for unit test."), "resume.txt"),
        "job_description": "Python Engineer wanted."
    }
    r_no_csrf = client.post("/api/analyze", data=data1, content_type="multipart/form-data")
    assert r_no_csrf.status_code == 403

    # 2. Valid CSRF via X-CSRF-Token header -> 200
    data2 = {
        "resume_file": (io.BytesIO(b"Candidate Python Engineer resume text content for unit test."), "resume.txt"),
        "job_description": "Python Engineer wanted."
    }
    r_hdr = client.post("/api/analyze", data=data2, content_type="multipart/form-data", headers={"X-CSRF-Token": token})
    assert r_hdr.status_code == 200
    assert r_hdr.get_json()["status"] == "success"

    # 3. Valid CSRF via form field csrf_token -> 200
    data3 = {
        "resume_file": (io.BytesIO(b"Candidate Python Engineer resume text content for unit test."), "resume.txt"),
        "job_description": "Python Engineer wanted.",
        "csrf_token": token
    }
    r_form = client.post("/api/analyze", data=data3, content_type="multipart/form-data")
    assert r_form.status_code == 200
    assert r_form.get_json()["status"] == "success"


# =========================================================================
# 4. Career Mentor & Interview Studio Complex Endpoints
# =========================================================================

def test_career_mentor_evaluate_role_csrf():
    """Verify /api/career-mentor/evaluate-role enforces fail-closed CSRF."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    aid = "phase6_1_mentor_test_aid"
    ANALYSIS_CACHE[aid] = {
        "candidate_profile": {"name": {"full_name": "Test Candidate"}, "skills": [], "projects": []},
        "resume_skills": []
    }
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [aid]

    # Missing token -> 403
    r_missing = client.post("/api/career-mentor/evaluate-role", json={"role_name": "Backend Engineer", "analysis_id": aid})
    assert r_missing.status_code == 403

    # Valid token -> 200
    r_valid = client.post("/api/career-mentor/evaluate-role", json={"role_name": "Backend Engineer", "analysis_id": aid}, headers={"X-CSRF-Token": token})
    assert r_valid.status_code == 200
    assert r_valid.get_json()["status"] == "success"


def test_interview_sessions_lifecycle_csrf():
    """Verify /api/interview/sessions creation and deletion enforce CSRF and ownership."""
    client = app.test_client()
    token = client.get("/api/csrf-token").get_json()["csrf_token"]

    headers = {"X-CSRF-Token": token}

    # 1. Create session without CSRF -> 403
    r_create_no_csrf = client.post("/api/interview/sessions", json={"mode": "technical", "difficulty": "Medium", "max_questions": 5})
    assert r_create_no_csrf.status_code == 403

    # 2. Create session with valid CSRF -> 201
    r_create = client.post("/api/interview/sessions", json={"mode": "technical", "difficulty": "Medium", "max_questions": 5}, headers=headers)
    assert r_create.status_code == 201
    sid = r_create.get_json()["session"]["session_id"]

    # 3. Practice answer submit without CSRF -> 403
    r_ans_no_csrf = client.post("/api/interview-practice/submit", json={"session_id": sid, "question_index": 0, "user_answer": "Valid text answer."})
    assert r_ans_no_csrf.status_code == 403

    # 4. Practice answer submit with valid CSRF -> 200
    r_ans = client.post("/api/interview-practice/submit", json={"session_id": sid, "question_index": 0, "user_answer": "Valid text answer."}, headers=headers)
    assert r_ans.status_code == 200

    # 5. Delete session without CSRF -> 403
    r_del_no_csrf = client.delete(f"/api/interview/sessions/{sid}")
    assert r_del_no_csrf.status_code == 403

    # 6. Delete session with invalid CSRF -> 403
    r_del_bad = client.delete(f"/api/interview/sessions/{sid}", headers={"X-CSRF-Token": "bad"})
    assert r_del_bad.status_code == 403

    # 7. Delete session with valid CSRF -> 200
    r_del = client.delete(f"/api/interview/sessions/{sid}", headers=headers)
    assert r_del.status_code == 200


def test_cross_session_ownership_preserved_alongside_csrf():
    """Verify that even when an attacker presents their own valid CSRF token, cross-session ownership blocks access."""
    victim = app.test_client()
    attacker = app.test_client()

    v_tok = victim.get("/api/csrf-token").get_json()["csrf_token"]
    a_tok = attacker.get("/api/csrf-token").get_json()["csrf_token"]

    # Victim creates a session
    r_create = victim.post("/api/interview/sessions", json={"mode": "technical"}, headers={"X-CSRF-Token": v_tok})
    assert r_create.status_code == 201
    victim_sid = r_create.get_json()["session"]["session_id"]

    # Attacker attempts to delete victim's session using attacker's valid CSRF token -> 403 Unauthorized
    r_attack = attacker.delete(f"/api/interview/sessions/{victim_sid}", headers={"X-CSRF-Token": a_tok})
    assert r_attack.status_code == 403
    assert "unauthorized" in r_attack.get_json()["message"].lower()

    # Victim's session still exists
    r_check = victim.get(f"/api/interview/sessions/{victim_sid}")
    assert r_check.status_code == 200


# =========================================================================
# 5. Unauthenticated Programmatic ML Endpoint (/api/match)
# =========================================================================

def test_api_match_stateless_ml_does_not_require_csrf():
    """
    Verify /api/match does not require CSRF token.
    /api/match is a stateless, programmatic ML scoring API protected by IP rate limiting
    and does not mutate or read any session or server-side user state.
    """
    client = app.test_client()
    payload = {
        "resume_text": "Python engineer with SQL and Docker experience.",
        "job_description": "Python, SQL, Docker required."
    }
    resp = client.post("/api/match", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "compatibility_score" in data


# =========================================================================
# 6. CORS and Credential Headers Verification
# =========================================================================

def test_cors_preflight_allows_csrf_header():
    """Verify CORS preflight OPTIONS requests allow X-CSRF-Token and credentials for configured frontend origins."""
    client = app.test_client()
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token, Accept"
    }
    resp = client.open("/api/analyze", method="OPTIONS", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"
    allow_headers = resp.headers.get("Access-Control-Allow-Headers", "")
    assert "X-CSRF-Token" in allow_headers or "x-csrf-token" in allow_headers.lower()
