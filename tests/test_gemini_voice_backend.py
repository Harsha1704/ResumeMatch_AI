"""
Unit and Integration Tests for Gemini Live API Voice Backend (Phase 2).
Covers:
  - Ephemeral token creation with authenticated session and CSRF.
  - Fail-closed security: CSRF, unauthenticated, cross-owner isolation, completed session checks.
  - Privacy & Candidate Consent verification.
  - ₹0 Free-Tier Budget Protection: Paid model rejection and billable tool prevention.
  - Server-side API key protection (permanent GEMINI_API_KEY is never exposed).
  - Rate limiting (5 requests per 10 minutes).
  - Quota exhaustion (HTTP 429) and auth failure (HTTP 502) error handling.
  - PII redaction: confirms phone, email, address, and URLs are removed from prompt context.
  - Regression assurance: existing interview endpoints remain unaffected.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure testing environment is active
os.environ["RESUMEMATCH_ENV"] = "testing"

from app import app
from src.interview import (
    InterviewSessionManager,
    GeminiVoiceService,
    get_voice_rate_limiter,
    strip_candidate_pii,
)
from src.interview.gemini_voice_service import (
    GeminiVoiceQuotaExceededError,
    GeminiVoiceAuthError,
    GeminiVoiceConfigError,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the global rate limiter before each test."""
    limiter = get_voice_rate_limiter()
    limiter.reset()
    yield
    limiter.reset()


def _create_authenticated_session(client, questions=None, candidate_evidence=None):
    """Helper to establish an authenticated session with CSRF token and a sample interview session."""
    # 1. Fetch CSRF token
    csrf_resp = client.get("/api/csrf-token")
    assert csrf_resp.status_code == 200
    csrf_data = csrf_resp.get_json()
    csrf_token = csrf_data["csrf_token"]

    # 2. Touch interview-practice to establish interview_owner_id
    practice_init = client.get("/api/interview-practice")
    assert practice_init.status_code == 200
    init_data = practice_init.get_json()
    session_id = init_data["session_id"]

    return csrf_token, session_id


# =========================================================================
# 1. CSRF and Input Validation Tests
# =========================================================================

def test_voice_token_missing_csrf_rejected(client):
    """Rejects request with 403 when CSRF token is missing."""
    resp = client.post("/api/interview/voice/token", json={
        "session_id": "dummy-session-id",
        "candidate_consent": True
    })
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["status"] == "error"
    assert "CSRF" in data["message"]


def test_voice_token_invalid_csrf_rejected(client):
    """Rejects request with 403 when CSRF token is invalid or cross-session mismatched."""
    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": "invalid-token-12345"},
        json={
            "session_id": "dummy-session-id",
            "candidate_consent": True
        }
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert "CSRF" in data["message"]


def test_voice_token_missing_session_id_rejected(client):
    """Rejects request with 400 when session_id is omitted or empty."""
    csrf_token, _ = _create_authenticated_session(client)
    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={"candidate_consent": True}
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Missing or invalid session_id" in data["message"]


def test_voice_token_nonexistent_session_returns_404(client):
    """Rejects request with 404 when session_id does not exist."""
    csrf_token, _ = _create_authenticated_session(client)
    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "candidate_consent": True
        }
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert "Interview session not found" in data["message"]


# =========================================================================
# 2. Ownership & Session Eligibility Isolation
# =========================================================================

def test_voice_token_cross_owner_isolation_rejected(client):
    """Rejects request with 403 when user attempts to access an interview session owned by another user."""
    # User A creates a session
    csrf_a, session_id_a = _create_authenticated_session(client)

    # User B creates fresh client session
    with app.test_client() as client_b:
        csrf_b, session_id_b = _create_authenticated_session(client_b)

        # User B attempts to access User A's session
        resp = client_b.post(
            "/api/interview/voice/token",
            headers={"X-CSRF-Token": csrf_b},
            json={
                "session_id": session_id_a,
                "candidate_consent": True
            }
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert "Unauthorized access" in data["message"]


def test_voice_token_completed_session_rejected(client):
    """Rejects request with 400 if the interview session is already completed."""
    csrf_token, session_id = _create_authenticated_session(client)

    # Complete the session
    session_obj = InterviewSessionManager.get_session(session_id)
    assert session_obj is not None
    session_obj.complete_session()
    assert session_obj.is_completed is True

    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "candidate_consent": True
        }
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Completed interview sessions cannot be re-opened" in data["message"]


