# Phase 15.1: Security & Reliability Audit Report

**Application:** ResumeMatch AI  
**Phase:** 15.1 — Deployment Hardening  
**Date:** 2026-11-15  
**Auditor:** Application Security & MLOps Infrastructure Auditor  

---

## 1. Threat Model & Security Posture Overview

The ResumeMatch AI application serves candidate evaluation workflows handling sensitive candidate documents (curricula vitae, resumes) and structured job specifications. In Phase 15.1, the application was systematically hardened against common web application vulnerabilities (OWASP Top 10) and ML inference denial-of-service risks.

---

## 2. Hardened Security Controls

### A. Document Upload & File Inspection (`src/security/upload_validator.py`)
- **Strict Extension Whitelist:** Only `.pdf`, `.docx`, and `.txt` extensions are accepted. Executables (`.exe`, `.dll`, `.bat`, `.sh`, `.py`) and web scripts (`.html`, `.svg`, `.js`) are rejected before disk interaction.
- **Magic Byte Signature Inspection:**
  - **PDF Documents:** Must begin with the canonical `%PDF-` signature bytes. Renamed binaries or payload scripts masquerading as PDFs are rejected immediately.
  - **Word Documents (DOCX):** Must begin with the standard OpenXML / ZIP archive signature (`PK\x03\x04`).
  - **Plain Text:** Inspected for binary null bytes (`\x00`) and validated for clean UTF-8 / ASCII encoding.
- **File Size Ceiling:** Enforced at 16 MB (`16 * 1024 * 1024` bytes) through Flask's `MAX_CONTENT_LENGTH` and secondary byte-array length checks, defending against memory exhaustion and decompression bombs.

### B. Path Traversal & Filename Sanitization
- Filenames undergo strict sanitization via `werkzeug.utils.secure_filename`.
- Inputs containing directory traversal sequences (`..`, `/`, `\`), null bytes (`\x00`), or absolute paths are stripped down to safe basenames.
- File uploads are processed directly in-memory as byte streams without writing unvetted files to public or temporary system directories.

### C. Cross-Site Request Forgery (CSRF) Defense (`src/security/csrf.py`)
- **Cryptographic Token Issuance:** Unique 256-bit cryptographically secure tokens (`secrets.token_hex(32)`) are minted per user session.
- **Form Verification:** All state-changing HTML form POST requests (`/analyze`, `/interview/*`, `/mentor/*`) require a valid `csrf_token` input.
- **Timing Attack Resistance:** Token validation utilizes constant-time string comparisons (`secrets.compare_digest`) to prevent timing side-channel exploitation.
- **Headless API Exemption:** Pure JSON endpoints (`/api/*`) require explicit `Content-Type: application/json` headers and are protected via dedicated IP rate limiters rather than cookie-based session tokens.

### D. Rate Limiting & Resource Exhaustion Defense (`src/security/rate_limiter.py`)
- **Sliding-Window Rate Limiter:** Implemented with thread-safe `threading.Lock` primitives.
- **Tiered Thresholds:**
  - **Headless API (`/api/match`):** Capped at 60 requests per minute per IP address.
  - **Document Upload Form (`/analyze`):** Capped at 30 uploads per minute per IP address.
- **Standardized HTTP 429 Responses:** Rejected requests receive an explicit `HTTP 429 Too Many Requests` status code with a numeric `Retry-After` header indicating seconds until quota replenishment.
- **Memory Management:** Expired client timestamp buckets are pruned automatically to eliminate memory leaks under distributed scanning.

### E. Input Boundary Validation
- All string inputs submitted to `/api/match` are strictly validated:
  - Minimum length: 10 characters (rejects empty or whitespace payloads).
  - Maximum length: 100,000 characters (prevents computational denial-of-service on regex analyzers and feature extractors).
  - Model backend input is restricted to an approved enumeration (`"production"`, `"challenger_m5"`).

### F. Information Disclosure & Error Sanitization
- **Path Suppression:** Global error handlers (HTTP 400, 404, 429, 500) intercept unhandled exceptions and return sanitized error descriptions.
- **Stack Trace Concealment:** Raw Python tracebacks and internal repository paths (e.g., `D:\skillsync1\...`) are never leaked to external clients.
- **Log Privacy & Redaction:** Resume content is never dumped in plaintext to operational log streams. Logs record only document lengths, hash digests, and sanitized operational metadata.

### G. Database Integrity & Injection Prevention
- Both SQLite databases (`embedding_cache.sqlite` and `embedding_queue.sqlite`) utilize parameterized SQL queries exclusively, eliminating SQL injection vectors.
- SQLite connections operate with Write-Ahead Logging (`WAL` mode) and a 30.0-second busy timeout to prevent database lock contention under concurrent load.

---

## 3. Vulnerability Verification Summary

| Threat Vector | Mitigation Mechanism | Verification Test | Result |
|---|---|---|:---:|
| **Executable Upload Masquerading** | Magic byte inspection (`%PDF-`, `PK\x03\x04`) | `test_file_upload_security_and_validation` | **BLOCKED** |
| **Directory Path Traversal** | `secure_filename` + character stripping | `test_file_upload_security_and_validation` | **BLOCKED** |
| **Cross-Site Request Forgery** | Constant-time session CSRF tokens | `test_csrf_and_rate_limiting` | **BLOCKED** |
| **API Denial of Service (DoS)** | 60 rpm sliding window rate limiter | `test_csrf_and_rate_limiting` | **BLOCKED** |
| **Malformed Payload Crash** | Strict JSON schema and length bounds | `test_api_input_boundaries_and_error_handling` | **BLOCKED** |
| **Sensitive Data Exposure** | Stack trace & local path suppression | `test_error_handling_and_security` | **BLOCKED** |
| **Database Corruption / Loss** | SQLite WAL mode & stale job recovery | `test_zero_lost_jobs_across_restarts` | **PRESERVED** |
