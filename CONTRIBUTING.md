# Contributing Guidelines

Thank you for contributing to the **Drug Safety Signal Detector & Regulatory Submission Readiness Checker** project for the IBM Bob AI Hackathon.

## Team Standards & Workflow

1. **Branching Strategy**:
   - `main`: Production and stable release branch.
   - `feature/<feature-name>`: Dedicated feature development branches.
   - `fix/<bug-name>`: Dedicated bug fix branches.

2. **Code Style & Formatting**:
   - **Frontend**: Follow modern React/TypeScript best practices with clean modular components.
   - **Backend**: Adhere to PEP 8 standards, utilizing type hints throughout FastAPI endpoints and data models.
   - **Documentation**: Maintain comprehensive and accurate documentation under `docs/`.

3. **Security & Secrets**:
   - **NEVER** commit real API keys, passwords, connection strings, or secrets to the repository.
   - Use `src/.env.example` as a template and maintain local credentials in `.env` (ignored by `.gitignore`).

4. **Commit Guidelines**:
   - Write clear, imperative commit messages (e.g., `Add PRR calculation utility`, `Create CTD validation schema`).
   - Keep pull requests focused on specific features or fixes.

5. **Hackathon Submission Compliance**:
   - Ensure all top-level submission files (`submission.yaml`, `README.md`, `demo/`, `presentation/`) remain consistent with the official Bob AI Hackathon template guidelines.
