# Deployment Guide — PharmSignals

This app has two deployable pieces:

- **Backend** (`src/backend`) — FastAPI service, deploy as a Docker container (Render, Railway, Fly.io, or any Docker host).
- **Frontend** (`src/frontend`) — Next.js app, deploy to Vercel.

Deploy the backend first so you have its public URL to give to the frontend.

---

## 1. Backend (FastAPI) — Render (recommended) or Railway

Files: [`src/backend/Dockerfile`](src/backend/Dockerfile), [`src/backend/.dockerignore`](src/backend/.dockerignore), [`render.yaml`](render.yaml)

### Option A — Render, via Blueprint (`render.yaml`)

1. Push this repo to GitHub.
2. In Render: **New > Blueprint**, select the repo. Render reads `render.yaml` at the repo root and creates a `pharmsignals-backend` web service that builds `src/backend/Dockerfile`.
3. Set the secret env var Render will prompt for (marked `sync: false` in `render.yaml`):
   - `GEMINI_API_KEY`
4. Deploy. Render assigns a public URL like `https://pharmsignals-backend.onrender.com`.
5. Verify: `GET https://<your-backend>.onrender.com/api/v1/health` should return `{"status": "healthy", ...}`.

### Option B — Render/Railway, manual Docker service

1. Create a new **Web Service** (Render) or **Service** (Railway) from the repo.
2. Set:
   - **Root/Context directory**: `src/backend`
   - **Dockerfile path**: `src/backend/Dockerfile` (or just `Dockerfile` if context is already `src/backend`)
3. The container reads `$PORT` automatically (both Render and Railway inject it) and binds `uvicorn` to it — no extra config needed.
4. Add environment variables (see table below).
5. Deploy and verify `/api/v1/health`.

### Backend environment variables

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` | Optional | Enables Google Gemini 2.5 Flash as the **primary** model for both the IBM Bob Copilot and the M4 grounded reasoning. |
| `ENVIRONMENT` | Optional | `production` on deploy. |

If `GEMINI_API_KEY` is not set, Copilot and the M4 reasoner automatically fall back to the deterministic rule-based engine — the app still runs and demos correctly with zero LLM keys configured.

No database is required to run the current feature set (FAERS/PRR data and the ICH M4 knowledge base ship as flat files under `src/backend/app/data` and `src/backend/app/m4_rag/knowledge`, bundled into the Docker image).

---

## 2. Frontend (Next.js) — Vercel

Files: [`src/frontend/vercel.json`](src/frontend/vercel.json), [`src/frontend/next.config.js`](src/frontend/next.config.js)

1. In Vercel: **Add New > Project**, import this repo.
2. Set **Root Directory** to `src/frontend` (Vercel needs this since the Next.js app lives in a subfolder, not the repo root).
3. Framework preset should auto-detect as **Next.js** (confirmed by `vercel.json`).
4. Add the environment variable:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<your-backend-domain>/api/v1` (the backend URL from step 1, with `/api/v1` appended).
5. Deploy.

### CORS

The backend currently allows all origins (`allow_origins=["*"]` in [`src/backend/app/main.py`](src/backend/app/main.py)) so the Vercel frontend will be able to call it out of the box. For a stricter production setup, replace `["*"]` with your exact Vercel domain(s) once you know the final URL.

---

## 3. Local development (unchanged)

```bash
# Backend
cd src/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd src/frontend
npm install
npm run dev
```

Copy `src/.env.example` to `src/.env` (backend) and set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` for local frontend dev.

---

## 4. Verifying a deploy end-to-end

1. `GET {backend_url}/api/v1/health` → `200 OK`.
2. Open the deployed frontend URL, confirm the header shows the backend as **online**.
3. Run a signal detection query and a CTD gap report (e.g. the VIOXX preset) to confirm the frontend ↔ backend round-trip works end-to-end, including the Mode 1 → Mode 2 safety-signal banner on the readiness screen.
