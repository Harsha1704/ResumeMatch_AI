# RESUMEMATCH AI — PHASE 7.3: PRODUCTION DEPLOYMENT & INFRASTRUCTURE ARCHITECTURE

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`, Branch: `main`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`, Branch: `deploy/vercel-render-free`)  
**Audit Date**: November 17, 2026  
**Document Status**: Approved Final Architecture Specification

---

## 1. Executive Summary & Recommended Architecture

ResumeMatch AI is structured as a decoupled web application comprising:
1. **Frontend**: Modern Single-Page Application (React 19, Vite 8, TypeScript, Tailwind CSS v4) hosted on Vercel.
2. **Backend**: Python Flask REST API with scikit-learn machine learning inference pipelines hosted on Render.

To resolve the decoupling challenges between Vercel and Render (cross-origin cookies, CORS preflights, upload size limits, and browser tracking prevention), we evaluated two primary architectural options:
- **Option 1 (Recommended)**: Custom Subdomains on Shared Apex Domain (`app.resumematch.ai` + `api.resumematch.ai`) with a host-only cookie for `api.resumematch.ai`.
- **Option 2**: Vercel Reverse Proxy Rewriting to Render (`frontend.vercel.app/api/*` $\rightarrow$ `onrender.com/api/*`).

### Recommended Architecture Decision: **OPTION 1 (Shared Apex Subdomains with Host-Only Cookie)**

Option 1 is the recommended production architecture. Directing browser API calls straight to the Render backend avoids serverless proxy payload ceilings and execution duration timeouts, while maintaining strong cookie isolation via host-only scoping.

---

## 2. Comparative Architectural Evaluation

