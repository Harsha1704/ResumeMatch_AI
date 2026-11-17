# ResumeMatch AI — Phase 5 & Phase 5.1 Implementation Report: Evidence-Grounded Interview Studio

**Date**: November 17, 2026  
**Repository**: `Harsha1704/ResumeMatch_AI`  
**Branch**: `fix/resumematch-final-repair`  
**Starting Commit Phase 5.1**: `4b5e0ef60ec49c9a81a7f4f1eb0bc4afa23e1056`  
**Implementation Phase**: Phase 5 & 5.1 — Interview Studio Reliability, Evidence Persistence & Hardening  

---

## 1. Executive Summary

Phase 5 & 5.1 deliver a production-quality, evidence-grounded **Interview Studio** fully integrated into ResumeMatch AI. The system provides candidates with a realistic, deterministic interview preparation environment that generates tailored questions based on their verified resume evidence and target job requirements, evaluates written answers against six transparent coaching criteria, guards against keyword stuffing and unevidenced claims, and maintains durable practice history and progress tracking with zero LLM hallucination.

Phase 5.1 specifically hardens the interview studio:
1. **Candidate Evidence Restoration Across Restarts**: Preserves `candidate_evidence` in SQLite via `candidate_evidence_json`, restores it upon session reload, maintains backward compatibility with older database schemas, and ensures reloaded sessions continue to enforce evidence grounding during answer evaluation.
2. **Honest Technical Accuracy Verification**: Differentiates genuinely verified technical claims from recognized keyword mentions and unverifiable domain terms using `_TECH_VALIDATION_RULES`. Simply mentioning Python, React, SQL, or Docker receives `recognized` status rather than claiming automated technical verification.
3. **Structured Achievement and Metric Grounding**: Analyzes answer assertions against candidate resume evidence, categorizing claims into:
   - `resume_supported_claims`: metrics and accomplishments substantiated by verified project descriptions.
   - `candidate_self_reported_claims`: qualitative assertions without resume-conflicting claims.
   - `unsupported_claims`: unestablished metrics or scale numbers triggering clear coaching warnings.
   - `general_technical_explanations`: theoretical or architectural explanations not claiming personal accomplishments.
   - `truthful_disclosures`: candid admissions of lacking production experience or metrics, praised in coaching feedback for transparency.
4. **Uniform Fail-Closed CSRF Enforcement**: Applies strict CSRF fail-closed validation across all state-changing endpoints (`POST /api/interview/evaluate`, `POST /api/interview/confirm-activity`, `POST /api/interview/reset`, `POST /api/interview-studio/generate`, `POST /api/interview/sessions`, `DELETE /api/interview/sessions/<session_id>`, `POST /api/interview-practice/submit`).
5. **Hardened API Input Validation**: Validates JSON types before calling string methods or processing values across `mode`, `difficulty`, `target_role`, `analysis_id`, `session_id`, `user_answer`, `question_index`, `max_questions`, `expected_key_points`, and `important_concepts`, returning controlled `400` responses without unhandled 500s or silent conversions to default values.
6. **Observable Persistence Failures**: Removes swallowed exceptions in session persistence, adds structured logging, and returns controlled `500` status with descriptive error messages when SQLite operations fail.

---

## 2. Architecture & Module Design

