
# Source Code Directory (`src/`)

This directory contains the full-stack codebase for **PharmSignals** ("Drug Safety Signal Detector & Regulatory Submission Readiness Checker" — Problem Statement P2, IBM Bobathon 2026).

---

## Directory Architecture

```
src/
├── .env.example       # Template for environment variables and optional LLM keys
├── README.md          # Source directory overview and module map
│
├── frontend/          # Next.js 14 / React 18 User Interface (White-First Enterprise Layout)
│   ├── app/           # App router pages (page.tsx, layout.tsx, globals.css)
│   ├── components/    # Reusable UI components (Sidebar, Header, MetricCard, StatusBadge, Copilot)
│   ├── lib/           # Centralized API client (api.ts) with typed payloads
│   ├── public/        # Static assets
│   ├── package.json   # Frontend dependency specifications (Next.js 14, Tailwind v3, Recharts)
│   └── README.md      # Frontend documentation
│
└── backend/           # Python 3.10+ FastAPI Application & Analytical Compute Engines
    ├── app/
    │   ├── main.py    # FastAPI application entry point & CORS configuration
    │   ├── api/v1/    # REST endpoints (health, signals, clusters, backtest, m4, readiness, copilot)
    │   ├── m1_faers/  # Module M1: FAERS Ingestion & scikit-learn Adverse Event Clustering
    │   ├── m2_prr/    # Module M2: Evans PRR & Pearson Chi-Square statistical engine
    │   ├── m3_digital_twin/ # Module M3: Longitudinal walk-forward digital twin backtester
    │   ├── m4_rag/    # Module M4: ICH M4 CTD RAG retriever & gap report generator
    │   ├── data/      # Real openFDA FAERS pre-processed datasets & benchmark matrices
    │   └── core/      # Core settings and configuration
    ├── tests/         # Complete automated test suite (121 pytest tests across M1–M5)
    ├── requirements.txt # Python dependency specification
    └── README.md      # Backend documentation
```

---

## Communication Architecture

1. **Frontend $\to$ Backend**: The Next.js frontend calls the FastAPI backend via `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000/api/v1`).
2. **Stateless REST**: Backend endpoints compute real-time PRR calculations, load historical backtest trajectories, evaluate candidate CTD dossiers, and serve grounded IBM Bob Copilot inquiries.
3. **One-Command Startup**: Root `package.json` uses `concurrently` to run both services simultaneously via `npm run dev`.
