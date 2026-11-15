# ResumeMatch AI — Phase 2.1: Security Hardening & Production Persistence Report

**Date:** November 15, 2026  
**Branch:** `feature/phase2-1-security-hardening`  
**Repository:** `https://github.com/Harsha1704/ResumeMatch_AI`  
**Status:** PASS (All security hardening tests, regression tests, and production build passing)

---

## 1. Executive Summary

Phase 2.1 focused on hardening the application's runtime security, strictly isolating interview sessions, implementing end-to-end CSRF defense across browser API endpoints, fixing error-handling in the React frontend to prevent silent data degradation, and establishing an honest production persistence blueprint.

All modifications strictly adhere to non-negotiable project constraints:
- Zero modifications to ML model weights, Logistic Regression, TF-IDF dimensions, feature engineering pipelines, or prediction probabilities.
- Zero runtime LLM dependencies or synthetic predictions.
- All ten React application pages and legacy Jinja routes remain fully operational.
- All code changes are completely isolated to `feature/phase2-1-security-hardening`.

---

## 2. Security Vulnerabilities Addressed & Implementations

### A. Interview Session Ownership & Cross-Session Isolation (Task 1)
- **Defect:** Prior to Phase 2.1, interview practice sessions in `InterviewSessionManager` were indexed globally by `session_id` without ownership tracking. A user could read another candidate's active questions, submit answers into another candidate's session, or view another candidate's interview results by simply passing their `session_id`.
- **Implementation:**
  - In `src/interview/interview_session.py`, added `owner_session_id` to `InterviewSession` and `InterviewSessionManager.create_session`.
  - Added `InterviewSessionManager.validate_ownership(session_id, owner_id)` ensuring strict ownership verification.
  - In `app.py`, created `_get_browser_session_uid()` to establish a cryptographically stable session UID (`session["_session_uid"] = str(uuid.uuid4())`).
  - Implemented `get_authorized_interview_session(session_id, auto_create_if_missing)`.
  - Every read and write (`/api/interview-practice`, `/api/interview-practice/submit`, `/api/interview-results`, `/api/interview/reset`) verifies that the requested `session_id` belongs to the requesting browser session.
  - **Security Outcome:** Cross-session access returns **HTTP 403 Forbidden**. Non-existent or expired sessions return **HTTP 404 Not Found**.

### B. Constant-Time CSRF Protection (Task 2)
- **Defect:** While HTML form POST endpoints had CSRF validation in Phase 2, JSON and multipart browser API endpoints lacked CSRF validation, leaving them open to cross-origin request forgery.
- **Implementation:**
  - Added `GET /api/csrf-token` to issue or retrieve the active session's CSRF token.
  - In `src/security/csrf.py`, implemented `get_submitted_csrf_token()` to extract tokens from `X-CSRF-Token` or `X-CSRFToken` request headers, multipart form data, or JSON payloads.
  - Implemented `validate_request_csrf()` with constant-time token comparison (`secrets.compare_digest`) to prevent timing side-channel attacks.
  - In `app.py`, implemented `@require_browser_csrf` decorator and applied it to all state-changing endpoints:
    - `POST /api/analyze`
    - `POST /api/interview-studio/generate`
    - `POST /api/interview-practice/submit`
    - `POST /api/interview/reset`
    - `POST /api/interview/evaluate`
    - `POST /api/interview/confirm-activity`
    - `POST /api/candidate/update-role`
    - `POST /api/candidate/confirm-education`
    - `POST /api/mentor/update-name`
    - `POST /api/mentor/progress`
    - `POST /api/mentor/reset-progress`
  - In `frontend/src/services/api.ts`, implemented `fetchCsrfToken()` with in-memory caching. Both `fetchJson` and `analyzeResume` automatically attach the `X-CSRF-Token` header on state-changing requests (`POST`, `PUT`, `DELETE`, `PATCH`).
  - Explicit Headless Exemption: `/api/match` is explicitly documented as a programmatic, stateless developer integration endpoint (exempt from browser CSRF tokens), protected by IP sliding-window rate limiting (`api_rate_limiter`) and strict payload validation.

