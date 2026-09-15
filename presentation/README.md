# Presentation Materials

This directory contains the pitch deck and presentation assets for **PharmSignals** (Problem Statement P2: Drug Safety Signal Detector & Regulatory Submission Readiness Checker) submitted by **Team Demon Slayer** for the **IBM Bobathon 2026**.

---

## Slide Deck File

- **`slides.pdf`**: Official presentation deck (14 slides) structured according to the official IBM Bobathon evaluation guidelines:
  1. **Title & Problem Context**: Post-marketing surveillance volume (20M+ FAERS reports) and CTD dossier complexity (100,000+ pages, 5 modules).
  2. **Core Problem Breakdown**: Undetected adverse events (Vioxx 27,000+ cardiac events) and costly dossier rejections ($50M–$100M delays).
  3. **PharmSignals Solution Overview**: Dual-mode clinical intelligence platform (Mode 1: Signal Detection; Mode 2: Submission Readiness).
  4. **Mode 1 — Signal Detection Architecture**: Ingestion of real openFDA FAERS data, 2×2 contingency table calculation, Evans PRR statistics, and Pearson $\chi^2$.
  5. **Adverse Event Clustering**: Multi-dimensional scikit-learn clustering (KMeans + PCA) grouping adverse events by clinical and demographic features.
  6. **Longitudinal Walk-Forward Backtesting**: Empirical validation on historical market withdrawals (+242 days early detection on Vioxx).
  7. **Mode 2 — ICH M4 CTD Submission Readiness**: Automated audit across Modules 1–5, completeness scoring, and missing section detection.
  8. **Priority Regulatory Gap Matrix**: Severity classification (CRITICAL, MAJOR, STANDARD) with official ICH citations and remediation roadmaps.
  9. **IBM Technology Integration**: Detailed breakdown of IBM Bob as an AI SDLC Partner (accelerating architecture, implementation, testing with 121 automated tests, and documentation) plus the interactive domain Copilot.
  10. **System Architecture & Data Flow**: Clean separation of concerns between React/Next.js frontend, FastAPI backend, and analytical engines.
  11. **Live Demonstration Highlights**: Walkthrough of key workflows and user journeys demonstrated in the demo video.
  12. **Synthetic Benchmark & Data Integrity**: Clear disclosure of openFDA FAERS data vs. synthetic test dossiers (104 entries, 55% completeness).
  13. **Impact, Scalability & Pharmacovigilance Vision**: Time and cost savings, safety surveillance acceleration, and regional CTD expansion.
  14. **Team & Conclusion**: Team Demon Slayer summary and submission repository details.

---

## Evaluation Alignment

The presentation directly reflects the actual codebase and demo video:
- **Demo Video Walkthrough**: [https://youtu.be/7POfIsw83OA](https://youtu.be/7POfIsw83OA)
- **Primary Execution**: Local development runtime (`npm run dev`), no deployed cloud endpoint (`NOT DEPLOYED`).
- **Codebase Truth**: Grounded entirely in implemented functionality without exaggerated or unverified claims.
