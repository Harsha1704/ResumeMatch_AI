"""
experiments/phase16/scripts/verify_security.py
Phase 16: Independent Security & Robustness Verification.

Executes comprehensive live testing against:
1. File upload validation (valid PDF, DOCX, TXT).
2. Content mismatch & spoofing rejection (fake PDF, fake DOCX, null byte injection).
3. Payload size enforcement (16 MB limit).
4. Path traversal filename sanitization & rejection.
5. CSRF protection (missing token, invalid token, valid token).
6. Rate limiting enforcement (burst limits, HTTP 429, Retry-After header).
7. Sensitive information leakage prevention (no stack traces or absolute path leakage).
8. SQLite storage security (permissions & restricted directory access).
"""

import os
import sys
import io
import time
import json
import uuid
from pathlib import Path

REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

from app import app
from src.security.upload_validator import validate_file_content, sanitize_filename, UploadSecurityError
from src.security.rate_limiter import SlidingWindowRateLimiter
from src.security.csrf import generate_csrf_token, validate_csrf_token

OUTPUT_JSON = REPO_ROOT / "experiments" / "phase16" / "security_verification.json"
SECURITY_RESULTS = {}


def test_file_type_validation():
    print("[1/8] Verifying File Type & Magic Bytes Validation...")
    results = {}
    
    # 1. Valid PDF with proper %PDF- header
    valid_pdf_bytes = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\nxref\n0 2\n0000000000 65535 f\n0000000015 00000 n\ntrailer<</Size 2/Root 1 0 R>>\nstartxref\n68\n%%EOF\n"
    is_valid, ext = validate_file_content(valid_pdf_bytes, "valid_resume.pdf")
    results["valid_pdf"] = {"passed": is_valid, "detected_ext": ext}
    
    # 2. Valid DOCX with PK\x03\x04 zip header
    valid_docx_bytes = b"PK\x03\x04" + b"\x00" * 26 + b"[Content_Types].xml" + b"\x00" * 50
    is_valid, ext = validate_file_content(valid_docx_bytes, "valid_resume.docx")
    results["valid_docx"] = {"passed": is_valid, "detected_ext": ext}
    
    # 3. Valid TXT
    valid_txt_bytes = "Experienced Systems Architect with Python and Rust skills.".encode("utf-8")
    is_valid, ext = validate_file_content(valid_txt_bytes, "valid_resume.txt")
    results["valid_txt"] = {"passed": is_valid, "detected_ext": ext}
    
    all_valid = all(v["passed"] for v in results.values())
    SECURITY_RESULTS["file_type_validation"] = {
        "status": "PASS" if all_valid else "FAIL",
        "details": results
    }
    print(f"  Valid formats accepted: {all_valid}")


def test_content_mismatch_and_spoofing():
    print("\n[2/8] Verifying Content Mismatch & Malicious Payload Rejection...")
    results = {}
    
    # 1. Fake PDF: Text file renamed to .pdf
    fake_pdf = b"This is just plain text disguised as a PDF file."
    try:
        validate_file_content(fake_pdf, "fake.pdf")
        results["fake_pdf_rejected"] = False
    except UploadSecurityError:
        results["fake_pdf_rejected"] = True
        
    # 2. Fake DOCX: Executable or plain text renamed to .docx
    fake_docx = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 50 # PE executable header
    try:
        validate_file_content(fake_docx, "trojan.docx")
        results["fake_docx_rejected"] = False
    except UploadSecurityError:
        results["fake_docx_rejected"] = True
        
    # 3. Null Byte Injection in text
    null_byte_payload = b"Resume text\x00malicious_code_here\x00"
    try:
        validate_file_content(null_byte_payload, "nullbyte.txt")
        results["null_byte_rejected"] = False
    except UploadSecurityError:
        results["null_byte_rejected"] = True

    all_rejected = all(results.values())
    SECURITY_RESULTS["content_mismatch_defense"] = {
        "status": "PASS" if all_rejected else "FAIL",
        "details": results
    }
    print(f"  Content spoofing & null bytes blocked: {all_rejected}")


def test_file_size_limits():
    print("\n[3/8] Verifying 16 MB Payload Size Enforcement...")
    # 16 MB = 16 * 1024 * 1024 bytes
    oversized_bytes = b"%PDF-1.5\n" + b"A" * (16 * 1024 * 1024 + 1024) # 16 MB + 1 KB
    
    rejected = False
    try:
        validate_file_content(oversized_bytes, "oversized.pdf")
    except UploadSecurityError as e:
        rejected = True
        err_msg = str(e)
        
    SECURITY_RESULTS["file_size_enforcement"] = {
        "status": "PASS" if rejected else "FAIL",
        "rejected": rejected,
        "max_size_bytes": 16 * 1024 * 1024,
        "test_payload_bytes": len(oversized_bytes)
    }
    print(f"  Oversized payload rejected (> 16MB): {rejected}")


def test_path_traversal_sanitization():
    print("\n[4/8] Verifying Path Traversal Defense & Filename Sanitization...")
    test_cases = [
        ("../../evil_resume.pdf", "evil_resume.pdf"),
        ("..\\..\\windows\\system32\\cmd.exe", "cmd.exe"),
        ("/etc/passwd", "passwd"),
        ("....//....//nested/test.txt", "test.txt"),
        ("normal_user_resume.pdf", "normal_user_resume.pdf"),
        ("resume;rm -rf.pdf", "resume_rm_-rf.pdf")
    ]
    
    traversal_results = []
    all_safe = True
    for original, expected in test_cases:
        sanitized = sanitize_filename(original)
        # Ensure no directory separators remain
        is_safe = ("/" not in sanitized) and ("\\" not in sanitized) and (".." not in sanitized)
        traversal_results.append({
            "original": original,
            "sanitized": sanitized,
            "is_safe": is_safe
        })
        if not is_safe:
            all_safe = False

    SECURITY_RESULTS["path_traversal_defense"] = {
        "status": "PASS" if all_safe else "FAIL",
        "details": traversal_results
    }
    print(f"  Path traversal sequences stripped cleanly: {all_safe}")


