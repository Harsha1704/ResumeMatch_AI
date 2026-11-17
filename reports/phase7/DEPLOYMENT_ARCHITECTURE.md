# RESUMEMATCH AI — PHASE 7.1: PRODUCTION DEPLOYMENT & INFRASTRUCTURE ARCHITECTURE

**Target Repository**: `Harsha1704/ResumeMatch_AI`  
**Working Branch**: `fix/resumematch-final-repair`  
**Baseline Commit**: `1757b326371ebf43a76141ff6347e8ccdc0b1a51`  
**Verified Live Deployed Commit**: `07b88a058f166f13491fa9050ba835d95fd0e8fd`  
**Verified Vercel Deployment**: `https://frontend-orzkrjj8t-harsha1704s-projects.vercel.app` (Project: `frontend`, Team: `harsha1704s-projects`, Branch: `main`)  
**Verified Render Deployment**: `https://resumematch-ai-api-atil.onrender.com` (Service: `resumematch-ai-api`, ID: `srv-dbspslmi0phs73dqbptg`, Branch: `deploy/vercel-render-free`)  
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
| **File Upload Capacity** | **Full 16 MB streaming** directly to Render Gunicorn worker ([app.py#L43](file:///d:/skillsync1/app.py#L43)). | **CRITICAL FAILURE**: Vercel Serverless Function & Edge proxy enforces a hard **4.5 MB body limit**. Uploads > 4.5 MB abort with HTTP 413. |
| **Inference Latency & Timeouts** | Render allows long-running requests (up to 120s+ timeout in Gunicorn). Cold starts and heavy ML models run without interruption. | **CRITICAL FAILURE**: Vercel Hobby proxy aborts requests after **10 seconds** (HTTP 504 Gateway Timeout). Render cold start + model inference triggers 504. |
| **CORS Overhead** | Explicit allowlist in Flask (`FRONTEND_ORIGINS`). Preflight handled cleanly. | Zero browser CORS overhead, but proxy header rewrites required. |
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

### 3.2 Real Production Configuration Names ([app.py](file:///d:/skillsync1/app.py))

```bash
# Render Service Environment Variables
RESUMEMATCH_ENV=production
SECRET_KEY=<generate-strong-cryptographic-hex-secret-64chars>
FRONTEND_ORIGINS=https://app.resumematch.ai,https://frontend-harsha1704s-projects.vercel.app
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_DOMAIN=.resumematch.ai
MAX_CONTENT_LENGTH=16777216
PORT=10000
```

```bash
# Vercel Project Environment Variables
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
