# RESUMEMATCH AI — PHASE 7: PRODUCTION DEPLOYMENT & INFRASTRUCTURE ARCHITECTURE

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`)  
**Audit Date**: November 17, 2026  
**Document Status**: Approved Final Architecture Specification

---

## 1. Executive Summary & Production Architecture Decision

ResumeMatch AI is structured as a decoupled web application comprising:
1. **Frontend**: Modern Single-Page Application (React 19, Vite 8, TypeScript, Tailwind CSS v4) hosted on Vercel.
2. **Backend**: Python Flask REST API with scikit-learn machine learning inference pipelines hosted on Render.

To resolve the decoupling challenges between Vercel and Render (cross-origin cookies, CORS preflights, upload size limits, and browser tracking prevention), we evaluated two primary architectural options:
- **Option 1**: Custom Subdomains on Shared Apex Domain (`app.resumematch.ai` + `api.resumematch.ai`).
- **Option 2**: Vercel Reverse Proxy Rewriting to Render (`frontend.vercel.app/api/*` -> `onrender.com/api/*`).

### Definitive Architecture Decision: **OPTION 1 (Shared Apex Subdomains)**

Option 1 is definitively chosen. Option 2 has fatal infrastructure limitations (a hard 4.5 MB request body limit on Vercel proxy functions and a 10-second timeout ceiling) that break ResumeMatch AI's core functionality (16 MB resume uploads and ML inference).

---

## 2. Comprehensive Architectural Comparison

| Dimension | Option 1: Shared Custom Apex Domain (`*.resumematch.ai`) | Option 2: Vercel Reverse Proxy (`vercel.json` Rewrites) |
| :--- | :--- | :--- |
| **Hosting Topology** | Frontend: `https://app.resumematch.ai` (Vercel)<br>Backend: `https://api.resumematch.ai` (Render) | Frontend: `https://frontend-harsha1704s-projects.vercel.app`<br>Backend: `https://resumematch-ai-api-atil.onrender.com` |
| **Site Relationship** | **Same-Site** (Shares apex eTLD+1 `resumematch.ai`) | **Same-Origin** (From browser perspective, proxied through Vercel) |
| **Cookie Architecture** | `SameSite=Lax`, `Secure=True`, `HttpOnly=True`.<br>Sent by all browsers on same-site cross-subdomain requests. | Same-origin cookie handling. |
| **Browser Compatibility** | **100% universal across Chromium, Firefox, Safari/WebKit, and iOS WebKit** without relying on third-party cookie concessions. | 100% universal across browsers. |
| **File Upload Capacity** | **Full 16 MB streaming** directly to Render Gunicorn worker ([app.py#L42](file:///d:/skillsync1/app.py#L42)). | **CRITICAL FAILURE**: Vercel Serverless Function & Edge proxy enforces a hard **4.5 MB body limit**. Uploads > 4.5 MB abort with HTTP 413. |
| **Inference Latency & Timeouts** | Render allows long-running requests (up to 120s+ timeout in Gunicorn). Cold starts and heavy ML models run without interruption. | **CRITICAL FAILURE**: Vercel Hobby proxy aborts requests after **10 seconds** (HTTP 504 Gateway Timeout). Render cold start + model inference triggers 504. |
| **CORS Overhead** | Standard CORS with browser caching (`Access-Control-Max-Age: 86400`). Handled cleanly in Flask. | Zero browser CORS overhead, but proxy header rewrites required. |
| **Cost & Quota Efficiency** | Direct requests bypass Vercel serverless execution limits. Minimal free-tier bandwidth overhead. | Every API call consumes Vercel serverless execution time and double bandwidth. |
| **Failure Domains** | Independent: frontend static assets serve even if backend experiences high load. | Single point of failure: Vercel proxy issues take down API even if Render backend is healthy. |

---

## 3. Option 1 Implementation Blueprint

### 3.1 Domain & DNS Topology

Assuming the registered domain is `resumematch.ai` (or user's chosen custom domain):

```mermaid
flowchart TD
    User["End User Browser (Chrome / Safari / Firefox)"]
    DNS["DNS Provider (Cloudflare / Namecheap / Route 53)"]
    Vercel["Vercel Edge Network (app.resumematch.ai)"]
    Render["Render Web Service (api.resumematch.ai)"]
    
    User -->|1. HTTPS GET /| Vercel
    Vercel -->|2. Serves React 19 SPA Assets| User
    User -->|3. HTTPS POST /api/analyze (Up to 16MB)| Render
    Render -->|4. ML Inference & Same-Site Session Cookie| User
```

#### Required DNS Records

| Record Type | Host / Name | Target / Value | TTL | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **CNAME** | `app` | `cname.vercel-dns.com` | Auto / 300 | Routes frontend traffic to Vercel |
| **CNAME** | `api` | `resumematch-ai-api-atil.onrender.com` | Auto / 300 | Routes API traffic to Render |
| **TXT / ALIAS** | `@` (Apex) | As directed by DNS provider | Auto | Domain apex verification |

### 3.2 SSL / TLS Certificate Automation
- **Vercel (`app.resumematch.ai`)**: Vercel automatically provisions and renews Let's Encrypt certificates via ALPN/DNS-01.
- **Render (`api.resumematch.ai`)**: Render automatically provisions and renews Let's Encrypt certificates upon CNAME verification. Zero manual certificate management required.

### 3.3 Backend Configuration ([app.py](file:///d:/skillsync1/app.py))

1. **CORS Configuration**:
   ```python
   CORS_ALLOWED_ORIGINS = [
       "https://app.resumematch.ai",
       "https://frontend-harsha1704s-projects.vercel.app",
       "https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app",
       "http://localhost:5173",
       "http://127.0.0.1:5173"
   ]
   ```
2. **Session Cookie Attributes**:
   ```python
   app.config.update(
       SESSION_COOKIE_HTTPONLY=True,
       SESSION_COOKIE_SECURE=True,
       SESSION_COOKIE_SAMESITE="Lax",
       SESSION_COOKIE_DOMAIN=None,  # Bound to api.resumematch.ai
       PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
       MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16 MB
   )
   ```

### 3.4 Frontend Configuration ([frontend/.env.production](file:///d:/skillsync1/frontend/.env.production))

```bash
VITE_API_BASE_URL=https://api.resumematch.ai
```

---

## 4. Vercel Project Remediation Plan (`resumematch_ai`)

### 4.1 Root Cause of Current Failure
The failed project `resumematch_ai` on Vercel is failing with `LAMBDA_SIZE_EXCEEDED` (732.81 MB vs 500 MB limit) because its **Root Directory** in Vercel settings is set to `.`. This causes Vercel to invoke `@vercel/python`, packaging all Python packages (`scikit-learn`, `numpy`, `scipy`, `matplotlib`) into a serverless function.

### 4.2 Administrative Resolution Steps
1. Navigate to the **Vercel Dashboard**.
2. Select the `resumematch_ai` project.
3. If this project is redundant (since the React frontend is deployed as project `frontend`):
   - Navigate to **Settings** -> **Advanced** -> Click **Delete Project**.
4. If this project is intended to be retained:
   - Navigate to **Settings** -> **General** -> **Root Directory**.
   - Change `.` to `frontend`.
   - Save and trigger **Redeploy**.

---

## 5. Rollback Plan

If custom DNS propagation is delayed or encounters issues during rollout, the following safe fallback procedure is pre-tested:

1. **Emergency Fallback to Direct Provider URLs**:
   - Update Vercel frontend environment variable: `VITE_API_BASE_URL=https://resumematch-ai-api-atil.onrender.com`.
   - Ensure `https://frontend-harsha1704s-projects.vercel.app` is in Render backend `CORS_ALLOWED_ORIGINS` (already verified active).
   - Redeploy frontend on Vercel.
2. **Caveats of Emergency Fallback**:
   - Safari/WebKit users may experience session drops due to third-party cookie restrictions across `*.vercel.app` and `*.onrender.com`.
   - File uploads and ML inference remain functional on Chromium/Firefox.
3. **Restoration**:
   - Once DNS records for `app.resumematch.ai` and `api.resumematch.ai` propagate, restore `VITE_API_BASE_URL=https://api.resumematch.ai`.
