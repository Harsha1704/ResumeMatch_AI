# RESUMEMATCH AI — PHASE 7.3: PRODUCTION RELEASE & DEPLOYMENT CHECKLIST

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`, Branch: `main`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`, Branch: `deploy/vercel-render-free`)  
**Document Purpose**: Definitive Step-by-Step Dual-Branch Release Gate Checklist for System Administrators

---

## 1. Classification & Verification Boundaries

To prevent conflation of local testing with live production readiness, all release verifications are divided into four strict categories:

1. **Simulated Same-Site Browser Tests (`.test` Domains)**:
   - Validates RFC 6265bis cookie transmission and Web platform mechanics in real Chromium, Firefox, and WebKit browser engines via local HTTPS servers and a CONNECT proxy.
   - **Constraint**: Proves that the architecture is sound under web platform specifications. It **does NOT** prove that `app.resumematch.ai` and `api.resumematch.ai` are currently active, registered, or operational on the Internet.
2. **Actual DNS and TLS Verification (Cloud & Registrar)**:
   - Verification of domain registrar ownership, DNS CNAME resolution (`cname.vercel-dns.com` and `resumematch-ai-api-atil.onrender.com`), and valid public CA-signed TLS certificate issuance (Let's Encrypt / DigiCert).
3. **Actual Vercel & Render Deployment Verification (Dual-Branch)**:
   - Verification of commit SHA synchronization across Vercel (`main`) and Render (`deploy/vercel-render-free`), service health, start commands, and build logs.
4. **Live Production Acceptance Testing (Real Browsers on Live Domains)**:
   - End-to-end user flows (session initiation, CSRF tokens, host-only cookies, candidate/mentor mutations, resume uploads, authorized analysis retrieval, dashboard) tested directly against public URLs.

---

## 2. Pre-Release Engineering Verification (All Codebase Items Passed)

- [x] **Branch Isolation Check**: Work committed strictly to `fix/resumematch-final-repair`. No uncommitted or unstaged changes.
- [x] **Backend Regression**: All 771 pytest tests pass cleanly (`py -3.14 -m pytest tests/ -q`).
- [x] **Phase 7 Production Readiness Suite**: All 20 tests pass cleanly (`py -3.14 -m pytest tests/test_phase7*.py -v`).
- [x] **Real Startup Tests**: Tested production startup in real subprocess with missing and insecure secrets; verified fail-closed `RuntimeError`.
- [x] **Host-Only Production Cookie Enforcement**: Verified that `SESSION_COOKIE_DOMAIN` cannot be configured in production (fails closed with `RuntimeError`). Verified actual `Set-Cookie` response headers (`session=...; Secure; HttpOnly; SameSite=Lax`) with **no Domain attribute** (host-only cookie locked strictly to API origin). Verified credentialed mutations and queries succeed.
- [x] **Production SameSite=Lax Enforcement**: Verified that `SESSION_COOKIE_SAMESITE` must be `Lax` in production; conflicting overrides (`None`, `Strict`, `invalid`) fail closed at startup with `RuntimeError`.
- [x] **Simulated Same-Site Subdomain Browser Tests**: Tested across separate HTTPS origins (`app.resumematch.test` and `api.resumematch.test`) via local CONNECT proxy in tested engines (Chromium 159.0, Firefox 159.0, WebKit 27.2 WinCairo on Windows; findings strictly limited to tested configurations, not claiming universal Safari or Firefox behavior). Verified CSRF token retrieval, raw HTTP `Set-Cookie` attributes, host-only scoping, mutation success, session continuity, sibling isolation, uncredentialed rejection, disallowed origin read rejection, genuine unauthorized-origin state-changing mutation rejection via real page navigation on an unapproved HTTPS server (`https://unauthorized.external.test:8444`), and genuine unapproved same-site sibling origin security enforcement (`https://evil.resumematch.test:8445`). Proved same-site Lax cookie transmission under RFC 6265bis, verified signed session cookie receipt, server-side fail-closed CSRF rejection (HTTP 403), isolated CORS preflight rejection, and state preservation.
- [x] **Simulated Cross-Origin Browser Tests**: Tested cross-origin interactions in Chromium, Firefox, and WebKit with correlated CDP preflight verification.
- [x] **Complete Route Inventory CSRF**: Verified missing token (403), invalid token (403), and valid token (pass) across all 17 state-changing routes.
- [x] **Real DOCX Archive Bomb**: Generated genuine 1000:1 ratio DOCX bomb; verified fail-closed rejection by validator and resume parser.
- [x] **Exceeded Rate Limiting**: Tested threshold exceeding (60 req/min) on `/api/match`; verified HTTP 429 with `Retry-After`.
- [x] **IDOR Reads & Mutations**: Verified unowned analysis reads (403) and unowned session mutations (create, submit, delete) return 403.
- [x] **Combined Frontend Test Suite**: All 17 tests pass across unit and browser suites (`npm test --prefix frontend`).
- [x] **Frontend Production Build**: `tsc -b && vite build` completes cleanly with 0 errors.
- [x] **Frontend Linting**: `oxlint` completes with 0 errors.

---

## 3. Mandatory Cloud Deployment & Release Ordering Sequence

> [!CAUTION]
> **CRITICAL RELEASE GATE: STRICT RELEASE SEQUENCING REQUIRED TO PREVENT DOWNTIME**
> Modern browsers (Chromium, Firefox, Safari/WebKit) strictly drop `SameSite=Lax` cookies on cross-site fetch sub-resource requests (`vercel.app` $\rightarrow$ `onrender.com`).
> `render.yaml` declares `RESUMEMATCH_ENV: production`. Pushing the new release commit to branch `deploy/vercel-render-free` triggers an **immediate, automatic build and deployment on Render** that enforces `SameSite=Lax` and host-only cookies.
> **Failure Mode Prevented by this Sequence**:
> If the backend release is pushed before the frontend custom domain is active and serving the updated `VITE_API_BASE_URL=https://api.resumematch.ai`, any user on the live frontend will immediately experience an outage where all mutations (`POST /api/candidate/update-role`), uploads (`POST /api/analyze`), and authorized sessions fail closed with `HTTP 403 Forbidden` (`CSRF token missing or invalid`).
>
> **MANDATORY RELEASE RULE**:
> Do NOT push or fast-forward the new release commit to `deploy/vercel-render-free` until Steps 3.1 through 3.8 are fully operational and verified.

### Step 3.1: Verify Domain Ownership & Configure DNS Records
- [ ] **Verify Ownership**: Confirm administrative control over `resumematch.ai` at DNS registrar / Cloudflare.
- [ ] **Configure Frontend CNAME Record**:
  - Type: `CNAME` | Host / Name: `app` | Target: `cname.vercel-dns.com` | Proxy: DNS only (TTL: 300s)
- [ ] **Configure Backend CNAME Record**:
  - Type: `CNAME` | Host / Name: `api` | Target: `resumematch-ai-api-atil.onrender.com` | Proxy: DNS only (TTL: 300s)
- [ ] **DNS Propagation Check**:
  - `dig CNAME app.resumematch.ai +short` $\rightarrow$ resolves to `cname.vercel-dns.com`
  - `dig CNAME api.resumematch.ai +short` $\rightarrow$ resolves to `resumematch-ai-api-atil.onrender.com`

### Step 3.2: Bind Custom Subdomain to Existing Vercel Frontend Project
- [ ] In Vercel Project `frontend` $\rightarrow$ **Settings** $\rightarrow$ **Domains**:
  - Add `app.resumematch.ai` as a Production Domain.
  - Wait for Vercel DNS status indicator to show valid assignment (green checkmark).

### Step 3.3: Bind Custom Subdomain to Existing Render Backend Service
- [ ] In Render Service `resumematch-ai-api` (`srv-dbspslmi0phs73dqbptg`) $\rightarrow$ **Settings** $\rightarrow$ **Custom Domains**:
  - Add `api.resumematch.ai`.
- [ ] **Confirm Verified Service Spec**:
  - Start Command: `gunicorn --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app` (reconciled in `render.yaml`).
  - Build Command: `pip install -r requirements.txt`.

### Step 3.4: Verify Public TLS Certificates on Both Domains
- [ ] **Verify Frontend TLS**:
  - Request `https://app.resumematch.ai/` via curl or browser.
  - Expect: Valid public CA-signed TLS certificate (issued to `app.resumematch.ai` / `*.resumematch.ai`).
- [ ] **Verify Backend TLS**:
  - Request `https://api.resumematch.ai/health` via curl.
  - Expect: Valid public CA-signed TLS certificate and HTTP 200 `{"status": "healthy"}`.

### Step 3.5: Configure Render CORS Allowed Origins (Preserving Rollback Origins)
- [ ] In Render Service `resumematch-ai-api` $\rightarrow$ **Environment**:
  - Update `FRONTEND_ORIGINS` to include the custom domain while preserving the existing verified Vercel origins:
    ```env
    FRONTEND_ORIGINS=https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app,https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app
    ```
  - Save environment variable. Render executes a rolling restart of the *current* running backend without deploying the new branch yet.
  - *Blueprint Synchronization Semantics*: In Render, blueprint synchronizations can overwrite dashboard environment variables with values specified in `render.yaml`. To eliminate configuration drift, `render.yaml` declares these exact same three origins. When the backend release is subsequently deployed via Blueprint/Git, the declared origins match identically, ensuring the eventual Render deployment retains all three origins without overwriting dashboard settings.

### Step 3.6: Configure Vercel API Base URL
- [ ] In Vercel Project `frontend` $\rightarrow$ **Settings** $\rightarrow$ **Environment Variables**:
  - Set `VITE_API_BASE_URL` = `https://api.resumematch.ai` (Target: Production).

### Step 3.7: Deploy Frontend Release & Verify Live API Routing
- [ ] **Merge Repair Branch to `main` (Triggers Vercel Production Build)**:
  - Create and merge Pull Request: `fix/resumematch-final-repair` $\rightarrow$ `main`.
  - Vercel automatically builds `main` with `VITE_API_BASE_URL=https://api.resumematch.ai` and deploys to `app.resumematch.ai`.
- [ ] **Verify Deployed JavaScript & Routing**:
  - Inspect production bundle on `https://app.resumematch.ai` via browser devtools Network tab.
  - Confirm API requests are dispatched to `https://api.resumematch.ai/*` (not the old `*.onrender.com` URL).
  - Confirm CORS preflight `OPTIONS https://api.resumematch.ai/api/csrf-token` receives:
    - `Access-Control-Allow-Origin: https://app.resumematch.ai`
    - `Access-Control-Allow-Credentials: true`

### Step 3.8: Real-Browser Acceptance Tests Against Custom Domains (Pre-Backend Promotion)
While Render is still running the existing backend commit/configuration, execute the full workflow on `https://app.resumematch.ai`:
- [ ] **1. CSRF Token & Session Retrieval**: `GET https://api.resumematch.ai/api/csrf-token` with `credentials: include` returns 200 OK.
- [ ] **2. Candidate Role Mutation**: `POST /api/candidate/update-role` succeeds with 200 OK.
- [ ] **3. Session Continuity**: `POST /api/mentor/update-name` succeeds with 200 OK in the same session.
- [ ] **4. Multipart Resume Upload**: `POST /api/analyze` succeeds with 200 OK and returns valid `analysis_id`.
- [ ] **5. Authorized Analysis Retrieval**: `GET /api/analysis/<analysis_id>` returns 200 OK.
- [ ] **6. Dashboard Access**: `GET /api/dashboard` returns 200 OK.

### Step 3.9: Promote Backend Release Enforcing Production SameSite=Lax & Host-Only Cookies
- [ ] **ONLY after Steps 3.1 through 3.8 have completely passed and verified**:
  - Fast-forward / merge `main` into `deploy/vercel-render-free` and push to GitHub:
    ```bash
    git checkout deploy/vercel-render-free
    git merge main --ff-only  # or git merge main
    git push origin deploy/vercel-render-free
    ```
  - Render automatically detects the push to `deploy/vercel-render-free` and deploys the new release commit containing the hardened `app.py` (`SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_DOMAIN=None`, fail-closed guards).
- [ ] **Verify Deployment Commit & Startup Logs on Render Dashboard**:
  - Confirm Render service `resumematch-ai-api` deployment shows commit SHA: `<RELEASE_COMMIT_SHA>`.
  - Confirm Render logs show clean Gunicorn startup with no `RuntimeError`.

### Step 3.10: Repeat Real-Browser Acceptance Suite on Live Production Backend
Repeat all acceptance checks from Step 3.8 on `https://app.resumematch.ai` across Chromium, Firefox, and Safari:
- [ ] **1. Cookie Header Inspection**: Confirm response header `Set-Cookie: session=...; Secure; HttpOnly; SameSite=Lax` with **no Domain attribute** (host-only).
- [ ] **2. Sibling Subdomain Isolation**: Confirm `app.resumematch.ai` has no session cookies from `api.resumematch.ai`.
- [ ] **3. Full User Flow**: Execute complete candidate profile update, mentor profile update, resume upload, analysis inspection, and dashboard telemetry.
- [ ] **4. Production Stability**: Verify zero 403 Forbidden errors across all credentialed workflows.

---

## 4. Optional Administrative Actions (Requiring Explicit Owner Authorization)

These items are **not prerequisites** for the ResumeMatch AI frontend release and must not be executed without explicit owner approval:

1. **Secondary Vercel Project (`resumematch_ai`)**:
   - Status: A separate, non-functional project that historically attempted to package the root repository into an AWS Lambda function (`LAMBDA_SIZE_EXCEEDED`).
   - Impact on Release: None. The active frontend is hosted by the distinct Vercel project named `frontend`.
   - Recommended Action: Owner may optionally delete or reconfigure `resumematch_ai` in the Vercel dashboard as an administrative hygiene action.
2. **Vercel Deployment Protection & Authentication**:
   - Explanation of Architecture: On Vercel, "Deployment Protection" (Vercel Authentication) is typically configured to protect Preview deployments with team SSO, while the assigned Production Custom Domain (`app.resumematch.ai`) serves public end-users directly without authentication gates.
   - Security Policy: Access controls should **not** be disabled or bypassed globally. Administrators should verify whether `https://app.resumematch.ai` is publicly reachable as a Production Domain before modifying any project-wide security settings.

---

## 5. Safe Rollback Procedure & Architectural Risk Analysis

If custom domain DNS, TLS, or routing fails during deployment and rollback is necessary:

### 5.1 Critical Distinction Between Protocol Dimensions
When planning or executing a rollback, administrators must clearly distinguish between four independent protocol layers:
1. **CORS Origin Compatibility**: HTTP `Access-Control-Allow-Origin` allows the client browser to read API responses. Preserving verified Vercel origins in `FRONTEND_ORIGINS` allows cross-origin requests to pass CORS preflights, but **does NOT** permit cookie access or bypass browser third-party cookie restrictions.
2. **Cookie SameSite Compatibility**: The Phase 7.3 production backend strictly enforces `SameSite=Lax`. Cross-site requests between `*.vercel.app` and `*.onrender.com` strictly drop `SameSite=Lax` cookies in modern browsers.
3. **Browser Third-Party Cookie Restrictions & Safari Incompatibility**: Browsers (especially Apple Safari / WebKit under Intelligent Tracking Prevention, and Firefox under Total Cookie Protection) partition or block third-party cookies on cross-site sub-resource requests regardless of CORS headers. **The legacy cross-site architecture is NOT a guaranteed Safari-compatible rollback**, as cross-site third-party cookie restrictions under WebKit ITP can strictly block session persistence on cross-site domains.
4. **Session & CSRF Compatibility**: Flask signed session cookies store the CSRF synchronizer token and user identity. The backend verifies the cryptographic signature (HMAC-SHA256) of the signed session cookie without requiring decryption. If browser cookie transmission fails, all state-changing endpoints (`POST /api/candidate/update-role`, `POST /api/analyze`) fail closed with HTTP 403 Forbidden.

### 5.2 Verification of Effective Fallback Configuration (Commit 07b88a058f166f13491fa9050ba835d95fd0e8fd)
Reverting the Git branch `deploy/vercel-render-free` to baseline commit `07b88a058f166f13491fa9050ba835d95fd0e8fd` restores the legacy code:
- `SESSION_COOKIE_SAMESITE = "None" if APP_ENV == "production" else "Lax"`
- `SESSION_COOKIE_SECURE = True`
- `SESSION_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_DOMAIN = None`

> [!IMPORTANT]
> **ENVIRONMENT VARIABLES DO NOT REVERT WITH GIT COMMITS**
> Reverting a commit in Git does NOT revert dashboard environment variables on Render. Administrators must verify the Render service environment variables:
> - `RESUMEMATCH_ENV`: must be `production` (triggers `SESSION_COOKIE_SECURE=True` and `SameSite=None` in baseline code).
> - `FRONTEND_ORIGINS`: must retain `https://frontend-harsha1704s-projects.vercel.app,https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app`.
> - `SESSION_COOKIE_SAMESITE`: if explicitly set in the Render dashboard during Phase 7 testing, ensure it does not conflict with the baseline code.

### 5.3 Observed Fallback Cookie Behavior Across Browsers:
- **Chromium (159.0)**: Accepts `SameSite=None; Secure` cookies cross-site provided third-party cookies are enabled.
- **Firefox (159.0)**: Accepts `SameSite=None; Secure` cookies under standard ETP, but partitions under strict privacy modes.
- **WebKit (27.2 / Safari)**: Subject to Intelligent Tracking Prevention (ITP). Third-party cookies on cross-site requests (`*.vercel.app` $\rightarrow$ `*.onrender.com`) are frequently blocked or dropped. **The legacy architecture is NOT guaranteed to work for Safari users.**

### 5.4 Mandatory Rollback Sequencing

> [!WARNING]
> **TEMPORARY OUTAGE RISK DURING NON-ATOMIC TRANSITIONS**
> Because Vercel (frontend) and Render (backend) are decoupled platforms lacking distributed two-phase commit, rolling back between same-site and cross-site topologies cannot occur instantaneously. If the frontend is reverted to the old API URL while the backend is still running the production SameSite=Lax release, cross-site fetch calls will drop cookies and fail with 403 Forbidden.
> **The backend release/configuration MUST be reverted and healthy BEFORE the frontend API URL is restored.**

1. **Step 1: Freeze Promotion & Preserve Working State**:
   - Immediately halt further promotion steps.
   - If the custom-domain deployment (`app.resumematch.ai` $\rightarrow$ `api.resumematch.ai`) is functional, preserve it rather than initiating a disruptive rollback.
2. **Step 2: Revert Backend Release & Verify Environment Variables First**:
   - Revert branch `deploy/vercel-render-free` to baseline commit `07b88a058f166f13491fa9050ba835d95fd0e8fd` and push to GitHub.
   - Verify Render environment variables (`RESUMEMATCH_ENV=production`, `FRONTEND_ORIGINS` containing verified Vercel URLs).
   - Wait for Render deployment to complete on `srv-dbspslmi0phs73dqbptg`.
3. **Step 3: Verify Backend Health & Effective Cookie Headers on Render Domain**:
   - Request `GET https://resumematch-ai-api-atil.onrender.com/health` via curl; verify HTTP 200 OK.
   - Inspect response headers on `GET /api/csrf-token`: verify `Set-Cookie` contains `SameSite=None; Secure; HttpOnly`.
4. **Step 4: Restore Frontend API URL & Redeploy Vercel**:
   - In Vercel Project `frontend` $\rightarrow$ **Settings** $\rightarrow$ **Environment Variables**:
     Set `VITE_API_BASE_URL` back to `https://resumematch-ai-api-atil.onrender.com`.
   - Trigger an explicit **Redeploy** on Vercel so Vite compiles client assets with the fallback API base URL.
5. **Step 5: Verify Fallback User Workflows in Real Browsers**:
   - On the fallback frontend URL, test session initiation (`GET /api/csrf-token`), candidate role mutation, mentor name continuity, multipart resume upload, authorized analysis retrieval, and dashboard access.
   - Note: In Safari/WebKit, cross-site cookie restrictions can still prevent session continuity in the legacy architecture.
6. **Step 6: Preserve Security Invariants**:
   - Never disable CSRF token validation.
   - Never disable session ownership or IDOR checks.
   - Never downgrade HttpOnly or Secure cookie attributes.
   - Never disable or weaken production SameSite=Lax on the custom-domain architecture.
