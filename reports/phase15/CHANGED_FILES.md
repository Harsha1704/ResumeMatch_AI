# Phase 15: File Inventory & Change Tracking

**Repository:** `ResumeMatch AI`  
**Phase:** 15 — Production Flask Integration  
**Date:** 2026-11-15  

---

## 1. Production Checkpoint Integrity (Zero Changes)

The production checkpoints and baseline pipelines were preserved with absolute fidelity. Hashes and byte sizes verified before and after Phase 15 execution:

| Artifact Path | Expected Size (Bytes) | Observed Size (Bytes) | SHA-256 Digest | Status |
|---|:---:|:---:|---|:---:|
| `models/best_model.joblib` | 61,487 | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **UNMODIFIED (100% Match)** |
| `models/feature_pipeline.joblib` | 270,105 | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **UNMODIFIED (100% Match)** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **UNMODIFIED (100% Match)** |
| `models/phase13/semantic_skill_fusion_challenger.joblib` | 78,194 | 78,194 | `50aaabfe53025a04d2221f71fa6977bec9615649cff84e8da37d299f5cc44807` | **UNMODIFIED (100% Match)** |

---

## 2. Rollback Artifacts Preserved

Before applying in-place modifications to the production web application, bit-for-bit verbatim copies were archived in `experiments/phase15/backup/`:

1. `experiments/phase15/backup/app_original.py`: Pre-Phase 15 Flask web server application.
2. `experiments/phase15/backup/matching_engine_original.py`: Pre-Phase 15 monolithic TF-IDF / SpaCy matching engine.
3. `experiments/phase15/backup/analyze_original.html`: Pre-Phase 15 resume/job submission HTML template.
4. `experiments/phase15/backup/results_original.html`: Pre-Phase 15 scoring presentation HTML template.

To roll back immediately, copy these 4 files back to their original locations.

---

## 3. Modified Application Files

### 1. `app.py`
- **Purpose:** Primary Flask web application entrypoint.
- **Modifications:**
  - Added configuration `app.config["MODEL_BACKEND"] = os.environ.get("RESUMEMATCH_MODEL_BACKEND", "production")` to maintain strict default safety.
  - Enhanced `/health` route to verify and report `challenger_available`, `cache_status`, and `active_backend_default`.
  - Updated `/analyze` route to extract user model choice (`model_backend`), validate it against allowable backends (`"production"`, `"challenger_m5"`), and pass it through to the matching engine.
  - Added `@app.route("/api/match", methods=["POST"])` high-performance JSON API endpoint for headless matching, automated evaluations, and microservice consumption.

### 2. `src/analysis/matching_engine.py`
- **Purpose:** Core analytical and scoring engine.
- **Modifications:**
  - Added `model_backend: str = "production"` optional parameter to `analyze()` and `analyze_resume_and_job()`.
  - Maintained complete backward compatibility: when `model_backend == "production"` (or omitted), executes original Production Baseline (TF-IDF + SpaCy domain pipeline).
  - Integrated `challenger_service.predict_match()` when `model_backend == "challenger_m5"`.
  - Added defensive `try-except` block: if Challenger execution fails for any hardware/runtime reason, automatically logs an error and falls back to Production Baseline, returning `model_used="Production Baseline (Fallback from Challenger Error)"`.
  - Appended telemetry metadata to results: `model_used`, `model_backend`, `is_challenger`, `inference_latency_ms`, `cache_status`, and `calibration_note`.

### 3. `templates/analyze.html`
- **Purpose:** Resume upload and job description submission form.
- **Modifications:**
  - Added visual model selection UI cards allowing recruiters/evaluators to explicitly opt into Challenger Model 5 or retain Production Baseline (Default).
  - Included informative helper text explaining that Model 5 uses cached neural embeddings and is currently in experimental evaluation mode.

### 4. `templates/results.html`
- **Purpose:** Candidate-job fit analysis visualization page.
- **Modifications:**
  - Added responsive badge header indicating the exact model provenance (`Production Baseline (TF-IDF + Domain Pipeline)` vs `Challenger Model 5 (Semantic-Skill Fusion)`).
  - Surfaced real-time inference latency and cache status (`HIT (<50ms)` vs `MISS / COMPUTED`).
  - Added amber disclaimer card when Challenger Model 5 is used, explaining that raw probabilities are derived from softmax cross-entropy output and remain uncalibrated for standalone recruiter hiring cutoffs.

---

## 4. Newly Created Architecture & Service Files

### 1. `src/services/embedding_service.py`
- **Purpose:** Decoupled embedding management service.
- **Capabilities:**
  - Wraps Phase 14 `EmbeddingCache` with thread-safe singleton lifecycle.
  - Avoids loading PyTorch / `SentenceTransformer` into memory during cache-hit serving.
  - Provides `encode_async()` for asynchronous background embedding pre-warming via Python `ThreadPoolExecutor`.
  - Exposes health, cache statistics, and memory telemetry.

### 2. `src/services/challenger_service.py`
- **Purpose:** High-level inference adapter for Model 5 cached evaluation.
- **Capabilities:**
  - Wraps `predict_fusion_cached()` with latency tracking and diagnostic reporting.
  - Formats output payloads into structured dictionaries compatible with Flask and JSON API schemas.

---

## 5. Newly Created Tests, Scripts & Reports

### 1. `experiments/phase15/tests/test_flask_integration.py`
- Complete automated pytest suite (10 test cases) verifying checkpoints, endpoints, uploads, form validation, model switching, numerical equivalence, fallback safety, concurrency, and security.

### 2. `experiments/phase15/scripts/benchmark_flask_app.py`
- Production benchmarking script measuring cold-start latency, RSS memory footprint across serving states, cache-hit vs cache-miss latencies, concurrency throughput, and storage growth.

### 3. `reports/phase15/phase15_benchmark.json`
- Machine-readable benchmark results detailing 100-request latency distributions, memory usage, and release gate statuses.

### 4. `reports/phase15/phase15_test_results.md`
- Documentation of test executions, assertion criteria, and full regression verification across Phases 13.1, 14, and 15.

### 5. `reports/phase15/PHASE15_REPORT.md`
- Master engineering report synthesizing system architecture, UI integration, performance benchmarks, safety audit, release gate assessment, and instructions for running the application.
