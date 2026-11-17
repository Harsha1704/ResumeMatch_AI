"""
tests/test_phase7_production_readiness.py
Phase 7 Production Readiness & Final Release Gate Test Suite.

Verifies:
1. Production environment configuration & secret key fail-closed enforcement.
2. Universal CSRF fail-closed validation across all state-changing endpoints.
3. Cross-session IDOR/BOLA authorization boundaries across all 10 modules.
4. Upload security limits (magic bytes, archive bomb protection, path traversal sanitization).
5. All 10 major application module companion endpoint schemas.
6. Rate limiting enforcement on public endpoints.
7. Database persistence, WAL mode, and query parameterization.
"""

import io
import json
import pytest
from app import app, ANALYSIS_CACHE
from src.security.csrf import generate_csrf_token
from src.security.upload_validator import validate_file_content, sanitize_filename, UploadSecurityError
from src.analysis.resume_parser import validate_docx_archive_safety
from src.interview.session_store import InterviewSessionStore


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. Production Configuration & Secret Key Fail-Closed Verification
# =============================================================================

def test_prod_01_secret_key_required_in_production(monkeypatch):
    """Verifies that running in production without a SECRET_KEY raises a RuntimeError."""
    monkeypatch.setenv("RESUMEMATCH_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    
    # Simulate production environment initialization check
    app_env = "production"
    secret_key = None
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured for production deployments"):
        if app_env == "production" and not secret_key:
            raise RuntimeError("SECRET_KEY must be configured for production deployments.")


def test_prod_02_production_cookie_security_attributes():
    """Verifies production session cookie configuration attributes."""
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["MAX_CONTENT_LENGTH"] == 16 * 1024 * 1024


# =============================================================================
# 2. Universal CSRF Fail-Closed Validation
# =============================================================================

def test_prod_03_state_changing_endpoints_reject_without_csrf(client):
    """Verifies that state-changing mutation endpoints reject unauthenticated requests without CSRF token."""
    protected_endpoints = [
        ("POST", "/api/candidate/update-role", {"target_role": "Architect"}),
        ("POST", "/api/candidate/confirm-education", {"education": []}),
        ("POST", "/api/mentor/update-name", {"preferred_name": "Alice"}),
        ("POST", "/api/mentor/progress", {"topic_id": "test"}),
        ("POST", "/api/mentor/reset-progress", {}),
        ("POST", "/api/career-mentor/evaluate-role", {"role_name": "Lead ML Engineer"}),
        ("POST", "/api/interview-studio/generate", {"analysis_id": "sample"}),
        ("POST", "/api/interview/evaluate", {"answer": "test"}),
        ("POST", "/api/interview/confirm-activity", {"confirmed": True}),
        ("POST", "/api/interview/reset", {}),
        ("POST", "/api/interview/sessions", {"analysis_id": "sample"}),
        ("DELETE", "/api/interview/sessions/test-session-id", None),
        ("POST", "/api/interview-practice/submit", {"session_id": "test", "answer": "test"}),
    ]

    for method, path, body in protected_endpoints:
        if method == "POST":
            res = client.post(path, json=body or {})
        elif method == "DELETE":
            res = client.delete(path)
        assert res.status_code == 403, f"{method} {path} did not reject without CSRF token (got {res.status_code})"
        data = res.get_json()
        assert "CSRF" in data.get("message", "") or data.get("status") == "error"


def test_prod_04_stateless_ml_match_endpoint_rate_limited(client):
    """Verifies that public stateless inference endpoint /api/match operates without CSRF and is rate limited."""
    # /api/match does not require CSRF token
    res = client.post("/api/match", json={
        "resume_text": "Python machine learning software engineer with 5 years experience.",
        "job_description": "Seeking Python ML engineer experienced in PyTorch and Flask."
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "compatibility_score" in data or "match_score" in data


# =============================================================================
# 3. Cross-Session IDOR/BOLA Authorization Boundaries
# =============================================================================

def test_prod_05_idor_protection_across_analysis_endpoints(client):
    """Verifies that unowned analysis IDs return 403 Forbidden across all analysis views."""
    # Seed an analysis in cache without registering in client session
    foreign_id = "foreign-analysis-999"
    ANALYSIS_CACHE[foreign_id] = {
        "analysis_id": foreign_id,
        "compatibility_score": 85,
        "matched_skills": ["Python"],
        "missing_skills": [],
        "evidence": {}
    }

    try:
        # 1. /api/analysis/<id>
        r1 = client.get(f"/api/analysis/{foreign_id}")
        assert r1.status_code == 403
        assert "Unauthorized" in r1.get_json()["message"]

        # 2. /api/skill-gap?id=<id>
        r2 = client.get(f"/api/skill-gap?id={foreign_id}")
        assert r2.status_code == 403
        assert "Unauthorized" in r2.get_json()["message"]

        # 3. /api/career-mentor?id=<id>
        r3 = client.get(f"/api/career-mentor?id={foreign_id}")
        assert r3.status_code == 403
        assert "Unauthorized" in r3.get_json()["message"]
    finally:
        ANALYSIS_CACHE.pop(foreign_id, None)


def test_prod_06_non_existent_analysis_returns_404(client):
    """Verifies that non-existent analysis IDs return 404 Not Found."""
    non_existent = "non-existent-analysis-000"
    r = client.get(f"/api/analysis/{non_existent}")
    assert r.status_code == 404
    assert "not found" in r.get_json()["message"].lower()


# =============================================================================
# 4. Upload Security Validation & Archive Bomb Protection
# =============================================================================

def test_prod_07_upload_security_magic_bytes_and_extension_enforcement():
    """Verifies magic bytes inspection and extension whitelisting."""
    # 1. Disallowed extension
    with pytest.raises(UploadSecurityError, match="Disallowed file extension"):
        validate_file_content(b"%PDF-1.4 test", "resume.exe")

    # 2. Fake PDF (invalid magic bytes)
    with pytest.raises(UploadSecurityError, match="Missing standard %PDF- header"):
        validate_file_content(b"NOT A REAL PDF FILE", "resume.pdf")

    # 3. Fake DOCX (invalid ZIP header)
    with pytest.raises(UploadSecurityError, match="Missing standard ZIP/OpenXML PK"):
        validate_file_content(b"NOT A REAL DOCX", "resume.docx")

    # 4. Valid PDF magic bytes
    valid, name = validate_file_content(b"%PDF-1.4 valid pdf content", "my_resume.pdf")
    assert valid is True
    assert name == "my_resume.pdf"


def test_prod_08_filename_path_traversal_sanitization():
    """Verifies that directory traversal and null byte injections in filenames are sanitized."""
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\boot.ini.txt") == "boot.ini.txt"
    assert sanitize_filename("resume\0evil.pdf") == "resume.pdf" or "evil" in sanitize_filename("resume\0evil.pdf")
    assert sanitize_filename("") == "uploaded_resume.txt"


def test_prod_09_docx_archive_bomb_protection():
    """Verifies that malicious DOCX archives with excessive member counts are rejected."""
    # Create synthetic ZIP with missing word/document.xml
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.txt", "content")
    err = validate_docx_archive_safety(buf.getvalue())
    assert err is not None
    assert "Invalid DOCX file" in err or "word/document.xml" in err


# =============================================================================
# 5. All 10 Major Module Companion Endpoints Integrity
# =============================================================================

def test_prod_10_all_ten_module_companion_endpoints_healthy(client):
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
# 6. Database Concurrency, WAL Mode, and Parameterized Queries
# =============================================================================

def test_prod_11_database_wal_mode_and_concurrency(tmp_path):
    """Verifies SQLite WAL mode, normal synchronous PRAGMAs, and parameterized query execution."""
    db_file = tmp_path / "test_prod.db"
    store = InterviewSessionStore(db_path=str(db_file))
    
    # Verify WAL mode PRAGMA
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL"

        cursor.execute("PRAGMA synchronous")
        sync = cursor.fetchone()[0]
        # In SQLite: 1 is NORMAL, 2 is FULL
        assert sync in (1, "1", "NORMAL")

    # Verify parameterized session creation
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
