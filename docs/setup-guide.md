# Setup & Installation Guide

This guide details the prerequisites, environment setup, and verification workflow for **PharmSignals** ("Drug Safety Signal Detector & Regulatory Submission Readiness Checker" — Problem Statement P2, IBM Bobathon 2026).

---

## 1. System Requirements & Prerequisites

Ensure the following tools and runtimes are installed on your development machine:

| Component | Required Version | Verification Command | Notes |
|---|---|---|---|
| **Git** | 2.30+ | `git --version` | Required for source control |
| **Node.js** | 18 LTS or higher (tested on Node 20) | `node --version` | Required for frontend & process runner |
| **npm** | 9.0+ | `npm --version` | Node package manager |
| **Python** | 3.10+ (tested on Python 3.11 & 3.13) | `python --version` | Required for FastAPI backend & statistical compute |
| **OS** | Windows 10/11, macOS, or Linux | N/A | Windows PowerShell and CMD fully supported |

---

## 2. Quickstart: One-Command Full Stack Startup (Recommended)

From the project root directory:

```bash
# Step 1: Install root launcher dependencies
npm install

# Step 2: Install backend Python dependencies
pip install -r src/backend/requirements.txt

# Step 3: Install frontend dependencies
npm install --prefix src/frontend

# Step 4: Launch Backend & Frontend concurrently with ONE command
npm run dev
```

### What Happens on `npm run dev`:
- **FastAPI Backend**: Launches on `http://localhost:8000` (`python -m uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 8000 --reload`)
- **Next.js Frontend**: Launches on `http://localhost:3000` (`npm run dev --prefix src/frontend`)
- Streams unified prefixed logs (`[BACKEND]`, `[FRONTEND]`) to your terminal.
- Press `Ctrl + C` once to cleanly terminate both processes.

---

## 3. Standalone Execution Options

### Option A: Running Backend Independently

```bash
# Navigate to backend directory
cd src/backend

# (Optional) Create & activate Python virtual environment
python -m venv .venv
# On Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# On macOS/Linux: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the complete test suite (121 tests)
python -m pytest

# Start Uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger documentation is available at `http://localhost:8000/docs`.

### Option B: Running Frontend Independently

```bash
# Navigate to frontend directory
cd src/frontend

# Install dependencies
npm install

# Build production bundle (validates TypeScript types & static pages)
npm run build

# Start development server
npm run dev
```

The user interface will be live at `http://localhost:3000`.

---

## 4. Environment Configuration

Copy the configuration template:

```bash
# On Windows (PowerShell):
Copy-Item src/.env.example src/.env

# On macOS/Linux:
cp src/.env.example src/.env
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8000/api/v1` | Backend API URL for frontend communication |
| `GEMINI_API_KEY` | No | *Empty* | Optional Google Gemini 2.5 Flash key powering the IBM Bob Copilot and M4 grounded reasoning |

> **Note**: The platform features a **100% deterministic offline fallback engine** when `GEMINI_API_KEY` is omitted, guaranteeing zero hallucinations and full functionality for offline hackathon judging.

---

## 5. Verification & Health Check Endpoints

Execute these verification commands from any terminal to confirm all subsystems are operational:

1. **Backend Subsystem Health**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   *Response:* `{"status":"healthy","services":{"safety_engine":"ready","ctd_engine":"ready","bob_copilot":"ready"}}`

2. **Signals Summary (M1/M2 Engine)**:
   ```bash
   curl http://localhost:8000/api/v1/signals/summary
   ```
   *Response:* `{"total_drug_event_pairs":300,"confirmed_signals":222,...}`

3. **Vioxx Backtest Trajectory (M3 Engine)**:
   ```bash
   curl http://localhost:8000/api/v1/signals/backtest/VIOXX
   ```
   *Response:* `{"drug_name":"VIOXX","lead_time_days":242,...}`

