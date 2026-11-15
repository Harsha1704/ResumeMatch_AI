# ResumeMatch AI — Modern SaaS Frontend

Enterprise-grade React frontend for the **ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System**.

## Stack
- **Framework:** React 19 + Vite 8 + TypeScript
- **Styling:** Tailwind CSS v4 (Dark SaaS Charcoal Theme)
- **Routing:** React Router v7
- **Visuals & Charts:** Recharts & Lucide React
- **Backend:** Flask 3.x REST API (`app.py`)

---

## Getting Started Locally

### 1. Start Flask API Backend
In the project root directory:
```bash
# Terminal 1: Run Flask Backend
python app.py
# Backend runs on http://127.0.0.1:5000
```

### 2. Start React Frontend
In the `frontend/` directory:
```bash
# Terminal 2: Run React Frontend
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:5173
```
Vite automatically proxies `/api` and `/health` requests to `http://127.0.0.1:5000`.

---

## Deployment to Vercel

1. In your Vercel Dashboard, click **Add New Project** and select this repository.
2. Configure project settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-backend-app.onrender.com` (your Render URL without trailing slash)
4. Click **Deploy**. Single-page routing is preconfigured via `vercel.json`.

---

## Deployment to Render (Backend)

The backend includes a preconfigured `render.yaml` blueprint:
1. In your Render Dashboard, click **New > Blueprint**.
2. Connect your GitHub repository. Render will automatically detect `render.yaml`.
3. Set `FRONTEND_ORIGINS` to your Vercel domain:
   ```
   FRONTEND_ORIGINS=https://your-app.vercel.app
   ```
4. Deploy the web service.

---

## Module Directory
- `/`: Executive Intelligence Dashboard
- `/analyze`: Resume Analyzer with Drag & Drop, pasted text, and Model Selector
- `/results`: Quantitative Match Score, 3-Class Probability Bar, Matched & Missing Skills
- `/skill-gap`: Doughnut Coverage Gauge, Evidence Breakdown, and Prioritized Roadmap Table
- `/career-mentor`: Personalized Counseling, 9-point assessments, and milestone roadmaps
- `/interview-studio`: Resume-aware Question Banks & Spoken/Simpler Answer Toggles
- `/interview-practice`: Interactive Simulator with Live Timer & Heuristic Evaluation
- `/interview-results`: Complete Practice Performance Review
- `/model-performance`: Empirical Benchmarks, Confusion Matrix Heatmap, and CSV Exports
- `/datasets`: Data Provenance, Word Count Distributions, and 4,476-skill Taxonomy
