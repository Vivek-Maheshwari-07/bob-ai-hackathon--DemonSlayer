# Drug Safety Signal Detector & Regulatory Submission Readiness Checker

An intelligent dual-capability platform for pharmacovigilance and regulatory affairs teams to detect emerging drug safety signals, verify ICH M4 Common Technical Document (CTD) dossier readiness, and query findings through an interactive IBM Bob AI Copilot.

---

## Team

- **Team Name**: Demon Slayer
- **Track**: AI
- **Team Lead**: TODO (To be updated with official hackathon registration details)
- **Team Members**: TODO (To be updated with official hackathon registration details)

---

## Problem Statement

Life sciences safety and regulatory teams face complex challenges during post-marketing surveillance and pre-market submission cycles:

- **Pharmacovigilance & Safety Investigation**: Monitoring adverse events across growing volumes of reports makes early detection of subtle or emerging safety signals difficult. Manual triage risks missing high-priority safety trends.
- **Safety Signal Complexity**: Differentiating genuine safety signals from statistical noise requires disproportionality methods (such as Proportional Reporting Ratio - PRR) and event clustering, which are often isolated in non-intuitive tools.
- **Regulatory Submission Readiness Bottlenecks**: Regulatory submissions conform to strict ICH M4 Common Technical Document (CTD) structures (Modules 1 through 5). Evaluating whether a dossier is complete, properly formatted, and free of missing critical sections is time-consuming and error-prone.
- **Fragmented Workflows**: Safety data analysts and regulatory compliance specialists often work in disparate silos without a centralized system to link signal emergence with dossier documentation gaps.

---

## Our Solution

Our platform provides a unified workspace addressing both post-market surveillance and pre-market dossier compliance:

### Safety Signal Detection
- **Adverse-Event Ingestion & Preparation**: Standardizes and processes multi-source adverse reaction data.
- **Event Clustering**: Groups related adverse events to identify underlying physiological or clinical patterns.
- **Emerging Trend Identification**: Highlights temporal surges and shifts in event reporting.
- **PRR Calculation & Representation**: Computes Proportional Reporting Ratios to flag statistical disproportionality for drug-event pairs.
- **Explainable Signal Alerts**: Generates clear, contextual reasoning for why a signal was flagged to support safety specialist reviews.

### Regulatory Submission Readiness
- **CTD Dossier Structural Inspection**: Scans submissions against ICH M4 structural expectations (Module 1: Administrative, Module 2: Summaries, Module 3: Quality, Module 4: Nonclinical, Module 5: Clinical).
- **Section Completeness Verification**: Verifies presence, formatting, and completeness of mandatory sections.
- **Readiness Scoring**: Calculates an aggregate submission-readiness percentage alongside granular module-wise scores.
- **Critical Gap Identification**: Flags missing documents, omitted sub-sections, and formatting non-compliances.
- **Automated Gap Report**: Generates actionable remediation summaries for regulatory submission leads.

---

## IBM Bob Integration

IBM Bob is designed as a load-bearing, contextual AI copilot embedded directly into both the Safety Dashboard and CTD Checker workflows. Rather than acting as a simple generic chatbot, Bob synthesizes backend analytics, PRR metrics, and dossier inspection outputs to answer targeted domain questions.

### Planned Copilot Inquiries:
- *"Why was this safety signal flagged for the selected drug?"*
- *"Which adverse event is showing the strongest emerging signal in the last quarter?"*
- *"What are the critical gaps in this CTD dossier preventing submission?"*
- *"Why is Module 3 incomplete, and which quality reports are missing?"*
- *"What should the regulatory team review first to achieve 90%+ submission readiness?"*

*(Note: IBM Bob integration architecture is established in the initial design; live copilot endpoints and model bindings are under active MVP construction.)*

---

## Key Features

- **Adverse Event Analytics**: Dynamic data filtering, clustering, and frequency distribution.
- **PRR Disproportionality Engine**: Automated Proportional Reporting Ratio computation with confidence intervals and thresholds.
- **Explainable Safety Alerts**: Context-rich summaries detailing event distribution, reporting timelines, and comparative risk.
- **ICH M4 Structure Validation**: Automated validation covering CTD Modules 1 to 5.
- **Readiness Metric Engine**: Real-time overall and module-by-module compliance scoring.
- **Actionable Gap Reporting**: Prioritized list of missing documents with remediation recommendations.
- **Interactive IBM Bob Copilot**: Natural-language conversational interface for safety and regulatory investigation.

---

## User Workflow

```
User (Safety Scientist / Regulatory Specialist)
  │
  ▼
Select Workflow: [ Safety Dashboard ] OR [ CTD Checker ]
  │
  ├──► [ Safety Workflow ]
  │       ├── Data Ingestion (Adverse Event Datasets)
  │       ├── Event Clustering & Emerging Pattern Analysis
  │       ├── PRR Calculation & Disproportionality Scoring
  │       └── Explainable Signal Alerts
  │
  └──► [ Regulatory Workflow ]
          ├── CTD Dossier Folder / Metadata Ingestion
          ├── ICH M4 Completeness & Structure Inspection
          ├── Module-Wise & Overall Readiness Scoring
          └── Critical Missing Section Gap Report
  │
  ▼
IBM Bob Copilot Interaction
  └── Natural-language deep-dive into flagged signals and remediation recommendations
```