4. **Adverse Event Clustering (M1 ML Engine)**:
   ```bash
   curl "http://localhost:8000/api/v1/signals/clusters?n_clusters=4"
   ```
   *Response:* `{"clusters":[{"cluster_id":1,"cluster_name":"Cluster 1: Acute Ischemia & High Mortality",...}],...}`

5. **Candidate CTD Dossier Presets (M4 Engine)**:
   ```bash
   curl http://localhost:8000/api/v1/m4/presets
   ```

6. **Frontend Web UI**:
   Open `http://localhost:3000` in Google Chrome, Edge, or Firefox.

---

## 6. Running Automated Tests

Run the full automated test suite from the repository root:

```bash
npm test
```
*(Equivalent to `python -m pytest src/backend`)*

**Test Suite Coverage (121 Tests):**
- `test_health.py`: Subsystem heartbeat & API status (2 tests)
- `test_clustering.py`: Multi-dimensional KMeans & PCA adverse event clustering (3 tests)
- `test_m1_faers.py`: FAERS data ingestion, cleaning & normalization (9 tests)
- `test_m2_prr.py`: Evans PRR calculation, $\chi^2$, 95% CI & classification (13 tests)
- `test_copilot_and_custom_calc.py`: Custom 2×2 calculation & IBM Bob Copilot (13 tests)
- `test_m3_trajectory.py`: Vioxx (+242d), Avandia (+1205d), and Baycol backtests (7 tests)
- `test_m4_*.py`: ICH M4 CTD RAG retriever, completeness scoring & gap matrices (74 tests)

---

## 7. Cloud Deployment Guide (Reference Only)

> **Submission Evaluation Note**: For this official submission, PharmSignals is evaluated via local execution (`npm run dev`) and the official recorded demonstration video ([https://youtu.be/7POfIsw83OA](https://youtu.be/7POfIsw83OA)). The live deployment status in `demo/live-demo-url.txt` is intentionally set to `NOT DEPLOYED`. The optional steps below are provided strictly as reference architecture for hosting.

If deploying a live cloud instance in an enterprise environment:

### Step 1: Deploy FastAPI Backend (Render / Railway)
1. **Render (https://render.com)**:
   - Create a **New Web Service** linked to your GitHub repository.
   - **Root Directory**: `src/backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Note the deployed URL (e.g., `https://pharmsignals-api.onrender.com`).

### Step 2: Deploy Next.js Frontend (Vercel)
1. **Vercel (https://vercel.com)**:
   - Click **Add New Project** and import the repository.
   - **Root Directory**: `src/frontend`
   - **Framework Preset**: `Next.js`
   - **Environment Variables**:
     - `NEXT_PUBLIC_API_BASE_URL`: `https://pharmsignals-api.onrender.com/api/v1` (point to deployed backend)
   - Click **Deploy**.
   - Copy the public URL (e.g., `https://pharmsignals.vercel.app`) into `demo/live-demo-url.txt`.

---

## 8. Troubleshooting Guide

| Problem | Probable Cause | Recommended Solution |
|---|---|---|
| **Port 8000 or 3000 already in use** | A previous server instance is running in the background | Terminate the process holding the port: `npx kill-port 8000 3000` or restart your terminal. |
| **`npm run dev` fails on Windows** | PowerShell execution policy restricts running scripts | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in PowerShell before launching. |
| **`ModuleNotFoundError: No module named 'app'`** | Python ran without the backend app directory in path | Run Uvicorn with `--app-dir src/backend` or navigate directly into `cd src/backend`. |
| **Frontend displays "Backend Offline"** | FastAPI server is not reachable on port 8000 | Verify backend is running via `curl http://localhost:8000/api/v1/health`. |
| **Missing Python packages** | Dependencies were not installed in the active environment | Run `pip install -r src/backend/requirements.txt`. |
| **Node build fails with PostCSS error** | Incompatible Tailwind plugin version | Ensure dependencies in `src/frontend/package.json` are installed via `npm install --prefix src/frontend`. |

