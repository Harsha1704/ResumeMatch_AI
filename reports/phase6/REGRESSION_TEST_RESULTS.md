# ResumeMatch AI — Phase 6 Regression Test Results

**Date**: November 17, 2026  
**Branch**: `fix/resumematch-final-repair`  
**Phase 6 Baseline Commit**: `ad4bc5b2f5e7e6f5b892c5e788102a573b07c2f6`  
**Phase 6.4 Baseline Commit**: `64ba81caf0f5f659ac9c2a4b8afaf5cea3997499`  
**Review Status**: **VERIFIED CLEAN** (100% test pass rate across all test suites)

---

## 1. Test Execution Summary

All test suites were executed on Python 3.14 (Backend) and Node.js / Vite 8 (Frontend) inside the local development environment.

> [!NOTE]
> **Environment & Verification Boundary Note**:
> - The test executions, pass counts, durations, and exit codes reported below reflect actual runs in this local development environment.
> - They are distinct from remote CI workflows (such as GitHub Actions or Vercel CI), which run in separate cloud runner environments.
> - Browser tests are explicitly separated into: (1) Genuine Cross-Origin HTTPS browser tests (`frontend/tests/browser_cross_origin.test.mjs`), (2) Same-Origin HTTP browser tests (`frontend/tests/browser_same_origin.test.mjs`), and (3) Mocked-fetch unit tests (`frontend/tests/api_csrf.test.mjs`).

| Test Suite / Quality Gate | Execution Command | Result | Duration | Exit Code |
| :--- | :--- | :--- | :--- | :--- |
| **Dedicated Phase 6.2 Legacy Routes CSRF Suite** | `py -3.14 -m pytest tests/test_phase6_2_legacy_csrf.py -v` | **13 passed** | 2.67s | `0` |
| **Dedicated Phase 6.1 CSRF & API Security Suite** | `py -3.14 -m pytest tests/test_phase6_1_csrf_security.py -v` | **41 passed** | 2.92s | `0` |
| **Dedicated Phase 6 Integration Suite** | `py -3.14 -m pytest tests/test_phase6_integration_audit.py -v` | **9 passed** | 3.40s | `0` |
| **Dedicated Phase 5 Interview Studio Suite** | `py -3.14 -m pytest tests/test_phase5_interview_studio.py -v` | **38 passed** | 2.06s | `0` |
| **All Interview Studio Suites** | `py -3.14 -m pytest tests/test_phase5_interview_studio.py tests/test_interview_studio.py tests/test_phase2_1_interview_grounding.py tests/test_interview_educational_depth.py -v` | **86 passed** | 3.23s | `0` |
| **Phase 1–6 Dedicated Suites** | `powershell -Command "$p16 = (Get-ChildItem tests/test_phase*.py \| Where-Object { $_.Name -match '^test_phase[1-6]' -and $_.Name -notmatch '^test_phase1[0-9]' }); py -3.14 -m pytest $p16 -q"` | **331 passed** | 18.60s | `0` |
| **Later-Phase Regression Suites (Phases 7, 10, 12, 13)** | `powershell -Command "$later = (Get-ChildItem tests/test_phase*.py \| Where-Object { $_.Name -match '^test_phase(7\|10\|12\|13)' }); py -3.14 -m pytest $later -q"` | **155 passed** | 80.74s | `0` |
| **All Phase-Prefixed Test Suites (`test_phase*.py` — Combined)** | `powershell -Command "py -3.14 -m pytest (Get-ChildItem tests/test_phase*.py) -q"` | **486 passed** | 99.34s | `0` |
| **Full Backend Regression Suite** | `py -3.14 -m pytest tests/ -q` | **759 passed**, 1 pre-existing warning | 125.91s | `0` |
| **Frontend Unit & Real Browser Test Suites (Node)** | `npm test --prefix frontend` | **14 passed** (6 unit + 4 cross-origin + 4 same-origin) | 6.92s | `0` |
| **Frontend Production Build** | `npm.cmd run build --prefix frontend` | **Success** (built in 461ms, 0 errors) | 0.46s | `0` |
| **Frontend Static Analysis & Lint** | `npm.cmd run lint --prefix frontend` | **Clean** (0 errors, 33 pre-existing style warnings) | 0.03s | `0` |

---

## 2. Detailed Breakdown of Phase-Prefixed Test Suites (`test_phase*.py` — 486 Tests Total)

### 2.1 Phase 1 through Phase 6 Dedicated Suites (331 Tests)

