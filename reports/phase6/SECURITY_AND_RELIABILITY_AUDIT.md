# ResumeMatch AI — Phase 6 Security & Reliability Audit Report

**Date**: November 17, 2026  
**Repository**: `Harsha1704/ResumeMatch_AI`  
**Branch**: `fix/resumematch-final-repair`  
**Starting Commit**: `ad4bc5b2f5e7e6f5b892c5e788102a573b07c2f6`  
**Auditor**: Senior Security Engineer & Production-Readiness Reviewer  
**Status**: **PASS (Hardened & Verified)**

---

## 1. Executive Summary

A comprehensive application security and reliability audit was conducted across all ten functional modules of **ResumeMatch AI**. The audit focused on Broken Object Level Authorization (BOLA / IDOR), Cross-Site Request Forgery (CSRF), Cross-Origin Resource Sharing (CORS), Session Hijacking and Isolation, Document Parsing Vulnerabilities (Zip Bombs / Malicious Binaries), Database Transaction Concurrency, and Error Handling Information Leakage.

All discovered security vulnerabilities were eliminated with minimal safe code modifications, backed by automated adversarial regression tests in [`tests/test_phase6_integration_audit.py`](file:///d:/skillsync1/tests/test_phase6_integration_audit.py).

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
- **Verification**: Verified by dedicated adversarial suites:
  - [`tests/test_phase6_1_csrf_security.py`](file:///d:/skillsync1/tests/test_phase6_1_csrf_security.py) (41 test cases covering API token delivery, JSON/multipart validation, and cross-session isolation).
  - [`tests/test_phase6_2_legacy_csrf.py`](file:///d:/skillsync1/tests/test_phase6_2_legacy_csrf.py) (13 test cases covering legacy form routes, cross-session rejection, and multi-mutation session continuity).
  - [`frontend/tests/api_csrf.test.mjs`](file:///d:/skillsync1/frontend/tests/api_csrf.test.mjs) (6 unit tests verifying fail-closed token retrieval aborts mutations, header attachment, in-memory caching, and 403 clearing without auto-replay).

### 2.4 Production Browser Cookie Architecture Review & Real Browser Verification (Phase 6.3) — VERIFIED & DOCUMENTED

#### A. Request Destinations & `VITE_API_BASE_URL` Configuration
- In [`frontend/src/services/api.ts`](file:///d:/skillsync1/frontend/src/services/api.ts):
  ```typescript
  const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '';
  ```
- **Local Vite Development**: `frontend/.env.development` defines `VITE_API_BASE_URL=` (empty). Requests use relative paths (`/api/...`), and `frontend/vite.config.ts` proxies `/api` and `/health` requests to `http://127.0.0.1:5000`.
- **Production Decoupled Setup**: In production, `frontend/.env.example` documents `VITE_API_BASE_URL=https://resumematch-ai-api.onrender.com`. When populated in Vercel environment variables, the React SPA dispatches requests directly to Render (`https://resumematch-ai-api.onrender.com/api/...`), establishing a cross-site connection from `https://resumematch-ai.vercel.app`.

#### B. Cross-Site Browser Engine Behavior (Analysis vs. Real Browser Testing)
- **Architectural Analysis**:
  - `vercel.app` and `onrender.com` are separate Public Suffix List (PSL) domains, classifying requests as cross-site (third-party).
  - Modern engines enforce strict third-party cookie restrictions:
    1. **Safari WebKit (Intelligent Tracking Prevention - ITP)**: Strips or partitions third-party cookies by default regardless of `SameSite=None; Secure`.
    2. **Chrome / Chromium (Privacy Sandbox & Tracking Protection)**: Restricts third-party cookies and partitions unpartitioned cookies.
    3. **Firefox (Enhanced Tracking Protection / Total Cookie Protection)**: Isolates cookies in per-site jars, dropping cross-site session continuity.
- **Empirical Real Browser Testing via Playwright**:
  - Verified across real browser binaries running on Windows via [`frontend/tests/browser_compatibility.test.mjs`](file:///d:/skillsync1/frontend/tests/browser_compatibility.test.mjs):
    - **Chromium** (Playwright CFT v159.0.8154.6 / System Chrome v157.0.8103.78): **PASS**
    - **Firefox** (Playwright Firefox v159.0): **PASS**
    - **WebKit** (Playwright WebKit v27.2): **PASS**
  - All three browsers successfully retrieved session-bound CSRF tokens via `fetch('/api/csrf-token')`, retained `HttpOnly` session cookies in their real cookie jars, rejected unauthenticated mutations with HTTP 403 Forbidden, and successfully executed protected mutations with `X-CSRF-Token` returning HTTP 200 OK.
  - Furthermore, empirical tests verified that requests using `credentials: 'omit'` immediately drop session cookies and fail with HTTP 403 Forbidden.

#### C. Exact Configurations for Recommended Production Architectures
*Per strict constraints, no production domains or settings were modified. The exact configurations required for each architecture are detailed below:*

1. **Architecture 1: Same-Site Custom Domains (Recommended — Standard Production)**
   - **Domains**:
     - Frontend SPA: `https://app.resumematch.ai`
     - Backend API: `https://api.resumematch.ai`
   - **Frontend Config**: `VITE_API_BASE_URL=https://api.resumematch.ai`
   - **Backend Flask Config**:
     - `SESSION_COOKIE_DOMAIN = ".resumematch.ai"`
     - `SESSION_COOKIE_SAMESITE = "Lax"`
     - `SESSION_COOKIE_SECURE = True`
     - `SESSION_COOKIE_HTTPONLY = True`
     - `FRONTEND_ORIGINS = "https://app.resumematch.ai"`
   - **Mechanism**: Both origins share the apex domain `resumematch.ai`. Requests are first-party/same-site. Safari ITP, Chrome Tracking Protection, and Firefox ETP never block same-site cookies.

2. **Architecture 2: Reverse-Proxy / URL Rewrites (Single-Origin)**
   - **Domains**: Both frontend and backend accessed under `https://resumematch-ai.vercel.app`
   - **Frontend Config**: `VITE_API_BASE_URL=""` (**Must be empty**; relative paths `/api/...` ensure requests route through the proxy).
   - **Vercel Rewrite Config** in `frontend/vercel.json`:
     ```json
     {
       "rewrites": [
         { "source": "/api/:path*", "destination": "https://resumematch-ai-api.onrender.com/api/:path*" },
         { "source": "/health", "destination": "https://resumematch-ai-api.onrender.com/health" },
         { "source": "/(.*)", "destination": "/index.html" }
       ]
     }
     ```
   - **Backend Flask Config**:
     - `SESSION_COOKIE_DOMAIN = None` (**Crucial**: must NOT emit `Domain=onrender.com`).
     - `SESSION_COOKIE_SAMESITE = "Lax"` (Must NOT be `None`).
     - `SESSION_COOKIE_SECURE = True`.
     - `SESSION_COOKIE_HTTPONLY = True`.
     - `ProxyFix` middleware enabled to trust `X-Forwarded-Proto` and `X-Forwarded-Host`.

#### D. Why a Reverse-Proxy Rewrite Alone Does NOT Guarantee Cookie Compatibility
A URL rewrite alone is insufficient if the following four critical preconditions are not met:
1. **Conflicting Upstream Domain Attribute**: If the upstream Render service sets a `Domain` attribute (e.g. `Domain=resumematch-ai-api.onrender.com`) on `Set-Cookie`, the browser on `resumematch-ai.vercel.app` will reject or refuse to attach the cookie to subsequent requests. `SESSION_COOKIE_DOMAIN` must be omitted (`None`).
2. **SameSite Mismatch**: If the backend retains `SameSite=None` without TLS on forwarded hops, or if plain HTTP is used, modern browsers reject the cookie. Under a reverse-proxy, cookies must be configured as `SameSite=Lax`.
3. **Upstream TLS Scheme Awareness (`X-Forwarded-Proto`)**: When the edge proxy terminates SSL and forwards over HTTP, Flask must recognize `X-Forwarded-Proto: https` (via Werkzeug `ProxyFix`) to mark cookies `Secure`.
4. **Client-Side Env Variable Bypass**: If `VITE_API_BASE_URL` is configured with Render's URL in Vercel environment variables, the React SPA will bypass the rewrite entirely and issue direct cross-site requests, re-introducing the third-party cookie failure.

---

### 2.5 Document Parsing Limits & Archive Bomb Protection — VERIFIED
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

### 2.5 SQLite Concurrency, Transactions & Persistence — VERIFIED
- **Database Engine**:
  - SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL`), `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=30000`.
  - Connection isolation: thread-safe connection pooling per thread (`check_same_thread=False`).
- **Atomic Operations & Rollback**:
  - Session mutations (`create_session`, `submit_answer`, `next_question`, `complete_session`, `delete_session`) use context-managed database transactions.
  - If disk write fails, the database transaction rolls back, in-memory state is restored to its prior state (preventing split-brain divergence), and an observable `500 Internal Server Error` is returned with structured logging.

### 2.6 Information Leakage & Error Handling — VERIFIED
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
| **CSRF Protection** | **PASS** | Fail-closed token validation on all state-changing mutation endpoints |
| **CORS Policy** | **PASS** | Strict whitelist (`FRONTEND_ORIGINS`), credentials enabled, explicit methods (`GET`, `POST`, `PUT`, `DELETE`) |
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
