# Render Backend Setup — ResumeMatch AI

This branch contains the Flask backend runtime preparation for Render. It does not deploy a service or create hosting resources.

## Render web service

- **Root directory:** repository root
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app`
- The same start command is recorded in the repository `Procfile`.

Render supplies the `PORT` environment variable. Keep the single Gunicorn worker for the initial free-instance memory test; do not start the separate embedding worker on the same small instance without measuring combined memory.

## Required environment variables

Set these in the Render service dashboard (do not commit secrets):

| Variable | Value |
|---|---|
| `RESUMEMATCH_ENV` | `production` |
| `SECRET_KEY` | A newly generated, long random secret |
| `FRONTEND_ORIGIN` | Exact deployed Vercel origin, e.g. `https://your-app.vercel.app` |
| `RESUMEMATCH_MODEL_BACKEND` | `production` |
| `MAX_CONTENT_LENGTH` | `16777216` |
| `PERSISTENT_STORAGE_DIR` | (Optional) Path to mounted persistent volume, e.g. `/var/data` |
| `ANALYSIS_DB_PATH` | (Optional) Explicit full path to SQLite analysis database |

For Vercel preview domains, use `FRONTEND_ORIGINS` with a comma-separated list of exact origins. Do not use a wildcard when credentials/cookies are enabled.

The production app now refuses to start if `SECRET_KEY` is missing. Production session cookies are HttpOnly, Secure, and SameSite=None so credentialed requests can work across the Vercel/Render origins. The React client must send requests with credentials enabled.

## Persistence Architecture & Render Storage Realities

1. **Ephemeral Filesystem on Free Tier:**
   Render Free services use ephemeral container filesystems. Local SQLite databases (`data/cache/analysis_store.sqlite`) are reset upon instance redeployment, restart, or sleep.
2. **Persistent Disk Support:**
   When using a paid Render web service with a Persistent Disk mount (e.g. `/var/data`), set `PERSISTENT_STORAGE_DIR=/var/data`. The application will automatically store `analysis_store.sqlite` on the mounted disk.
3. **Multi-Instance PostgreSQL Blueprint:**
   For horizontally scaled deployments (multiple worker instances), SQLite cannot be safely shared across instances. Migrate to PostgreSQL using the provided JSONB schema:
   - `analyses(analysis_id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64), created_at DOUBLE PRECISION, updated_at DOUBLE PRECISION, analysis_json JSONB)`
4. **Candidate Data Privacy:**
   Private resumes and candidate dossiers are NEVER stored in public static directories. They are stored solely in the private L2 database.

## Important free-tier limitations

- Render free services may sleep and cold-start.
- In-memory interview practice sessions and unpersisted progress can reset when instances sleep.
- The embedding cache and job queue use local SQLite files. Render's ephemeral filesystem is not durable, and a separate worker process cannot safely share a local SQLite database across separate services.
- The separate Sentence Transformers worker is intentionally not included in the web start command. Challenger-model asynchronous cache-miss jobs will not be processed until a durable shared queue/cache and a suitable worker deployment are designed.
- Confirm the required model artifacts and evaluation JSON files are present in the deployed Git revision before enabling inference.

## Verification still required

This is configuration preparation, not a verified live deployment. Before deployment, run the project test suite and a local Gunicorn smoke test, verify model artifacts, then test the production environment variables and Vercel-to-Render cookie/CORS flow. Do not treat the app as production-ready until those checks pass.
