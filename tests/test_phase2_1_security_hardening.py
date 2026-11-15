"""
Comprehensive Security Hardening and Production Persistence Test Suite for Phase 2.1.
Verifies:
1. Interview session cross-session authorization (403 Forbidden).
2. Interview answer submission cross-session protection (403 Forbidden).
3. Interview results cross-session protection (403 Forbidden).
4. Nonexistent interview session handling (404 Not Found).
5. CSRF token issuance (/api/csrf-token).
6. CSRF missing token rejection on browser APIs (403 Forbidden).
7. CSRF invalid token rejection on browser APIs (403 Forbidden).
8. CSRF valid token acceptance with constant-time comparison.
9. Headless /api/match documented programmatic exemption.
10. PERSISTENT_STORAGE_DIR configurable path support.
"""

import os
import pytest
from app import app
from src.interview import InterviewSessionManager
from src.services.analysis_store import AnalysisStore


@pytest.fixture(autouse=True)
def reset_testing_flags():
    app.config["TESTING"] = True
    app.config["ENFORCE_CSRF_IN_TESTS"] = False
    yield
    app.config["TESTING"] = True
    app.config["ENFORCE_CSRF_IN_TESTS"] = False


def test_interview_session_cross_session_protection():
    """Verify that an interview practice session cannot be accessed across different browser sessions."""
    # Session 1: creates practice session
    with app.test_client() as client1:
        gen_res = client1.post(
            "/api/interview-studio/generate",
            json={"action": "practice", "max_questions": 5}
        )
        assert gen_res.status_code == 200
        data1 = gen_res.get_json()
        session_id = data1["active_session_id"]
        assert session_id is not None

        # Valid owner in Session 1 can read practice question
        owner_res = client1.get(f"/api/interview-practice?session_id={session_id}")
        assert owner_res.status_code == 200
        assert owner_res.get_json()["session_id"] == session_id

    # Session 2: intruder trying to inspect Session 1's practice session
    with app.test_client() as client2:
        intruder_res = client2.get(f"/api/interview-practice?session_id={session_id}")
        assert intruder_res.status_code == 403
        body = intruder_res.get_json()
        assert "unauthorized" in body["message"].lower()


def test_interview_answer_cross_session_protection():
    """Verify that users cannot submit answers into another candidate's practice session."""
    with app.test_client() as client1:
        gen_res = client1.post(
            "/api/interview-studio/generate",
            json={"action": "practice", "max_questions": 5}
        )
        assert gen_res.status_code == 200
        session_id = gen_res.get_json()["active_session_id"]

    # Session 2 tries to submit answer into Session 1's session_id
    with app.test_client() as client2:
        intruder_submit = client2.post(
            "/api/interview-practice/submit",
            json={
                "session_id": session_id,
                "question_index": 0,
                "user_answer": "Malicious injected answer",
                "direction": "next"
            }
        )
        assert intruder_submit.status_code == 403
        assert "unauthorized" in intruder_submit.get_json()["message"].lower()

    # Session 1 owner can submit answer legitimately
    with client1:
        owner_submit = client1.post(
            "/api/interview-practice/submit",
            json={
                "session_id": session_id,
                "question_index": 0,
                "user_answer": "I implemented a distributed worker architecture using Python and Redis.",
                "direction": "next"
            }
        )
        assert owner_submit.status_code == 200
        assert owner_submit.get_json()["session_id"] == session_id


def test_interview_results_cross_session_protection():
    """Verify that interview results are private and inaccessible to other browser sessions."""
    with app.test_client() as client1:
        gen_res = client1.post(
            "/api/interview-studio/generate",
            json={"action": "practice", "max_questions": 3}
        )
        session_id = gen_res.get_json()["active_session_id"]

        # Owner finishes practice
        client1.post(
            "/api/interview-practice/submit",
            json={
                "session_id": session_id,
                "question_index": 0,
                "user_answer": "Configured microservices deployment using Docker and Kubernetes.",
                "direction": "finish"
            }
        )

        owner_res = client1.get(f"/api/interview-results?session_id={session_id}")
        assert owner_res.status_code == 200
        assert owner_res.get_json()["results"]["session_id"] == session_id

    # Session 2 attempts to read Session 1's results
    with app.test_client() as client2:
        intruder_results = client2.get(f"/api/interview-results?session_id={session_id}")
        assert intruder_results.status_code == 403
        assert "unauthorized" in intruder_results.get_json()["message"].lower()


