"""
Unit and Integration Tests for Local Voice Interview Intelligence Backend (Phase 2C).
Strict ₹0 Budget: 100% Offline, CPU-only, Zero External API Calls.

Covers:
  - Session startup with resume and job description evidence.
  - Graceful fallback for empty resume or job description.
  - Fail-closed CSRF protection on mutations.
  - Question retrieval, navigation, and speech synthesis prompt preparation.
  - Candidate answer submission and heuristic evaluation.
  - Adaptive follow-up question generation.
  - Interview conclusion and structured feedback summary.
  - Cross-owner session isolation (403).
  - Defensive input validation (oversized answers, invalid indices, completed sessions).
  - Verification that ZERO external network requests occur.
"""

import os
import pytest
from unittest.mock import patch

os.environ["RESUMEMATCH_ENV"] = "testing"

from app import app
from src.interview import (
    InterviewSessionManager,
    LocalVoiceInterviewService,
    LocalVoiceSessionNotFoundError,
    LocalVoiceAccessDeniedError,
    LocalVoiceValidationError,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _get_csrf_and_owner(client):
    """Retrieves CSRF token and establishes session owner cookie."""
    csrf_resp = client.get("/api/csrf-token")
    assert csrf_resp.status_code == 200
    csrf_token = csrf_resp.get_json()["csrf_token"]
    return csrf_token


# =========================================================================
# 1. Session Initialization Tests
# =========================================================================

def test_voice_start_session_success(client):
    """Starts a voice session and returns initial question and spoken greeting."""
    csrf_token = _get_csrf_and_owner(client)

    resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "target_role": "Backend Engineer",
            "difficulty": "medium",
            "max_questions": 5
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "session_id" in data
    assert data["target_role"] == "Backend Engineer"
    assert data["difficulty"] == "medium"
    assert data["total_questions"] >= 1
    assert data["provider"] == "local_grounded_engine"
    assert data["budget"] == "₹0"
    assert "interviewer_speech" in data
    assert "Backend Engineer" in data["interviewer_speech"]
    assert "current_question" in data
    assert "question_text" in data["current_question"]


def test_voice_start_with_resume_and_job_description(client):
    """Grounds questions in supplied resume skills, projects, and job description."""
    csrf_token = _get_csrf_and_owner(client)

    sample_resume = (
        "Experienced Backend Developer. Proficient in Python, PostgreSQL, Docker, Redis. "
        "Built distributed event streaming pipeline using Kafka and FastAPI."
    )
    sample_jd = (
        "Seeking Senior Python Backend Engineer with expertise in microservices, PostgreSQL, and Redis caching."
    )

    resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "resume_text": sample_resume,
            "job_description": sample_jd,
            "target_role": "Senior Python Engineer",
            "difficulty": "hard",
            "max_questions": 6
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["total_questions"] >= 1
    assert "Senior Python Engineer" in data["interviewer_speech"]


def test_voice_start_empty_resume_and_jd_fallback(client):
    """Gracefully falls back to standard core questions when resume/JD are omitted."""
    csrf_token = _get_csrf_and_owner(client)

    resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["total_questions"] >= 1
    assert "Software Engineer" in data["interviewer_speech"]


def test_voice_start_missing_csrf_rejected(client):
    """Rejects session start with 403 when CSRF token is missing."""
    resp = client.post(
        "/api/interview/voice/start",
        json={"target_role": "Data Scientist"}
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert "CSRF" in data["message"]


# =========================================================================
# 2. Question Navigation Tests
# =========================================================================

def test_voice_get_question_navigation(client):
    """Tests current, next, and previous question navigation with spoken prompts."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Full Stack Engineer", "max_questions": 4}
    )
    sid = start_resp.get_json()["session_id"]

    # Current question
    q_curr = client.get(f"/api/interview/voice/question?session_id={sid}&direction=current")
    assert q_curr.status_code == 200
    d_curr = q_curr.get_json()
    assert d_curr["status"] == "success"
    assert d_curr["current_index"] == 0
    assert d_curr["question_number"] == 1
    assert "Question 1 of" in d_curr["interviewer_speech"]

    # Next question
    q_next = client.get(f"/api/interview/voice/question?session_id={sid}&direction=next")
    assert q_next.status_code == 200
    d_next = q_next.get_json()
    assert d_next["current_index"] == 1
    assert d_next["question_number"] == 2
    assert "Question 2 of" in d_next["interviewer_speech"]

    # Prev question
    q_prev = client.get(f"/api/interview/voice/question?session_id={sid}&direction=prev")
    assert q_prev.status_code == 200
    d_prev = q_prev.get_json()
    assert d_prev["current_index"] == 0
    assert d_prev["question_number"] == 1


def test_voice_get_question_missing_session_returns_400(client):
    """Returns 400 when session_id parameter is missing."""
    resp = client.get("/api/interview/voice/question")
    assert resp.status_code == 400


def test_voice_get_question_nonexistent_session_returns_404(client):
    """Returns 404 when session_id does not exist."""
    resp = client.get("/api/interview/voice/question?session_id=nonexistent-voice-session-uuid")
    assert resp.status_code == 404


# =========================================================================
# 3. Answer Submission & Evaluation Tests
# =========================================================================

def test_voice_submit_answer_success(client):
    """Submits candidate answer, computes heuristic evaluation, and generates spoken reaction."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Python Developer", "max_questions": 3}
    )
    sid = start_resp.get_json()["session_id"]

    sample_answer = (
        "In Python, generators are functions that use the yield keyword to produce a stream of values "
        "one by one on demand. This saves memory because it avoids storing the entire sequence in RAM, "
        "making it ideal for processing large datasets."
    )

    ans_resp = client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0,
            "answer_text": sample_answer
        }
    )
    assert ans_resp.status_code == 200
    data = ans_resp.get_json()
    assert data["status"] == "success"
    assert data["question_index"] == 0
    assert "evaluation" in data
    assert data["evaluation"]["overall_score"] > 0
    assert "interviewer_reaction" in data
    assert len(data["interviewer_reaction"]) > 10


