# RESUMEMATCH AI — PHASE 7.1: PRODUCTION RELEASE & DEPLOYMENT CHECKLIST

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`, Branch: `main`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`, Branch: `deploy/vercel-render-free`)  
**Document Purpose**: Step-by-Step Dual-Branch Release Gate Checklist for System Administrators

---

## 1. Pre-Release Engineering Verification (All Verified)

- [x] **Branch Isolation Check**: Work committed strictly to `fix/resumematch-final-repair`. No uncommitted or unstaged changes.
- [x] **Backend Regression**: All 771 pytest tests pass cleanly (`py -3.14 -m pytest tests/ -q`).
- [x] **Phase 7.1 Production Readiness Suite**: All 20 tests pass cleanly (`py -3.14 -m pytest tests/test_phase7*.py -v`).
- [x] **Real Startup Tests**: Tested production startup in real subprocess with missing and insecure secrets; verified fail-closed `RuntimeError`.
- [x] **Real Production Cookie Headers**: Verified actual `Set-Cookie` response headers (`session=...; Secure; HttpOnly; SameSite=Lax; Domain=resumematch.ai`).
- [x] **Complete Route Inventory CSRF**: Verified missing token (403), invalid token (403), and valid token (pass) across all 17 state-changing routes.
- [x] **Real DOCX Archive Bomb**: Generated genuine 1000:1 ratio DOCX bomb; verified fail-closed rejection by validator and resume parser.
- [x] **Exceeded Rate Limiting**: Tested threshold exceeding (60 req/min) on `/api/match`; verified HTTP 429 with `Retry-After`.
- [x] **IDOR Reads & Mutations**: Verified unowned analysis reads (403) and unowned session mutations (create, submit, delete) return 403.
- [x] **Frontend Unit & Browser Suites**: All 14 tests pass across Chromium, Firefox, and WebKit (`npm test --prefix frontend`).
- [x] **Frontend Production Build**: `tsc -b && vite build` completes cleanly with 0 errors.
- [x] **Frontend Linting**: `oxlint` completes with 0 errors.

---

## 2. Cloud Infrastructure & Dashboard Configuration Checklist

### 2.1 Vercel Dashboard Actions (Project: `frontend`)
- [ ] **Adjust Vercel Deployment Protection**:
  - In Vercel Project `frontend` -> **Settings** -> **Deployment Protection**:
  - Disable Deployment Protection or configure public bypass so end-users can access without team SSO login.
- [ ] **Configure Frontend Production Environment Variables**:
  - In Vercel Project `frontend` -> **Settings** -> **Environment Variables**:
    - `VITE_API_BASE_URL` = `https://api.resumematch.ai`
- [ ] **Bind Custom Domain**:
  - In Vercel Project `frontend` -> **Settings** -> **Domains**:
    - Add `app.resumematch.ai`.
- [ ] **Remediate Secondary Failing Project `resumematch_ai`**:
  - Open Vercel Project `resumematch_ai` -> **Settings** -> **Advanced** -> Click **Delete Project**.

### 2.2 Render Dashboard Actions (Service: `resumematch-ai-api`)
- [ ] **Verify Service Spec**:
  - Build Command: `pip install -r requirements.txt`.
  - Start Command: `gunicorn --worker-class sync --workers 2 --bind 0.0.0.0:$PORT wsgi:app`.
- [ ] **Set Real Production Environment Variables**:
  - `RESUMEMATCH_ENV` = `production`
  - `SECRET_KEY` = `<GENERATE_CRYPTOGRAPHIC_HEX_KEY_64_CHARS>` (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`)
  - `FRONTEND_ORIGINS` = `https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app`
  - `SESSION_COOKIE_SAMESITE` = `Lax`
  - `SESSION_COOKIE_DOMAIN` = `.resumematch.ai` (or omit for host-only `None`)
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

## 3. Dual-Branch Deployment Sequence (Guarantees Same Commit)

Vercel tracks `main` while Render tracks `deploy/vercel-render-free`. To guarantee both services deploy the exact same release commit:

1. **Step 1: Merge Repair Branch to Main (Deploys Vercel)**:
   - Create Pull Request: `fix/resumematch-final-repair` $\rightarrow$ `main`.
   - Review and merge.
   - Vercel automatically deploys `main` to project `frontend`.
2. **Step 2: Fast-Forward Deploy Branch for Render (Deploys Render)**:
   - Synchronize branch `deploy/vercel-render-free` with `main`:
     ```bash
     git checkout deploy/vercel-render-free
     git pull origin deploy/vercel-render-free
     git merge main --ff-only  # or git merge main
     git push origin deploy/vercel-render-free
     ```
   - Render automatically detects the push to `deploy/vercel-render-free` and triggers deployment on `srv-dbspslmi0phs73dqbptg`.
3. **Step 3: Verify Deployment Commit Hash on Both Dashboards**:
   - Verify that Vercel Deployment lists commit SHA: `<RELEASE_COMMIT_SHA>`.
   - Verify that Render Deploy lists commit SHA: `<RELEASE_COMMIT_SHA>`.

---

## 4. Post-Deployment Smoke Verification (Live Acceptance Testing)

Execute in Chromium, Firefox, and Safari:

- [ ] **1. Public Health Check**:
  - Request `https://api.resumematch.ai/health`.
  - Expect: HTTP 200 `{"status": "healthy"}`.
- [ ] **2. CSRF & Session Initialization**:
  - Request `https://api.resumematch.ai/api/csrf-token` with `credentials: include`.
  - Expect: HTTP 200, JSON `{ "csrf_token": "..." }`, Response Header `Set-Cookie: session=...; Secure; HttpOnly; SameSite=Lax`.
- [ ] **3. Frontend SPA Loading**:
  - Open `https://app.resumematch.ai`.
  - Expect: React 19 UI renders without Vercel SSO login wall or missing chunk errors.
- [ ] **4. End-to-End Resume Analysis Flow**:
  - Upload sample `.pdf` or `.docx` resume (< 16 MB).
  - Paste job description.
  - Click **Analyze**.
  - Expect: Preflight `OPTIONS` succeeds; request sends `X-CSRF-Token`; redirects to `/results/:id`.
- [ ] **5. Multi-Module Session Persistence Flow**:
  - Navigate to **Skill Gap** -> Matched/missing skills render.
  - Navigate to **Interview Studio** -> Question sets generate.
  - Navigate to **Career Mentor** -> Role readiness dossier loads.
- [ ] **6. Cross-Browser Sign-Off**:
  - Verified in Chrome, Firefox, and Safari (confirms same-site cookie persistence under Apple ITP).

---

## 5. Rollback Procedures

1. **Frontend Rollback**:
   - In Vercel Dashboard -> **Deployments** -> Select previous stable deployment (`07b88a0`) -> Click **Promote to Production**.
2. **Backend Rollback**:
   - In Render Dashboard -> **Deploys** -> Select previous stable deploy (`07b88a0`) -> Click **Rollback**.
