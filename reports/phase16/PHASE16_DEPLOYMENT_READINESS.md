# Phase 16: Deployment Readiness & Operational Guide

**Workspace:** `D:\skillsync1`  
**Phase:** 16 (Final Release Verification & Deployment Readiness)  
**Execution Date:** 2026-11-15  
**Auditor Roles:** Principal MLOps Engineer, Release Manager, Site Reliability Engineer  

---

## 1. System Architecture Overview

ResumeMatch AI is structured as a decoupled, multi-process architecture designed to provide low latency, high throughput, and strict process-level fault isolation:

```
+-----------------------------------------------------------------------------+
|                           HTTP CLIENTS / BROWSERS                           |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                       WSGI WEB SERVER (Gunicorn / Waitress)                 |
|  - Process RSS: 53–78 MB                                                    |
|  - sys.modules: ZERO PyTorch / SentenceTransformer                          |
|  - Serves: HTML UI, /api/match, /api/queue/<id>, /health                    |
|  - Default Engine: Production Baseline (TF-IDF + Logistic Regression)       |
|  - Fast-Path Engine: Model 5 Challenger (Cached Embedding Reader)          |
+-----------------------------------------------------------------------------+
             |                                             |
    (Read Embeddings)                             (Enqueue Cache Misses)
             |                                             |
             v                                             v
+-----------------------------+               +-------------------------------+
|  embedding_cache.sqlite     |               |    embedding_queue.sqlite     |
|  (SQLite WAL Mode)          |               |    (SQLite WAL Mode)          |
|  - Key: Hash(Text + Model)  |               |    - ACID Job Queue           |
|  - Value: 384-dim Float32   |               |    - Retry & Stale Detection  |
+-----------------------------+               +-------------------------------+
             ^                                             |
             |                                             |
      (Write Embeddings)                           (Claim Pending Jobs)
             |                                             |
             +-----------------------+---------------------+
                                     |
+------------------------------------+----------------------------------------+
|                 BACKGROUND EMBEDDING WORKER DAEMON                          |
|  - Process RSS: ~412 MB                                                     |
|  - Houses: PyTorch, SentenceTransformer (all-MiniLM-L6-v2)                  |
|  - Offline Execution: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1              |
|  - Recovery: Recovers orphaned jobs on startup (timeout > 60s)              |
+-----------------------------------------------------------------------------+
```

---

## 2. Production Environment Configuration

The following environment variables should be defined in `.env` or injected by your container orchestrator (Kubernetes, Docker Compose, or AWS ECS):

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Disables debug mode and interactive debugger. |
| `FLASK_APP` | `app:app` | WSGI application entry point. |
| `SECRET_KEY` | *(Strong random 64-char hex)* | Session cookie signing key. |
| `MODEL_BACKEND` | `production` | **Default model.** Keeps Model 5 opt-in experimental. |
| `HF_HUB_OFFLINE` | `1` | Forces SentenceTransformers to use local cached weights. |
| `TRANSFORMERS_OFFLINE`| `1` | Prevents runtime outbound network calls to Hugging Face. |
| `CACHE_DB_PATH` | `/var/data/skillsync/cache/embedding_cache.sqlite` | Persistent cache database path. |
| `QUEUE_DB_PATH` | `/var/data/skillsync/cache/embedding_queue.sqlite` | Persistent job queue database path. |
| `MAX_CONTENT_LENGTH` | `16777216` (16 MB) | Maximum allowable payload size for resume uploads. |
| `RATE_LIMIT_ENABLED`| `true` | Enables sliding window rate limiting. |

---

## 3. Process Execution & Supervision

### A. Linux Host (Systemd Configuration)

Create two systemd unit files to manage the web and worker processes independently.

#### 1. Web Service (`/etc/systemd/system/skillsync-web.service`)
```ini
[Unit]
Description=ResumeMatch AI Flask Web Application
After=network.target

[Service]
Type=simple
User=skillsync
WorkingDirectory=/opt/skillsync
EnvironmentFile=/opt/skillsync/.env
ExecStart=/opt/skillsync/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 60 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### 2. Background Worker (`/etc/systemd/system/skillsync-worker.service`)
```ini
[Unit]
Description=ResumeMatch AI Background Embedding Worker
After=network.target

[Service]
Type=simple
User=skillsync
WorkingDirectory=/opt/skillsync
EnvironmentFile=/opt/skillsync/.env
ExecStart=/opt/skillsync/venv/bin/python -m src.services.embedding_worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### B. Windows Host (Waitress & Background Process)

On Windows servers, run using `waitress`:

```powershell
# In PowerShell / Windows Task Scheduler (Web Server)
venv\Scripts\waitress-serve --listen=0.0.0.0:5000 app:app

# In separate background terminal / Task Scheduler (Embedding Worker)
venv\Scripts\python -m src.services.embedding_worker
```

---

## 4. Storage & Volume Mounts

When deploying in Docker or Kubernetes:
- The `data/cache` directory **must be mounted on a persistent volume** with POSIX locking support.
- Do **NOT** use network shares (such as NFSv3) with unreliable file locking, as SQLite WAL mode requires POSIX shared-memory locks (`.shm` file). Local SSD or cloud block storage (AWS EBS, GCP Persistent Disk) is strongly required.
- File permissions must grant read/write access to both the `skillsync-web` and `skillsync-worker` service accounts.

---

## 5. Health Checks & Monitoring

The application provides a comprehensive JSON health check endpoint:

```bash
curl http://localhost:5000/health
```

**Expected Response (`HTTP 200`):**
```json
{
  "status": "healthy",
  "service": "Multimodal Resume-Job Matching System",
  "framework": "Flask 3.x",
  "model_loaded": true,
  "challenger_available": true,
  "active_backend_default": "production",
  "flask_rss_mb": 53.1,
  "cache_stats": {
    "total_cached": 150,
    "resumes": 75,
    "jobs": 75
  },
  "queue_stats": {
    "pending": 0,
    "processing": 0,
    "completed": 210,
    "failed": 0,
    "total": 210
  }
}
```

### Monitoring Thresholds:
- **`flask_rss_mb` > 180 MB:** Trigger warning alert.
- **`queue_stats.pending` > 100:** Trigger worker scale-up alert (queue backlog accumulating).
- **`queue_stats.failed` > 10:** Trigger dead-letter investigation alert.

---

## 6. Documented Limitations & Operational Boundaries

1. **Experimental Opt-In Model 5:**
   - Model 5 (Semantic & Skill Fusion) must remain an **opt-in experimental challenger** (`model_backend="challenger_m5"`).
   - Production Baseline (TF-IDF + Logistic Regression) must remain the default model backend.
2. **Cold-Start Embedding Latency:**
   - On cache misses, embedding generation requires 15–20 ms per text on CPU. When `allow_fallback=True` is provided (default), the API returns a Production Baseline prediction immediately while the worker computes the embedding in the background. If `allow_fallback=False` is requested, the client receives `HTTP 202 Accepted` and must poll `/api/queue/<job_id>`.
3. **Quarantined Test Set:**
   - The file `manifests/v1/held_out_test_v1.parquet` is strictly quarantined and must never be accessed by runtime code or evaluation scripts.
4. **Single-Worker Scalability:**
   - A single CPU embedding worker processes ~6 embeddings/sec (~360 resumes/minute). For installations expecting high upload velocity (>500 resumes/hour), run 2 to 4 worker instances. SQLite WAL mode supports multiple concurrent worker processes seamlessly.