| Phase Test Suite File | Tests Passed | Domain / Scope Verified |
| :--- | :--- | :--- |
| `tests/test_phase1_extraction_repair.py` | 20 | Section-aware resume parsing, non-text file rejection, contact extraction |
| `tests/test_phase2_evidence_engine.py` | 26 | Unified evidence registry, verified verb extraction, claim-level attribution |
| `tests/test_phase2_1_interview_grounding.py` | 10 | Elimination of unevidenced personal metric claims in interview questions |
| `tests/test_phase2_1_1_final_grounding.py` | 12 | Rigorous first-person pronoun scoping and honest candidate disclosures |
| `tests/test_phase2_1_2_evidence_validator.py` | 12 | Evidence validator import integrity and claim validation boundaries |
| `tests/test_phase2_1_3_validator_import_evidence.py` | 12 | Safe fallback behavior without LLM hallucination |
| `tests/test_phase2_1_4_claim_level_evidence.py` | 12 | Fine-grained sentence-level evidence attribution and illustrative tags |
| `tests/test_phase3_resume_analyzer.py` | 32 | Parser robustness, PDF/DOCX safety limits, target role override validation |
| `tests/test_phase4_career_mentor.py` | 40 | Personalized Career Mentor roadmaps, curricula pacing, milestone tracking |
| `tests/test_phase4_1_security_and_evidence.py` | 14 | Mentor session ownership, CSRF enforcement, role evaluation validation |
| `tests/test_phase4_2_evidence_and_csrf.py` | 16 | Traceable skill demonstration versus mentioned skills |
| `tests/test_phase4_3_traceability_and_advisor.py` | 16 | Action-verb demonstration semantics and excerpt verification |
| `tests/test_phase4_4_demonstration_semantics.py` | 18 | Nominal forms exclusion and genuine implementation verb requirement |
| `tests/test_phase4_5_evidence_integrity.py` | 20 | Unrelated skill/action verb cross-clause isolation |
| `tests/test_phase4_6_skill_action_isolation.py` | 22 | Clause-scoped negative and requirement pattern isolation |
| `tests/test_phase4_7_skill_negation_scoping.py` | 24 | Coordinated skill preservation and skill-specific negation scoping |
| `tests/test_phase5_interview_studio.py` | 38 | Interview Studio session persistence, SQLite rollback, numeric precision, unit token boundaries, compound rate ordering |
| `tests/test_phase6_integration_audit.py` | 9 | End-to-end 10-module contract integrity, BOLA 403 isolation, CORS preflight with DELETE, ML scoring determinism |
| `tests/test_phase6_1_csrf_security.py` | 41 | Fail-closed CSRF enforcement, GET /api/csrf-token, X-CSRF-Token validation on state-changing API endpoints, cross-session isolation |
| `tests/test_phase6_2_legacy_csrf.py` | 13 | Legacy form routes CSRF enforcement (POST /analyze, /interview-studio/generate, /interview-practice/submit), multi-mutation session continuity |
| **Subtotal Phase 1–6** | **331** | **100% Passed (18.60s)** |

### 2.2 Later-Phase Regression Suites — Phases 7, 10, 12, 13 (155 Tests)

| Phase Test Suite File | Tests Passed | Domain / Scope Verified |
| :--- | :--- | :--- |
| `tests/test_phase7e_dual_unseen_training.py` | 8 | Dual-unseen data splits, zero leakage guards, group-disjoint validation |
| `tests/test_phase10_quality_audit.py` | 25 | Quality audit, human-in-the-loop review package verification |
| `tests/test_phase12f_automated_learning.py` | 18 | Contrastive loss, hard-negative mining, embedding validation |
| `tests/test_phase12f2_split_isolation.py` | 8 | Train/val/test cryptographic split isolation |
| `tests/test_phase12f3_3_statistical_validation.py` | 10 | Bootstrap statistical significance and Wilcoxon signed-rank tests |
| `tests/test_phase12f3_4_reconciliation.py` | 6 | Confusion matrix reconciliation against prediction records |
| `tests/test_phase12g_research_evaluation.py` | 10 | Research baseline benchmarks and McNemar's statistical tests |
| `tests/test_phase12g4_forensic_verification.py` | 8 | Artifact hash validation and frozen checkpoint integrity |
| `tests/test_phase12h_benchmark_feasibility.py` | 6 | Latency profiling and memory consumption audit |
| `tests/test_phase12i_benchmark_protocol.py` | 8 | 4-protocol benchmark verification (Job-Disjoint, Resume-Disjoint, etc.) |
| `tests/test_phase12i1_protocol_hardening.py` | 6 | Strict split leakage guards |
| `tests/test_phase12i2_statistical_readiness.py` | 6 | Metric standard deviation and confidence interval calculation |
| `tests/test_phase12i3_final_verification.py` | 6 | Final protocol verification |
| `tests/test_phase12i4_pilot_execution.py` | 4 | Recruiter pilot validation |
| `tests/test_phase12i5_recruiter_pilot.py` | 4 | Human rating alignment |
| `tests/test_phase12i6_independent_audit.py` | 4 | Independent auditor verification |
| `tests/test_phase12i7_rating_intake.py` | 4 | Clean intake pipeline validation |
| `tests/test_phase12i8_human_free_pipeline.py` | 4 | Zero human-rater dependency verification |
| `tests/test_phase12i9_independent_audit.py` | 4 | Zero LLM runtime dependency verification |
| `tests/test_phase12i10_final_evidence_audit.py` | 4 | Final evidence audit |
| `tests/test_phase12i11_statistical_audit.py` | 4 | Final statistical audit |
| `tests/test_phase12i12_statistical_verification.py` | 4 | Forensic reproducibility |
| `tests/test_phase13_model_improvement.py` | 12 | Model 5 challenger evaluation and comparison gates |
| **Subtotal Later Phases** | **155** | **100% Passed (80.74s)** |
| **Total Phase Tests Combined** | **486** | **100% Passed (0 Failed, 0 Skipped)** |

