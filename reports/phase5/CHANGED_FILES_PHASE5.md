# ResumeMatch AI — Phase 5, 5.1, 5.2, 5.3, 5.4, 5.5 & 5.6 Changed Files Inventory

**Branch**: `fix/resumematch-final-repair`  
**Starting Commit Phase 5.6**: `3a7add7052396ac0e85b08d862b4b12714473bf0`  
**Phase**: Phase 5, 5.1, 5.2, 5.3, 5.4, 5.5 & 5.6 — Compound Rate Unit Parsing & Semantic Distinction  
**Date**: November 17, 2026  

---

## 1. Backend Modules Created & Modified

| File | Status | Description |
| :--- | :--- | :--- |
| [`src/interview/session_store.py`](file:///d:/skillsync1/src/interview/session_store.py) | **Modified** | Persistent SQLite store with WAL mode; added `candidate_evidence_json` column and backward-compatible migration; added structured logging and re-raising of database errors so read/write outages are observable (no silent empty lists or zeroed progress). |
| [`src/interview/interview_session.py`](file:///d:/skillsync1/src/interview/interview_session.py) | **Modified** | Implemented rollback on failed persistence in `create_session`, `submit_answer`, `next_question`, `prev_question`, `jump_to`, and `complete_session`; evicted unpersisted sessions from `ACTIVE_SESSIONS` on creation error; removed swallowed exceptions in read operations. |
| [`src/interview/answer_evaluator.py`](file:///d:/skillsync1/src/interview/answer_evaluator.py) | **Modified** | Reordered `_UNIT_PATTERN` so compound rate units (`requests/sec`, `queries/sec`, `queries/s`, `req/s`, `rps`, `qps`) evaluate before shorter prefix alternatives (`requests`, `request`, `queries`, `query`), preventing rate metrics from being misparsed as counts; preserved strict token boundary lookaheads `(?![a-zA-Z0-9])` rejecting substring matches (`94students`, `94msomething`, `94requestsExtra`); enforced semantic distinction between rates (`req/s`) and counts (`requests`) ensuring rate claims cannot match count evidence and vice versa; added `NUMERIC_NORMALIZATION_POLICY = "strict_precision"`; implemented `_normalize_numeric_string()` to safely normalize comma grouping (`1,000` == `1000`) while preserving precision; updated `_verify_metric_claim()` to fail closed when resume units are missing or ambiguous. |
| [`src/interview/question_generator.py`](file:///d:/skillsync1/src/interview/question_generator.py) | **Modified** | Guaranteed string type on `related_skill` across all question categories; adapted questions by mode and difficulty. |
| [`src/interview/evidence_mapper.py`](file:///d:/skillsync1/src/interview/evidence_mapper.py) | **Modified** | Extracted projects and internships from both top-level and `candidate_profile` dictionaries for complete evidence synthesis. |
| [`app.py`](file:///d:/skillsync1/app.py) | **Modified** | Enforced ownership verification in `POST /api/interview/reset`, rejecting cross-user resets with 403; wrapped all database read operations to distinguish observable 500 errors from genuine 404s; enforced fail-closed CSRF across all state-changing interview endpoints. |

---

## 2. Frontend Components & Services Modified

| File | Status | Description |
| :--- | :--- | :--- |
| [`frontend/src/services/api.ts`](file:///d:/skillsync1/frontend/src/services/api.ts) | **Modified** | Added `getCsrfToken()` helper automatically attaching `X-CSRF-Token` headers from cookie/meta to outgoing mutation requests; added optional `csrf_token` parameters. |
| [`frontend/src/pages/InterviewPracticePage.tsx`](file:///d:/skillsync1/frontend/src/pages/InterviewPracticePage.tsx) | **Modified** | Rendered honest status badges for criterion scores (`verified`, `recognized`, `unverifiable`, `warning`); updated live evaluation displays. |
| [`frontend/src/pages/InterviewResultsPage.tsx`](file:///d:/skillsync1/frontend/src/pages/InterviewResultsPage.tsx) | **Modified** | Added criterion status badges (`verified`, `recognized`, `warning`) to per-question review cards. |
| [`frontend/src/pages/InterviewStudioPage.tsx`](file:///d:/skillsync1/frontend/src/pages/InterviewStudioPage.tsx) | **Modified** | Added mode selection, difficulty controls, practice history tab with resume/delete, and question metadata preview. |
| [`frontend/src/types/index.ts`](file:///d:/skillsync1/frontend/src/types/index.ts) | **Modified** | Updated type definitions for `CriterionScore`, `HeuristicEvaluation`, `InterviewSessionItem`, and `InterviewProgressSummary`. |

---

## 3. Test Suites Created & Executed

| File | Status | Description |
| :--- | :--- | :--- |
| [`tests/test_phase5_interview_studio.py`](file:///d:/skillsync1/tests/test_phase5_interview_studio.py) | **Modified** | Expanded to 38 comprehensive tests covering compound rate unit ordering and rate-vs-count semantic distinction, evidence restoration across restarts, technical validation sentence scoping and negation/hypothetical handling, decimal-safe exact numeric matching, safe comma grouping normalization, fail-closed unit checking, complete unit token boundary validation (rejecting `94students`, `94msomething`, `94requestsExtra`), elimination of unverified self-reported metric bonuses, database read failure observability (distinct 404 vs 500), write failure rollback, cross-user reset/deletion rejection with 403, CSRF enforcement, and input type hardening. |
