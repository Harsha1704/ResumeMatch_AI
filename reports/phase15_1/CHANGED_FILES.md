# Phase 15.1: File Inventory & Change Tracking

**Repository:** `ResumeMatch AI`  
**Phase:** 15.1 — Deployment Hardening  
**Date:** 2026-11-15  

---

## 1. Production Checkpoint Integrity (Zero Changes)

The historical production models and preprocessing checkpoints were verified before, during, and after Phase 15.1. Exact physical byte counts and SHA-256 hashes confirm zero modifications:

| Artifact Path | Expected Size (Bytes) | Observed Size (Bytes) | SHA-256 Digest | Status |
|---|:---:|:---:|---|:---:|
| `models/best_model.joblib` | 61,487 | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **UNTOUCHED (100% Match)** |
| `models/feature_pipeline.joblib` | 270,105 | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **UNTOUCHED (100% Match)** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **UNTOUCHED (100% Match)** |
| `models/phase13/semantic_skill_fusion_challenger.joblib` | 78,194 | 78,194 | `50aaabfe53025a04d2221f71fa6977bec9615649cff84e8da37d299f5cc44807` | **UNTOUCHED (100% Match)** |

---

## 2. Preserved Rollback Copies

Bit-for-bit pre-Phase 15.1 snapshots were archived in `experiments/phase15_1/backup/`:

1. `experiments/phase15_1/backup/app_pre_phase15_1.py`: Pre-Phase 15.1 Flask server entrypoint.
2. `experiments/phase15_1/backup/matching_engine_pre_phase15_1.py`: Pre-Phase 15.1 matching engine.
3. `experiments/phase15_1/backup/embedding_service_pre_phase15_1.py`: Pre-Phase 15.1 embedding service.
4. `experiments/phase15_1/backup/challenger_service_pre_phase15_1.py`: Pre-Phase 15.1 challenger service adapter.
5. `experiments/phase15_1/backup/analyze_pre_phase15_1.html`: Pre-Phase 15.1 analyzer form template.
6. `experiments/phase15_1/backup/results_pre_phase15_1.html`: Pre-Phase 15.1 results presentation template.

---

## 3. Modified Application Files

### 1. `app.py`
- Implemented lazy module imports to keep cold boot RSS at **51.9 MB** (well below the 200 MB SLA).
- Integrated `UploadSecurityError` validation: validates magic bytes (`%PDF-`, `PK\x03\x04`), safe filenames, and max 16 MB size.
- Integrated `SlidingWindowRateLimiter`: 60 rpm on `/api/match`, 30 rpm on `/analyze` uploads with HTTP 429 and `Retry-After`.
- Integrated `validate_csrf_token` on all HTML form POST submissions.
- Added `/api/jobs/<job_id>` GET endpoint to query background embedding job status.
- Enhanced `/health` endpoint to report `flask_rss_mb`, `queue_stats`, `cache_stats`, and model loading state.
- Enhanced `/api/match` with boundary validation and `allow_fallback` semantics (HTTP 202 on cache miss when fallback disabled).

### 2. `src/analysis/matching_engine.py`
- Refactored `ResumeMatchingEngine` to use lazy property getters for `inference_engine` and `challenger_service`.
- Enhanced Model 5 prediction handler with structured fallback fields:
  - `model_requested`
  - `model_used`
  - `fallback_triggered`
  - `fallback_reason`
  - `pending_jobs`
- Non-blocking cache miss: automatically triggers fallback to Production Baseline with explicit notice while background worker processes embeddings.

### 3. `src/services/embedding_service.py`
- Completely removed `SentenceTransformer` and `torch` imports from web process context.
- Integrated `EmbeddingJobQueue`: cache misses are pushed asynchronously to the persistent SQLite queue.
- Exposes `get_embedding_or_queue()`, `is_cached()`, `get_job_status()`, and `get_stats()`.

### 4. `src/services/challenger_service.py`
- Decoupled from transformer forward passes: reads vectors from cache and executes fusion feature calculation and classifier forward pass in < 50ms.
- Non-blocking miss handler: returns `status="cache_miss_pending"` with `job_ids`.

### 5. `templates/analyze.html`
- Embedded `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">` in the main analysis form.

### 6. `templates/results.html`
- Added explicit fallback status badge (`Fallback to Baseline`) with tooltip indicating the precise reason.
- Added amber warning notice banner informing recruiters when an analysis defaulted to the baseline due to queued neural embeddings.

---

## 4. Newly Created Architecture & Security Modules

### 1. `src/services/job_queue.py`
- Persistent SQLite-backed queue with Write-Ahead Logging (`WAL` mode) and 30-second busy timeout.
- Manages job states: `pending`, `processing`, `completed`, `failed`.
- Supports retries with configurable `max_retries` and automatic recovery of stale/crashed in-flight jobs.

### 2. `src/services/embedding_worker.py`
- Dedicated background worker daemon that houses PyTorch and SentenceTransformer (`all-MiniLM-L6-v2`).
- Runs in offline mode (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`), eliminating external network stalls.
- Continuously claims pending jobs, computes dense embeddings, persists them to `PersistentEmbeddingCache`, and marks jobs completed.

### 3. `worker.py`
- Standalone CLI launcher for background embedding daemon.

### 4. `src/security/upload_validator.py`
- Deep content validator: extension whitelist (`.pdf`, `.docx`, `.txt`), magic bytes signature verification, and path traversal defense via `secure_filename`.

### 5. `src/security/rate_limiter.py`
- In-memory thread-safe sliding-window rate limiter with automatic pruning of expired client windows.

### 6. `src/security/csrf.py`
- Cryptographic session-bound CSRF token generator and constant-time validator (`secrets.compare_digest`).

---

## 5. Newly Created Tests, Benchmarks & Reports

- `experiments/phase15_1/tests/test_deployment_hardening.py`: Automated test suite (10 tests, 100% pass rate).
- `experiments/phase15_1/scripts/benchmark_deployment.py`: Production benchmark script (1,000 requests, 100 queue jobs, concurrency stress, crash recovery).
- `reports/phase15_1/phase15_1_benchmark.json`: Raw machine-readable benchmark telemetry.
- `reports/phase15_1/phase15_1_test_results.md`: Comprehensive test report.
- `reports/phase15_1/phase15_1_security_report.md`: Deep security controls and threat model audit.
- `reports/phase15_1/PHASE15_1_REPORT.md`: Master engineering report for Phase 15.1.