def test_interview_nonexistent_session_returns_404():
    """Verify that unknown or expired practice session IDs return 404 Not Found."""
    with app.test_client() as client:
        # 1. Practice query
        res_get = client.get("/api/interview-practice?session_id=nonexistent-session-uuid-999")
        assert res_get.status_code == 404

        # 2. Answer submit
        res_sub = client.post(
            "/api/interview-practice/submit",
            json={"session_id": "nonexistent-session-uuid-999", "question_index": 0, "user_answer": "test"}
        )
        assert res_sub.status_code == 404

        # 3. Results query
        res_res = client.get("/api/interview-results?session_id=nonexistent-session-uuid-999")
        assert res_res.status_code == 404


def test_csrf_token_endpoint():
    """Verify GET /api/csrf-token issues a cryptographically secure token."""
    with app.test_client() as client:
        res = client.get("/api/csrf-token")
        assert res.status_code == 200
        body = res.get_json()
        assert body["status"] == "success"
        token = body["csrf_token"]
        assert isinstance(token, str)
        assert len(token) == 64  # secrets.token_hex(32) produces 64 hex characters


def test_csrf_missing_token_rejected_on_browser_api():
    """Verify state-changing browser API requests without CSRF token return 403 Forbidden."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    with app.test_client() as client:
        payload = {
            "resume_text": "Experienced Python Engineer.",
            "job_description": "Seeking Python Developer.",
            "target_role": "Python Engineer"
        }
        res = client.post("/api/analyze", json=payload)
        assert res.status_code == 403
        data = res.get_json()
        assert "csrf" in data["error_message"].lower()


def test_csrf_invalid_token_rejected_on_browser_api():
    """Verify state-changing browser API requests with forged token return 403 Forbidden."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    with app.test_client() as client:
        # Establish session first
        client.get("/api/csrf-token")

        payload = {
            "resume_text": "Experienced Python Engineer.",
            "job_description": "Seeking Python Developer.",
            "target_role": "Python Engineer"
        }
        res = client.post(
            "/api/analyze",
            json=payload,
            headers={"X-CSRF-Token": "forged_malicious_token_12345"}
        )
        assert res.status_code == 403
        data = res.get_json()
        assert "csrf" in data["error_message"].lower()


def test_csrf_valid_token_accepted_on_browser_api():
    """Verify state-changing browser API requests with valid token succeed."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    with app.test_client() as client:
        token_res = client.get("/api/csrf-token")
        assert token_res.status_code == 200
        valid_token = token_res.get_json()["csrf_token"]

        payload = {
            "resume_text": "Experienced Python Engineer with Scikit-learn and SQL experience.",
            "job_description": "Seeking Python Developer with SQL experience.",
            "target_role": "Python Developer"
        }
        res = client.post(
            "/api/analyze",
            json=payload,
            headers={"X-CSRF-Token": valid_token}
        )
        assert res.status_code == 200
        assert res.get_json()["status"] == "success"


def test_headless_api_match_exemption():
    """Verify that programmatic /api/match remains accessible without CSRF tokens (headless exception)."""
    app.config["ENFORCE_CSRF_IN_TESTS"] = True
    with app.test_client() as client:
        payload = {
            "resume_text": "Python Developer with machine learning expertise.",
            "job_description": "Wanted machine learning developer with Python.",
            "target_role": "Machine Learning Developer",
            "model_backend": "production"
        }
        res = client.post("/api/match", json=payload)
        assert res.status_code == 200
        assert res.get_json()["status"] == "success"


def test_persistent_storage_dir_configuration(tmp_path):
    """Verify that PERSISTENT_STORAGE_DIR correctly configures the SQLite database location."""
    persistent_mount = tmp_path / "persistent_disk"
    os.environ["PERSISTENT_STORAGE_DIR"] = str(persistent_mount)
    try:
        store = AnalysisStore()
        assert store.db_path.parent == persistent_mount.resolve()
        assert store.db_path.name == "analysis_store.sqlite"
        assert persistent_mount.exists()
    finally:
        os.environ.pop("PERSISTENT_STORAGE_DIR", None)