### C. Robust React Error Handling (Task 3)
- **Defect:** `AnalysisContext.tsx` previously caught any error during analysis retrieval (including network failures and HTTP 500 server errors) and purged `localStorage`, immediately falling back to `sample-preview` demo data.
- **Implementation:**
  - Exported custom `ApiError` class in `api.ts` with `status: number`, `message: string`, and `data?: any`.
  - In `AnalysisContext.tsx`, error handling now strictly checks:
    ```typescript
    const isAuthOrNotFound = status === 404 || status === 403;
    ```
    - **404 / 403 (Expired or Unauthorized):** Clears `rm_active_analysis_id` and sets an actionable error message.
    - **500 / Network Drop / Outage:** Does **NOT** clear `rm_active_analysis_id` and does **NOT** switch the user to demo data. Retains the current analysis context safely and exposes `retryLoad()` and `error`.
  - In `Header.tsx`, rendered a transient error indicator with explicit **"Retry"** and **"Demo"** controls so users have full visibility and control over their state.

### D. Production Persistence Architecture (Task 4)
- **Implementation:**
  - Updated `src/services/analysis_store.py` to support `PERSISTENT_STORAGE_DIR` (e.g. `/var/data` on mounted disks) as well as `RESUMEMATCH_ANALYSIS_DB` and `ANALYSIS_DB_PATH`.
  - Added comprehensive production documentation in `src/services/analysis_store.py` and `RENDER_BACKEND_SETUP.md`:
    - **Render Free Ephemeral Warning:** SQLite storage on standard Render Free web services will not survive redeploys or instance sleep restarts.
    - **Mounted Volume Configuration:** For single-instance persistence on Render, attach a Persistent Disk and configure `PERSISTENT_STORAGE_DIR=/var/data`.
    - **PostgreSQL Multi-Instance Migration Blueprint:** Documented schema and transition path for horizontally-scaled multi-worker deployments where SQLite file-locking is inappropriate.
    - **Data Privacy Assurance:** Resumes and candidate dossiers are never stored in public static directories.

---

## 3. Test Verification Matrix

### Targeted Security Hardening Suite (`tests/test_phase2_1_security_hardening.py`)
| Test Case | Description | Expected Status | Result |
| :--- | :--- | :--- | :--- |
| `test_interview_session_cross_session_protection` | Cross-session access to practice question | 403 Forbidden | **PASS** |
| `test_interview_answer_cross_session_protection` | Submitting answers to another user's session | 403 Forbidden | **PASS** |
| `test_interview_results_cross_session_protection` | Accessing another candidate's results | 403 Forbidden | **PASS** |
| `test_interview_nonexistent_session_returns_404` | Querying unknown/expired session ID | 404 Not Found | **PASS** |
| `test_csrf_token_endpoint` | `GET /api/csrf-token` issuance | 200 OK (64 hex chars) | **PASS** |
| `test_csrf_missing_token_rejected_on_browser_api` | Missing CSRF token on state-changing API | 403 Forbidden | **PASS** |
| `test_csrf_invalid_token_rejected_on_browser_api` | Forged CSRF token on state-changing API | 403 Forbidden | **PASS** |
| `test_csrf_valid_token_accepted_on_browser_api` | Valid CSRF token on state-changing API | 200 OK | **PASS** |
| `test_headless_api_match_exemption` | Programmatic `/api/match` endpoint | 200 OK (Exempt) | **PASS** |
| `test_persistent_storage_dir_configuration` | `PERSISTENT_STORAGE_DIR` path resolution | Store created in mount | **PASS** |

### Frontend Build & Typecheck
- Command: `cmd.exe /c "npm --prefix frontend run build"`
- Output: `✓ 2485 modules transformed. built in 464ms (0 errors)`
- Lint: `cmd.exe /c "npm --prefix frontend run lint"`
- Output: `Found 56 warnings and 0 errors.`

### Full Pytest Suite (`tests/`)
- Command: `python -m pytest tests/ -q`
- Output: `444 passed, 1 warning in 96.82s (100% PASS)`
- Regression & Companion Suite:
  - `tests/test_phase2_1_security_hardening.py`: 10/10 passed
  - `tests/test_analysis_persistence_and_auth.py`: 6/6 passed
  - `tests/test_react_companion_api.py`: 9/9 passed
  - `tests/test_flask_routes.py`: 2/2 passed
  - `tests/test_analysis_integration.py`: 9/9 passed
  - `tests/test_interview_studio.py`: 32/32 passed

---

## 4. Conclusion & Production Readiness
The application is fully hardened against cross-session tampering, CSRF exploits, state loss on network blips, and ephemeral data loss. All ML pipelines, checkpoints, and evaluations remain untouched and deterministic. Ready for deployment.
