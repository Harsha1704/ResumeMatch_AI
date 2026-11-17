# ResumeMatch AI — Phase 5, 5.1 & 5.2 Changed Files Inventory

**Branch**: `fix/resumematch-final-repair`  
**Starting Commit Phase 5.2**: `ebcbf02590a3b2095afaca4e0e3ab3aad5134da1`  
**Phase**: Phase 5, 5.1 & 5.2 — Interview Studio Evaluation Scoring, Claim Verification & Persistence Reliability  
**Date**: November 17, 2026  

---

## 1. Backend Modules Created & Modified

| File | Status | Description |
| :--- | :--- | :--- |
| [`src/interview/session_store.py`](file:///d:/skillsync1/src/interview/session_store.py) | **Modified** | Persistent SQLite store with WAL mode; added `candidate_evidence_json` column and backward-compatible migration; added structured logging and re-raising of database errors so read/write outages are observable (no silent empty lists or zeroed progress). |
| [`src/interview/interview_session.py`](file:///d:/skillsync1/src/interview/interview_session.py) | **Modified** | Implemented rollback on failed persistence in `create_session`, `submit_answer`, `next_question`, `prev_question`, `jump_to`, and `complete_session`; evicted unpersisted sessions from `ACTIVE_SESSIONS` on creation error; removed swallowed exceptions in read operations. |
| [`src/interview/answer_evaluator.py`](file:///d:/skillsync1/src/interview/answer_evaluator.py) | **Modified** | Made technical validation sentence-scoped with negation and hypothetical handling; implemented multi-attribute metric-to-evidence matching considering value, unit, and metric category (`accuracy_quality`, `latency_speed`, etc.); denied specificity credit to unsupported metrics and added scoring deductions, ensuring fabricated metrics never improve overall scores over equivalent answers without them. |
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
| [`tests/test_phase5_interview_studio.py`](file:///d:/skillsync1/tests/test_phase5_interview_studio.py) | **Modified** | Expanded to 34 comprehensive tests covering evidence restoration across restarts, technical validation sentence scoping and negation/hypothetical handling, metric type/context matching (e.g. 94% Macro F1 != 94% latency reduction), fabricated metric score penalty verification, database read failure observability (distinct 404 vs 500), write failure rollback, cross-user reset/deletion rejection with 403, CSRF enforcement, and input type hardening. |