| Dimension | Option 1: Shared Custom Apex Domain (`*.resumematch.ai`) [Recommended] | Option 2: Vercel Reverse Proxy (`vercel.json` Rewrites) |
| :--- | :--- | :--- |
| **Hosting Topology** | Frontend: `https://app.resumematch.ai` (Vercel)<br>Backend: `https://api.resumematch.ai` (Render) | Frontend: `https://frontend-harsha1704s-projects.vercel.app`<br>Backend: `https://resumematch-ai-api-atil.onrender.com` |
| **Site Relationship** | **Same-Site** (Shares apex registrable domain `resumematch.ai`) | **Same-Origin** (From browser perspective, proxied through Vercel) |
| **Cookie Architecture** | `SameSite=Lax`, `Secure=True`, `HttpOnly=True`.<br>**Host-only cookie** locked strictly to `api.resumematch.ai` (`SESSION_COOKIE_DOMAIN=None`). | Same-origin cookie handling. |
| **Browser Compatibility** | **High compatibility tested and expected** across tested browser engines (Chromium 159.0, Firefox 159.0, and WebKit 27.2 WinCairo on Windows). In a same-site setup, browsers transmit `SameSite=Lax` cookies on credentialed API requests, avoiding third-party cookie blocking under Apple ITP. Findings are strictly limited to the tested browser versions and configurations and do not claim universal Safari or Firefox behavior. | Compatible across standard browsers. |
| **Payload Upload Capacity** | **Full 16 MB streaming** directly to Render Gunicorn worker ([app.py#L43](file:///d:/skillsync1/app.py#L43)). | Per [authoritative Vercel documentation](https://vercel.com/docs/concepts/limits/overview#serverless-function-limits), Serverless Function invocations enforce a **4.5 MB maximum request body payload limit**. Uploads of 16 MB documents fail when handled through serverless proxies. |
| **Inference Latency & Timeouts** | Render web services support persistent connections with Gunicorn timeout configured to **120 seconds** (`--timeout 120`). ML inference and cold starts run unhindered. | Per [Vercel Function documentation](https://vercel.com/docs/functions/runtimes#execution-duration), default function execution duration is capped at **10 seconds on Hobby** plans (15–60s on Pro). Long-running model inference risks HTTP 504 Gateway Timeouts. |
| **CORS Overhead** | Explicit allowlist in Flask (`FRONTEND_ORIGINS`). Standard CORS preflight with browser caching (`Access-Control-Max-Age: 86400`). | Zero browser CORS overhead, but proxy header rewrites required. |
| **Quota & Cost Efficiency** | Direct requests bypass Vercel serverless function invocations and double bandwidth consumption. | Every proxied API request consumes Vercel serverless function bandwidth and execution quotas. |
| **Failure Isolation** | Independent failure domains: frontend static assets remain accessible even if backend experiences heavy load. | Single point of failure: Vercel routing or function limits impact API availability even when Render is healthy. |

---

## 3. Option 1 Implementation Blueprint

### 3.1 Domain & DNS Topology

Assuming the registered domain is `resumematch.ai`:

```mermaid
flowchart TD
    User["End User Browser (Chrome / Safari / Firefox)"]
    DNS["DNS Registrar / Cloudflare DNS"]
    Vercel["Vercel Edge Network (app.resumematch.ai)"]
    Render["Render Web Service (api.resumematch.ai)"]
    
    User -->|1. HTTPS GET /| Vercel
    Vercel -->|2. Serves React 19 SPA Assets| User
    User -->|3. HTTPS POST /api/analyze (Up to 16MB)| Render
    Render -->|4. ML Inference & Host-Only Same-Site Cookie| User
```

#### Required DNS Records

| Record Type | Host / Name | Target / Value | TTL | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **CNAME** | `app` | `cname.vercel-dns.com` | Auto / 300 | Routes frontend traffic to Vercel |
| **CNAME** | `api` | `resumematch-ai-api-atil.onrender.com` | Auto / 300 | Routes API traffic to Render |
| **TXT / ALIAS** | `@` (Apex) | As directed by DNS provider | Auto | Domain apex verification |

### 3.2 Cookie Domain Security: Enforced Host-Only Cookie Policy

- **Enforced Production Policy**: **Host-Only Cookie** for `api.resumematch.ai`.
- **Configuration ([app.py#L51-L69](file:///d:/skillsync1/app.py#L51-L69))**:
  ```python
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SECURE = True
  SESSION_COOKIE_SAMESITE = "Lax"
  SESSION_COOKIE_DOMAIN = None  # Host-only: strictly bound to api.resumematch.ai
  ```
- **Security Rationale**:
  Omitting the `Domain` attribute (`SESSION_COOKIE_DOMAIN=None`) ensures that the browser locks the cookie strictly to the receiving API origin. Sibling subdomains (such as `app.resumematch.ai`, staging sites, or user content domains) can never access or receive the session cookie.
  Because `app.resumematch.ai` and `api.resumematch.ai` share the same registrable apex domain (`resumematch.ai`), browser requests with `credentials: 'include'` are classified by browsers as **same-site**; browsers transmit `SameSite=Lax` cookies to `api.resumematch.ai` without cross-site third-party blocking under WebKit/Safari ITP. The backend verifies the cryptographically signed session cookie against `SECRET_KEY` on each request without requiring cookie decryption (Flask default session cookies are cryptographically signed with HMAC-SHA256, not encrypted).

### 3.3 Active Render Service Configuration

- **Actual Verified Deployed Start Command** (configured on Render service `srv-dbspslmi0phs73dqbptg` and reconciled in [render.yaml](file:///d:/skillsync1/render.yaml)):
  ```bash
  gunicorn --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app
  ```
  *(1 worker with 2 threads prevents memory exhaustion on Render 512 MB free instances, while 120s timeout accommodates cold boots).*
- **Environment Variables & Render Blueprint Synchronization**:
  - `RESUMEMATCH_ENV`: `production` (promoted only after custom domains and routing are operational)
  - `SECRET_KEY`: `<high-entropy-random-secret-64chars>`
  - `FRONTEND_ORIGINS`:
    - Value in `render.yaml` and Production Dashboard: `https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app,https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app`
    - Preserves both verified live Vercel rollback origins (`https://frontend-harsha1704s-projects.vercel.app` and `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app`) alongside the target custom domain `https://app.resumematch.ai`.
    - **Blueprint Synchronization Semantics**: In Render, blueprint synchronizations can overwrite dashboard environment variables with values specified in `render.yaml`. Reconciling `render.yaml` to declare all three origins guarantees that dashboard changes (made in Step 5 before code deployment) will not be overwritten or regressed when the release commit is eventually deployed via Git/Blueprint in Step 9.
  - `SESSION_COOKIE_SAMESITE`: `Lax` (enforced at startup; overrides rejected in production)
  - `SESSION_COOKIE_DOMAIN`: Omitted / not set (app.py strictly enforces `None` in production)

### 3.4 Four-Part Verification Boundary & Mandatory Deployment Ordering

1. **Simulated Same-Site Browser Tests (`.test` Domains)**: Proves RFC 6265bis same-site cookie transport, host-only scoping, CORS preflight correlation, and server-side unauthorized mutation rejection via local HTTPS and CONNECT proxy across tested browser engines. Does NOT indicate that `app.resumematch.ai` or `api.resumematch.ai` are already registered or live on the public Internet.
2. **Actual DNS & TLS Verification**: Confirms public registrar CNAME routing and valid public CA TLS certificates.
3. **Sequential Staged Deployment**:
   - Vercel frontend is updated with `VITE_API_BASE_URL=https://api.resumematch.ai` and deployed to `app.resumematch.ai` FIRST.
   - Render backend release commit (enforcing `SameSite=Lax` and host-only cookies in `RESUMEMATCH_ENV=production`) is pushed to `deploy/vercel-render-free` ONLY AFTER the frontend is verified live and operational on the custom domain.
4. **Vercel Rebuild Requirement**: Changing `VITE_API_BASE_URL` requires an explicit Vercel **Redeploy** (or merging to `main`) to compile the new base URL into client static assets.
5. **Live Acceptance Smoke Testing**: Verifies real-browser flows before and after promoting Render backend.
6. **Optional Administrative Actions**: Maintenance on secondary project `resumematch_ai` or Vercel Deployment Protection are optional administrative choices requiring explicit owner authorization, not release blockers.

### 3.5 Safe Rollback Architecture & Protocol Distinctions

If rollback to the legacy cross-site topology becomes necessary:
1. **Protocol Distinctions**:
   - **CORS vs. Cookies**: Preserving `FRONTEND_ORIGINS` satisfies HTTP preflight checks, but **does NOT** permit cookie access or circumvent browser third-party cookie blocking.
   - **CORS Response Blocking vs. Server-Side Mutation Rejection**: CORS is a client-side browser policy that prevents unauthorized JavaScript from reading responses. In contrast, server-side CSRF validation independently inspects requests and actively rejects unauthorized mutations (HTTP 403 Forbidden), guaranteeing that application state cannot be modified regardless of client CORS handling.
   - **SameSite Compatibility**: The production backend enforces `SameSite=Lax`. Cross-site sub-resource requests drop `SameSite=Lax` cookies, breaking CSRF and sessions.
   - **Browser Privacy Controls**: Safari/WebKit (ITP) and Firefox block third-party cookies on cross-site requests. **The legacy cross-site architecture is NOT a guaranteed Safari-compatible rollback**, as cross-site third-party cookie restrictions under WebKit ITP can strictly block session persistence on cross-site domains.
2. **Effective Fallback Configuration (Commit 07b88a058f166f13491fa9050ba835d95fd0e8fd)**:
   - Baseline code sets: `SESSION_COOKIE_SAMESITE = "None" if APP_ENV == "production" else "Lax"`, `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_DOMAIN = None`.
   - **Environment Variables Do Not Revert with Git Commits**: Administrators must verify Render service environment variables (`RESUMEMATCH_ENV=production`, `FRONTEND_ORIGINS` containing verified Vercel URLs).
3. **Mandatory Rollback Ordering**:
   - **Step 1**: Freeze promotion and preserve working custom-domain state wherever possible.
   - **Step 2**: Revert the Render backend to baseline commit `07b88a058f166f13491fa9050ba835d95fd0e8fd` on `deploy/vercel-render-free` FIRST and verify `/health` and `SameSite=None; Secure` cookie headers.
   - **Step 3**: Only after backend rollback is healthy, revert `VITE_API_BASE_URL` on Vercel and redeploy the frontend.
   - **Step 4**: Verify session initiation, CSRF, uploads, and mutations on the reverted deployment in Chromium, Firefox, and Safari.
4. **Transition Outage Risk**: Because Vercel and Render deploy independently without distributed two-phase commit, any non-atomic switch between same-site and cross-site carries an inherent temporary window of session failure until both services complete deployment.
