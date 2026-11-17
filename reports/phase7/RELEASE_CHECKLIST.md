# RESUMEMATCH AI — PHASE 7: PRODUCTION RELEASE & DEPLOYMENT CHECKLIST

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`)  
**Document Purpose**: Operational Step-by-Step Release Gate Checklist for System Administrators

---

## 1. Pre-Release Verification (Engineering Sign-Off)

Before performing any actions in production cloud dashboards, ensure all engineering milestones are verified:

- [x] **Branch Verification**: All changes are committed and pushed to `fix/resumematch-final-repair`. No uncommitted files or unstaged changes.
- [x] **Backend Regression**: All 770 pytest tests pass cleanly (`py -3.14 -m pytest tests/ -q`).
- [x] **Production Readiness Suite**: All 19 Phase 7 tests pass cleanly (`py -3.14 -m pytest tests/test_phase7*.py -v`).
- [x] **Frontend Unit & Browser Suites**: All 14 tests pass across Chromium, Firefox, and WebKit (`npm test --prefix frontend`).
- [x] **Frontend Production Build**: `tsc -b && vite build` completes cleanly with 0 errors.
- [x] **Frontend Linting**: `oxlint` completes with 0 errors.
- [x] **Fail-Closed CSRF Protection**: All 13 mutating API routes verified rejecting unauthenticated/untokenized mutations with HTTP 403.
- [x] **Session Isolation**: Multi-session IDOR isolation verified across all analysis endpoints.
- [x] **Archive Bomb & File Validation**: Magic bytes inspection and DOCX 10:1 compression ratio limits verified.

---

## 2. Cloud Infrastructure & Dashboard Configuration Checklist

These steps require administrative access to the Vercel, Render, and DNS registrar dashboards:

### 2.1 Vercel Dashboard Actions
- [ ] **Remediate Failing Project `resumematch_ai`**:
  - Open Vercel Dashboard -> Project `resumematch_ai`.
  - If redundant: Click **Settings** -> **Advanced** -> **Delete Project**.
  - If retaining: Click **Settings** -> **General** -> Change **Root Directory** from `.` to `frontend` -> Save.
- [ ] **Adjust Vercel Deployment Protection**:
  - In Vercel Project `frontend` -> **Settings** -> **Deployment Protection**:
  - For public access, configure protection settings so public users can access the application without SSO login prompts.
- [ ] **Configure Frontend Production Environment Variables**:
  - In Vercel Project `frontend` -> **Settings** -> **Environment Variables**:
    - `VITE_API_BASE_URL` = `https://api.resumematch.ai` (or `https://resumematch-ai-api-atil.onrender.com` during transition)
- [ ] **Bind Custom Domain**:
  - In Vercel Project `frontend` -> **Settings** -> **Domains**:
    - Add `app.resumematch.ai`.

### 2.2 Render Dashboard Actions
- [ ] **Verify Service Status**:
  - Open Render Dashboard -> Service `resumematch-ai-api` (`srv-dbspslmi0phs73dqbptg`).
  - Verify Build Command: `pip install -r requirements.txt`.
  - Verify Start Command: `gunicorn --worker-class sync --workers 2 --bind 0.0.0.0:$PORT wsgi:app`.
- [ ] **Set Production Environment Variables**:
  - `FLASK_ENV` = `production`
  - `SECRET_KEY` = `<GENERATE_CRYPTOGRAPHIC_HEX_KEY_64_CHARS>` (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`)
  - `CORS_ALLOWED_ORIGINS` = `https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app`
  - `PYTHON_VERSION` = `3.14.0` (or `3.11+`)
- [ ] **Bind Custom Domain**:
  - In Render Service -> **Settings** -> **Custom Domains**:
    - Add `api.resumematch.ai`.

### 2.3 DNS Registrar / Cloudflare Actions
- [ ] **Add CNAME Record for Frontend**:
  - Type: `CNAME` | Name: `app` | Target: `cname.vercel-dns.com` | Proxy: DNS only
- [ ] **Add CNAME Record for API**:
  - Type: `CNAME` | Name: `api` | Target: `resumematch-ai-api-atil.onrender.com` | Proxy: DNS only

---

## 3. Production Deployment & Merge Execution

Once cloud configurations and DNS records are staged:

- [ ] **Pull Request & Code Review**:
  - Create Pull Request: `fix/resumematch-final-repair` -> `main`.
  - Review release documentation in [reports/phase7/](file:///d:/skillsync1/reports/phase7/).
- [ ] **Merge to Main**:
  - Merge the pull request.
- [ ] **Trigger Production Builds**:
  - Trigger Vercel production deployment from `main` on project `frontend`.
  - Trigger Render manual deploy (Clear build cache & deploy) from `main` on service `srv-dbspslmi0phs73dqbptg`.

---

## 4. Post-Deployment Smoke Verification (Live Acceptance Testing)

Execute in Chromium (Chrome/Edge), Firefox, and Safari (macOS/iOS):

- [ ] **1. Public Health Check**:
  - Request `https://api.resumematch.ai/health` (or `https://resumematch-ai-api-atil.onrender.com/health`).
  - Expect: HTTP 200 `{"status": "healthy"}`.
- [ ] **2. CSRF & Session Initialization**:
  - Request `https://api.resumematch.ai/api/csrf-token` (or Render endpoint) with `credentials: include`.
  - Expect: HTTP 200, JSON `{ "csrf_token": "..." }`, Response Header `Set-Cookie: session=...; Secure; HttpOnly; SameSite=Lax`.
- [ ] **3. Frontend SPA Loading**:
  - Open `https://app.resumematch.ai` (or `https://frontend-harsha1704s-projects.vercel.app`).
  - Expect: React 19 UI renders without console errors or missing chunk errors.
- [ ] **4. End-to-End Resume Analysis Flow**:
  - Upload a standard `.pdf` or `.docx` resume (< 16 MB).
  - Paste a valid job description.
  - Click **Analyze**.
  - Expect:
    - Preflight `OPTIONS /api/analyze` returns HTTP 200 with `Access-Control-Allow-Origin`.
    - Request sends `X-CSRF-Token` header.
    - Processing succeeds; navigation redirects to `/results/:id`.
    - Multi-model scores render accurately.
- [ ] **5. Multi-Module Session Persistence Flow**:
  - Click **Skill Gap** -> Matched/missing skills display for active analysis.
  - Click **Interview Studio** -> Question sets generate successfully.
  - Click **Career Mentor** -> Role readiness dossier loads.
- [ ] **6. Browser Compatibility Sign-Off**:
  - Verify above steps in Chrome.
  - Verify above steps in Firefox.
  - Verify above steps in Safari / WebKit (confirms same-site cookie persistence under Apple ITP).

---

## 5. Rollback & Contingency Procedures

If any critical issue arises during live smoke verification:

1. **Frontend Rollback**:
   - In Vercel Dashboard -> **Deployments** -> Select previous stable deployment (`07b88a0`) -> Click **Promote to Production**.
2. **Backend Rollback**:
   - In Render Dashboard -> **Deploys** -> Select previous stable deploy (`07b88a0`) -> Click **Rollback**.
3. **Emergency Provider URLs**:
   - Set Vercel `VITE_API_BASE_URL=https://resumematch-ai-api-atil.onrender.com` if custom domain routing encounters DNS propagation delays.
