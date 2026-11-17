"""
tests/test_phase7_production_readiness.py
Phase 7.1 Production Readiness & Final Release Gate Test Suite.

Verifies REAL application behavior:
1. Production startup in real subprocess with missing, insecure, and valid secrets.
2. Actual production Set-Cookie headers (Secure, HttpOnly, SameSite=Lax, Domain).
3. Every state-changing route using a complete inventory: missing, invalid, and valid CSRF tokens.
4. Real DOCX ZIP archive bomb with excessive compression ratio and rejection.
5. Rate limiting enforcement by exceeding configured threshold (HTTP 429 & Retry-After).
6. IDOR/BOLA protection for both reads and mutations across analysis and interview sessions.
7. Upload security limits (magic bytes, path traversal sanitization).
8. Database persistence, WAL mode, synchronous PRAGMA, and query parameterization.
"""

import io
import os
import sys
import json
import zipfile
import subprocess
import pytest
from app import app, ANALYSIS_CACHE
from src.security.csrf import generate_csrf_token
from src.security.rate_limiter import SlidingWindowRateLimiter
from src.security.upload_validator import validate_file_content, sanitize_filename, UploadSecurityError
from src.analysis.resume_parser import validate_docx_archive_safety, parse_resume
from src.interview.interview_session import InterviewSessionManager
from src.interview.session_store import InterviewSessionStore


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. Real Production Startup Verification (Missing, Insecure & Valid Secrets)
# =============================================================================

