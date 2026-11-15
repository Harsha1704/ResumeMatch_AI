# Phase 2.1 — Changed Files Inventory

**Branch:** `feature/phase2-1-security-hardening`  
**Date:** November 15, 2026

---

## 1. Added Files

1. `tests/test_phase2_1_security_hardening.py`
   - **Purpose:** Comprehensive security validation covering interview session ownership (read/submit/results cross-session isolation returning 403, 404 for nonexistent sessions), CSRF token issuance (`GET /api/csrf-token`), CSRF enforcement on state-changing browser APIs (rejecting missing/invalid tokens with 403), valid token constant-time acceptance, headless `/api/match` exemption, and `PERSISTENT_STORAGE_DIR` configuration.
2. `tests/conftest.py`
   - **Purpose:** Autouse test fixture ensuring standard Flask testing mode (`TESTING=True`) across pytest sessions.
3. `reports/phase2-1/PHASE2_1_SECURITY_HARDENING_REPORT.md`
   - **Purpose:** Full technical verification and security audit report.
4. `reports/phase2-1/CHANGED_FILES.md`
   - **Purpose:** Inventory of all added and modified files in Phase 2.1.

---

## 2. Modified Files

1. `src/interview/interview_session.py`
   - Added `owner_session_id: Optional[str] = None` to `InterviewSession` and `InterviewSessionManager.create_session`.
   - Added `InterviewSessionManager.validate_ownership(session_id, owner_id)` to ensure practice sessions cannot be read or manipulated across browser sessions.
2. `src/security/csrf.py`
   - Implemented `get_submitted_csrf_token()` extracting tokens from `X-CSRF-Token` / `X-CSRFToken` request headers, form data, or JSON payloads.
   - Implemented `validate_request_csrf()` performing constant-time verification (`secrets.compare_digest`).
3. `app.py`
   - Added `_get_browser_session_uid()` providing a persistent browser session UID.
   - Implemented `get_authorized_interview_session(session_id, auto_create_if_missing)` to validate interview session ownership on reads, submits, and results queries (returning 403 for unauthorized access and 404 for unknown IDs).
   - Added `require_browser_csrf` decorator enforcing CSRF on state-changing browser endpoints.
   - Added `GET /api/csrf-token` endpoint for client-side CSRF token retrieval.
   - Protected all state-changing endpoints: `/api/analyze`, `/api/interview-studio/generate`, `/api/interview-practice/submit`, `/api/interview/reset`, `/api/interview/evaluate`, `/api/interview/confirm-activity`, `/api/candidate/update-role`, `/api/candidate/confirm-education`, `/api/mentor/update-name`, `/api/mentor/progress`, and `/api/mentor/reset-progress`.
   - Updated `allow_headers` in CORS to include `X-CSRF-Token` and `X-CSRFToken`.
4. `frontend/src/services/api.ts`
   - Created `ApiError` class storing HTTP status code, message, and error payload.
   - Implemented `fetchCsrfToken()` with in-memory caching.
   - Configured `fetchJson` and `analyzeResume` to automatically fetch and attach `X-CSRF-Token` header on all state-changing requests (`POST`, `PUT`, `DELETE`, `PATCH`).
5. `frontend/src/context/AnalysisContext.tsx`
   - Refactored error handling: treats only HTTP 404 and 403 as expired/unauthorized IDs (clearing localStorage only in those cases).
   - On network errors, timeouts, or HTTP 500 internal server errors, preserves active ID in localStorage and does NOT switch user to demo data.
   - Exposes `error`, `retryLoad()`, and `loadDemoPreview()` to components.
6. `frontend/src/components/layout/Header.tsx`
   - Added transient error badge with "Retry" and "Demo" controls to allow user-driven recovery without silent state degradation.
7. `src/services/analysis_store.py`
   - Added support for `PERSISTENT_STORAGE_DIR` (e.g. `/var/data` for mounted persistent disks on Render/Cloud).
   - Added architecture documentation on Ephemeral Filesystems, Render Persistent Disks, and multi-instance PostgreSQL migration blueprints.
8. `RENDER_BACKEND_SETUP.md`
   - Documented `PERSISTENT_STORAGE_DIR` and `ANALYSIS_DB_PATH` configuration.
   - Documented ephemeral filesystem warnings on Render free tier and external PostgreSQL migration path.
10. `src/interview/answer_evaluator.py`
    - Restored stem cleaning (`_clean_stem`) for key point coverage matching so plural/singular differences (e.g. project/projects) match correctly without compromising semantic precision.