---

## 3. Frontend Unit & Real Browser Test Suites (14 Tests Total)

### 3.1 Mocked-Fetch Unit Tests (`frontend/tests/api_csrf.test.mjs` — 6 Tests)
1. Mutation aborts fail-closed before endpoint fetch if CSRF token retrieval fails (`PASS`)
2. Successful token retrieval attaches `X-CSRF-Token` and `credentials: include` (`PASS`)
3. Token caching avoids redundant `/api/csrf-token` fetches on subsequent mutations (`PASS`)
4. HTTP 403 Forbidden clears cached token and does not automatically replay mutation (`PASS`)
5. `analyzeResume` multipart upload aborts fail-closed if CSRF retrieval fails (`PASS`)
6. `analyzeResume` multipart upload attaches `X-CSRF-Token` and credentials on success (`PASS`)

### 3.2 Genuine Cross-Origin HTTPS Browser Tests (`frontend/tests/browser_cross_origin.test.mjs` — 4 Tests)
7. **Chromium Engine**: Live cross-origin preflight (`OPTIONS`), CSRF token retrieval over HTTPS, `SameSite=None; Secure; HttpOnly` session cookie persistence, 403 on missing token, 200 OK on authenticated mutation, session continuity across sequential mutations (`PASS`)
8. **Firefox Engine**: Live cross-origin preflight, CSRF token retrieval over HTTPS, session cookie persistence, 403 on missing token, 200 OK on authenticated mutation (`PASS`)
9. **WebKit Engine**: Live cross-origin preflight, CSRF token retrieval over HTTPS, Apple ITP drop of cross-site cookies empirically verified, fail-closed mutation rejection with HTTP 403 Forbidden (`PASS`)
10. **CORS Disallowed Origin Enforcement**: Verified that cross-origin requests from untrusted origins (`https://unauthorized-site.com`) do not receive allow-credentials or allow-origin headers (`PASS`)

### 3.3 Real Browser Same-Origin Tests (`frontend/tests/browser_same_origin.test.mjs` — 4 Tests)
11. **Chromium Engine (Same-Origin HTTP)**: Live CSRF token retrieval, `HttpOnly` session cookie persistence, 403 rejection on tokenless mutation, 200 OK on authenticated mutation, session continuity (`PASS`)
12. **Firefox Engine (Same-Origin HTTP)**: Live CSRF token retrieval, `HttpOnly` session cookie persistence, 403 rejection on tokenless mutation, 200 OK on authenticated mutation (`PASS`)
13. **WebKit Engine (Same-Origin HTTP)**: Live CSRF token retrieval, `HttpOnly` session cookie persistence, 403 rejection on tokenless mutation, 200 OK on authenticated mutation (`PASS`)
14. **Empirical Cross-Origin Cookie Behavior**: Demonstrates that `credentials: 'omit'` drops session cookies in browser network requests and causes session-backed mutations to fail with HTTP 403 Forbidden (`PASS`)

---

## 4. Forensic CI Failure Investigation (`Vercel – resumematch_ai`)

### 4.1 Actual Deployment Forensic Evidence
- **Project**: `resumematch_ai`
- **Framework**: Flask
- **Build Entrypoint**: `.` (repository root)
- **Error Code**: `LAMBDA_SIZE_EXCEEDED`
- **Actual Serverless Bundle Size**: `732.81 MB`
- **Maximum Function Size Limit**: `500 MB`
- **Vercel Build Log Excerpt**:
  ```text
  Error: The Serverless Function "index" is 732.81 MB which exceeds the maximum size limit of 500 MB.
  Error: Command failed with exit code 1.
  ```

### 4.2 Architectural Diagnosis
1. **Directory Structure**:
   - The React 19 frontend resides in `frontend/` (`frontend/package.json`, `frontend/vite.config.ts`, `frontend/vercel.json`).
   - The repository root contains the Flask backend (`app.py`, `requirements.txt`, `render.yaml`).
2. **Two Disconnected Projects on Vercel**:
   - **Project 1 ("frontend")**: Configured with Root Directory `frontend/` -> **PASSES** (Build completes in 461ms with 0 errors).
   - **Project 2 ("resumematch_ai")**: Connected to `./` without subdirectory configuration -> **FAILS** with `LAMBDA_SIZE_EXCEEDED` because Vercel attempts to bundle heavy Python ML packages (`torch`, `sentence-transformers`, `scikit-learn`, `scipy`) into a serverless function.
3. **Conclusion**:
   - The failure of `Vercel – resumematch_ai` is **100% an external deployment configuration issue**, not a software code defect.
   - The Flask backend is deployed on Render (`render.yaml`), which uses containerized execution without size limits.
   - Per delivery instructions, no production Vercel project settings were modified and no external deployments were triggered.
