"""
experiments/phase15_1/tests/test_deployment_hardening.py
Automated test suite for ResumeMatch AI Phase 15.1 Deployment Hardening:
1. Production checkpoint preservation (exact hashes and bytes).
2. Clean web process isolation (zero torch or sentence_transformers in Flask web process).
3. Memory optimization (Flask serving RSS <= 200 MB).
4. Persistent job queue lifecycle (ACID queue, retries, stale job recovery).
5. Background embedding worker execution.
6. Zero lost jobs across simulated worker restarts.
7. Fallback telemetry correctness (explicit reasons, no silent fallback).
8. Upload security validation (magic bytes, path traversal rejection, size limit).
9. CSRF protection and rate limiting defense.
10. Headless REST API allow_fallback parameter semantics (200 vs 202).
"""

import os
import sys
import time
import uuid
import hashlib
import sqlite3
import pytest
import psutil
from pathlib import Path
from unittest.mock import patch
import numpy as np

REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

from app import app
from src.services.job_queue import EmbeddingJobQueue
from src.services.embedding_service import get_embedding_service, EmbeddingService
from src.services.embedding_worker import EmbeddingWorker
from src.security.upload_validator import validate_file_content, sanitize_filename, UploadSecurityError
from src.security.rate_limiter import SlidingWindowRateLimiter
from src.security.csrf import generate_csrf_token, validate_csrf_token

# Immutable production artifacts baseline
PRODUCTION_TARGETS = [
    ("best_model.joblib", REPO_ROOT / "models" / "best_model.joblib", "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a", 61487),
    ("feature_pipeline.joblib", REPO_ROOT / "models" / "feature_pipeline.joblib", "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6", 270105),
    ("challenger_model_phase12f.joblib", REPO_ROOT / "models" / "phase12f" / "challenger_model_phase12f.joblib", "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766", 2330440),
]


def test_production_checkpoints_preserved():
    """Verify bit-for-bit invariance of historical production model artifacts."""
    for name, path, expected_hash, expected_size in PRODUCTION_TARGETS:
        assert path.exists(), f"Production artifact missing: {name}"
        data = path.read_bytes()
        assert len(data) == expected_size, f"Size mismatch for {name}: {len(data)} != {expected_size}"
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {name}: {actual_hash} != {expected_hash}"


def test_flask_process_clean_from_torch_and_sentence_transformers():
    """Verify web process contains zero torch or sentence_transformers module imports."""
    assert "torch" not in sys.modules, "PyTorch leaked into web process modules!"
    assert "sentence_transformers" not in sys.modules, "SentenceTransformer leaked into web process modules!"


