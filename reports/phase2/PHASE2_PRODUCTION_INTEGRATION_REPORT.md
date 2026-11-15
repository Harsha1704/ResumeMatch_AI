# ResumeMatch AI — Phase 2: Critical API Fixes & Production Integration Report

**Date:** November 15, 2026  
**Branch:** `feature/react-production-hardening`  
**Repository:** `https://github.com/Harsha1704/ResumeMatch_AI`  
**Status:** PASS (All 24 backend integration and persistence tests passing; React build clean)

---

## 1. Executive Summary

Phase 2 addressed critical backend API flaws, restored durable SQLite analysis persistence across memory cache evictions, enforced strict cross-session authorization, and solidified the React frontend integration.

Prior to Phase 2:
- Analysis results existed purely in an in-memory dictionary (`ANALYSIS_CACHE`), causing data loss whenever the memory cache evicted entries or worker processes restarted.
- When querying non-existent or invalid analysis IDs (`/api/analysis/<id>`, `/api/skill-gap?id=...`, etc.), the API silently fell back to returning sample candidate data (`sample-preview`) instead of an explicit `404 Not Found`.
- Cross-session authorization on companion endpoints was absent: any session could access another session's private candidate dossier without ownership checks.
- The React frontend `api.ts` was configured with `credentials: 'omit'`, preventing session cookies from transmitting cross-origin, which broke session continuity.
- In demo mode, the UI lacked clear distinction between authentic sample preview data and live analyzed candidate dossiers.

In Phase 2:
1. **Durable SQLite Persistence Restored:** Created `src/services/analysis_store.py` providing an ACID, thread-safe, WAL-enabled SQLite L2 store with strict JSON serialization (zero pickle). Integrated tiered caching (L1 in-memory + L2 SQLite) in `app.py`.
2. **Strict Authorization & Security Enforced:** Implemented `get_authorized_analysis()`. Requesting invalid IDs strictly returns `404 Not Found`. Cross-session queries return `403 Forbidden`.
3. **Explicit Demo Identification:** Explicit demo IDs (`demo`, `sample`, `sample-preview`, `demo-preview`) safely return the authentic demo candidate profile with `is_demo: True`.
4. **Session Continuity Established:** Active analysis ID is tracked in `session["active_analysis_id"]`. Requests omitting `?id=` seamlessly load the active dossier from the current session.
5. **Frontend Credentials & UX Hardened:** Changed `credentials` to `'include'` in `frontend/src/services/api.ts`. Added `isDemo` context state, clear `DEMO PREVIEW` vs `ACTIVE DOSSIER` badges in the Header and Sidebar, and automatic recovery if a stored local ID expires.

---

## 2. Root Cause Analysis & Technical Resolutions

| Issue ID | Component | Defect Description | Root Cause | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `app.py` / Cache | Analysis data loss on cache eviction or restart | Only stored in transient `ANALYSIS_CACHE: Dict[str, Dict]` | Integrated `AnalysisStore` (SQLite WAL mode). Tier 1 memory cache falls back to Tier 2 durable store. |
| **BUG-02** | `app.py` / API | Silent sample fallback for non-existent IDs | `_get_active_analysis(None)` returned when `analysis_id not in ANALYSIS_CACHE` | Refactored route handlers to query `get_authorized_analysis()`; non-existent IDs return `404 Not Found`. |
| **BUG-03** | `app.py` / Security | Cross-session data exposure | `api_get_analysis`, `api_skill_gap`, `api_career_mentor`, `api_interview_studio` did not check `session["allowed_analyses"]` | Cross-session access attempts return `403 Forbidden` (`Access unauthorized: this analysis dossier belongs to another session.`). |
| **BUG-04** | `frontend/api.ts` | Session cookies not sent | `credentials: 'omit'` in `fetchJson` | Updated `credentials: 'include'` for both JSON and multipart form requests. |
| **BUG-05** | Frontend Context | Stale or unauthorized localStorage ID causes lockup | No invalid ID error handling in `AnalysisContext.tsx` | Catches 404/403, purges stale `rm_active_analysis_id`, and safely falls back to demo mode. |
| **BUG-06** | Frontend UI | Ambiguity between Demo and Real Candidate | No visual badge in Header or Sidebar | Added amber `DEMO PREVIEW` badge in Header and Sidebar drawer; displays emerald `ACTIVE DOSSIER` with filename on real upload. |

---

## 3. Storage Architecture (`AnalysisStore`)

- **File Path:** `src/services/analysis_store.py`
- **Database Engine:** SQLite 3 in WAL (Write-Ahead Logging) mode, `synchronous = NORMAL`, `busy_timeout = 30000ms`, thread-safe (`check_same_thread=False`).
- **Database Location:** Configurable via `RESUMEMATCH_ANALYSIS_DB` or `ANALYSIS_DB_PATH`, defaulting to `data/cache/analysis_store.sqlite`.
- **Serialization:** Strict `json.dumps` and `json.loads` (zero `pickle` to prevent arbitrary code execution vulnerabilities).
- **Retention Management:** Automated LRU/FIFO capacity pruning. Configurable via `ANALYSIS_MAX_RECORDS` (default: 200). Prunes oldest entries when threshold is reached.
- **Tiered Cache Flow:**
  ```mermaid
  flowchart TD
      A[API Request for Analysis ID] --> B{In L1 ANALYSIS_CACHE?}
      B -->|Yes| C[Return Cached Dossier]
      B -->|No| D{In L2 SQLite Store?}
      D -->|Yes| E[Populate L1 Cache] --> F{Authorized in Session?}
      D -->|No| G[Return 404 Not Found]
      F -->|Yes| H[Return 200 Dossier]
      F -->|No| I[Return 403 Forbidden]
  ```

