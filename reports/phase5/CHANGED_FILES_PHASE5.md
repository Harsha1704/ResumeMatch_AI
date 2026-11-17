# ResumeMatch AI — Phase 5 & 5.1 Changed Files Inventory

**Branch**: `fix/resumematch-final-repair`  
**Starting Commit Phase 5.1**: `4b5e0ef60ec49c9a81a7f4f1eb0bc4afa23e1056`  
**Phase**: Phase 5 & 5.1 — Interview Studio Reliability, Evidence Persistence & Hardening  
**Date**: November 17, 2026  

---

## 1. Backend Modules Created & Modified

| File | Status | Description |
| :--- | :--- | :--- |
| [`src/interview/session_store.py`](file:///d:/skillsync1/src/interview/session_store.py) | **Modified** | Persistent SQLite store with WAL mode; added `candidate_evidence_json` column and backward-compatible migration; added structured logging and re-raising of database errors so persistence failures are observable. |
| [`src/interview/interview_session.py`](file:///d:/skillsync1/src/interview/interview_session.py) | **Modified** | Persisted `candidate_evidence` in `to_dict()` and restored in `from_dict()`; removed swallowed exceptions in `_save_to_store()`, re-raising persistence errors with structured logging. |
| [`src/interview/answer_evaluator.py`](file:///d:/skillsync1/src/interview/answer_evaluator.py) | **Modified** | Added `_TECH_VALIDATION_RULES` to distinguish `verified` contextual usage from `recognized` name-dropping; added metric and achievement grounding distinguishing `resume_supported_claims`, `candidate_self_reported_claims`, `unsupported_claims`, `general_technical_explanations`, and `truthful_disclosures`; added decimal-safe sentence segmentation and `claims_analysis` output. |
| [`src/interview/question_generator.py`](file:///d:/skillsync1/src/interview/question_generator.py) | **Modified** | Guaranteed string type on `related_skill` across all question categories; adapted questions by mode and difficulty. |
| [`src/interview/evidence_mapper.py`](file:///d:/skillsync1/src/interview/evidence_mapper.py) | **Modified** | Extracted projects and internships from both top-level and `candidate_profile` dictionaries for complete evidence synthesis. |
| [`app.py`](file:///d:/skillsync1/app.py) | **Modified** | Hardened input validation across all routes returning controlled `400` responses; enforced fail-closed CSRF across `/api/interview/evaluate`, `/api/interview/confirm-activity`, `/api/interview/reset`, `/api/interview-studio/generate`, `/api/interview/sessions`, `DELETE /api/interview/sessions/<id>`, and `/api/interview-practice/submit`; added observable 500 error responses on SQLite persistence failures. |

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
| [`tests/test_phase5_interview_studio.py`](file:///d:/skillsync1/tests/test_phase5_interview_studio.py) | **Modified** | Expanded from 19 to 28 comprehensive tests covering candidate evidence restoration across restarts, cross-user isolation after restart, duplicate answer submissions, completed session behavior, technical accuracy distinction (`recognized` vs `verified`), unsupported achievement/metric grounding, CSRF enforcement across all state-changing endpoints in production mode, malformed JSON field types rejection, and observable SQLite write failure handling. |
