# Setup & Installation Guide

This guide details the prerequisites, environment setup, and development workflow for the **Drug Safety Signal Detector & Regulatory Submission Readiness Checker**.

---

## Prerequisites

Ensure the following tools and services are available on your development system:

- **Git**: For source control and version management.
- **Python**: Required for the FastAPI backend and data analysis services (Python 3.10+ recommended).
- **Node.js & npm / yarn / pnpm**: Required for the Next.js frontend application (Node.js LTS recommended).
- **PostgreSQL**: Relational database engine for data persistence and audit logging.
- **IBM watsonx.ai & IBM Bob Access**: API credentials and project identifiers for AI reasoning and copilot capabilities.

---

## Repository Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Vivek-Maheshwari-07/bob-ai-hackathon--your-team-name-.git
   cd bob-ai-hackathon--your-team-name-
   ```

2. **Inspect Structure**:
   ```bash
   # Verify the top-level repository directories
   ls -la
   ```

---

## Environment Configuration

A template environment configuration file is provided in `src/.env.example`.

1. **Create Local Environment File**:
   Copy the example file to `.env` inside `src/`:
   ```bash
   cp src/.env.example src/.env
   ```

2. **Configure Variables**:
   Update `src/.env` with your development database and IBM service credentials.

> **IMPORTANT**: Never commit your `.env` file or any real API keys to the repository. The `.gitignore` file is configured to exclude all `.env` files automatically.

---

## Current Project Status

> **Notice for Hackathon Evaluators**:
> The repository is currently in the **initial setup and MVP preparation phase**.
> - The repository structure, documentation skeleton, schema designs, and configuration templates are fully prepared.
> - Source code directories (`src/frontend/` and `src/backend/`) have been initialized with clean architectural skeletons.
> - Step-by-step local development commands (`npm run dev`, `uvicorn app.main:app`) and automated test suites will be populated as the core analytical modules and interface components are progressively implemented.

---

## Troubleshooting Guide

The table below outlines common setup issues encountered during initial development and their resolutions:

| Issue | Potential Cause | Resolution |
|---|---|---|
| **Python Virtual Environment Conflicts** | Multiple Python versions or conflicting packages | Create a clean virtual environment (`python -m venv .venv`) and activate it before installing dependencies. |
| **Node.js Package Installation Failures** | Cache corruption or network timeouts | Clear npm cache (`npm cache clean --force`) or remove `node_modules` and re-run installation. |
| **PostgreSQL Connection Errors** | Database service not running or invalid `DATABASE_URL` | Ensure PostgreSQL service is active locally or remotely, and verify username, password, port, and database name in `.env`. |
| **Missing Environment Variables** | `.env` not loaded or key missing | Ensure all required variables specified in `src/.env.example` are defined in your local `src/.env`. |
| **IBM watsonx.ai Authentication Errors** | Invalid API Key or expired Project ID | Confirm your API key and Project ID within the IBM Cloud / watsonx console and ensure correct endpoint URL. |