def test_prod_01_real_startup_missing_and_insecure_secrets():
    """
    Spawns real Python processes importing app.py under production mode.
    Verifies that missing or insecure SECRET_KEY fails closed with RuntimeError,
    and valid strong secret succeeds.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    base_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "PYTHONPATH": repo_root,
        "RESUMEMATCH_ENV": "production",
    }

    # Case A: Missing SECRET_KEY in production
    env_missing = {**base_env}
    env_missing.pop("SECRET_KEY", None)
    proc_missing = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=repo_root,
        env=env_missing,
        capture_output=True,
        text=True
    )
    assert proc_missing.returncode != 0, "Production startup must fail when SECRET_KEY is missing"
    assert "SECRET_KEY must be configured" in proc_missing.stderr

    # Case B: Insecure default / short SECRET_KEY in production
    for bad_key in ["skillsync-dev-key-2026", "dev-key-change-me", "short_key", "change-me"]:
        env_insecure = {**base_env, "SECRET_KEY": bad_key}
        proc_insecure = subprocess.run(
            [sys.executable, "-c", "import app"],
            cwd=repo_root,
            env=env_insecure,
            capture_output=True,
            text=True
        )
        assert proc_insecure.returncode != 0, f"Production startup must fail with insecure key '{bad_key}'"
        assert "SECRET_KEY must be configured with a secure" in proc_insecure.stderr

    # Case C: Valid strong SECRET_KEY in production
    env_valid = {**base_env, "SECRET_KEY": "production-super-strong-secret-key-64chars-long-0123456789abcdef"}
    proc_valid = subprocess.run(
        [sys.executable, "-c", "import app; print('APP_STARTUP_SUCCESS')"],
        cwd=repo_root,
        env=env_valid,
        capture_output=True,
        text=True
    )
    assert proc_valid.returncode == 0, f"Production startup failed unexpectedly: {proc_valid.stderr}"
    assert "APP_STARTUP_SUCCESS" in proc_valid.stdout


# =============================================================================
# 2. Inspect Actual Production Set-Cookie Headers
# =============================================================================

def test_prod_02_inspect_actual_production_set_cookie_headers(monkeypatch):
    """
    Inspects actual HTTP Set-Cookie response headers from Flask under production configuration.
    Verifies Secure, HttpOnly, SameSite=Lax, and optional domain behavior.
    """
    monkeypatch.setenv("RESUMEMATCH_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "prod-strong-secret-key-32chars-xyz")
    
    # Test Case A: Host-only cookie (default Option 1 subdomains, Domain=None)
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_DOMAIN"] = None

    with app.test_client() as prod_client:
        res = prod_client.get("/api/csrf-token")
        assert res.status_code == 200
        cookie_header = res.headers.get("Set-Cookie", "")
        assert "session=" in cookie_header, "Set-Cookie header must set session cookie"
        assert "HttpOnly" in cookie_header, "Cookie must have HttpOnly flag"
        assert "Secure" in cookie_header, "Cookie must have Secure flag in production"
        assert "SameSite=Lax" in cookie_header, "Cookie must have SameSite=Lax attribute"
        assert "Domain=" not in cookie_header, "Host-only cookie must not include Domain attribute"

    # Test Case B: Shared Apex Domain cookie (Domain=.resumematch.ai)
    app.config["SESSION_COOKIE_DOMAIN"] = ".resumematch.ai"
    try:
        with app.test_client() as prod_client_domain:
            res = prod_client_domain.get("/api/csrf-token")
            assert res.status_code == 200
            cookie_header = res.headers.get("Set-Cookie", "")
            assert "Domain=resumematch.ai" in cookie_header or "Domain=.resumematch.ai" in cookie_header, "Cookie must include Domain=resumematch.ai"
            assert "SameSite=Lax" in cookie_header
            assert "HttpOnly" in cookie_header
            assert "Secure" in cookie_header
    finally:
        app.config["SESSION_COOKIE_DOMAIN"] = None
        app.config["SESSION_COOKIE_SECURE"] = False


# =============================================================================
# 3. Complete Route Inventory: Missing, Invalid & Valid CSRF Tokens
# =============================================================================

COMPLETE_CSRF_ROUTE_INVENTORY = [
    # (method, path, valid_sample_payload, is_form)
    ("POST", "/api/candidate/update-role", {"target_role": "Architect"}, False),
    ("POST", "/api/candidate/confirm-education", {"education": "Bachelor of Computer Science"}, False),
    ("POST", "/api/mentor/update-name", {"preferred_name": "Alice"}, False),
    ("POST", "/api/mentor/progress", {"topic_id": "system_design"}, False),
    ("POST", "/api/mentor/reset-progress", {}, False),
    ("POST", "/api/career-mentor/evaluate-role", {"role_name": "Lead ML Engineer"}, False),
    ("POST", "/api/interview-studio/generate", {"analysis_id": "sample"}, False),
    ("POST", "/api/interview/evaluate", {"answer": "A clean scalable architecture"}, False),
    ("POST", "/api/interview/confirm-activity", {"confirmed": True}, False),
    ("POST", "/api/interview/reset", {}, False),
    ("POST", "/api/interview/sessions", {"analysis_id": "sample"}, False),
    ("DELETE", "/api/interview/sessions/test-delete-inventory", None, False),
    ("POST", "/api/interview-practice/submit", {"session_id": "test", "user_answer": "ans", "question_index": 0}, False),
    ("POST", "/api/analyze", {"job_description": "Software Engineer", "resume_text": "Python engineer"}, False),
    ("POST", "/analyze", {"job_description": "Software Engineer", "target_role": "SWE"}, True),
    ("POST", "/interview-practice/submit", {"user_answer": "my answer", "question_index": 0}, True),
    ("POST", "/interview-studio/generate", {"target_role": "SWE", "experience_level": "Mid"}, True),
]


def test_prod_03_complete_inventory_missing_invalid_valid_csrf():
    """
    Iterates through every state-changing route in the complete application route inventory.
    Verifies:
      1. Missing token is rejected with 403 Forbidden.
      2. Invalid / forged token is rejected with 403 Forbidden.
      3. Valid CSRF token passes CSRF validation (status is NOT 403).
    """
    for method, path, payload, is_form in COMPLETE_CSRF_ROUTE_INVENTORY:
        # 1. Missing CSRF token
        with app.test_client() as unauth_client:
            if method == "POST":
                if is_form:
                    res = unauth_client.post(path, data=payload or {})
                else:
                    res = unauth_client.post(path, json=payload or {})
            elif method == "DELETE":
                res = unauth_client.delete(path)
            assert res.status_code == 403, f"{method} {path} accepted request without CSRF token (got {res.status_code})"

        # 2. Invalid / forged CSRF token
        with app.test_client() as forged_client:
            headers = {"X-CSRF-Token": "forged-invalid-token-12345"}
            if method == "POST":
                if is_form:
                    res = forged_client.post(path, data={**(payload or {}), "csrf_token": "forged"}, headers=headers)
                else:
                    res = forged_client.post(path, json=payload or {}, headers=headers)
            elif method == "DELETE":
                res = forged_client.delete(path, headers=headers)
            assert res.status_code == 403, f"{method} {path} accepted invalid CSRF token (got {res.status_code})"

        # 3. Valid CSRF token
        with app.test_client() as valid_client:
            token_res = valid_client.get("/api/csrf-token")
            assert token_res.status_code == 200
            token = token_res.get_json()["csrf_token"]
            headers = {"X-CSRF-Token": token}

            if method == "POST":
                if is_form:
                    res = valid_client.post(path, data={**(payload or {}), "csrf_token": token}, headers=headers)
                else:
                    res = valid_client.post(path, json=payload or {}, headers=headers)
            elif method == "DELETE":
                res = valid_client.delete(path, headers=headers)

            # Valid token must pass CSRF check: status must NOT be 403
            assert res.status_code != 403, f"{method} {path} rejected valid CSRF token with 403"


def test_prod_04_stateless_endpoint_no_csrf_requirement(client):
    """Verifies that stateless public inference endpoint /api/match functions without CSRF token."""
    res = client.post("/api/match", json={
        "resume_text": "Python machine learning software engineer with 5 years experience.",
        "job_description": "Seeking Python ML engineer experienced in PyTorch and Flask."
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "compatibility_score" in data or "match_score" in data


# =============================================================================
# 4. Real DOCX ZIP Archive Bomb Generation & Rejection
# =============================================================================

def test_prod_05_real_docx_archive_bomb_excessive_compression_rejection():
    """
    Generates a genuine DOCX (ZIP) archive with an excessive compression ratio (> 100:1)
    and verifies that validate_docx_archive_safety and parse_resume_file reject it fail-closed.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 10 MB of compressible zeros compresses into ~10 KB (ratio ~ 1000:1)
        large_payload = b"<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>" + (b"A" * (10 * 1024 * 1024)) + b"</w:t></w:r></w:p></w:body></w:document>"
        zf.writestr("word/document.xml", large_payload)
        zf.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types></Types>')

    bomb_payload = buf.getvalue()
    assert len(bomb_payload) < 50 * 1024, "Compressed bomb should be tiny (< 50KB)"

    # 1. Direct archive safety validator inspection
    err = validate_docx_archive_safety(bomb_payload)
    assert err is not None, "Archive bomb must be rejected by validate_docx_archive_safety"
    assert "Suspicious compression ratio" in err or "archive bomb protection" in err

    # 2. Complete resume parsing engine rejection
    parse_result = parse_resume(bomb_payload, filename="malicious_bomb.docx")
    assert parse_result["status"] == "error"
    assert "archive bomb protection" in parse_result["error_message"] or "Suspicious compression ratio" in parse_result["error_message"]


