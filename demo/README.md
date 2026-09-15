# Demonstration Artifacts

This directory contains the demonstration evidence for **PharmSignals** (Problem Statement P2: Drug Safety Signal Detector & Regulatory Submission Readiness Checker) submitted by **Team Demon Slayer** for the **IBM Bobathon 2026**.

---

## Contents

- **`demo-video-link.txt`**: Official walkthrough video recording demonstrating application startup, Mode 1 (Signal Detection & Clustering), Mode 2 (ICH M4 CTD Submission Readiness), and the IBM Bob Copilot.
  - Video URL: `https://youtu.be/7POfIsw83OA`
- **`live-demo-url.txt`**: Live deployment status.
  - Value: `NOT DEPLOYED` (The application is evaluated via local execution and the recorded video walkthrough).
- **`screenshots/`**: Directory containing genuine high-resolution screenshots of the running platform:
  - `01-dashboard.png` — Central Pharmacovigilance Dashboard with KPIs and Bubble Chart
  - `02-signal-detection.png` — Signal Detection Workspace, 2×2 Calculator, and Clustering Studio
  - `03-historical-analysis.png` — Historical Backtest showing +242 days early detection lead time
  - `04-submission-readiness.png` — ICH M4 CTD Submission Readiness Checker across Modules 1–5
  - `05-reports-and-export.png` — Reports & Audit Exports
  - `README.md` — Detailed annotations for each screenshot

---

## How to Run Locally

PharmSignals runs locally using a single command or standard two-tier commands:

```bash
# 1. Install dependencies
pip install -r src/backend/requirements.txt
npm --prefix src/frontend install

# 2. Configure environment
cp src/.env.example src/.env

# 3. Start both backend (port 8000) and frontend (port 3000)
npm run dev
```

Open `http://localhost:3000` in any modern web browser. Complete setup instructions and troubleshooting are detailed in [`docs/setup-guide.md`](../docs/setup-guide.md).

---

## Synthetic Benchmark & Test Data Disclosure

- **Adverse Event Data**: Mode 1 utilizes genuine openFDA FAERS post-marketing adverse event records (2004–2023) cleaned and normalized for benchmark safety signals (VIOXX / rofecoxib, BAYCOL / cerivastatin, AVANDIA / rosiglitazone).
- **ICH M4 CTD Dossier Benchmark**: The pre-configured dossiers (such as BOB-701 Oncology IND and Vioxx NDA 21-042 outlines) and the test benchmark dossier (104 checkable entries: 57 present, 47 missing; raw 54.81% / displayed 55% completeness) are **synthetic benchmark test dossiers** constructed according to official ICH M4 guidelines to rigorously test and demonstrate the gap detection engine. They are not actual corporate proprietary submissions.

---

## Known Limitations

- **Cloud Deployment**: The application is not hosted on public cloud infrastructure (`NOT DEPLOYED`); local execution and the demo video are the primary evaluation mechanisms.
- **Decision Support Only**: PharmSignals produces statistical disproportionality signals and structural regulatory gap assessments to accelerate expert review. It does not establish clinical causality or substitute for formal regulatory review by health authorities.