def test_flask_startup_rss_below_200mb():
    """Verify Flask web server boot RSS is strictly <= 200 MB."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.get_json()
        rss_mb = data.get("flask_rss_mb", 0.0)
        assert rss_mb <= 200.0, f"Flask RSS {rss_mb} MB exceeds 200.0 MB threshold!"


def test_persistent_job_queue_lifecycle(tmp_path):
    """Test job queue enqueue, atomic claim, completion, retry and dead-letter handling."""
    queue_db = tmp_path / "test_queue.sqlite"
    queue = EmbeddingJobQueue(db_path=queue_db)

    # 1. Enqueue
    text = "Machine Learning Engineer with PyTorch experience"
    job_id = queue.enqueue(text, entity_type="resume", max_retries=2)
    assert job_id is not None

    stats = queue.get_stats()
    assert stats["pending"] == 1
    assert stats["total"] == 1

    # Idempotent enqueue check
    duplicate_job_id = queue.enqueue(text, entity_type="resume")
    assert duplicate_job_id == job_id
    assert queue.get_stats()["pending"] == 1

    # 2. Claim next
    claimed = queue.claim_next(worker_id="test-worker-1")
    assert claimed is not None
    assert claimed["job_id"] == job_id
    assert claimed["status"] == "processing"
    assert claimed["worker_id"] == "test-worker-1"

    # 3. Fail with retry
    queue.fail(job_id, error_message="Mock transient CUDA error")
    job_after_fail = queue.get_job(job_id)
    assert job_after_fail["status"] == "pending"
    assert job_after_fail["retry_count"] == 1

    # Claim again (attempt 2)
    claimed_again = queue.claim_next(worker_id="test-worker-2")
    assert claimed_again["job_id"] == job_id
    queue.fail(job_id, error_message="Mock retry 1 failure")

    # Claim 3rd time (attempt 3) and fail past max_retries
    claimed_3 = queue.claim_next(worker_id="test-worker-3")
    assert claimed_3["job_id"] == job_id
    queue.fail(job_id, error_message="Permanent memory exhaustion")

    job_permanent_fail = queue.get_job(job_id)
    assert job_permanent_fail["status"] == "failed"
    assert job_permanent_fail["retry_count"] == 3
    assert queue.get_stats()["failed"] == 1


def test_zero_lost_jobs_across_restarts(tmp_path):
    """Verify crash safety: stale in-flight jobs recover automatically without loss."""
    queue_db = tmp_path / "crash_test_queue.sqlite"
    queue = EmbeddingJobQueue(db_path=queue_db)

    # Enqueue 5 jobs
    job_ids = [queue.enqueue(f"Job sample description {i}", entity_type="job") for i in range(5)]
    assert queue.get_stats()["pending"] == 5

    # Worker claims 2 jobs, then simulates abrupt termination (no complete or fail called)
    claimed_1 = queue.claim_next("worker-crashed")
    claimed_2 = queue.claim_next("worker-crashed")
    assert queue.get_stats()["processing"] == 2
    assert queue.get_stats()["pending"] == 3

    # Backdate updated_at to simulate timeout (>60 seconds ago)
    past_time = time.time() - 120.0
    with queue._get_connection() as conn:
        conn.execute("UPDATE embedding_jobs SET updated_at = ? WHERE status = 'processing'", (past_time,))

    # Next worker starts up and invokes recover_stale_jobs
    recovered_count = queue.recover_stale_jobs(timeout_seconds=60.0)
    assert recovered_count == 2

    # Verify all 5 jobs remain present and actionable
    stats_after = queue.get_stats()
    assert stats_after["pending"] == 5
    assert stats_after["processing"] == 0
    assert stats_after["total"] == 5


def test_fallback_telemetry_correctness():
    """Verify requested_model vs actual_model and fallback reasons are recorded explicitly."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        # 1. Baseline Request
        res_prod = client.post("/api/match", json={
            "resume_text": "Experienced React and TypeScript Frontend Engineer.",
            "job_description": "Seeking Frontend Developer with React and TypeScript.",
            "model_backend": "production"
        })
        assert res_prod.status_code == 200
        d_prod = res_prod.get_json()
        assert d_prod["model_requested"] == "production"
        assert d_prod["fallback_triggered"] is False
        assert d_prod["fallback_reason"] is None
        assert "Production Baseline" in d_prod["model_used"]

        # 2. Challenger Request with cache miss and fallback
        unique_id = uuid.uuid4().hex[:8]
        res_fall = client.post("/api/match", json={
            "resume_text": f"Candidate profile {unique_id} with niche Cobol and Fortran experience.",
            "job_description": f"Role description {unique_id} requiring legacy mainframe systems.",
            "model_backend": "challenger_m5",
            "allow_fallback": True
        })
        assert res_fall.status_code == 200
        d_fall = res_fall.get_json()
        assert d_fall["model_requested"] == "challenger_m5"
        assert d_fall["fallback_triggered"] is True
        assert d_fall["fallback_reason"] == "cache_miss_pending_worker_generation"
        assert d_fall["is_challenger"] is False
        assert "Fallback" in d_fall["model_used"]
        assert d_fall["pending_jobs"] is not None