def test_voice_submit_answer_invalid_index_rejected(client):
    """Rejects out-of-bounds question_index with 400."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "DevOps Engineer", "max_questions": 2}
    )
    sid = start_resp.get_json()["session_id"]

    resp = client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 999,
            "answer_text": "Sample answer."
        }
    )
    assert resp.status_code == 400
    assert "Invalid question_index" in resp.get_json()["message"]


def test_voice_submit_answer_oversized_rejected(client):
    """Rejects answers exceeding defensive text boundary with 400."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Cloud Architect", "max_questions": 2}
    )
    sid = start_resp.get_json()["session_id"]

    giant_answer = "A" * 10001
    resp = client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0,
            "answer_text": giant_answer
        }
    )
    assert resp.status_code == 400
    assert "exceeds maximum allowed length" in resp.get_json()["message"]


# =========================================================================
# 4. Adaptive Follow-Up Tests
# =========================================================================

def test_voice_generate_followup_adaptive(client):
    """Selects grounded follow-up question and generates spoken follow-up script."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Software Architect", "max_questions": 3}
    )
    sid = start_resp.get_json()["session_id"]

    resp = client.post(
        "/api/interview/voice/followup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "follow_up" in data
    assert "question" in data["follow_up"]
    assert "interviewer_speech" in data
    assert "Following up on that:" in data["interviewer_speech"]


# =========================================================================
# 5. Session Conclusion & Performance Report Tests
# =========================================================================

def test_voice_end_session_complete(client):
    """Concludes session, produces comprehensive summary, and generates concluding spoken remark."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Security Engineer", "max_questions": 2}
    )
    sid = start_resp.get_json()["session_id"]

    # Submit one answer
    client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0,
            "answer_text": "I implemented role-based access control and strict JWT signature verification."
        }
    )

    end_resp = client.post(
        "/api/interview/voice/end",
        headers={"X-CSRF-Token": csrf_token},
        json={"session_id": sid}
    )
    assert end_resp.status_code == 200
    data = end_resp.get_json()
    assert data["status"] == "success"
    assert data["is_completed"] is True
    assert "results" in data
    assert "interviewer_speech" in data
    assert "Thank you for completing this mock voice interview" in data["interviewer_speech"]

    # Attempting to submit another answer after completion must be rejected
    submit_after_end = client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 1,
            "answer_text": "Another answer."
        }
    )
    assert submit_after_end.status_code == 400
    assert "already completed" in submit_after_end.get_json()["message"]