---

## Planned UI

1. **Safety Dashboard**: Interactive overview featuring adverse event distributions, PRR signal heatmaps, clustering graphs, and prioritized safety alerts.
2. **CTD Checker**: Visual submission readiness gauge, module-by-module (M1-M5) breakdown cards, file hierarchy tree with status indicators, and an exportable gap report view.
3. **Bob Copilot**: Docked or expandable conversational assistant providing contextual explanations and instant answers based on active dashboard data.

---

## Tech Stack

| Layer | Technology | Role / Purpose | Status |
|---|---|---|---|
| **Frontend** | React / Next.js | Modern, responsive web application and interactive dashboards | Planned / Scaffolded |
| **Styling & Visualization** | CSS / Recharts or Chart.js | Statistical charts, PRR distributions, and readiness gauges | Planned |
| **Backend API** | Python / FastAPI | High-performance asynchronous REST API for data processing | Planned / Scaffolded |
| **Data Processing** | Pandas | Data cleaning, aggregation, clustering, and PRR calculations | Planned |
| **Database** | PostgreSQL | Relational storage for safety datasets, CTD schemas, and audit trails | Planned |
| **AI Reasoning** | IBM watsonx.ai / Granite | Foundation models for explainable safety alerts and gap synthesis | Planned |
| **AI Copilot** | IBM Bob Integration | Load-bearing conversational copilot for natural-language inquiry | Planned |

---

## Repository Structure

```
/
├── submission.yaml          # Official hackathon metadata, team info, and solution summary
├── README.md                # Project overview, workflow, tech stack, and documentation
├── CONTRIBUTING.md          # Collaboration and contribution guidelines
├── .gitignore               # Ignored files, environments, and build artifacts
│
├── docs/                    # In-depth technical and architectural documentation
│   ├── problem-statement.md # Detailed breakdown of the P2 domain challenges
│   ├── solution-overview.md # Conceptual end-to-end platform design
│   ├── architecture.md      # System architecture, data flow, and component boundaries
│   └── setup-guide.md       # Development environment prerequisites and setup instructions
│
├── src/                     # Application source code
│   ├── .env.example         # Template for environment configuration and credentials
│   ├── README.md            # Source directory overview
│   ├── frontend/            # Next.js / React user interface structure
│   └── backend/             # FastAPI backend services, schemas, and endpoints
│
├── demo/                    # Hackathon demonstration artifacts
│   ├── demo-video-link.txt  # Link to recorded demonstration video
│   ├── live-demo-url.txt    # Deployed application live URL
│   ├── screenshots/         # Application visual captures and UI flows
│   └── README.md            # Demonstration artifact descriptions
│
├── presentation/            # Presentation slide deck outline and materials
│   └── README.md            # Planned 7-slide hackathon presentation structure
│
└── .github/
    └── workflows/
        └── validate.yml     # Automated workflow for repository structure and validation
```

---

## How to Run

Please refer to the detailed [Setup Guide](file:///d:/bob-ai-hackathon--your-team-name-/docs/setup-guide.md) for prerequisite requirements, environment configuration, and local setup steps.

*(Note: Detailed runtime execution instructions will be updated as the frontend and backend core services complete MVP implementation.)*

---

## Demo

- **Demo Video**: See [demo/demo-video-link.txt](file:///d:/bob-ai-hackathon--your-team-name-/demo/demo-video-link.txt)
- **Live Demo**: See [demo/live-demo-url.txt](file:///d:/bob-ai-hackathon--your-team-name-/demo/live-demo-url.txt)
- **Screenshots**: Visual walk-throughs will be placed in [demo/screenshots/](file:///d:/bob-ai-hackathon--your-team-name-/demo/screenshots/README.md) once core UI modules are rendered.

---

## Known Limitations

- **Project Phase**: The repository is currently in the initial setup and MVP preparation stage; application endpoints and user interfaces are being iteratively scaffolded.
- **Safety Signal Scope**: PRR calculations and event clustering are designed for standardized adverse event formats and will require schema mapping for custom internal safety databases.
- **Regulatory Rule Sets**: Initial CTD inspection rules focus on ICH M4 structure and completeness; regional extensions (e.g., US FDA Module 1 specific specifications) are scheduled for progressive enhancement.
- **AI Explanations**: Copilot outputs are intended to assist and guide safety and regulatory experts; they do not replace formal regulatory audits or qualified medical reviewer sign-offs.

---

## What We're Most Proud Of

- **Unified Life Sciences Intelligence**: Bridging post-market pharmacovigilance surveillance with pre-market regulatory submission readiness in a single coherent platform.
- **Transparent & Explainable Analytics**: Combining established statistical methodologies (PRR) with clear contextual narratives rather than opaque black-box scoring.
- **Actionable Dossier Gap Diagnostics**: Transforming tedious ICH M4 manual checklist reviews into structured, module-by-module remediation priorities.
- **Load-Bearing AI Integration**: Positioning IBM Bob as an intelligent analytical co-investigator that allows domain specialists to converse directly with their data and dossiers.
