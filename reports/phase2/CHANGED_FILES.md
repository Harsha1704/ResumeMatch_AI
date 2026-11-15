# Phase 2 — Changed Files Inventory

**Branch:** `feature/react-production-hardening`  
**Date:** November 15, 2026

---

## 1. Added Files

1. `src/services/analysis_store.py`
   - **Purpose:** Thread-safe, WAL-enabled durable SQLite persistence engine for candidate analysis records.
   - **Features:** Strict JSON serialization (`json.dumps`/`json.loads`), LRU/FIFO capacity pruning based on `ANALYSIS_MAX_RECORDS`, WAL journal mode, 30s busy timeout, non-blocking single/multi-thread connections.
2. `tests/test_analysis_persistence_and_auth.py`
   - **Purpose:** Comprehensive test suite for SQLite persistence recovery across cache clearing, cross-session 403 authorization protection, non-existent ID 404 rejection, explicit demo/sample routing, and session continuity.
3. `reports/phase2/PHASE2_PRODUCTION_INTEGRATION_REPORT.md`
   - **Purpose:** Full technical verification and release readiness audit report.
4. `reports/phase2/CHANGED_FILES.md`
   - **Purpose:** Inventory of all added and modified files in Phase 2.

---

## 2. Modified Files

1. `app.py`
   - Integrated `AnalysisStore` via `get_analysis_store()`.
   - Created `_persist_analysis(analysis_id, data, session_id)` and `_retrieve_analysis(analysis_id)` for tiered L1 memory + L2 SQLite caching.
   - Implemented `get_authorized_analysis(analysis_id, allow_demo_default)` helper to enforce strict cross-session isolation and return 404 for invalid IDs.
   - Updated `POST /analyze` and `POST /api/analyze` to persist analyses to SQLite and record `session["active_analysis_id"]`.
   - Updated `GET /results`, `GET /skill-gap`, `GET /api/analysis/<id>`, `GET /api/skill-gap`, `GET /api/career-mentor`, `GET /api/interview-studio`, and `POST /api/interview-studio/generate` to verify session ownership and query SQLite L2 cache if L1 evicted.
   - Added `is_demo: True` to demo sample candidate in `_get_active_analysis()`.
2. `frontend/src/services/api.ts`
   - Configured `credentials: 'include'` in `fetchJson` and `analyzeResume` to ensure Flask session cookies are transmitted on all API requests.
3. `frontend/src/types/index.ts`
   - Added optional `is_demo?: boolean;` field to `AnalysisResult` interface.
4. `frontend/src/context/AnalysisContext.tsx`
   - Added `isDemo: boolean` to `AnalysisContextType` and exported context value.
   - Added automatic error recovery: when a stored analysis ID fails with 404/403, clears `rm_active_analysis_id` and cleanly falls back to demo mode without breaking UI state.
5. `frontend/src/components/layout/Header.tsx`
   - Added dossier status badge: amber `DEMO PREVIEW` when in demo mode, emerald `Active Candidate: <filename>` when an analyzed resume is loaded.
6. `frontend/src/components/layout/Sidebar.tsx`
   - Added dynamic `DEMO PREVIEW` vs `ACTIVE DOSSIER` badge in the candidate drawer footer.
7. `frontend/src/pages/DatasetExplorerPage.tsx`
   - Cleaned up unused imports and added loading spinner state while dataset summary is fetching.
