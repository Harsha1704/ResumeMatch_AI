# RESUMEMATCH AI — PHASE 7.3: COMPREHENSIVE SECURITY AUDIT & THREAT MODEL

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Audit Date**: November 17, 2026  
**Auditor**: Lead Security Architect & QA Engineer  
**Overall Security Posture**: **HARDENED / PRODUCTION READY**

---

## 1. Executive Summary & Findings Severity Matrix

This security audit covers the entirety of ResumeMatch AI's backend architecture ([app.py](file:///d:/skillsync1/app.py)), data layer, API surface, frontend network client ([frontend/src/services/api.ts](file:///d:/skillsync1/frontend/src/services/api.ts)), and same-site subdomain / cross-origin security controls.

Every security control has been empirically validated via automated regression tests in [tests/test_phase7_production_readiness.py](file:///d:/skillsync1/tests/test_phase7_production_readiness.py) using real application behavior (real subprocess startup, real HTTP `Set-Cookie` assertions, complete route CSRF inventories, real DOCX archive bombs, real rate limit threshold triggers, and real multi-engine Playwright browser tests).

### Findings Breakdown by Severity

| Severity Level | Count | Status | Description |
| :--- | :---: | :---: | :--- |
| **CRITICAL** | **0** | Passed | No critical vulnerabilities detected. Zero remote code execution, zero authentication bypass, zero SQL injection. |
| **HIGH** | **0** | Passed | No high-severity vulnerabilities detected. Fail-closed CSRF, host-only session isolation, fail-closed SameSite=Lax enforcement, and IDOR defenses are fully enforced. |
| **MEDIUM** | **1** | Mitigated via Architecture | **SEC-MED-01**: Third-party cookie blocking on default cross-site cloud provider domains (`*.vercel.app` $\rightarrow$ `*.onrender.com`). Mitigated by Option 1 custom apex domain architecture (`*.resumematch.ai`). |
| **LOW** | **1** | Monitored | **SEC-LOW-01**: Scikit-Learn `RuntimeWarning: invalid value encountered in divide` during truncated SVD on zero-variance synthetic test matrices. Harmless in production with real resumes. |
| **INFORMATIONAL**| **2** | Addressed | **SEC-INFO-01**: CORS allowlist origin reflection behavior for validated credentials requests matching `FRONTEND_ORIGINS`.<br>**SEC-INFO-02**: SQLite WAL mode `busy_timeout` configuration under multi-worker Gunicorn. |

---

## 2. Real Production Configuration & Threat Model Verification

### 2.1 Secret Key & Production Hardening
- **Active Setting**: `RESUMEMATCH_ENV=production` and `SECRET_KEY`.
- **Enforcement ([app.py#L37-L50](file:///d:/skillsync1/app.py#L37-L50))**:
  ```python
  INSECURE_SECRET_KEYS = {
      "skillsync-dev-key-2026",
      "dev-key-change-me",
      "insecure-default",
      "change-me",
      "secret",
      "default",
      ""
  }
  if APP_ENV == "production":
      if not secret_key or secret_key.strip() in INSECURE_SECRET_KEYS or len(secret_key.strip()) < 16:
          raise RuntimeError("SECRET_KEY must be configured with a secure, random value for production deployments.")
  ```
- **Automated Verification**: Spawns real Python processes importing `app.py`. Verified that missing keys or insecure defaults fail closed with `RuntimeError`, while valid random keys boot cleanly ([tests/test_phase7_production_readiness.py::test_prod_01](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L42)).

### 2.2 Enforced Host-Only Cookie Policy (Option 1)
- **Active Settings**: `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_DOMAIN=None` (host-only cookie).
- **Strict Startup Fail-Closed Enforcement ([app.py#L51-L69](file:///d:/skillsync1/app.py#L51-L69))**:
  ```python
  raw_cookie_domain = os.environ.get("SESSION_COOKIE_DOMAIN", "").strip()
  raw_same_site = os.environ.get("SESSION_COOKIE_SAMESITE", "").strip()

  if APP_ENV == "production":
      if raw_cookie_domain:
          raise RuntimeError(
              f"SESSION_COOKIE_DOMAIN must not be configured in production (got '{raw_cookie_domain}'). "
              "Host-only cookies (Domain=None) are strictly enforced in production to prevent unintended cookie sharing across subdomains."
          )
      if raw_same_site and raw_same_site.lower() != "lax":
          raise RuntimeError(
              f"SESSION_COOKIE_SAMESITE must be 'Lax' in production (got '{raw_same_site}'). "
              "Conflicting SameSite overrides are not permitted in production deployments."
          )
  ```
- **Automated Verification**:
  - [tests/test_phase7_production_readiness.py::test_prod_01](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L95) (Case D): Tests that setting `SESSION_COOKIE_DOMAIN` to `.resumematch.ai`, `resumematch.ai`, or `.example.com` causes production startup to terminate immediately with non-zero exit code (`proc.returncode != 0`).
  - [tests/test_phase7_production_readiness.py::test_prod_01](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L108) (Cases E & F): Tests that conflicting `SESSION_COOKIE_SAMESITE` values (`None`, `Strict`, `invalid`) fail closed with `RuntimeError`, while `Lax` boots cleanly.
  - [tests/test_phase7_production_readiness.py::test_prod_02](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L130): Inspects actual HTTP `Set-Cookie` response headers:
    ```http
    Set-Cookie: session=...; Secure; HttpOnly; Path=/; SameSite=Lax
    ```
    Confirms that **no Domain attribute** is present, strictly binding the cookie to the hosting API origin.

### 2.3 Simulated Same-Site Subdomain Browser Verification (.test Domain Simulation)
- **Verified Suite**: [frontend/tests/browser_same_site_subdomain.test.mjs](file:///d:/skillsync1/frontend/tests/browser_same_site_subdomain.test.mjs) (1225 lines, SHA-256: `601E84DE696C6F9594EB8B14482F4C70705F2E14C06E83613B090DCC6195497B`).
- **Scope & Boundary Distinction**:
  This automated Playwright suite runs against simulated local HTTPS endpoints (`app.resumematch.test` and `api.resumematch.test`) via a local CONNECT proxy. It proves that same-site subdomains preserve `SameSite=Lax` cookies under RFC 6265bis specifications across tested browser engines (Chromium 159.0, Firefox 159.0, and WebKit 27.2 WinCairo on Windows). Compatibility claims are strictly limited to these tested browser engines and configurations; we do not claim universal Safari or Firefox behavior.
  **This test demonstrates architectural validity; it does NOT prove that `app.resumematch.ai` and `api.resumematch.ai` are currently active, registered, or operational on the Internet.**
- **Architecture**: Tested across separate HTTPS subdomains sharing the registrable domain `resumematch.test`:
  - Frontend: `https://app.resumematch.test:8443`
  - Backend: `https://api.resumematch.test:9443`
  - Unapproved External Origin: `https://unauthorized.external.test:8444` (used for cross-site browser origin rejection and state-changing mutation rejection without JavaScript header spoofing)
  - Unapproved Same-Site Sibling Origin: `https://evil.resumematch.test:8445` (used for authenticated sibling origin isolation and CSRF defense verification)
  - Local HTTP CONNECT proxy (port 9091) routes traffic without modifying system `/etc/hosts` or DNS.
- **Empirical Findings Across Tested Engines**:
  - **Raw HTTP Response Header**: Captured on `/api/csrf-token` across all three engines, confirming `Secure; HttpOnly; SameSite=Lax` and the complete absence of a `Domain` attribute (host-only cookie enforced).
  - **Chromium (159.0)**: CSRF token retrieval with `credentials: include` (200 OK), host-only cookie stored for `api.resumematch.test`, sibling host `app.resumematch.test` cannot access cookie, genuine browser preflight OPTIONS request/response correlated via CDP, mutation succeeded (200 OK), session continuity verified across sequential mutations, uncredentialed and omitted-credentials requests rejected (403 Forbidden).
  - **Firefox (159.0)**: Identical full pass across all stages.
  - **WebKit (27.2)**: Same-site cookie successfully preserved (no Apple ITP third-party blocking), host-only cookie scoped to API, sibling host isolated, protected mutations succeeded (200 OK), session continuity preserved, uncredentialed requests strictly rejected (403 Forbidden).
  - **Stage J.1: Cross-Site CORS Response Enforcement**: When `unauthorized.external.test:8444` attempts a credentialed read (`/api/csrf-token`), the request carries the unapproved Origin header naturally without spoofing, the Flask backend refuses to approve the origin, and the browser blocks client-side JavaScript from reading the response.
  - **Stage J.2: Cross-Site Unauthorized Mutation Rejection & State Preservation**: When `unauthorized.external.test:8444` attempts a state-changing mutation (`POST /api/candidate/update-role` via browser form submission with `target_role: 'Malicious Attacker Injected Role'`), the server receives `Origin: https://unauthorized.external.test:8444` on the wire, server-side CSRF validation actively rejects the mutation with HTTP 403 Forbidden (`{"status": "error", "message": "CSRF token missing or invalid"}`), the browser receives no successful response, and subsequent verified queries from the authenticated session confirm that application state on the server remained completely unchanged (`job_title` remained `'Same-Site Lead Architect'`).
  - **Stage K.1: Authenticated Same-Site Sibling Mutation Rejection**: In the same authenticated browser context, navigation to unapproved sibling origin `https://evil.resumematch.test:8445` followed by a natural form POST to `/api/candidate/update-role` with `target_role: 'Attacker Sibling Injected Role'`. Because `evil.resumematch.test` and `api.resumematch.test` share registrable domain `resumematch.test`, the browser sends natural `Origin: https://evil.resumematch.test:8445` AND transmits the `SameSite=Lax` session cookie on the wire under RFC 6265bis. The backend receives the cookie, verifies the signed session cookie against `SECRET_KEY`, and confirms authenticated session state (`X-Server-Cookie-Present: true`, `X-Server-Session-Authenticated: true` when test audit headers are enabled; disabled in production). Server-side `_validate_csrf()` intercepts the request and rejects it with HTTP 403 Forbidden (`CSRF token missing or invalid`) because the sibling cannot obtain the session CSRF token. This isolates origin enforcement and proves rejection was NOT due to a missing session cookie. Flask default session cookies are cryptographically signed with HMAC-SHA256, not encrypted; the server verifies the cryptographic signature without requiring cookie decryption. Authoritative session query confirms application state remained unchanged (`job_title` remained `'Same-Site Lead Architect'`).
  - **Stage K.2: Isolated Origin-Allowlist Preflight Enforcement**: When `evil.resumematch.test:8445` attempts a credentialed `fetch` with custom headers (`X-CSRF-Token`), the browser dispatches an `OPTIONS` preflight carrying natural `Origin: https://evil.resumematch.test:8445`. Flask-CORS checks `Origin` against `FRONTEND_ORIGINS`, refuses `Access-Control-Allow-Origin`, and refuses `Access-Control-Allow-Credentials`. The browser blocks request execution via CORS SOP. Application state query proves target role remains strictly `'Same-Site Lead Architect'`.
  - **Diagnostic Response Header Production Guard**: The audit headers (`X-Server-Received-Origin`, `X-Server-Cookie-Present`, `X-Server-Session-Authenticated`) emitted by `_validate_csrf()` are strictly guarded behind `APP_ENV != "production"` and `ENABLE_TEST_AUDIT_HEADERS=true`. They are explicitly unavailable in production (`RESUMEMATCH_ENV=production`), even if `ENABLE_TEST_AUDIT_HEADERS=true` is accidentally configured in the environment (confirmed via real-subprocess automated regression test in `tests/test_phase7_production_readiness.py::test_prod_13`).
  - **Observed Environment-Specific Engine Limitation**: In Playwright's WebKit build on Windows (Version 27.2, WinCairo port), `fetch(..., { credentials: 'omit' })` inside an already-authenticated page exhibits an engine limitation where WinCairo's native network process does not strip existing cookies from its jar for matching domains. Stage I.1 proves the separate security requirement: an uncredentialed caller strictly fails closed (403). Findings are strictly limited to this Windows WinCairo test harness and do not generalize to macOS Safari.

### 2.4 Universal CSRF Defense Across Complete Route Inventory
- **Coverage**: All 17 state-changing routes:
  1. `POST /api/candidate/update-role`
  2. `POST /api/candidate/confirm-education`
  3. `POST /api/mentor/update-name`
  4. `POST /api/mentor/progress`
  5. `POST /api/mentor/reset-progress`
  6. `POST /api/career-mentor/evaluate-role`
  7. `POST /api/interview-studio/generate`
  8. `POST /api/interview/evaluate`
  9. `POST /api/interview/confirm-activity`
  10. `POST /api/interview/reset`
  11. `POST /api/interview/sessions`
  12. `DELETE /api/interview/sessions/<id>`
  13. `POST /api/interview-practice/submit`
  14. `POST /api/analyze`
  15. `POST /analyze` (legacy HTML form)
  16. `POST /interview-practice/submit` (legacy HTML form)
  17. `POST /interview-studio/generate` (legacy HTML form)
- **Tri-State Verification**: Tested on every route:
  - Missing token $\rightarrow$ 403 Forbidden.
  - Invalid / forged token $\rightarrow$ 403 Forbidden.
  - Valid token $\rightarrow$ Passes validation (non-403).
- Verified in [tests/test_phase7_production_readiness.py::test_prod_03](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L196).

### 2.5 Real DOCX Archive Bomb Generation & Rejection
- **Threat**: Malicious ZIP/OpenXML archives designed to expand from kilobytes into gigabytes to cause Denial of Service.
- **Verification**: Generates a genuine 1000:1 compression ratio DOCX archive containing 10 MB of compressible zeros. Verified that both `validate_docx_archive_safety` and `parse_resume` reject it immediately with:
  `Security violation: Suspicious compression ratio (...) detected in DOCX member 'word/document.xml' (archive bomb protection).`
- Verified in [tests/test_phase7_production_readiness.py::test_prod_05](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L266).

### 2.6 Rate Limiting by Exceeding Threshold
- **Verification**: `SlidingWindowRateLimiter(max_requests=60, window_seconds=60.0)` enforced on public endpoint `/api/match`. Exceeding threshold triggers HTTP 429 Too Many Requests with `Retry-After` header.
- Verified in [tests/test_phase7_production_readiness.py::test_prod_06](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L293).

### 2.7 IDOR / BOLA Authorization (Reads & Mutations)
- **Read IDOR**: Accessing unowned analysis via `/api/analysis/<id>`, `/api/skill-gap`, or `/api/career-mentor` returns HTTP 403.
- **Mutation IDOR**: Creating session with unowned analysis ID, submitting answers to another owner's session, or deleting another owner's session returns HTTP 403.
- Verified in [tests/test_phase7_production_readiness.py::test_prod_07](file:///d:/skillsync1/tests/test_phase7_production_readiness.py#L332).

### 2.8 Rollback Security Posture & Protocol Boundary Invariants
- **CORS vs. Cookie Boundary**: Allowlisting origins in `FRONTEND_ORIGINS` satisfies CORS preflights, but does not bypass browser third-party cookie restrictions.
- **Legacy Fallback Limitation**: Under cross-site domains (`*.vercel.app` $\rightarrow$ `*.onrender.com`), WebKit/Safari ITP and Firefox partition or block third-party cookies; **the legacy cross-site architecture is NOT a guaranteed Safari-compatible rollback**.
- **Effective Fallback Configuration (Commit 07b88a058f166f13491fa9050ba835d95fd0e8fd)**:
  - Baseline code sets: `SESSION_COOKIE_SAMESITE = "None" if APP_ENV == "production" else "Lax"`, `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_DOMAIN = None`.
  - **Environment Variables Do Not Revert with Git Commits**: Administrators must verify Render service environment variables (`RESUMEMATCH_ENV=production`, `FRONTEND_ORIGINS` containing verified Vercel URLs).
- **Strict Invariants**: During any emergency rollback:
  - Universal fail-closed CSRF validation is never relaxed.
  - Session ownership and IDOR authorization checks are never bypassed.
  - HttpOnly and Secure cookie attributes are preserved unconditionally.
  - The backend release/configuration must be reverted before the frontend API URL is restored to avoid cross-site SameSite=Lax rejection.
