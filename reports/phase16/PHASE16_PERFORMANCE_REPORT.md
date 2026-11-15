# Phase 16: Comprehensive Performance & System Resource Report

**Workspace:** `D:\skillsync1`  
**Phase:** 16 (Final Release Verification & Deployment Readiness)  
**Execution Date:** 2026-11-15  
**Auditor Roles:** Principal Performance Engineer, Systems Architect, Capacity Planning Specialist  

---

## 1. Executive Performance Summary

During Phase 16, a rigorous performance benchmark was conducted against the decoupled Flask web application and background embedding worker pipeline.

The benchmark evaluated:
1. **1,000 cached inference requests** across 4 concurrency tiers (1, 5, 10, and 25 workers).
2. **100 asynchronous embedding queue jobs** processed sequentially by the offline transformer worker.
3. **Resident Set Size (RSS)** memory footprints across cold start, steady-state serving, worker execution, and combined system usage.

### Key Performance Highlights:
- **Zero Errors:** 1,000 out of 1,000 requests succeeded (**0.00% error rate**).
- **Fast-Path Cache Hit Latency:** Under single concurrency, median latency is **9.90 ms** (p95 = **32.11 ms**), easily beating the sub-50ms target.
- **Peak Throughput:** Achieved **114.81 req/sec** at concurrency = 5.
- **Memory Footprint:** Flask boot RSS is **53.10 MB**, well under the **200 MB** budget (73.45% headroom). Steady-state serving RSS remained stable at **78.45 MB**.
- **Worker Throughput:** The dedicated offline worker processes **5.95 embeddings/sec** on CPU with a median processing latency of **36.34 ms**.

---

## 2. Cached API Concurrency Benchmark (1,000 Requests)

All 1,000 requests were sent to the `/api/match` endpoint requesting Challenger Model 5 with pre-cached candidate and job profiles.

| Concurrency Level | Requests | Elapsed (s) | Throughput (req/s) | Error Rate | Mean Latency (ms) | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Min / Max (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Concurrency = 1** | 250 | 7.408 | 33.75 | 0.00% | 29.03 | **9.90** | 32.11 | 38.03 | 5.06 / 4,377.54* |
| **Concurrency = 5** | 250 | 2.178 | **114.81** | 0.00% | 41.75 | 34.32 | 100.73 | 134.54 | 5.13 / 174.40 |
| **Concurrency = 10** | 250 | 2.250 | 111.10 | 0.00% | 83.61 | 72.38 | 204.42 | 331.99 | 5.17 / 373.18 |
| **Concurrency = 25** | 250 | 2.807 | 89.05 | 0.00% | 205.14 | 158.95 | 508.88 | 756.91 | 8.71 / 1,424.49 |
| **Overall (1,000 Reqs)** | **1,000** | **14.643** | **68.29** | **0.00%** | **89.88** | **42.39** | **318.54** | **544.63** | **5.06 / 4,377.54** |

*\*Note: The max latency in concurrency 1 reflects initial lazy unpickling and model initialization on the very first call. Subsequent steady-state cache hits executed in 5–15 ms.*

---

## 3. Asynchronous Embedding Worker Throughput (100 Jobs)

To evaluate background queue absorption capacity, 100 distinct textual payloads (50 resumes and 50 job descriptions) were enqueued into `embedding_queue.sqlite` and drained by `EmbeddingWorker`.

```
================================================================================
BACKGROUND EMBEDDING WORKER METRICS (100 JOBS)
================================================================================
Total Jobs Enqueued:               100
Total Enqueue Overhead:            1.924 seconds (19.24 ms / enqueue)
Total Worker Processing Time:      16.803 seconds
Worker Batch Throughput:           5.95 jobs / second (on single CPU core)
Mean Latency per Embedding:        168.03 ms (includes cold-start model load)
P50 (Median) Job Latency:          36.34 ms
P95 Job Latency:                   48.36 ms
P99 Job Latency:                   181.64 ms
================================================================================
```

### Worker Performance Insights:
- Once the SentenceTransformer model weights (`all-MiniLM-L6-v2`) are loaded into memory, individual 384-dimensional dense embedding generations take only **11–13 ms** per text.
- SQLite WAL mode ensures zero lock contention between the Flask serving process (reading embeddings) and the background worker (writing embeddings).

---

## 4. Resident Set Size (RSS) Memory Footprint

A primary architectural requirement of Phase 15.1 and Phase 16 is preventing memory bloat in web workers.

```
+-------------------------------------------------------------------------+
| PROCESS COMPONENT         | MEASURED RSS | TARGET LIMIT | HEADROOM      |
+-------------------------------------------------------------------------+
| Flask Boot / Startup      | 53.10 MB     | <= 200.00 MB | 146.90 MB (73%)|
| Flask Steady-State Serving| 78.45 MB     | <= 200.00 MB | 121.55 MB (61%)|
| Background Worker Daemon  | 412.30 MB    | Unconstrained| Dedicated Proc |
| Total Combined System RSS | 490.75 MB    | <= 1.00 GB   | 509.25 MB (51%)|
+-------------------------------------------------------------------------+
```

### Architectural Verification:
- **Module Isolation:** `torch` and `sentence_transformers` are **never** loaded into the Flask web process (`sys.modules` verified clean).
- **Leak-Free Serving:** Running 1,000 rapid requests increased Flask memory from 53.10 MB to 78.45 MB (a modest 25.35 MB increase due to SQLite cache buffers and cached metadata), well within standard production container constraints.

---

## 5. Capacity Planning & Production Sizing Guidelines

Based on measured benchmarks, the following deployment profiles are recommended:

1. **Standard VPS / Container (2 vCPU, 2 GB RAM):**
   - 2 Gunicorn / Waitress web workers (~160 MB total web RSS).
   - 1 Embedding Worker daemon (~420 MB worker RSS).
   - Maximum capacity: **~200 req/sec** for cached traffic; **~6 jobs/sec** for uncached embeddings.
   - Resource utilization: ~30% RAM, safe margin for OS buffers.

2. **High-Traffic Container (4 vCPU, 4 GB RAM):**
   - 4 Gunicorn / Waitress web workers (~320 MB total web RSS).
   - 2 Embedding Worker daemons (~840 MB worker RSS).
   - Maximum capacity: **~400+ req/sec** for cached traffic; **~12 jobs/sec** for uncached embeddings.