```
+---------------------------------------------------------------------------------------------------------+
|                                         ResumeMatch AI Backend                                          |
+---------------------------------------------------------------------------------------------------------+
|  REST API Routes (app.py)                                                                              |
|  - GET /api/interview-studio          : Candidate context, questions, topics, recent sessions           |
|  - POST /api/interview-studio/generate: Dynamic question filtering & practice session initiation       |
|  - POST /api/interview/sessions       : Explicit session creation with mode/difficulty/role            |
|  - GET /api/interview/sessions        : Practice session history listing                                |
|  - GET /api/interview/sessions/<id>   : Session detail retrieval with ownership check                  |
|  - DELETE /api/interview/sessions/<id>: Safe session deletion with CSRF protection                     |
|  - GET /api/interview/progress        : Aggregated practice progress metrics                           |
|  - GET /api/interview-practice        : Active practice question & progress                             |
|  - POST /api/interview-practice/submit: Answer submission, deterministic evaluation & navigation        |
|  - GET /api/interview-results         : Session completion results & per-question feedback review       |
|  - POST /api/interview/evaluate       : Instant heuristic feedback with fail-closed CSRF               |
+---------------------------------------------------------------------------------------------------------+
                                   |                                |
                                   v                                v
+---------------------------------------------------+  +--------------------------------------------------+
|      Question Generation Engine                   |  |          Heuristic Answer Evaluator              |
|      (src/interview/question_generator.py)        |  |          (src/interview/answer_evaluator.py)     |
|  - Role & difficulty filtering                    |  |  - 6 Criteria: Relevance, Tech Accuracy,        |
|  - Candidate resume grounding                     |  |    Concept Coverage, Structure, Specificity,     |
|  - Complete answers & structured criteria         |  |    Evidence Consistency                          |
|  - Pedagogical steps & follow-up Q&As             |  |  - Anti-keyword stuffing detection               |
|                                                   |  |  - Defined validation rules vs recognized terms  |
|                                                   |  |  - Grounded achievement & metric categorization  |
+---------------------------------------------------+  +--------------------------------------------------+
                                   |                                |
                                   +----------------+---------------+
                                                    v
+---------------------------------------------------------------------------------------------------------+
|      Persistent Session Storage (src/interview/session_store.py & interview_session.py)                 |
|  - SQLite (data/cache/interview_sessions.sqlite) in WAL mode                                            |
|  - Multi-user isolation by owner_id                                                                     |
|  - candidate_evidence_json preserved across restarts                                                    |
|  - Transactional consistency & observable write failure logging                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Evaluation Criteria & Grounding Methodology

### Deterministic 6-Criterion Scoring Framework

| Criterion | Weight | Evaluation Method & Safeguards |
| :--- | :--- | :--- |
| **Relevance** | 20% | Keyword overlap against prompt tokens; penalizes extreme repetition and keyword stuffing (>35% single-token frequency or <25% unique token ratio). |
| **Technical Accuracy** | 20% | Distinguishes `verified` (domain validation rule genuinely satisfied in context) from `recognized` (name-dropping without validated usage) and `unverifiable` (outside rule bank). |
| **Concept Coverage** | 20% | Evaluates coverage of `expected_key_points` (70% subweight) and `important_concepts` (30% subweight) using stemming and boundary-aware matching. |
| **Clarity & Structure** | 15% | Evaluates structural progression against the designated framework (STAR, PREP, CAR, PAR, SOAR, PEEL, WHAT-WHY-HOW); penalizes verbatim duplicate sentences. |
| **Specificity & Examples** | 15% | Rewards quantified results, latency/throughput metrics, named architectural tools, and project contexts. |
| **Evidence Consistency** | 10% | Validates claims against candidate's verified resume profile; flags unevidenced technologies and unsupported metrics with actionable warnings. |

### Technical Verification vs. Heuristic Recognition

```
[Answer Contains Technical Terms]
            |
            v
   Are terms in _TECH_VALIDATION_RULES?
            |
    +-------+-------+
    | Yes           | No
    v               v
Do terms satisfy contextual rules?    Status: UNVERIFIABLE
    |                                 Score: 65%
    +-------+-------+                 Note: Outside automated rule bank
    | Yes           | No
    v               v