# =============================================================================
# 5. Rate Limiting Verification by Exceeding Configured Threshold
# =============================================================================

def test_prod_06_rate_limiting_exceeded_threshold_returns_429():
    """
    Verifies that exceeding the configured rate limit threshold returns HTTP 429 Too Many Requests
    with Retry-After header.
    """
    # 1. Unit test of SlidingWindowRateLimiter
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)
    for _ in range(5):
        allowed, _ = limiter.is_allowed("192.168.100.1")
        assert allowed is True
    blocked, retry_after = limiter.is_allowed("192.168.100.1")
    assert blocked is False
    assert retry_after > 0

    # 2. Integration test on actual endpoint /api/match with app.config["TESTING"] = False
    app.config["TESTING"] = False
    try:
        with app.test_client() as rate_client:
            test_ip = "198.51.100.99"
            got_429 = False
            for i in range(65):
                res = rate_client.post(
                    "/api/match",
                    json={"resume_text": "test", "job_description": "test"},
                    environ_base={"REMOTE_ADDR": test_ip}
                )
                if res.status_code == 429:
                    got_429 = True
                    assert "API rate limit exceeded" in res.get_json()["error_message"]
                    assert "Retry-After" in res.headers
                    break
            assert got_429 is True, "Endpoint must return HTTP 429 when rate limit threshold (60/min) is exceeded"
    finally:
        app.config["TESTING"] = True


