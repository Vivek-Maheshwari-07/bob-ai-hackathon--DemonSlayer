# Source Code Directory (`src/`)

This directory contains the primary codebase for the **Drug Safety Signal Detector & Regulatory Submission Readiness Checker**.

---

## Directory Structure

```
src/
├── .env.example       # Template for environment variables and API keys
├── README.md          # Source directory documentation
│
├── frontend/          # Next.js / React user interface application
│   ├── app/           # App router pages and layouts
│   ├── components/    # Reusable UI components (Dashboard, CTD, Copilot)
│   ├── lib/           # Utility functions and API client interfaces
│   ├── public/        # Static assets and icons
│   ├── package.json   # Node package manifest
│   └── README.md      # Frontend documentation
│
└── backend/           # FastAPI backend application
    ├── app/
    │   ├── main.py    # FastAPI application entry point
    │   ├── api/       # API route controllers
    │   ├── services/  # Business logic (PRR analysis, CTD validation, AI copilot)
    │   ├── models/    # Database ORM models
    │   ├── schemas/   # Pydantic data schemas
    │   ├── core/      # Application configuration and settings
    │   └── utils/     # Helper utilities and statistical routines
    ├── tests/         # Unit and integration test suites
    ├── requirements.txt # Python dependency specification
    └── README.md      # Backend documentation
```

---

## Getting Started

1. Set up your local configuration by copying `.env.example` to `.env`.
2. Follow the setup instructions in `frontend/README.md` and `backend/README.md` for their respective sub-projects.
