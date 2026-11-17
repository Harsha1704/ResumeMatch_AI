# ResumeMatch AI — Phase 6 Security & Reliability Audit Report

**Date**: November 17, 2026  
**Repository**: `Harsha1704/ResumeMatch_AI`  
**Branch**: `fix/resumematch-final-repair`  
**Phase 6 Starting Commit**: `ad4bc5b2f5e7e6f5b892c5e788102a573b07c2f6`  
**Phase 6.4 Starting Commit**: `64ba81caf0f5f659ac9c2a4b8afaf5cea3997499`  
**Phase 6.5 Starting Commit**: `13535d12a982622bb803e1caef27da7f66b1be3d`  
**Phase 6.6 Starting Commit**: `c8e51f901766899b9565590df4ad5850ca492f1e`  
**Auditor**: Senior Security Engineer & Production-Readiness Reviewer  
**Status**: **PASS (Hardened & Verified)**

---

## 1. Executive Summary

A comprehensive application security and reliability audit was conducted across all ten functional modules of **ResumeMatch AI**. The audit focused on Broken Object Level Authorization (BOLA / IDOR), Cross-Site Request Forgery (CSRF), Cross-Origin Resource Sharing (CORS), Session Hijacking and Isolation, Document Parsing Vulnerabilities (Zip Bombs / Malicious Binaries), Database Transaction Concurrency, and Error Handling Information Leakage.