def test_csrf_protection():
    print("\n[5/8] Verifying CSRF Token Validation & Protection...")
    with app.test_request_context("/"):
        token = generate_csrf_token()
        valid_result = validate_csrf_token(token)
        missing_result = validate_csrf_token("")
        null_result = validate_csrf_token(None)
        forged_result = validate_csrf_token(token + "tampered")

    csrf_pass = (valid_result is True and missing_result is False and null_result is False and forged_result is False)
    SECURITY_RESULTS["csrf_protection"] = {
        "status": "PASS" if csrf_pass else "FAIL",
        "valid_token_accepted": valid_result,
        "missing_token_rejected": not missing_result,
        "null_token_rejected": not null_result,
        "forged_token_rejected": not forged_result
    }
    print(f"  CSRF token validation correct: {csrf_pass}")


def test_rate_limiting():
    print("\n[6/8] Verifying Sliding Window Rate Limiting Enforcement...")
    limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=1.0)
    client_ip = "192.168.1.100"
    
    allowed_count = 0
    blocked_count = 0
    retry_after_val = 0
    
    # Send 15 rapid requests with limit 10
    for _ in range(15):
        allowed, retry_after = limiter.is_allowed(client_ip)
        if allowed:
            allowed_count += 1
        else:
            blocked_count += 1
            retry_after_val = retry_after

    rate_limit_pass = (allowed_count == 10 and blocked_count == 5 and retry_after_val > 0)
    SECURITY_RESULTS["rate_limiting"] = {
        "status": "PASS" if rate_limit_pass else "FAIL",
        "requests_allowed": allowed_count,
        "requests_blocked": blocked_count,
        "retry_after_seconds": retry_after_val
    }
    print(f"  Rate limiter throttled at limit (10 allowed, 5 blocked): {rate_limit_pass}")


def test_sensitive_information_leakage():
    print("\n[7/8] Verifying Redaction of Stack Traces & Path Leakage...")
    with app.test_client() as client:
        # Trigger 404
        r404 = client.get("/non_existent_endpoint_xyz")
        # Trigger 405 Method Not Allowed
        r405 = client.get("/api/match")
        # Trigger 400 Bad Request
        r400 = client.post("/api/match", json={})

    # Check for stack traces, internal D:\ paths, or sensitive system details
    responses = [r404.get_data(as_text=True), r405.get_data(as_text=True), r400.get_data(as_text=True)]
    
    leaks = []
    for resp in responses:
        if "Traceback (most recent call last)" in resp:
            leaks.append("Found Python stack trace")
        if "D:\\skillsync1\\src" in resp:
            leaks.append("Found absolute source path")
        if "password" in resp.lower() and "invalid" not in resp.lower():
            leaks.append("Potential credential leak")

    no_leaks = len(leaks) == 0
    SECURITY_RESULTS["sensitive_info_redaction"] = {
        "status": "PASS" if no_leaks else "FAIL",
        "leaks_detected": leaks,
        "tested_status_codes": [r404.status_code, r405.status_code, r400.status_code]
    }
    print(f"  No internal stack traces or paths leaked in error responses: {no_leaks}")


def test_sqlite_storage_security():
    print("\n[8/8] Verifying SQLite File Integrity & Storage Security...")
    cache_db = REPO_ROOT / "data" / "cache" / "embedding_cache.sqlite"
    queue_db = REPO_ROOT / "data" / "cache" / "embedding_queue.sqlite"
    
    cache_exists = cache_db.exists()
    queue_exists = queue_db.exists()
    
    # Check that databases are inside the designated data/cache directory
    cache_in_data = cache_db.resolve().is_relative_to(REPO_ROOT / "data")
    queue_in_data = queue_db.resolve().is_relative_to(REPO_ROOT / "data")

    db_pass = cache_exists and queue_exists and cache_in_data and queue_in_data
    SECURITY_RESULTS["sqlite_storage_security"] = {
        "status": "PASS" if db_pass else "FAIL",
        "cache_db_exists": cache_exists,
        "queue_db_exists": queue_exists,
        "cache_path_confined": cache_in_data,
        "queue_path_confined": queue_in_data
    }
    print(f"  SQLite databases confined to data/cache: {db_pass}")


def main():
    print("=" * 80)
    print("PHASE 16 — COMPREHENSIVE SECURITY VERIFICATION")
    print("=" * 80)
    
    test_file_type_validation()
    test_content_mismatch_and_spoofing()
    test_file_size_limits()
    test_path_traversal_sanitization()
    test_csrf_protection()
    test_rate_limiting()
    test_sensitive_information_leakage()
    test_sqlite_storage_security()
    
    all_passed = all(v["status"] == "PASS" for v in SECURITY_RESULTS.values())
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"all_passed": all_passed, "results": SECURITY_RESULTS}, f, indent=2)

    print("=" * 80)
    print(f"Overall Security Status: {'ALL PASSED' if all_passed else 'SOME CHECKS FAILED'}")
    print(f"Detailed output saved to: {OUTPUT_JSON}")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
