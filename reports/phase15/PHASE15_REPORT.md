# ResumeMatch AI — Phase 15: Production Flask Integration Report

**Engineering Phase:** Phase 15  
**Project:** ResumeMatch AI  
**Workspace:** `D:\skillsync1`  
**Date:** 2026-11-15  
**Auditor & Implementation Roles:** Principal MLOps Engineer, Software Architect, Information Retrieval Specialist, ML Evaluation Auditor  

---

## 1. Executive Summary

Phase 15 integrates the Phase 14 optimized cached-embedding inference architecture into the existing Flask-based ResumeMatch AI application (`app.py`). 

The primary objective was to deliver a production-ready, highly responsive web and API experience leveraging Challenger Model 5 (Semantic-Skill Fusion) while strictly adhering to safety constraints:
1. **Zero Checkpoint Mutation:** Production model weights (`best_model.joblib`, `feature_pipeline.joblib`, `challenger_model_phase12f.joblib`) remain 100% untouched and bit-for-bit identical to historical baselines.
2. **Zero Quarantined Test Contamination:** The quarantined official test split (`manifests/v1/held_out_test_v1.parquet`) was accessed zero times.
3. **Strict Baseline Default:** Production Baseline remains the default matching engine; Challenger Model 5 is accessible strictly through intentional opt-in.
4. **Decoupled Serving Architecture:** A dedicated service layer (`src/services/embedding_service.py` and `src/services/challenger_service.py`) shields the web serving process from unnecessary transformer loading during cache-hit serving.
5. **Zero Downtime Fallback:** Any unexpected exception in Challenger Model 5 (e.g. out-of-memory or model load error) automatically degrades to the Production Baseline without raising an HTTP 500 error.
6. **Empirical Performance Verification:** In a benchmark of 100 API requests across representative technical roles, cached Model 5 achieved a p95 latency of **39.69 ms** (well under the 50 ms SLA target) and a **1.4x speedup** over Production Baseline.

---

## 2. Architecture & Service Layer Design

```
+-----------------------------------------------------------------------------------+
|                              FLASK WEB APPLICATION                                |
|  - Web UI: /upload, /analyze, /results                                            |
|  - JSON API: POST /api/match, GET /health                                         |
+-----------------------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------------------+
|                           SRC/ANALYSIS/MATCHING_ENGINE.PY                         |
|  - Validates inputs & parameters (model_backend: "production" | "challenger_m5")  |
+-----------------------------------------------------------------------------------+
             |                                                  |
             | (Default: "production")                          | (Opt-In: "challenger_m5")
             v                                                  v
+-----------------------------+                +------------------------------------+
|     PRODUCTION BASELINE     |                |        CHALLENGER SERVICE          |
|  - TF-IDF Vectorizer        |                |  - Latency instrumentation         |
|  - SpaCy Domain Pipeline    |                |  - Fallback error wrapper          |
|  - Logistic Classifier      |                +------------------------------------+
+-----------------------------+                                   |
                                                                  v
                                               +------------------------------------+
                                               |         EMBEDDING SERVICE          |
                                               |  - Persistent SQLite Cache Query   |
                                               +------------------------------------+
                                                        /                  \
                                              [Hit]    /                    \   [Miss]
                                                      v                      v
                                       +-----------------------+   +----------------+
                                       |  Feature Fusion Engine|   | Sentence-      |
                                       |  - Cosine / Dot / Diff|   | Transformer    |
                                       |  - Exact Scalers      |   | (MiniLM-L6-v2) |
                                       |  - Model 5 Joblib Head|   | [Loads on miss]|
                                       +-----------------------+   +----------------+
```

### A. Decoupled Service Layer (`src/services/embedding_service.py`)
- **Memory Preservation:** The service decouples web request handling from heavy neural network weights. When query embeddings exist in the persistent SQLite cache, `SentenceTransformer` and PyTorch weights are never instantiated.
- **Asynchronous Pre-Warming:** Exposes an `encode_async()` interface utilizing a controlled Python `ThreadPoolExecutor` (max 2 workers) allowing background batch encoding without stalling incoming HTTP connections.
- **SQLite Concurrency & WAL Mode:** Configured with `timeout=30.0` and Write-Ahead Logging (`WAL` journal mode) to allow simultaneous readers and safe serialization of cache writes without database locking errors.

### B. High-Level Adapter (`src/services/challenger_service.py`)
- Provides clean isolation between Flask controllers and raw ML feature arithmetic.
- Manages precision formatting, timing telemetry, and structured diagnostic payloads.

### C. Fail-Safe Fallback Handler (`src/analysis/matching_engine.py`)
- If Challenger Model 5 encounters any runtime exception (e.g. disk corruption, cache read errors, or memory exhaustion), it intercepts the exception, logs a warning with full traceback, and silently falls back to Production Baseline.
- The output metadata explicitly tags the response with:
  ```json
  {
    "model_used": "Production Baseline (Fallback from Challenger Error)",
    "is_challenger": false,
    "fallback_triggered": true
  }
  ```