# =========================================================================
# 3. Privacy & Candidate Consent Verification
# =========================================================================

def test_voice_token_missing_candidate_consent_rejected(client):
    """Rejects request with 400 when explicit candidate consent is missing or False."""
    csrf_token, session_id = _create_authenticated_session(client)

    # Case A: candidate_consent omitted
    resp_omitted = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={"session_id": session_id}
    )
    assert resp_omitted.status_code == 400
    assert "Candidate consent is required" in resp_omitted.get_json()["message"]

    # Case B: candidate_consent is False
    resp_false = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "candidate_consent": False
        }
    )
    assert resp_false.status_code == 400
    assert "Candidate consent is required" in resp_false.get_json()["message"]


def test_pii_stripping_logic():
    """Verifies that candidate PII (phone, email, address, URLs, IDs) is stripped from text."""
    dirty_text = (
        "Candidate John Doe. Email: john.doe@example.com. Phone: (555) 123-4567. "
        "Address: 123 Main Street, Suite 400. Portfolio: https://github.com/johndoe. "
        "SSN: 123-45-6789. Experienced in Python, Docker, and PostgreSQL."
    )
    clean_text = strip_candidate_pii(dirty_text)

    assert "john.doe@example.com" not in clean_text
    assert "[EMAIL_REDACTED]" in clean_text
    assert "123-4567" not in clean_text
    assert "[PHONE_REDACTED]" in clean_text
    assert "https://github.com/johndoe" not in clean_text
    assert "[URL_REDACTED]" in clean_text
    assert "123 Main Street" not in clean_text
    assert "[ADDRESS_REDACTED]" in clean_text
    assert "123-45-6789" not in clean_text
    assert "[ID_REDACTED]" in clean_text

    # Technical skills remain intact
    assert "Python" in clean_text
    assert "Docker" in clean_text
    assert "PostgreSQL" in clean_text


# =========================================================================
# 4. ₹0 Free-Tier Protection & Model Eligibility
# =========================================================================

def test_paid_model_strictly_rejected(client):
    """Guarantees ₹0 budget by rejecting paid models (e.g. gemini-1.5-pro, gemini-ultra) and unapproved models."""
    csrf_token, session_id = _create_authenticated_session(client)

    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "candidate_consent": True,
            "model": "gemini-1.5-pro"
        }
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "not in the approved ₹0 Free Tier allowlist" in data["message"]


def test_missing_api_key_returns_503(client, monkeypatch):
    """Returns 503 Service Unavailable when GEMINI_API_KEY is not configured on the server."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("src.interview.gemini_voice_service.GeminiVoiceService.get_api_key", return_value=""):
        csrf_token, session_id = _create_authenticated_session(client)

        resp = client.post(
            "/api/interview/voice/token",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "session_id": session_id,
                "candidate_consent": True
            }
        )
        assert resp.status_code == 503
        data = resp.get_json()
        assert "GEMINI_API_KEY is not configured on the server" in data["message"]


# =========================================================================
# 5. Rate Limiting Protection
# =========================================================================

def test_voice_token_rate_limiting_enforced(client, monkeypatch):
    """Enforces maximum 5 token requests per 10 minutes to protect free-tier quotas."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-free-tier-test-key")
    csrf_token, session_id = _create_authenticated_session(client)

    mock_token = {"token": "auth_tokens/test_token_123", "model": "gemini-3.8-live", "expires_in_seconds": 1800}

    # Make 5 successful requests
    for i in range(5):
        resp = client.post(
            "/api/interview/voice/token",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "session_id": session_id,
                "candidate_consent": True,
                "_mock_token_response": mock_token
            }
        )
        assert resp.status_code == 200

    # 6th request must be rejected with 429 Too Many Requests
    resp_rate_limited = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "candidate_consent": True,
            "_mock_token_response": mock_token
        }
    )
    assert resp_rate_limited.status_code == 429
    data = resp_rate_limited.get_json()
    assert "Voice session rate limit reached" in data["message"]


