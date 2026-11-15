# ResumeMatch AI — Deployment Audit

**Target branch:** `deploy/vercel-render-free`  
**Base branch:** `main` (read-only; do not merge or modify during deployment work)  
**Target hosting:** Vercel frontend + Render Flask API  
**Design requirement:** Preserve the current ResumeMatch AI dashboard appearance, navigation, charts, forms, and user-facing workflows.

## 1. Existing application

The repository currently contains a Flask + Jinja2 monolithic web application. It is not currently a separate React frontend and REST-only backend.

### Existing dashboard pages

The current templates include:

- Dashboard — `templates/index.html`
- Resume Analyzer — `templates/analyze.html`
- Analysis Results — `templates/results.html`
- Skill Gap Analytics — `templates/skill_gap.html`
- Career Mentor — `templates/career_mentor.html`
- Interview Studio — `templates/interview_studio.html`
- Interview Practice — `templates/interview_practice.html`
- Interview Results — `templates/interview_results.html`
- Model Performance — `templates/model_performance.html`
- Dataset Explorer — `templates/dataset_explorer.html`

Shared layout and visual assets:

- `templates/base.html`
- `static/css/dashboard.css`, `career_mentor.css`, `interview.css`, `style.css`
- `static/js/main.js`, `charts.js`, `analyzer.js`, `career_mentor.js`, `interview.js`
- Bootstrap 5.3, Bootstrap Icons, Chart.js, and Plotly.js are used by the existing UI.

## 2. Existing Flask routes

Page routes currently include:

- `GET /`
- `GET/POST /analyze`
- `GET /results`
- `GET /skill-gap`
- `GET /model-performance`
- `GET /datasets`
- `GET /career-mentor`
- `GET /interview-studio`
- `POST /interview-studio/generate`
- `GET /interview-practice`
- `POST /interview-practice/submit`
- `GET /interview-results`

JSON/API routes currently include:

- `GET /health`
- `GET /api/jobs/<job_id>`
- `POST /api/match`
- `GET /api/model-performance/export`
- `POST /api/interview/evaluate`
- `POST /api/interview/confirm-activity`
- `POST /api/interview/reset`
- `POST /api/mentor/update-name`
- `POST /api/mentor/progress`
- `POST /api/mentor/reset-progress`
- `POST /api/candidate/update-role`
- `POST /api/candidate/confirm-education`

These routes and their behavior must be mapped before replacing Jinja-rendered pages with React. Existing session-dependent workflows must continue to work.

## 3. Deployment blockers and risks found

1. **Frontend/backend separation is a real migration.** The current templates contain the page markup and server-rendered data. A Vercel React frontend requires porting all ten views and their interactions, not just adding a Vite folder.
2. **Session handling is cross-origin sensitive.** The current Flask app uses sessions. Vercel and Render use different hostnames, so cookie/CORS behavior must be designed and tested before the React app is considered complete.
3. **In-memory state is not durable.** The app contains process-local analysis/session/progress state. Restarts, free-tier sleep, or multiple processes can lose that state. This affects uploaded-resume analysis, interview practice, and mentor progress.
4. **SQLite/cache persistence needs a deliberate plan.** Runtime cache/queue files must not be assumed durable on an ephemeral filesystem. Do not split a SQLite file across separate services.
5. **Embedding worker resource usage needs validation.** The repository includes a dedicated Sentence Transformers worker. The previously measured combined web + worker memory is close to the memory ceiling of a small free instance; do not deploy both processes together without a measured resource plan.
6. **Production configuration needs hardening.** The current Flask secret-key configuration includes a development fallback. Production must require a strong environment-provided secret.
7. **Dependencies need a production audit.** Current `requirements.txt` does not include Gunicorn and does not list every optional worker/health-check dependency referenced by the code.

## 4. Implementation sequence

### Phase A — API and production backend
- Preserve the existing ML inference, parsing, skill-gap, mentor, and interview business logic.
- Separate API responses from Jinja page rendering without removing existing behavior prematurely.
- Add production server configuration, environment validation, upload limits, CORS/session strategy, and health checks.
- Define how temporary uploads and session-bound state behave on free hosting; do not claim durable storage until implemented.

### Phase B — React frontend
- Create a Vite + React frontend under a dedicated directory.
- Reproduce the existing sidebar, top navigation, typography, colours, cards, responsive layout, charts, and loading/error states.
- Port all ten existing views and their interactions.
- Connect the frontend to the Flask API and verify session continuity across the Vercel/Render boundary.

### Phase C — verification and deployment
- Add API contract and frontend build tests.
- Run the existing regression tests and new end-to-end workflow tests.
- Verify resume upload, matching, results, skill-gap navigation, mentor progress, interview practice, model charts, and dataset exploration.
- Add Render configuration and Vercel configuration only after the service boundaries and runtime requirements are validated.
- Deploy only after the user reviews the completed branch and approves the deployment actions.

## 5. Safety rules for this work

- All commits for this deployment migration go to `deploy/vercel-render-free`.
- Never push deployment work to `main`.
- Do not delete existing templates or static assets until the replacement React pages pass feature-parity tests.
- Do not remove ML features or silently substitute mock data.
- Do not expose secrets, uploaded resumes, or private user data in logs.
- Do not create or deploy paid resources without explicit user approval.