All discovered security vulnerabilities were eliminated with minimal safe code modifications, backed by automated adversarial regression tests in [`tests/test_phase6_integration_audit.py`](file:///d:/skillsync1/tests/test_phase6_integration_audit.py), [`tests/test_phase6_1_csrf_security.py`](file:///d:/skillsync1/tests/test_phase6_1_csrf_security.py), [`tests/test_phase6_2_legacy_csrf.py`](file:///d:/skillsync1/tests/test_phase6_2_legacy_csrf.py), and Node / Playwright test suites in `frontend/tests/`.

---

## 2. Vulnerability Assessment & Remediations

### 2.1 Broken Object Level Authorization (BOLA / IDOR) — RESOLVED
- **Vulnerability**:
  - In `app.py`, endpoints `GET /api/analysis/<analysis_id>` and `GET /api/skill-gap?id=...` lacked session-bound authorization checks.
  - While legacy HTML routes (`/results`, `/skill-gap`) and newer modules (`/api/career-mentor`, `/api/interview-studio`) checked `session["allowed_analyses"]`, `api_get_analysis` directly retrieved `ANALYSIS_CACHE[analysis_id]` if the ID was present in memory.
  - An attacker guessing or intercepting an analysis ID could retrieve another candidate's full resume analysis dossier, contact information, project history, and skill breakdown.
- **Remediation**:
  - Implemented centralized authorization helper `_resolve_authorized_analysis(aid)` in `app.py`.
  - When an explicit ID is requested:
    - If ID does not exist in `ANALYSIS_CACHE`, returns `404 Not Found`.
    - If ID exists but does not belong to the requesting session (`aid not in session.get("allowed_analyses", [])`), returns `403 Forbidden` (`"Unauthorized access to requested analysis ID"`).
    - If ID is `"sample"`, `"demo"`, or `"sample-preview"`, returns authentic demo candidate profile (`200 OK`).
    - If ID is omitted, returns current session's latest authorized analysis or fallback demo (`200 OK`).
  - Applied `_resolve_authorized_analysis` across `api_get_analysis`, `api_skill_gap`, `api_career_mentor`, `api_career_mentor_evaluate_role`, and aliased `_resolve_authorized_interview_analysis` to it.
- **Verification**: Verified by `test_02_cross_session_analysis_access_rejected_with_403` and `test_03_nonexistent_analysis_id_returns_404_across_all_modules`.

### 2.2 Cross-Origin Session Continuity & CORS Security — RESOLVED
- **Vulnerability**:
  - The frontend client `frontend/src/services/api.ts` used `credentials: 'omit'` in `fetchJson` and omitted credentials in `analyzeResume`.
  - In cross-origin deployments (Vercel CDN frontend + Render Flask API backend), session cookies were dropped, breaking candidate ownership and CSRF validation.
  - Furthermore, `methods` in Flask-CORS only allowed `["GET", "POST", "OPTIONS"]`, causing preflight `OPTIONS` requests for `DELETE /api/interview/sessions/<id>` to fail.
- **Remediation**:
  - Updated `fetchJson` in `frontend/src/services/api.ts` to `credentials: 'include'`.
  - Added `credentials: 'include'` and automated `X-CSRF-Token` header attachment to `analyzeResume`.
  - Updated Flask-CORS `methods` in `app.py` line 76 to include `DELETE` and `PUT`: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`.
  - Added `"Accept"` to allowed request headers in CORS.
- **Verification**: Verified by `test_06_cors_configuration_and_preflight_headers` and `test_08_interview_session_ownership_and_safe_deletion_csrf`.

### 2.3 State-Changing CSRF Enforcement, Token Delivery & Legacy Mutation Hardening (Phase 6.1 & Phase 6.2) — RESOLVED & VERIFIED
- **Vulnerability & Challenge**:
  - The React frontend is deployed separately (Vercel CDN) from the Flask API backend (Render).
  - Previous implementations relied on template injection for CSRF tokens or attempted to read `csrf_token` from `document.cookie` or meta tags.
  - Because `SESSION_COOKIE_HTTPONLY = True`, JavaScript cannot read the session cookie, and a static SPA on Vercel does not have server-side rendered meta tags.
  - Legacy HTML form routes (`POST /analyze`, `POST /interview-studio/generate`, `POST /interview-practice/submit`) were initially unvalidated for CSRF, leaving legacy session-backed workflows open to cross-site request forgery.
  - Furthermore, previous validations contained test-mode bypasses (`if not is_testing`), allowing mutations without valid CSRF tokens during automated test runs.
- **Architectural Remediation**:
  1. **Session-Bound Token Delivery Endpoint (`GET /api/csrf-token`)**:
     - Added dedicated endpoint in `app.py` returning `{"status": "success", "csrf_token": <64-char-hex>}`.
     - Token is bound to the active Flask session via `src.security.csrf.generate_csrf_token()`.
     - Cross-origin credentialed requests from whitelisted frontend origins receive the token alongside the `HttpOnly` session cookie (`SameSite=None, Secure=True` in production; `SameSite=Lax` in development).
  2. **Universal Fail-Closed CSRF Validation (`_validate_csrf`)**:
     - Implemented unified, fail-closed CSRF validator `_validate_csrf(data=None)`.
     - Checks `X-CSRF-Token` request header, JSON body `csrf_token`, or multipart/urlencoded form field `csrf_token`.
     - Validates in constant time against `session.get("csrf_token")` using `secrets.compare_digest`.
     - Rejects non-string inputs safely to prevent type confusion vulnerabilities.
     - **Removed all testing bypasses**: Validation is strictly enforced across ALL environments including `app.config["TESTING"] = True`. Missing, invalid, or cross-session mismatched tokens strictly return `403 Forbidden` (`{"status": "error", "message": "CSRF token missing or invalid"}` for API requests or HTTP 403 Forbidden with description for HTML form submissions).
  3. **Universal Endpoint Coverage & Full Mutation Inventory**:
     - Audited and applied `_validate_csrf` to all 17 state-changing mutation endpoints (14 JSON/multipart API routes and 3 legacy HTML form routes):
       - `POST /analyze` (Legacy HTML form & file upload; mutates session `allowed_analyses` and cache)
       - `POST /interview-studio/generate` (Legacy HTML form; generates interview session and mutates active session)
       - `POST /interview-practice/submit` (Legacy HTML form; records practice answer in SQLite store)
       - `POST /api/analyze` (JSON & multipart file upload; mutates session `allowed_analyses` and cache)
       - `POST /api/mentor/update-name` (JSON; mutates session preferred name)
       - `POST /api/mentor/progress` (JSON; mutates milestone tracking)
       - `POST /api/mentor/reset-progress` (JSON; resets session milestone tracking)
       - `POST /api/candidate/update-role` (JSON; mutates session target role)
       - `POST /api/candidate/confirm-education` (JSON; mutates session education attestation)
       - `POST /api/career-mentor/evaluate-role` (JSON; reads session dossier, mutates career mentor context)
       - `POST /api/interview-studio/generate` (JSON; creates SQLite session, mutates `active_interview_session_id`)
       - `POST /api/interview/sessions` (POST; creates SQLite practice session & ownership)
       - `DELETE /api/interview/sessions/<session_id>` (DELETE; deletes SQLite practice session)
       - `POST /api/interview-practice/submit` (JSON; persists answers in SQLite store)
       - `POST /api/interview/confirm-activity` (JSON; mutates session candidate confirmations)
       - `POST /api/interview/reset` (JSON; resets SQLite store & active session)
       - `POST /api/interview/evaluate` (JSON; AJAX evaluator bound to active session)
     - **Documented Safe Exception (`POST /api/match`)**:
       - `POST /api/match` is an unauthenticated, stateless ML inference endpoint. It accepts a resume string and job description string and returns match score and predicted class. It neither reads nor mutates Flask sessions, cookies, or database records. It is protected against abuse by a strict sliding-window IP rate limiter (`api_rate_limiter`, 60 req/min). Bypassing CSRF for this endpoint is standard, safe, and necessary for external programmatic integrations.
  4. **React Client In-Memory Fail-Closed Token Management (`frontend/src/services/api.ts`)**:
     - Implemented `getCsrfToken()`, `fetchCsrfToken()`, and `clearCsrfToken()`.
     - Retains token safely in memory (no insecure localStorage or client-side plain-text cookie persistence).
     - **Fail-Closed Enforcement**: If CSRF token retrieval fails or returns empty, mutations are aborted immediately *before* calling `fetch` on the mutation endpoint. No unauthenticated or tokenless request is transmitted.
     - On 403 Forbidden responses, `clearCsrfToken()` clears the cached token without automatically retrying or replaying mutations (mutations must never be replayed without explicit user intent).
     - Both `fetchJson` and `analyzeResume` enforce fail-closed token retrieval and attach `X-CSRF-Token` header.
  5. **Legacy HTML Form Template Hardening**:
     - Embedded `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">` into all form blocks across `templates/interview_studio.html`, `templates/interview_practice.html`, and `templates/analyze.html`.

---

### 2.4 Browser Compatibility Verification & Genuine Mutation Preflight (Phase 6.6 & 6.7)

#### Tested Software Versions
- **Playwright Package**: `1.65.1` (dynamically read from package manifest)
- **Chromium Binary**: `159.0.8154.6` (dynamically verified via `browser.version()`)
- **Firefox Binary**: `159.0` (dynamically verified via `browser.version()`)
- **WebKit Binary**: `27.2` (dynamically verified via `browser.version()`)

#### Genuine Mutation-Triggered Preflight Verification & CDP Correlation
- In [`frontend/tests/browser_cross_origin.test.mjs`](file:///d:/skillsync1/frontend/tests/browser_cross_origin.test.mjs), rather than issuing manual `fetch(method: OPTIONS)` calls with browser-forbidden headers, the suite triggers a real cross-origin POST mutation from the browser document context with `Content-Type: application/json` and `X-CSRF-Token`.
- **Preflight Capture & Correlation Verification**:
  - **In Chromium**: Intercepted the browser's internal network stack via Chrome DevTools Protocol (`Network.requestWillBeSent` and `Network.responseReceived`).
    - Captured the genuine browser preflight OPTIONS request and its unique CDP `requestId`.
    - Strictly correlated the preflight response using the matching `requestId`, guaranteeing that response headers belong to the OPTIONS preflight and not the subsequent POST mutation.
    - Verified the preflight request URL corresponds to `/api/candidate/update-role`.
    - Verified `Access-Control-Request-Method: POST`.
    - Verified `Access-Control-Request-Headers` includes both `content-type` and `x-csrf-token`.
    - Verified correlated preflight response status `200 OK`, `Access-Control-Allow-Origin: https://localhost:3443`, `Access-Control-Allow-Credentials: true`, and `Access-Control-Allow-Headers: X-CSRF-Token`.
    - Enforced fail-closed assertions: fails test immediately if preflight request or correlated response is not captured (no silent skips).
  - **In Firefox**: Documented that Marionette internal socket networking evaluates the preflight internally without surfacing preflight requests/responses to high-level automation listeners. The test strictly separates server-header evidence (verified via the standalone `APIRequestContext` probe) from browser-enforced mutation evidence (the browser evaluates the preflight and successfully completes the protected POST with HTTP 200 OK).
  - **In WebKit (Reconciled Default Behavior)**: Verified that under native Apple WebKit default privacy settings (ITP active), third-party cross-origin cookies are dropped (`sessionCookie === undefined`). Consequently, the cross-origin mutation fails closed with HTTP 403 Forbidden (`itcMutation.status === 403`). No browser privacy settings were altered or relaxed to force a 200 OK result. In contrast, same-origin WebKit retains the session cookie and completes mutations with HTTP 200 OK.
- **Separate Missing-Token Rejection**: Tested separately from the authenticated flow; verified that cross-origin mutations without `X-CSRF-Token` return HTTP 403 Forbidden (`CSRF token missing or invalid`).

---

### 2.5 Recommended Production Architecture: Same-Site Host-Only Cookie Decision

#### Architectural Specification
- **Frontend SPA Origin**: `https://app.resumematch.ai`
- **Backend API Origin**: `https://api.resumematch.ai`
- **Protocol**: HTTPS strictly enforced.
- **Cookie Attributes**:
  - `SESSION_COOKIE_SAMESITE = "Lax"`
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SECURE = True`
  - `SESSION_COOKIE_DOMAIN = None` (Host-only cookie; omit `Domain` attribute).
- **CORS Whitelist**: `FRONTEND_ORIGINS = "https://app.resumematch.ai"`

#### Corrected Security Scope & Limitations: What Host-Only Cookies Do and Do NOT Prevent
1. **What Host-Only Cookies Protect**:
   - Setting `SESSION_COOKIE_DOMAIN = None` creates a host-only cookie scoped strictly to the FQDN `api.resumematch.ai`.
   - Sibling subdomains (e.g. `app.resumematch.ai`, `blog.resumematch.ai`, `docs.resumematch.ai`, or third-party marketing services) never receive the API session cookie directly in ambient HTTP requests.
   - Sibling subdomains cannot "toss" a domain-scoped cookie (`Domain=.resumematch.ai`) to shadow or overwrite the API cookie under RFC 6265 rules.
   - `HttpOnly=True` prevents client-side JavaScript on any origin from reading the cookie string via `document.cookie`.
2. **What Host-Only Cookies Do NOT Protect (Security Reality)**:
   - Host-only cookies do **NOT** prevent an XSS vulnerability on the frontend (`app.resumematch.ai`) from initiating credentialed cross-origin requests to `api.resumematch.ai`.
   - Because `api.resumematch.ai` whitelists `app.resumematch.ai` in CORS with `supports_credentials=True`, malicious JavaScript executing on `app.resumematch.ai` can issue `fetch('https://api.resumematch.ai/...', { credentials: 'include' })`, and the browser will automatically attach the host-only session cookie.
3. **Mandatory Defense-in-Depth Requirements**:
   - Because cookies cannot prevent authenticated request execution by compromised frontend JavaScript, robust application security requires:
     - Strict Content Security Policy (CSP) to restrict script sources and exfiltration endpoints.
     - Context-aware HTML and JavaScript output encoding to prevent script injection.
     - Ongoing dependency vulnerability scanning.
     - Session-bound CSRF token validation on all mutating endpoints.
     - Fine-grained server-side authorization and rate limiting.

---

### 2.6 Production Readiness Claims & Verification Tiers

To ensure complete transparency and eliminate assumptions, production configuration is strictly classified into five distinct categories:

1. **A. Verified Source Configuration**:
   - `frontend/src/services/api.ts` uses `credentials: 'include'`.
   - `frontend/vercel.json` contains ONLY SPA fallback `/(.*) -> /index.html`; no `/api/*` rewrites exist; reverse-proxy is **NOT active** in source.
   - `render.yaml` sets `FRONTEND_ORIGIN: https://resumematch-ai.vercel.app` and `RESUMEMATCH_ENV: production`.
   - `app.py` in production sets `SameSite=None`, `Secure=True`, `HttpOnly=True`, `Domain=None`, and allows CORS for `FRONTEND_ORIGIN`.
2. **B. Verified Cloud Deployment Settings**:
   - Target frontend: `https://resumematch-ai.vercel.app` (registered on Vercel).
   - Target backend: `https://resumematch-ai-api.onrender.com` (registered on Render).
3. **C. Unknown Private Dashboard Settings**:
   - Exact environment variables currently set inside Vercel's private cloud dashboard project settings for `resumematch-ai` (e.g. build-time `VITE_API_BASE_URL`).
4. **D. Recommended Future Architecture (Not Currently Deployed)**:
   - Same-site apex domain alignment (`app.resumematch.ai` + `api.resumematch.ai`) with host-only cookie, or single-origin reverse-proxy rewrite. This architecture is **NOT currently deployed or active** on production DNS or cloud settings.
5. **E. Actual Production Compatibility (Remains Unverified)**:
   - Actual production compatibility remains **unverified** until custom domains and cloud deployment settings are configured, deployed, and tested in live environments across real user devices and networks.
   - Under current decoupled deployment (`https://resumematch-ai.vercel.app` calling `https://resumematch-ai-api.onrender.com`), the application is **incompatible with Safari/WebKit** due to Apple ITP blocking third-party cookies.

---

### 2.7 Document Parsing Limits & Archive Bomb Protection — VERIFIED
- **File Upload Limits**:
  - Maximum upload size strictly enforced at 16 MB (`MAX_CONTENT_LENGTH = 16 * 1024 * 1024`).
  - Supported extensions restricted to `.pdf`, `.docx`, and `.txt`.
- **DOCX OpenXML Archive Bomb Protection** (`validate_docx_archive_safety` in `src/analysis/resume_parser.py`):
  - Limits total ZIP member entries to 500 (`MAX_DOCX_MEMBER_COUNT`).
  - Limits single member uncompressed size to 32 MB (`MAX_DOCX_SINGLE_MEMBER_SIZE`).
  - Limits total uncompressed archive size to 64 MB (`MAX_DOCX_UNCOMPRESSED_SIZE`).
  - Rejects compression ratios exceeding 100:1 for members > 10KB.
- **PDF & Binary Safety**:
  - Rejects corrupted or encrypted PDFs without OCR fallback.
  - Rejects binary executable signatures (`MZ` for PE/EXE, `ELF` for Linux binaries, null bytes in TXT files).

### 2.8 SQLite Concurrency, Transactions & Persistence — VERIFIED
- **Database Engine**:
  - SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL`), `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=30000`.
  - Connection isolation: thread-safe connection pooling per thread (`check_same_thread=False`).
- **Atomic Operations & Rollback**:
  - Session mutations (`create_session`, `submit_answer`, `next_question`, `complete_session`, `delete_session`) use context-managed database transactions.
  - If disk write fails, the database transaction rolls back, in-memory state is restored to its prior state (preventing split-brain divergence), and an observable `500 Internal Server Error` is returned with structured logging.

### 2.9 Information Leakage & Error Handling — VERIFIED
- **Structured Error Responses**:
  - Database exceptions are caught, logged to server logs with stack traces, and returned to clients as sanitized JSON error messages (`500 Internal Server Error`).
  - Database connection strings, SQL queries, internal filesystem paths, and exception tracebacks are never leaked in API response payloads.
- **Secrets Management**:
  - Secret key configured via `SECRET_KEY` environment variable; production mode strictly requires a non-empty environment secret.

---

## 3. Security Audit Matrix

| Security Domain | Status | Control Mechanism |
| :--- | :--- | :--- |
| **Authentication & Session Isolation** | **PASS** | Session-bound `allowed_analyses` and `interview_owner_id`; 403 on cross-session access |
| **CSRF Protection** | **PASS** | Fail-closed token validation on all 17 state-changing mutation endpoints |
| **CORS Policy** | **PASS** | Strict whitelist (`FRONTEND_ORIGINS`), credentials enabled, explicit methods (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`) |
| **Cross-Origin Testing** | **PASS** | Automated Playwright tests across separate origins (`https://localhost:3443` -> `https://127.0.0.1:5443`) in Chromium, Firefox, WebKit |
| **File Upload Security** | **PASS** | 16 MB ceiling, extension whitelist, magic byte verification, zip bomb protection |
| **Input Validation & Sanitization** | **PASS** | String type guards, character length ceilings (120 chars role, 100 chars evaluation) |
| **Persistence & Concurrency** | **PASS** | SQLite WAL mode, 30s busy timeout, atomic rollback on persistence failure |
| **Information Disclosure** | **PASS** | Sanitized error responses, zero stack trace leakage, zero LLM prompt injection surface |
| **Machine Learning Safety** | **PASS** | Frozen model artifact SHA256 verification, zero LLM runtime dependency, deterministic scoring |

---

## 4. Complete Mutating Endpoint Inventory (18 Routes Total)

The following inventory details all state-changing endpoints in ResumeMatch AI (`POST`, `PUT`, `PATCH`, `DELETE`), their payload formats, state mutation behavior, session dependency, and CSRF protection mechanisms:

| # | Route | Method | Payload Format | Mutates State | Session Auth | CSRF Enforced | Security Notes & Exception Justification |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `POST /analyze` | POST | Form (multipart / urlencoded) | Yes | Yes | **Yes** (`_validate_csrf`) | Legacy HTML resume submission. Mutates `session["allowed_analyses"]` and server analysis cache. Protected with fail-closed CSRF validation; rejected with 403 Forbidden on missing/invalid token. |
| 2 | `POST /interview-studio/generate` | POST | Form (urlencoded) | Yes | Yes | **Yes** (`_validate_csrf`) | Legacy HTML studio question generation and practice initialization. Mutates SQLite session store and `session["active_interview_session_id"]`. Protected with fail-closed CSRF validation. |
| 3 | `POST /interview-practice/submit` | POST | Form (urlencoded) | Yes | Yes | **Yes** (`_validate_csrf`) | Legacy HTML practice answer submission. Mutates SQLite practice answer records and navigates. Protected with fail-closed CSRF validation. |
| 4 | `POST /api/analyze` | POST | JSON / Multipart Form | Yes | Yes | **Yes** (`_validate_csrf`) | Core SPA resume analysis endpoint. Mutates `session["allowed_analyses"]` and in-memory cache. Enforces fail-closed CSRF via header or form field. |
| 5 | `POST /api/candidate/confirm-education` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Candidate education attestation. Mutates `session["candidate_confirmations"]`. |
| 6 | `POST /api/candidate/update-role` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Target position update. Mutates `session["candidate_target_role"]` (capped at 120 chars). |
| 7 | `POST /api/career-mentor/evaluate-role` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Role alignment evaluation. Reads authorized session dossier; mutates mentor context (capped at 100 chars). |
| 8 | `POST /api/interview-practice/submit` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Submits candidate answer. Mutates SQLite session store and answer history. |
| 9 | `POST /api/interview-studio/generate` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Generates interview questions, binds candidate evidence, and creates SQLite practice session. Mutates `session["active_interview_session_id"]`. |
| 10 | `POST /api/interview/confirm-activity` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Confirms candidate project/internship activity. Mutates `session["candidate_confirmations"]`. |
| 11 | `POST /api/interview/evaluate` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | AJAX instant answer scoring. Bound to active session; evaluates claim grounding against candidate evidence. |
| 12 | `POST /api/interview/reset` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Resets active interview session and clears practice answers in SQLite store. |
| 13 | `POST /api/interview/sessions` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Creates new Interview Practice session in SQLite store; binds ownership to `session["interview_owner_id"]`. |
| 14 | `DELETE /api/interview/sessions/<session_id>` | DELETE | None (URL parameter) | Yes | Yes | **Yes** (`_validate_csrf`) | Permanently deletes SQLite interview session. Enforces session ownership check (`interview_owner_id`) and CSRF validation. |
| 15 | `POST /api/mentor/progress` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Updates career roadmap milestone completion checkboxes. Mutates session milestone progress tracker. |
| 16 | `POST /api/mentor/reset-progress` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Resets career roadmap milestone tracker. Mutates session progress dictionary. |
| 17 | `POST /api/mentor/update-name` | POST | JSON | Yes | Yes | **Yes** (`_validate_csrf`) | Updates candidate display name. Mutates `session["candidate_preferred_name"]`. |
| 18 | `POST /api/match` | POST | JSON | **No** | **No** | **No (Safe Exception)** | **Stateless ML Inference Exception**: Programmatic matching endpoint. Accepts `{resume_text, job_description}` and runs frozen TF-IDF + Logistic Regression inference. It does NOT read or mutate Flask sessions, cookies, or database records. Protected by a sliding-window IP rate limiter (`api_rate_limiter`, 60 req/min). Bypassing CSRF is safe, necessary, and standard for external programmatic API consumers. |