# =========================================================================
# 6. Ephemeral Token Generation & Permanent Key Protection
# =========================================================================

def test_voice_token_success_authenticated(client, monkeypatch):
    """
    Verifies that an authenticated request with candidate consent:
    1. Returns status success with ephemeral token.
    2. Includes sanitized context and system instruction.
    3. NEVER exposes the permanent server-side GEMINI_API_KEY.
    4. Connects via native WebSocket URL and targets gemini-3.8-live.
    """
    secret_key = "AIzaSySecretTestKeyThatMustNeverLeakToClient"
    monkeypatch.setenv("GEMINI_API_KEY", secret_key)
    monkeypatch.setenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")

    csrf_token, session_id = _create_authenticated_session(client)

    mock_token = {
        "token": "auth_tokens/ephemeral_live_mock_xyz123",
        "model": "models/gemini-3.8-live",
        "websocket_url": "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent",
        "expires_in_seconds": 1800,
        "uses_allowed": 1
    }

    resp = client.post(
        "/api/interview/voice/token",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "candidate_consent": True,
            "_mock_token_response": mock_token
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["session_id"] == session_id
    assert data["token"] == "auth_tokens/ephemeral_live_mock_xyz123"
    assert data["model"] == "models/gemini-3.8-live"
    assert data["websocket_url"].startswith("wss://")
    assert data["expires_in_seconds"] == 1800
    assert "system_instruction" in data
    assert "Ask ONE question at a time" in data["system_instruction"]

    # Security Assertion: Confirm server permanent secret key is NOT in response body or headers
    raw_response_text = resp.data.decode("utf-8")
    assert secret_key not in raw_response_text
    for h_name, h_val in resp.headers:
        assert secret_key not in h_val


# =========================================================================
# 7. Quota Exhaustion & Error Handling
# =========================================================================

def test_voice_token_quota_exhaustion_handled(client, monkeypatch):
    """Verifies that HTTP 429 from Google returns a clean, user-friendly 429 response."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-free-tier-test-key")
    csrf_token, session_id = _create_authenticated_session(client)

    with patch("src.interview.gemini_voice_service.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.ok = False
        mock_post.return_value = mock_response

        resp = client.post(
            "/api/interview/voice/token",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "session_id": session_id,
                "candidate_consent": True
            }
        )
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["code"] == "QUOTA_EXHAUSTED"
        assert "quota exhausted" in data["message"].lower()


def test_voice_token_auth_failure_handled(client, monkeypatch):
    """Verifies that HTTP 401/403 from Google returns a 502 Bad Gateway response."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-free-tier-test-key")
    csrf_token, session_id = _create_authenticated_session(client)

    with patch("src.interview.gemini_voice_service.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.ok = False
        mock_post.return_value = mock_response

        resp = client.post(
            "/api/interview/voice/token",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "session_id": session_id,
                "candidate_consent": True
            }
        )
        assert resp.status_code == 502
        data = resp.get_json()
        assert data["code"] == "AUTH_FAILURE"


# =========================================================================
# 8. Regression Assurance for Existing Interview Endpoints
# =========================================================================

