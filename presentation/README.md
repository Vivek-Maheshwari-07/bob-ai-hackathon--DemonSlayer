# Presentation Materials

This directory will hold the pitch deck slides and presentation assets for the hackathon evaluation.

---

## Planned Slide Structure (7 Slides)

### Slide 1: Problem & Industry Context
- Growing volumes of post-marketing adverse-event reports and risk of delayed signal detection.
- High cost and submission delays caused by incomplete or malformed ICH M4 CTD dossiers.
- Severe operational friction arising from disconnected safety and regulatory tooling.

### Slide 2: The Solution
- Dual-capability platform: Adverse-Event Safety Signal Detection + ICH M4 CTD Dossier Readiness Checker.
- Disproportionality statistics (PRR) combined with automated document hierarchy inspection.
- Embedded IBM Bob AI Copilot for interactive, explainable inquiry.

### Slide 3: User Workflow & Experience
- Safety Scientist triage flow: Data ingestion → Event clustering → PRR calculation → Explainable alert.
- Regulatory Specialist audit flow: Dossier upload → Structural check → Readiness scoring → Gap report.
- Natural-language investigation loop with IBM Bob.

### Slide 4: System Architecture & Technology Stack
- High-level overview: React/Next.js frontend, Python/FastAPI backend, PostgreSQL data store.
- Separation of concerns: Data layer, analytical engines, AI explanation pipelines.
- Data privacy, compliance, and enterprise scalability considerations.

### Slide 5: IBM Bob & watsonx.ai Integration
- Concrete, load-bearing role of IBM Bob as an intelligent copilot.
- IBM watsonx.ai / Granite models powering signal narrative generation and gap remediation roadmaps.
- Grounded contextual queries vs. generic LLM prompts.

### Slide 6: Product Demonstration & Highlights
- Walkthrough of the Safety Dashboard with live PRR metrics and cluster visualizations.
- Walkthrough of the CTD Checker displaying module-wise readiness and missing critical sections.
- Live conversational interaction with IBM Bob.

### Slide 7: Business Impact, Scalability & Future Scope
- Quantifiable time savings during submission preparation and safety signal triaging.
- Expansion to regional CTD specifications (e.g., US FDA Module 1, EMA regional requirements).
- Continuous real-time pharmacovigilance surveillance and automated REMS drafting.

---

## File Status

- Final presentation deck (`presentation.pdf` / `presentation.pptx`) will be uploaded prior to final hackathon submission.