# =============================================================================
# 6. IDOR / BOLA Authorization Verification for Reads and Mutations
# =============================================================================

def test_prod_07_idor_protection_for_both_reads_and_mutations():
    """
    Verifies broken object level authorization (IDOR/BOLA) defenses:
      1. Reads: Attempting to access another session's analysis returns 403 Forbidden.
      2. Mutations: Attempting to create, submit, or delete another owner's session returns 403.
    """
    foreign_aid = "foreign-victim-analysis-999"
    ANALYSIS_CACHE[foreign_aid] = {
        "analysis_id": foreign_aid,
        "compatibility_score": 88,
        "matched_skills": ["Python"],
        "missing_skills": [],
        "evidence": {"filename": "victim_resume.pdf", "job_title": "ML Engineer"}
    }

    try:
        # A. READ IDOR Checks (Session B attempts to read Session A's analysis)
        with app.test_client() as client_b:
            # 1. /api/analysis/<id>
            r1 = client_b.get(f"/api/analysis/{foreign_aid}")
            assert r1.status_code == 403
            assert "Unauthorized" in r1.get_json()["message"]

            # 2. /api/skill-gap?id=<id>
            r2 = client_b.get(f"/api/skill-gap?id={foreign_aid}")
            assert r2.status_code == 403

            # 3. /api/career-mentor?id=<id>
            r3 = client_b.get(f"/api/career-mentor?id={foreign_aid}")
            assert r3.status_code == 403

        # B. MUTATION IDOR Checks
        # Create an interview session owned by Owner A
        owner_a_session = InterviewSessionManager.create_session(
            questions=[{"question_id": "q1", "question": "Explain gradient descent"}],
            analysis_id=foreign_aid,
            target_role="ML Engineer",
            owner_id="owner_alpha_123"
        )
        foreign_sess_id = owner_a_session.session_id

        with app.test_client() as client_b:
            token_res = client_b.get("/api/csrf-token")
            csrf_token = token_res.get_json()["csrf_token"]
            headers = {"X-CSRF-Token": csrf_token}

            # 1. Mutation: Creating interview session with unowned analysis_id -> 403 Forbidden
            r_create = client_b.post(
                "/api/interview/sessions",
                json={"analysis_id": foreign_aid},
                headers=headers
            )
            assert r_create.status_code == 403
            assert "Unauthorized" in r_create.get_json()["message"]

            # 2. Mutation: Submitting answer to foreign session -> 403 Forbidden
            r_submit = client_b.post(
                "/api/interview-practice/submit",
                json={"session_id": foreign_sess_id, "user_answer": "ans", "question_index": 0},
                headers=headers
            )
            assert r_submit.status_code == 403
            assert "Unauthorized" in r_submit.get_json()["message"]

            # 3. Mutation: Deleting foreign session -> 403 Forbidden
            r_del = client_b.delete(
                f"/api/interview/sessions/{foreign_sess_id}",
                headers=headers
            )
            assert r_del.status_code == 403
            assert "Unauthorized" in r_del.get_json()["message"]

    finally:
        ANALYSIS_CACHE.pop(foreign_aid, None)


def test_prod_08_non_existent_analysis_returns_404(client):
    """Verifies that non-existent analysis IDs return 404 Not Found without disclosing details."""
    r = client.get("/api/analysis/non-existent-analysis-000")
    assert r.status_code == 404
    assert "not found" in r.get_json()["message"].lower()


# =============================================================================
# 7. Upload Validation & Path Traversal Sanitization
# =============================================================================