Status: VERIFIED    Status: RECOGNIZED
Score: 85%          Score: 70%
Note: Contextually  Note: Keyword detected but
verified usage      usage not rule-validated
```

### Achievement & Metric Categorization

1. **Resume-Supported Claims**: First-person achievements whose quantified metrics or outcomes are directly traced to project descriptions or confirmed details in the candidate profile.
2. **Candidate Self-Reported Claims**: Qualitative first-person assertions that do not assert unevidenced numerical metrics.
3. **Claims Not Established by Evidence (Unsupported)**: First-person assertions of specific numerical metrics (e.g., "scaled to 500,000 users", "reduced latency by 85%") that are absent from submitted resume evidence. These generate explicit grounding warnings.
4. **General Technical Explanations**: Theoretical or domain explanations mentioning numbers or metrics (e.g., "PostgreSQL default timeout is 30 seconds") that describe system behavior without claiming personal accomplishment.
5. **Truthful Candidate Disclosures**: Honest acknowledgments of lack of production deployment or metrics (e.g., "this was an academic project so I did not measure latency"). Praised in coaching feedback for transparency.

---

## 4. Security & Isolation Controls

1. **Fail-Closed CSRF Enforcement**: All state-changing POST and DELETE endpoints enforce CSRF validation. In production mode (`app.config["TESTING"] = False`), missing or invalid tokens return `403 Forbidden`.
2. **Analysis ID Authorization**: Validates requested analysis IDs against the active session's authorized list (`allowed_analyses`), returning `403` for unauthorized IDs and `404` for missing cache entries.
3. **Cross-User Session Boundaries**: Each practice session is bound to an `owner_id`. Multi-user access tests verify that independent clients receive `403` when attempting to inspect, submit answers to, or delete another user's session.
4. **Observable Persistence Failures**: SQLite write errors are logged with stack traces and returned as `500 Internal Server Error` rather than claiming success.

---

## 5. Verification & Test Results

All verification suites completed cleanly:

| Suite / Check | Command | Result |
| :--- | :--- | :--- |
| **Dedicated Phase 5 & 5.1 Suite** | `py -3.14 -m pytest tests/test_phase5_interview_studio.py -v` | **28 passed** in 1.89s |
| **All Interview Studio Suites** | `py -3.14 -m pytest tests/test_phase5_interview_studio.py tests/test_interview_studio.py tests/test_phase2_1_interview_grounding.py tests/test_interview_educational_depth.py -v` | **76 passed** in 3.07s |
| **Cumulative Phase 1–5 Suites** | `py -3.14 -m pytest tests/test_phase*.py -q` | **413 passed** in 103.48s |
| **Full Backend Test Suite** | `py -3.14 -m pytest tests/ -q` | **686 passed**, 1 pre-existing warning in 126.20s |
| **Frontend Production Build** | `npm.cmd run build --prefix frontend` | **Success** (built in 855ms, 0 errors) |
| **Frontend Lint** | `npm.cmd run lint --prefix frontend` | **Clean** (0 errors, 33 pre-existing warnings) |

---

## 6. Summary of Hardened APIs

| Endpoint | Method | CSRF | Type Validation | Error Codes |
| :--- | :--- | :--- | :--- | :--- |
| `/api/interview-studio` | GET | Safe | Query args validated | 200, 403, 404 |
| `/api/interview-studio/generate` | POST | Required | `mode`, `difficulty`, `target_role`, `max_questions`, `action` | 200, 400, 403, 404, 500 |
| `/api/interview/sessions` | POST | Required | `mode`, `difficulty`, `target_role`, `max_questions`, `questions` | 201, 400, 403, 404, 500 |
| `/api/interview/sessions` | GET | Safe | Session owner filtered | 200 |
| `/api/interview/sessions/<id>` | GET | Safe | `session_id` string validated | 200, 400, 403, 404 |
| `/api/interview/sessions/<id>` | DELETE | Required | `session_id` string validated | 200, 400, 403, 404, 500 |
| `/api/interview/progress` | GET | Safe | Session owner filtered | 200 |
| `/api/interview-practice` | GET | Safe | `session_id` string validated | 200, 400, 403, 404 |
| `/api/interview-practice/submit` | POST | Required | `session_id`, `question_index`, `user_answer`, `direction` | 200, 400, 403, 404, 500 |
| `/api/interview-results` | GET | Safe | `session_id` string validated | 200, 400, 403, 404, 500 |
| `/api/interview/evaluate` | POST | Required | `user_answer`, `question_text`, `expected_key_points`, `important_concepts` | 200, 400, 403, 404 |
| `/api/interview/confirm-activity` | POST | Required | `activity_key` non-empty string | 200, 400, 403 |
| `/api/interview/reset` | POST | Required | CSRF validated | 200, 403, 500 |