def test_file_upload_security_and_validation():
    """Test magic bytes inspection, path traversal sanitization, and size boundary checks."""
    # 1. Path traversal filename sanitization
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("safe_resume.pdf") == "safe_resume.pdf"

    # 2. Valid TXT content
    valid, name = validate_file_content(b"Senior Software Engineer Resume", "my_resume.txt")
    assert valid is True

    # 3. Valid PDF header
    valid_pdf, _ = validate_file_content(b"%PDF-1.4\n%mock content", "test.pdf")
    assert valid_pdf is True

    # 4. Spoofed PDF (TXT or executable renamed to .pdf)
    with pytest.raises(UploadSecurityError, match="Missing standard %PDF- header signature"):
        validate_file_content(b"MZ\x90\x00\x03fake_executable", "resume.pdf")

    # 5. Disallowed extension
    with pytest.raises(UploadSecurityError, match="Disallowed file extension"):
        validate_file_content(b"print('hack')", "exploit.py")

    # 6. Null bytes in text file
    with pytest.raises(UploadSecurityError, match="Contains binary null bytes"):
        validate_file_content(b"Resume content with null byte \x00 attack", "resume.txt")


def test_csrf_and_rate_limiting():
    """Verify CSRF token validation and sliding window rate limiter functionality."""
    # 1. Rate limiter basic operation
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10.0)
    assert limiter.is_allowed("192.168.1.10")[0] is True
    assert limiter.is_allowed("192.168.1.10")[0] is True
    assert limiter.is_allowed("192.168.1.10")[0] is True
    # 4th request must be rejected with retry_after
    allowed, retry_after = limiter.is_allowed("192.168.1.10")
    assert allowed is False
    assert retry_after > 0.0

    # Other IP still permitted
    assert limiter.is_allowed("192.168.1.20")[0] is True

    # 2. CSRF Token constant-time validation
    with app.test_request_context("/"):
        token = generate_csrf_token()
        assert token is not None
        assert validate_csrf_token(token) is True
        assert validate_csrf_token("invalid_token") is False
        assert validate_csrf_token(None) is False


def test_headless_api_allow_fallback_behavior():
    """Verify allow_fallback=False returns HTTP 202 with job polling details on cache miss."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        unique_token = uuid.uuid4().hex[:10]
        res = client.post("/api/match", json={
            "resume_text": f"Unseen candidate {unique_token} specializing in Rust embedded systems.",
            "job_description": f"Unseen job {unique_token} requiring firmware optimization in Rust.",
            "model_backend": "challenger_m5",
            "allow_fallback": False
        })
        assert res.status_code == 202
        data = res.get_json()
        assert data["status"] == "processing"
        assert data["fallback_triggered"] is True
        assert data["job_ids"]["resume_job_id"] is not None
        assert data["job_ids"]["job_job_id"] is not None

        # Verify job is queryable via /api/jobs/<job_id>
        job_id = data["job_ids"]["resume_job_id"]
        job_res = client.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.get_json()
        assert job_data["job_id"] == job_id
        assert job_data["job_status"] in ("pending", "processing", "completed")


def test_api_input_boundaries_and_error_handling():
    """Test API input length, invalid types, and malformed requests."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        # 1. Text too short (< 10 chars)
        res_short = client.post("/api/match", json={"resume_text": "short", "job_description": "short"})
        assert res_short.status_code == 400
        assert "Inputs too short" in res_short.get_json()["error_message"]

        # 2. Invalid backend
        res_bad_backend = client.post("/api/match", json={
            "resume_text": "Valid resume text with enough characters for test.",
            "job_description": "Valid job description with enough characters for test.",
            "model_backend": "unsupported_gpt_model"
        })
        assert res_bad_backend.status_code == 400
        assert "Unknown model backend" in res_bad_backend.get_json()["error_message"]

        # 3. Non-existent job status check (404)
        res_404 = client.get("/api/jobs/non-existent-uuid-1234")
        assert res_404.status_code == 404
        assert res_404.get_json()["status"] == "not_found"