- The end user receives valid candidate analysis immediately, ensuring continuous availability.

---

## 3. Web UI & REST API Integration

### A. Dynamic Model Selection in Web Interface (`templates/analyze.html`)
- Added clear visual selection cards for recruiter evaluation:
  1. **Production Baseline (Default):** Classical TF-IDF and domain-rule matching engine. Stable, deterministic, and recommended for standard workflows.
  2. **Challenger Model 5 (Experimental):** High-speed neural embedding fusion model utilizing cached representations.
- Includes descriptive subtext alerting the recruiter that Model 5 is an experimental research preview.

### B. Transparent Model Provenance & Calibration Disclaimers (`templates/results.html`)
- **Provenance Badge:** Prominently displays which engine generated the score (`Production Baseline` vs `Challenger Model 5 (Semantic-Skill Fusion)`).
- **Latency & Cache Status:** Informs evaluators whether the prediction utilized a cached embedding (`HIT (<50ms)`) or required real-time encoding.
- **Calibration Notice:** When Challenger Model 5 is selected, an amber advisory informs the user:
  > *"Notice: Challenger Model 5 probabilities are raw outputs from experimental softmax cross-entropy optimization. While highly discriminative, they are uncalibrated for standalone hiring threshold decisions. Always verify candidate credentials directly."*

### C. Headless REST API (`POST /api/match`)
- Exposes a dedicated JSON API endpoint for external services, automated benchmarking, and ATS integrations:
  ```bash
  curl -X POST http://localhost:5000/api/match \
    -H "Content-Type: application/json" \
    -d '{
      "resume_text": "Experienced Python Backend Developer with FastAPI and Docker.",
      "job_description": "Seeking Python Engineer with Docker experience.",
      "model_backend": "challenger_m5"
    }'
  ```
- Returns structured JSON containing overall score, match probability, match category, skill breakdown, inference latency, and cache status.

---

## 4. Performance Benchmarks & Empirical Latency Profiles

A comprehensive benchmark was conducted across a representative workload of 10 distinct technical disciplines (Backend, Frontend, Data Engineering, DevOps, Mobile iOS, Full Stack, ML/NLP, Cybersecurity, QA Automation, and Database Administration) performing 100 API requests.

The complete telemetry is archived in `reports/phase15/phase15_benchmark.json`.

### A. Latency Distribution Comparison (100 Requests)

| Metric | Production Baseline (TF-IDF + SpaCy) | Challenger Model 5 (Cache Hit Serving) | Challenger Model 5 (Cache Miss with Encoding) | Target SLA |
|---|:---:|:---:|:---:|:---:|
| **Mean Latency** | 37.79 ms | **26.66 ms** | 5,791.74 ms | — |
| **Median (p50)** | 36.40 ms | **24.56 ms** | 274.03 ms | — |
| **p95 Latency** | 50.65 ms | **39.69 ms** | 30,604.09 ms | **<= 50.0 ms (PASS)** |
| **p99 Latency** | 69.26 ms | **46.54 ms** | 50,416.16 ms | — |
| **Relative Speedup** | 1.0x (Baseline) | **1.4x Faster** | — | — |

*Key Takeaway:* In cache-hit serving mode, Challenger Model 5 consistently outperforms the Production Baseline, achieving sub-40ms p95 response times.

### B. Process Memory (RSS) Footprint

| State | Process RSS | Analysis |
|---|:---:|---|
| **Flask Boot (Cold Start)** | **204.73 MB** | Web application initialized, routes mounted, baseline loaded. |
| **Pure Cache-Hit Serving** | **204–214 MB** | Transformer remains unloaded; inference executed entirely via SQLite vectors and classifier head. |
| **Cache Miss (In-Process Fallback)** | **629.86 MB** | PyTorch and `all-MiniLM-L6-v2` transformer loaded into web process to compute new vectors. |

### C. Concurrency Throughput & Reliability
- **Concurrent Test:** 25 requests dispatched across 5 simultaneous threads (`ThreadPoolExecutor`).
- **Success Rate:** **100% (25/25 successful)**.
- **Throughput:** **33.95 requests/second**.
- **Mean Concurrent Latency:** 129.04 ms.
- **Database Lock Contention:** 0 errors encountered under WAL configuration.

### D. Deployable Artifact Sizing

| Component | Disk Size |
|---|:---:|
| Production Baseline Artifacts (`best_model.joblib` + `feature_pipeline.joblib`) | 323.8 KB |
| Challenger Model 5 Classifier Head | 76.4 KB |
| SQLite Cache Database (Pre-warmed) | 72.0 KB |
| Flask Web UI Assets (Templates + Static CSS/JS) | 1.91 MB |
| **Pure Web Serving Bundle** | **2.06 MB** |
| Full Offline SBERT HuggingFace Cache | 174.00 MB |
| **Total Full Offline Standalone Bundle** | **176.06 MB** |