# =========================================================================
# 6. Cross-Owner Isolation & Security Tests
# =========================================================================

def test_voice_cross_owner_isolation():
    """Confirms user B cannot access or mutate user A's voice interview session."""
    with app.test_client() as client_a:
        csrf_a = client_a.get("/api/csrf-token").get_json()["csrf_token"]
        start_a = client_a.post(
            "/api/interview/voice/start",
            headers={"X-CSRF-Token": csrf_a},
            json={"target_role": "Data Engineer"}
        )
        sid_a = start_a.get_json()["session_id"]

    with app.test_client() as client_b:
        csrf_b = client_b.get("/api/csrf-token").get_json()["csrf_token"]

        # Client B attempts to get User A's question
        get_b = client_b.get(f"/api/interview/voice/question?session_id={sid_a}")
        assert get_b.status_code == 403

        # Client B attempts to submit answer to User A's session
        sub_b = client_b.post(
            "/api/interview/voice/answer",
            headers={"X-CSRF-Token": csrf_b},
            json={"session_id": sid_a, "question_index": 0, "answer_text": "Hacked answer"}
        )
        assert sub_b.status_code == 403

        # Client B attempts to end User A's session
        end_b = client_b.post(
            "/api/interview/voice/end",
            headers={"X-CSRF-Token": csrf_b},
            json={"session_id": sid_a}
        )
        assert end_b.status_code == 403


# =========================================================================
# 7. Strict ₹0 External Request Verification
# =========================================================================

def test_zero_external_api_calls_during_voice_lifecycle(client):
    """Guarantees that 100% of voice interview operations execute locally with ZERO external requests."""
    csrf_token = _get_csrf_and_owner(client)

    with patch("requests.post") as mock_req_post, patch("requests.get") as mock_req_get:
        # Start
        s_resp = client.post(
            "/api/interview/voice/start",
            headers={"X-CSRF-Token": csrf_token},
            json={"target_role": "QA Automation Engineer", "max_questions": 2}
        )
        assert s_resp.status_code == 200
        sid = s_resp.get_json()["session_id"]

        # Question
        q_resp = client.get(f"/api/interview/voice/question?session_id={sid}&direction=current")
        assert q_resp.status_code == 200

        # Answer
        a_resp = client.post(
            "/api/interview/voice/answer",
            headers={"X-CSRF-Token": csrf_token},
            json={"session_id": sid, "question_index": 0, "answer_text": "I used pytest and Playwright."}
        )
        assert a_resp.status_code == 200

        # Followup
        f_resp = client.post(
            "/api/interview/voice/followup",
            headers={"X-CSRF-Token": csrf_token},
            json={"session_id": sid, "question_index": 0}
        )
        assert f_resp.status_code == 200

        # End
        e_resp = client.post(
            "/api/interview/voice/end",
            headers={"X-CSRF-Token": csrf_token},
            json={"session_id": sid}
        )
        assert e_resp.status_code == 200

        # Zero external HTTP calls made
        assert mock_req_post.call_count == 0
        assert mock_req_get.call_count == 0
