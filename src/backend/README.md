# Backend: FastAPI Application

This directory contains the Python FastAPI backend service powering the **Drug Safety Signal Detector & Regulatory Submission Readiness Checker**.

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py        # Application entry point and router registrations
│   ├── api/           # API endpoints (safety, ctd, copilot)
│   ├── services/      # Business logic (PRR analysis, CTD validation, Gemini)
│   ├── models/        # SQLAlchemy / Database ORM models
│   ├── schemas/       # Pydantic request and response schemas
│   ├── core/          # App settings, environment loading, and security
│   └── utils/         # Helper functions and statistical calculators
├── tests/             # Pytest test suites
├── requirements.txt   # Python dependencies
└── README.md          # Backend documentation
```

---

## Key Modules (Planned)

1. **Safety Signal Service (`services/safety_service.py`)**:
   - Ingestion of adverse event datasets.
   - Frequency clustering and temporal trend calculations.
   - Proportional Reporting Ratio (PRR) and statistical disproportionality evaluation.

2. **CTD Readiness Service (`services/ctd_service.py`)**:
   - Directory traversal against ICH M4 structure standards (Modules 1–5).
   - Missing section detection, readiness scoring, and gap report compilation.

3. **IBM Bob Copilot Service (`services/copilot_service.py`)**:
   - Orchestrates context assembly for Google Gemini 2.5 Flash.
   - Handles natural-language Q&A regarding active safety signals and CTD readiness reports.