def test_existing_interview_practice_routes_unaffected(client):
    """Verifies that existing text practice, studio, and results endpoints continue working normally."""
    csrf_token, session_id = _create_authenticated_session(client)

    # Verify GET /api/interview-practice returns question
    practice_resp = client.get(f"/api/interview-practice?session_id={session_id}")
    assert practice_resp.status_code == 200
    assert "question" in practice_resp.get_json()

    # Verify POST /api/interview-practice/submit records an answer
    submit_resp = client.post(
        "/api/interview-practice/submit",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": session_id,
            "question_index": 0,
            "answer_text": "I utilized Python with PyTorch and PostgreSQL for distributed data processing."
        }
    )
    assert submit_resp.status_code == 200
    assert submit_resp.get_json()["status"] == "success"

    # Verify GET /api/interview-results returns evaluation
    results_resp = client.get(f"/api/interview-results?session_id={session_id}")
    assert results_resp.status_code == 200
    assert "results" in results_resp.get_json()


# =========================================================================
# 9. Key Precedence and Security Isolation Tests
# =========================================================================

def test_gemini_api_key_env_precedence(monkeypatch):
    """Verifies that backend environment variable GEMINI_API_KEY takes precedence."""
    test_env_key = "AIzaSyTestEnvironmentKey_StrictPrecedence"
    monkeypatch.setenv("GEMINI_API_KEY", test_env_key)
    loaded_key = GeminiVoiceService.get_api_key()
    assert loaded_key == test_env_key


def test_gemini_key_fallback_local_file(monkeypatch, tmp_path):
    """Verifies fallback to local gemini.txt file when GEMINI_API_KEY is not in environment."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    fake_gemini_file = tmp_path / "gemini.txt"
    fake_gemini_file.write_text("API KEY\nAIzaSyTestLocalFileKey123\n", encoding="utf-8")
    with patch("src.interview.gemini_voice_service.REPO_ROOT", tmp_path):
        loaded_key = GeminiVoiceService.get_api_key()
        assert loaded_key == "AIzaSyTestLocalFileKey123"


# =========================================================================
# 10. Strict Allowlist & Model Constraints Verification
# =========================================================================

def test_model_allowlist_strictly_gemini_3_8_live():
    """Verifies that only gemini-3.8-live is permitted in the ₹0 Free Tier allowlist."""
    from src.interview.gemini_voice_service import APPROVED_FREE_TIER_MODELS, DEFAULT_FREE_TIER_MODEL
    assert APPROVED_FREE_TIER_MODELS == {"gemini-3.8-live"}
    assert DEFAULT_FREE_TIER_MODEL == "gemini-3.8-live"

    # Verify approved model passes
    valid, msg = GeminiVoiceService.validate_model_eligibility("gemini-3.8-live")
    assert valid is True

    # Verify models/ prefix is normalized and accepted
    valid, msg = GeminiVoiceService.validate_model_eligibility("models/gemini-3.8-live")
    assert valid is True

    # Verify rejected models
    for disallowed in ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-ultra", "gpt-4o-realtime"]:
        valid, msg = GeminiVoiceService.validate_model_eligibility(disallowed)
        assert valid is False
        assert "not in the approved ₹0 Free Tier allowlist" in msg


def test_ephemeral_token_websocket_compatibility():
    """Verifies ephemeral token generation parameters, single-use, and WebSocket target."""
    from src.interview.gemini_voice_service import GEMINI_LIVE_WEBSOCKET_URL
    assert GEMINI_LIVE_WEBSOCKET_URL == (
        "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    )

    # Validate simulated token response schema
    with patch("src.interview.gemini_voice_service.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "auth_tokens/test_ephemeral_token_abc"}
        mock_post.return_value = mock_resp

        result = GeminiVoiceService.create_ephemeral_token(
            model="gemini-3.8-live",
            timeout_seconds=5
        )

        assert result["token"] == "auth_tokens/test_ephemeral_token_abc"
        assert result["model"] == "models/gemini-3.8-live"
        assert result["websocket_url"] == GEMINI_LIVE_WEBSOCKET_URL
        assert result["uses_allowed"] == 1
        assert result["expires_in_seconds"] == 1800