---

## 5. Comprehensive Safety, Integrity & Release Gate Audit

### A. Production Checkpoints (Zero Mutation Verified)
All production model files were verified before and after Phase 15. The exact byte lengths and SHA-256 digests confirm absolute zero modification:

```
best_model.joblib:                61,487 bytes | 1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a [VERIFIED]
feature_pipeline.joblib:         270,105 bytes | 2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6 [VERIFIED]
challenger_model_phase12f.joblib: 2,330,440 bytes | 5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766 [VERIFIED]
```

### B. Quarantined Test Split Quarantine
- File `manifests/v1/held_out_test_v1.parquet` was never referenced, opened, or imported during Phase 15 development, testing, or benchmarking.

### C. Zero LLM Dependencies
- No OpenAI, Anthropic, or external cloud API calls exist in the runtime pipeline. Inference is 100% self-contained and local.

### D. Automated Test Suite (100% Pass Rate)
- `experiments/phase15/tests/test_flask_integration.py`: **10 / 10 PASSED**.
- Cumulative Regression (Phases 13.1, 14, 15): **27 / 27 PASSED**.

### E. Phase 15 Release Gate Evaluation Matrix

| Gate Criteria | Requirement | Observed Status | Assessment |
|---|---|:---:|:---:|
| **Gate 1: Checkpoint Preservation** | Exact hash and byte matches on all baseline models | 100% match | **PASS** |
| **Gate 2: Quarantined Test Quarantine** | Zero access to held-out test split | 0 accesses | **PASS** |
| **Gate 3: Default Serving Safety** | Baseline is default; Challenger is opt-in | Verified | **PASS** |
| **Gate 4: Fallback Resilience** | Automatic fallback without HTTP 500 | Verified | **PASS** |
| **Gate 5: Serving Latency SLA** | Cache-hit p95 <= 50.0 ms | **39.69 ms** | **PASS** |
| **Gate 6: Automated Test Verification** | 100% tests passing in pytest | 27 / 27 passed | **PASS** |
| **Gate 7: Pure Serving Memory** | Serving process RSS <= 200 MB | 204.73 MB on boot, 629 MB on miss | **CONDITIONAL / FAIL** |

*Audit Finding on Gate 7:* On initial boot, the Flask process requires ~204 MB RSS. When cache misses occur in the monolithic web process, loading `SentenceTransformer` elevates memory to ~630 MB. To maintain sub-200 MB memory in production environments, cache misses should be directed to an asynchronous sidecar worker or background ingestion process rather than in-process on-demand encoding.

---

## 6. Rollback Protocol & Operational Guide

### A. How to Run the Updated Flask Application

1. **Start the Web Application (Default Mode):**
   ```bash
   cd D:\skillsync1
   python app.py
   ```
   The application starts on `http://127.0.0.1:5000`. By default, all queries execute through the proven Production Baseline.

2. **Start with Challenger Model 5 as Default Backend (Optional):**
   ```bash
   set RESUMEMATCH_MODEL_BACKEND=challenger_m5
   python app.py
   ```

3. **Verify Application Health:**
   ```bash
   curl http://127.0.0.1:5000/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "active_backend_default": "production",
     "challenger_available": true,
     "cache_status": "connected"
   }
   ```

### B. Instant Rollback Procedure
If any unforeseen production issue occurs, the system can be rolled back immediately without recompilation:

```bash
# In D:\skillsync1
copy /Y experiments\phase15\backup\app_original.py app.py
copy /Y experiments\phase15\backup\matching_engine_original.py src\analysis\matching_engine.py
copy /Y experiments\phase15\backup\analyze_original.html templates\analyze.html
copy /Y experiments\phase15\backup\results_original.html templates\results.html
```
Restart the Flask server. All files revert to their pre-Phase 15 state.

---

## 7. Conclusion & Next Steps

Phase 15 successfully delivers production Flask integration for ResumeMatch AI. The application offers users and evaluators the ability to test the state-of-the-art Model 5 semantic-skill fusion engine with sub-40ms cached response times, while preserving 100% backward compatibility and system stability through automated Production Baseline fallbacks and transparent UI disclaimers.

Recommended next steps for subsequent engineering iterations:
1. **Asynchronous Sidecar Worker:** Move transformer-based cache-miss encoding out of the Flask web process into a standalone Celery / Redis background worker, locking web serving RSS strictly below 200 MB.
2. **Probability Calibration:** Implement isotonic regression or Platt scaling on the Model 5 classifier head to calibrate raw cross-entropy logits into calibrated real-world recruiter likelihoods.
