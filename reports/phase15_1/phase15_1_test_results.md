# Phase 15.1: Deployment Hardening Test Results

**Date:** 2026-11-15  
**Test Suite:** `experiments/phase15_1/tests/test_deployment_hardening.py`  
**Execution Environment:** Windows Server / Windows 11, Python 3.14.8, Pytest 9.1.1  
**Total Tests:** 10  
**Passed:** 10 (100%)  
**Failed:** 0  
**Execution Time:** 17.85 seconds  

---

## 1. Executive Summary

Phase 15.1 hardens the ResumeMatch AI Flask application and decouples web serving from transformer execution. The test suite thoroughly validates process isolation, memory safety, persistent asynchronous job queue semantics, failure recovery, security validation, and explicit fallback telemetry.

All 10 test cases in `test_deployment_hardening.py` passed with 100% compliance.

---

## 2. Test Case Specifications & Results

| # | Test Case Name | Objective / Assertion Target | Status | Duration |
|---|---|---|:---:|:---:|
| 1 | `test_production_checkpoints_preserved` | Verifies SHA-256 digests and physical byte sizes of immutable production models (`best_model.joblib`, `feature_pipeline.joblib`, `challenger_model_phase12f.joblib`). | **PASS** | 0.08s |
| 2 | `test_flask_process_clean_from_torch_and_sentence_transformers` | Confirms that neither `torch` nor `sentence_transformers` is loaded into `sys.modules` within the Flask web process. | **PASS** | 0.01s |
| 3 | `test_flask_startup_rss_below_200mb` | Verifies Flask cold-start RSS memory usage is strictly <= 200 MB (observed: **51.9–53.1 MB**). | **PASS** | 0.04s |
| 4 | `test_persistent_job_queue_lifecycle` | Validates ACID job transitions: enqueue, idempotent deduplication, atomic worker claim, retry increment, and permanent failure dead-lettering. | **PASS** | 0.12s |
| 5 | `test_zero_lost_jobs_across_restarts` | Simulates abrupt worker crash mid-processing, validates stale in-flight job recovery, and confirms zero job loss across daemon restarts. | **PASS** | 0.08s |
| 6 | `test_fallback_telemetry_correctness` | Asserts explicit recording of `model_requested`, `model_used`, `fallback_triggered`, and `fallback_reason`. Proves baseline output is never mislabeled as Model 5. | **PASS** | 0.92s |
| 7 | `test_file_upload_security_and_validation` | Tests magic bytes validation (`%PDF-`, `PK\x03\x04`), path traversal sanitization, and rejection of executable files or text with null bytes. | **PASS** | 0.03s |
| 8 | `test_csrf_and_rate_limiting` | Tests cryptographic constant-time CSRF validation and verifies in-memory sliding-window rate limiter returns HTTP 429 with `Retry-After`. | **PASS** | 0.02s |
| 9 | `test_headless_api_allow_fallback_behavior` | Verifies that `/api/match` with `allow_fallback=False` returns HTTP 202 Accepted on cache miss, providing queryable `job_ids` via `/api/jobs/<job_id>`. | **PASS** | 0.05s |
| 10 | `test_api_input_boundaries_and_error_handling` | Tests string type enforcement, min/max length boundaries (10 to 100,000 chars), invalid backend rejection, and 404 handlers. | **PASS** | 0.04s |

---

## 3. Regression Suite Verification

The Phase 15 integration suite (`experiments/phase15/tests/test_flask_integration.py`) was also executed and verified:
- **Phase 15 Tests:** **10 / 10 PASSED** in 23.48s.
- **Phase 15.1 Tests:** **10 / 10 PASSED** in 17.85s.
- **Historical Phase 13.1 & 14 Tests:** All verified and passing.

---

## 4. Key Findings & Architectural Observations

1. **Process Cleanliness:**
   - In earlier iterations, importing ML utilities pulled in PyTorch and SentenceTransformer at boot time.
   - By creating `src/services/job_queue.py` and delegating embedding generation to `src/services/embedding_worker.py`, the web process avoids importing `torch` entirely.
   - Flask cold boot RSS dropped from **204.7 MB** down to **51.9 MB** (a 74.6% reduction in memory footprint).
2. **Crash-Resilient Queue Semantics:**
   - Stale worker detection (`recover_stale_jobs(timeout_seconds=60.0)`) reliably identifies any jobs abandoned by crashed or terminated workers and resets them to `pending` with incremented retry counters.
   - 100% of tested jobs survived simulated abrupt worker shutdowns.
3. **Transparent Fallback Attribution:**
   - When Challenger Model 5 encounters a cache miss or unexpected error, the response explicitly tags `fallback_triggered: True` and includes the precise diagnostic reason (e.g., `cache_miss_pending_worker_generation`).
   - Zero silent fallback was observed across all test scenarios.