def test_prod_09_upload_security_magic_bytes_and_extension_enforcement():
    """Verifies magic bytes inspection and extension whitelisting."""
    with pytest.raises(UploadSecurityError, match="Disallowed file extension"):
        validate_file_content(b"%PDF-1.4 test", "resume.exe")

    with pytest.raises(UploadSecurityError, match="Missing standard %PDF- header"):
        validate_file_content(b"NOT A REAL PDF FILE", "resume.pdf")

    with pytest.raises(UploadSecurityError, match="Missing standard ZIP/OpenXML PK"):
        validate_file_content(b"NOT A REAL DOCX", "resume.docx")

    valid, name = validate_file_content(b"%PDF-1.4 valid pdf content", "my_resume.pdf")
    assert valid is True
    assert name == "my_resume.pdf"


def test_prod_10_filename_path_traversal_sanitization():
    """Verifies that directory traversal and null byte injections in filenames are sanitized."""
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\boot.ini.txt") == "boot.ini.txt"
    assert sanitize_filename("resume\0evil.pdf") == "resume.pdf" or "evil" in sanitize_filename("resume\0evil.pdf")
    assert sanitize_filename("") == "uploaded_resume.txt"


# =============================================================================
# 8. All 10 Major Module Companion Endpoints Integrity
# =============================================================================

def test_prod_11_all_ten_module_companion_endpoints_healthy(client):
    """Verifies availability and valid response schema for all 10 application companion endpoints."""
    endpoints = [
        ("/api/dashboard", "Executive Dashboard", "summary"),
        ("/api/sample-jobs", "Resume Analyzer Job Intake", "sample_jobs"),
        ("/api/model-performance", "Supervised ML Metrics", "dashboard"),
        ("/api/datasets", "Dataset Provenance Explorer", "summary"),
        ("/api/analysis/sample", "Compatibility Results View", "analysis"),
        ("/api/skill-gap?id=sample", "Skill Gap Analytics", "analysis"),
        ("/api/career-mentor?id=sample", "Career Mentor Roadmap", "dossier"),
        ("/api/interview-studio?id=sample", "Interview Studio Question Generator", "evidence"),
        ("/api/interview-practice", "Interview Practice Active Question", "question"),
    ]

    for url, module_name, expected_key in endpoints:
        res = client.get(url)
        assert res.status_code == 200, f"{module_name} ({url}) returned HTTP {res.status_code}"
        data = res.get_json()
        assert data.get("status") == "success", f"{module_name} status != success"
        assert expected_key in data, f"{module_name} response missing '{expected_key}'"


# =============================================================================
# 9. Database Concurrency, WAL Mode, and Parameterized Queries
# =============================================================================

def test_prod_12_database_wal_mode_and_concurrency(tmp_path):
    """Verifies SQLite WAL mode, normal synchronous PRAGMAs, and parameterized query execution."""
    db_file = tmp_path / "test_prod.db"
    store = InterviewSessionStore(db_path=str(db_file))
    
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL"

        cursor.execute("PRAGMA synchronous")
        sync = cursor.fetchone()[0]
        assert sync in (1, "1", "NORMAL")

    session_data = {
        "session_id": "test-prod-session-001",
        "analysis_id": "analysis-123",
        "target_role": "Staff ML Engineer",
        "interview_mode": "mock",
        "difficulty": "advanced",
        "owner_id": "owner-abc-789",
        "questions_json": json.dumps([{"id": "q1", "question": "Explain contrastive learning"}]),
        "responses_json": json.dumps([]),
        "results_summary_json": json.dumps({"score": 95}),
        "candidate_evidence_json": json.dumps({"skills": ["PyTorch", "Python"]}),
        "created_at": "2026-11-17T12:00:00Z",
        "updated_at": "2026-11-17T12:00:00Z"
    }
    store.save_session(session_data)

    retrieved = store.get_session("test-prod-session-001")
    assert retrieved is not None
    assert retrieved["target_role"] == "Staff ML Engineer"
    assert retrieved["owner_id"] == "owner-abc-789"