---

## 4. Endpoint Verification Matrix

| Endpoint | Method | Parameter Scenario | Expected Status | Response Behavior | Verified |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/analyze` | `POST` | Valid resume (text/file) + JD | `200 OK` | Generates analysis, persists to SQLite, sets session active ID | PASS |
| `/api/analysis/<id>` | `GET` | Valid ID owned by session | `200 OK` | Returns full candidate analysis dossier | PASS |
| `/api/analysis/<id>` | `GET` | Valid ID owned by another session | `403 Forbidden` | Rejects with `"Access unauthorized"` | PASS |
| `/api/analysis/<id>` | `GET` | Non-existent or invalid ID | `404 Not Found` | Returns `"Analysis dossier not found or has expired."` | PASS |
| `/api/analysis/<id>` | `GET` | `sample` / `demo` / `sample-preview` | `200 OK` | Returns authentic demo candidate with `is_demo: True` | PASS |
| `/api/skill-gap` | `GET` | No ID provided (active session) | `200 OK` | Returns active candidate skill gap analysis | PASS |
| `/api/skill-gap` | `GET` | No ID provided (no active session) | `200 OK` | Returns demo candidate skill gap analysis (`is_demo: True`) | PASS |
| `/api/skill-gap` | `GET` | `?id=nonexistent` | `404 Not Found` | Rejects with 404 error message | PASS |
| `/api/skill-gap` | `GET` | `?id=unauthorized_id` | `403 Forbidden` | Rejects with 403 error message | PASS |
| `/api/career-mentor` | `GET` | `?id=sample` | `200 OK` | Returns personalized roadmaps for demo candidate | PASS |
| `/api/interview-studio`| `GET` | `?id=sample` | `200 OK` | Returns balanced question portfolio for demo candidate | PASS |

---

## 5. Test Suite Execution Results

All test suites were executed using `pytest` on Python 3.14:

```powershell
python -m pytest tests/test_analysis_persistence_and_auth.py tests/test_react_companion_api.py tests/test_analysis_integration.py -v
```

### Output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0
plugins: anyio-4.16.0, cov-7.1.0, flask-1.3.0, mock-3.17.0
collected 24 items

tests/test_analysis_persistence_and_auth.py::test_sqlite_store_crud_and_serialization PASSED [  4%]
tests/test_analysis_persistence_and_auth.py::test_analysis_persistence_across_cache_clear PASSED [  8%]
tests/test_analysis_persistence_and_auth.py::test_unauthorized_cross_session_access_blocked PASSED [ 12%]
tests/test_analysis_persistence_and_auth.py::test_nonexistent_analysis_id_returns_404 PASSED [ 16%]
tests/test_analysis_persistence_and_auth.py::test_explicit_demo_sample_identifier PASSED [ 20%]
tests/test_analysis_persistence_and_auth.py::test_session_continuity_without_id PASSED [ 25%]
tests/test_react_companion_api.py::test_api_dashboard PASSED             [ 29%]
tests/test_react_companion_api.py::test_api_sample_jobs PASSED           [ 33%]
tests/test_react_companion_api.py::test_api_analysis_sample PASSED       [ 37%]
tests/test_react_companion_api.py::test_api_skill_gap PASSED             [ 41%]
tests/test_react_companion_api.py::test_api_model_performance PASSED     [ 45%]
tests/test_react_companion_api.py::test_api_datasets PASSED              [ 50%]
tests/test_react_companion_api.py::test_api_career_mentor PASSED         [ 54%]
tests/test_react_companion_api.py::test_api_interview_studio PASSED      [ 58%]
tests/test_react_companion_api.py::test_api_analyze_json_flow PASSED     [ 62%]
tests/test_analysis_integration.py::test_analyze_page_get PASSED         [ 66%]
tests/test_analysis_integration.py::test_analyze_flow_with_pasted_text PASSED [ 70%]
tests/test_analysis_integration.py::test_analyze_flow_with_uploaded_file PASSED [ 75%]
tests/test_analysis_integration.py::test_empty_submission_validation PASSED [ 79%]
tests/test_analysis_integration.py::test_results_expired_or_invalid_id PASSED [ 83%]
tests/test_analysis_integration.py::test_unauthorized_session_access_protection PASSED [ 87%]
tests/test_analysis_integration.py::test_target_role_length_validation PASSED [ 91%]
tests/test_analysis_integration.py::test_api_rejects_non_string_target_role PASSED [ 95%]
tests/test_analysis_integration.py::test_api_rejects_overlong_target_role PASSED [100%]

============================= 24 passed in 4.37s ==============================
```

Frontend compilation check:
```powershell
cmd.exe /c "npm --prefix frontend run build"
✓ 2485 modules transformed.
✓ built in 477ms (0 errors)
```

---

## 6. Deployment Readiness Assessment

1. **Branch Isolation:** All changes are committed exclusively to `feature/react-production-hardening`. `main` and `deploy/vercel-render-free` remain protected.
2. **Model Safety:** Checksum integrity for `models/best_model.joblib` and `models/feature_pipeline.joblib` is unchanged. No ML weights, hyperparameters, TF-IDF vocabularies, or decision thresholds were touched.
3. **Zero Human Dependency:** Zero human raters or synthetic labels required.
4. **Zero LLM Runtime Dependency:** 100% deterministic Scikit-Learn ML and rule-based NLP.
5. **Session & Persistence Security:** Strict authorization prevents information leakage across concurrent candidate sessions.
