# Frontend: Next.js Web Application

This directory contains the frontend user interface for the **Drug Safety Signal Detector & Regulatory Submission Readiness Checker**.

---

## Directory Structure

```
frontend/
├── app/                  # Next.js App Router (pages and layouts)
│   ├── layout.tsx        # Root layout with navigation and providers
│   ├── page.tsx          # Main landing dashboard
│   ├── safety/           # Safety Signal Detection dashboard views
│   ├── ctd/              # Regulatory Submission Readiness Checker views
│   └── copilot/          # Dedicated Bob Copilot interface
├── components/           # Modular, reusable UI components
│   ├── common/           # Shared navigation, badges, buttons, cards
│   ├── safety/           # Event frequency charts, PRR matrices, cluster graphs
│   ├── ctd/              # Module-wise breakdown cards, gap reports, tree view
│   └── copilot/          # Bob conversational drawer and query interface
├── lib/                  # Shared utilities and API client services
│   ├── api.ts            # REST API client interface for backend
│   └── types.ts          # TypeScript interfaces and data models
├── public/               # Static assets, logos, and icons
├── package.json          # Node package manifest
└── README.md             # Frontend overview and guidelines
```

---

## Key UI Sections (Planned)

1. **Safety Dashboard**:
   - Filterable adverse event data grid.
   - Interactive charts for Proportional Reporting Ratio (PRR) distributions.
   - Disproportionality alert cards with clinical summary tooltips.
2. **CTD Readiness Checker**:
   - Aggregate submission readiness meter (0–100%).
   - Module 1 through Module 5 breakdown cards.
   - Expandable dossier hierarchy with color-coded completeness indicators.
   - Exportable critical gap report.
3. **IBM Bob AI Copilot**:
   - Docked conversational assistant allowing natural-language inquiry across both safety and CTD data.
