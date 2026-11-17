# RESUMEMATCH AI — PHASE 7.2: PRODUCTION DEPLOYMENT & INFRASTRUCTURE ARCHITECTURE

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
- **Option 2**: Vercel Reverse Proxy Rewriting to Render (`frontend.vercel.app/api/*` -> `onrender.com/api/*`).

### Recommended Architecture Decision: **OPTION 1 (Shared Apex Subdomains with Host-Only Cookie)**

Option 1 is the recommended production architecture. Directing browser API calls straight to the Render backend avoids serverless proxy payload ceilings and execution duration timeouts, while maintaining strong cookie isolation via host-only scoping.

---

## 2. Comparative Architectural Evaluation

| Dimension | Option 1: Shared Custom Apex Domain (`*.resumematch.ai`) [Recommended] | Option 2: Vercel Reverse Proxy (`vercel.json` Rewrites) |
| :--- | :--- | :--- |
| **Hosting Topology** | Frontend: `https://app.resumematch.ai` (Vercel)<br>Backend: `https://api.resumematch.ai` (Render) | Frontend: `https://frontend-harsha1704s-projects.vercel.app`<br>Backend: `https://resumematch-ai-api-atil.onrender.com` |
| **Site Relationship** | **Same-Site** (Shares apex registrable domain `resumematch.ai`) | **Same-Origin** (From browser perspective, proxied through Vercel) |
| **Cookie Architecture** | `SameSite=Lax`, `Secure=True`, `HttpOnly=True`.<br>**Host-only cookie** locked strictly to `api.resumematch.ai` (`SESSION_COOKIE_DOMAIN=None`). | Same-origin cookie handling. |
| **Browser Compatibility** | **High compatibility tested and expected** across Chromium, Firefox, and WebKit (Safari). In a same-site setup, browsers transmit `SameSite=Lax` cookies on credentialed API requests, avoiding third-party cookie blocking under Apple ITP. Actual behavior in all client environments is expected rather than universally guaranteed. | Compatible across standard browsers. |
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

### 3.2 Cookie Domain Security: Host-Only Cookie Policy

- **Recommended Production Policy**: **Host-Only Cookie** for `api.resumematch.ai`.
- **Configuration**:
  ```python
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SECURE = True
  SESSION_COOKIE_SAMESITE = "Lax"
  SESSION_COOKIE_DOMAIN = None  # Host-only: strictly bound to api.resumematch.ai
  ```
- **Security Rationale**:
  Omitting the `Domain` attribute (`SESSION_COOKIE_DOMAIN=None`) ensures that the browser locks the cookie strictly to `api.resumematch.ai`. No other subdomain (e.g. `blog.resumematch.ai` or staging environments) can access or tamper with the session cookie.
  Because `app.resumematch.ai` and `api.resumematch.ai` share the same registrable apex domain (`resumematch.ai`), browser requests with `credentials: 'include'` are **same-site**; browsers transmit `SameSite=Lax` cookies to `api.resumematch.ai` without cross-site third-party blocking.

### 3.3 Active Render Service Configuration

- **Actual Verified Deployed Start Command** (configured on Render service `srv-dbspslmi0phs73dqbptg`):
  ```bash
  gunicorn --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app
  ```
  *(1 worker with 2 threads prevents memory exhaustion on Render 512 MB free instances, while 120s timeout accommodates cold boots).*
- **Active Environment Variables**:
  ```bash
  RESUMEMATCH_ENV=production
  SECRET_KEY=<generate-strong-cryptographic-hex-secret-64chars>
  FRONTEND_ORIGINS=https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app
  SESSION_COOKIE_SAMESITE=Lax
  # SESSION_COOKIE_DOMAIN is omitted (defaults to None / host-only)
  MAX_CONTENT_LENGTH=16777216
  PORT=10000
  ```

### 3.4 Active Vercel Frontend Configuration

```bash
# Vercel Project 'frontend' Environment Variables
VITE_API_BASE_URL=https://api.resumematch.ai
```

---

## 4. Dual-Branch Cloud Deployment Sequence

Vercel tracks `main` while Render tracks `deploy/vercel-render-free`. To guarantee both services receive the identical approved release commit:

1. **Step 1: Merge to `main`**:
   - Merge `fix/resumematch-final-repair` into `main`.
   - Vercel automatically deploys `main` to project `frontend`.
2. **Step 2: Fast-Forward `deploy/vercel-render-free`**:
   - Update branch `deploy/vercel-render-free` to match `main`:
     ```bash
     git checkout deploy/vercel-render-free
     git merge main --ff-only
     git push origin deploy/vercel-render-free
     ```
   - Render automatically deploys `deploy/vercel-render-free` to service `srv-dbspslmi0phs73dqbptg`.
3. **Step 3: Commit SHA Audit**:
   - Verify both dashboards display the exact same Git commit hash.

---

## 5. Rollback Plan

If custom DNS propagation encounters delays during rollout:

1. **Emergency Fallback to Direct Provider URLs**:
   - Update Vercel frontend environment variable: `VITE_API_BASE_URL=https://resumematch-ai-api-atil.onrender.com`.
   - Ensure `FRONTEND_ORIGINS` includes `https://frontend-harsha1704s-projects.vercel.app` (already verified active).
   - Redeploy frontend on Vercel.
2. **Restoration**:
   - Once DNS records for `app.resumematch.ai` and `api.resumematch.ai` propagate, restore `VITE_API_BASE_URL=https://api.resumematch.ai`.
