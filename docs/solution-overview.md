# Solution Overview: PharmSignals Intelligence Platform

---

## 1. Executive Summary

**PharmSignals** is a dual-capability clinical intelligence and regulatory compliance hub designed to streamline drug safety surveillance and eliminate regulatory submission bottlenecks. By bridging post-market pharmacovigilance analytics with pre-market ICH M4 dossier verification, PharmSignals empowers cross-functional teams to proactively manage drug safety liabilities and accelerate marketing authorization filings.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   PharmSignals — Regulatory Compliance Hub                       │
├─────────────────────────────────────────┬────────────────────────────────────────┤
│   MODE 1: SIGNAL DETECTION & PV         │   MODE 2: ICH M4 SUBMISSION READINESS  │
│   • openFDA FAERS Data Ingestion (M1)   │   • Candidate Dossier Ingest (PDF/Text)│
│   • Evans PRR & Chi² Statistics (M2)    │   • ICH M4 Ground-Truth RAG Engine     │
│   • Adverse Event Bubble Chart          │   • Module 1–5 Completeness Scoring    │
│   • 2x2 Custom Table Calculator         │   • Priority Gap Matrix & Severity     │
│   • Digital Twin Backtesting (M3)       │   • Grounded Remediation Roadmaps      │
│   • VIOXX (+242d) & AVANDIA (+1205d)    │   • 1-Click Preset Audits (NDA/IND)    │
└─────────────────────────────────────────┴────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │  IBM BOB AI COPILOT (Grounded Q&A & Remediation Guidance)  │
        └────────────────────────────────────────────────────────────┘
```

---

## 2. Target Users

- **Pharmacovigilance (PV) Scientists**: Execute real-time disproportionality surveillance and triage flagged adverse event signals.
- **Regulatory Affairs Directors**: Audit candidate CTD dossiers against ICH M4 requirements and prioritize gap remediations.
- **Medical Safety Officers**: Investigate clinical causality and evaluate historical trajectory behaviors.
- **Submission Project Managers**: Track module-by-module filing readiness scores before statutory agency submission.

---

## 3. Signal Detection & PV Analytics (Mode 1)

### Mathematical Methodology
PharmSignals evaluates disproportionality using the standard Evans methodology (Evans et al., 2001) across 2×2 contingency matrices:

$$\text{PRR} = \frac{a / (a + b)}{c / (c + d)}$$

where:
- $a$ = Case reports with target drug and target adverse reaction
- $b$ = Case reports with target drug and other adverse reactions
- $c$ = Case reports with other drugs and target adverse reaction
- $d$ = Case reports with other drugs and other adverse reactions

### Pearson Chi-Square ($\chi^2$), Uncorrected
$$\chi^2 = \frac{N (ad - bc)^2}{(a + b)(c + d)(a + c)(b + d)}$$
where $N = a + b + c + d$. PharmSignals intentionally uses the uncorrected Pearson statistic (no Yates' continuity correction) to match the standard pharmacovigilance disproportionality convention and the hand-verified openFDA reference values quoted throughout this document (e.g. VIOXX MI $\chi^2 = 839{,}918.65$, the January 2004 backtest value $\chi^2 = 345.40$).

### 95% Log-Normal Confidence Intervals
$$\text{Lower / Upper CI} = \exp\left( \ln(\text{PRR}) \pm 1.96 \sqrt{\frac{1}{a} - \frac{1}{a+b} + \frac{1}{c} - \frac{1}{c+d}} \right)$$

### Regulatory Signal Criteria
- **`SIGNAL` (Confirmed)**: $\text{PRR} \ge 2.0$, $\chi^2 \ge 4.0$, and Case Count $a \ge 3$.
- **`WEAK_SIGNAL`**: Borderline PRR ($\ge 1.5$) or marginal Chi-Square ($\ge 2.0$).
- **`NOISE`**: Does not satisfy statistical disproportionality thresholds.

### Multidimensional Adverse Event Clustering (scikit-learn KMeans & PCA)
PharmSignals groups adverse events into clinical archetypes using unsupervised machine learning across 7 clinical, statistical, and demographic dimensions:
$$\mathbf{x} = [\ln(\text{PRR}), \ln(a), \text{Mortality Rate}, \text{Hospitalization Rate}, \text{Serious Event Rate}, \text{Mean Onset Age}, \text{Female Ratio}]$$
- **Feature Normalization**: Z-score standardization via `StandardScaler`.
- **Partitioning**: $K$-Means clustering ($k \in [2, 8]$, default $k=4$).
- **Dimensionality Reduction**: 2-component Principal Component Analysis (PCA) projecting feature vectors onto an interactive 2D clinical landscape.
- **Archetype Output**: Automatically classifies clusters into explainable phenotypes (*Acute Ischemia & High Mortality*, *Organ Toxicity & Hospitalization*, *Metabolic & Fluid Decompensation*, *General Systemic Reactions*).

---

## 4. Digital-Twin Historical Backtesting (M3)

PharmSignals implements longitudinal monthly walk-forward backtesting using historical openFDA FAERS data artifacts:
- **Vioxx (Rofecoxib)**: Evaluates the myocardial infarction signal across monthly slices starting in 2004, identifying initial signal emergence on **January 31, 2004** ($\text{PRR} = 12.97, \chi^2 = 345.40, a = 31$). This represents **242 days (~8 months)** of early detection lead time before the FDA market withdrawal on September 30, 2004.
- **Avandia (Rosiglitazone)**: Reconstructs the congestive heart failure signal, demonstrating **1,205 days** of early detection lead time prior to the FDA Boxed Warning.
- **Baycol (Cerivastatin)**: Transparently identifies openFDA electronic reporting boundaries (`DATA_UNAVAILABLE_PRE_WITHDRAWAL`), ensuring zero data hallucination for legacy pre-2004 events.

---

## 5. Dossier Submission Readiness Checker (Mode 2)

### ICH M4 Ground-Truth RAG Architecture
PharmSignals indexes structural requirements across all five CTD modules:
- **Module 1**: Regional Administrative Information (1.1–1.5)
- **Module 2**: CTD Summaries & Overviews (2.1–2.7)
- **Module 3**: Quality / CMC (3.1–3.3)
- **Module 4**: Nonclinical Study Reports (4.1–4.3)
- **Module 5**: Clinical Study Reports (5.1–5.4)

### Quantitative Completeness Scoring
$$\text{Readiness Score} = \left( \frac{\text{Validated Sections Count}}{\text{Total Required Sections Count}} \right) \times 100\%$$

### Gap Severity Classification
- **`CRITICAL`**: Missing mandatory summaries or clinical efficacy reports (e.g. Module 2.4, 5.3.5) that represent direct grounds for Refusal-to-File (RTF).
- **`MAJOR`**: Incomplete study reports or analytical validation protocols.
- **`STANDARD`**: Minor formatting or supporting documentation items.

---

## 6. Three-Tier Decision Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Deterministic Analytical Layer (Code-Enforced)                           │
│    • Vectorized PRR, Chi-Square, and log-normal CI computations             │
│    • Exact ICH M4 structural rule verification                              │
│    • In-memory section extraction and completeness percentages              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Grounded AI Reasoning & Copilot (Augmentative)                           │
│    • Contextual clinical explanations for statistical alerts                │
│    • Prioritized regulatory remediation roadmaps                            │
│    • Conversational domain Q&A via IBM Bob AI Copilot                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Qualified Human Oversight (Authoritative)                                │
│    • Medical review and clinical causality assessment                       │
│    • Final regulatory sign-off on submission dossiers                       │
│    • Statutory health authority communications and filing decisions         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. What Makes PharmSignals Different

1. **Zero Dummy Data**: Every displayed analytical metric originates directly from real openFDA FAERS files or deterministic ICH M4 rule engines.
2. **Unified Lifecycle View**: Correlates post-market safety signal detection with pre-market dossier compliance in one workspace.
3. **Reproducible 1-Command Startup**: Starts both backend (FastAPI) and frontend (Next.js) concurrently with `npm run dev`.
4. **Reliable Offline Operation**: Built-in deterministic fallback engines guarantee complete functionality even without external cloud LLM credentials.

---

## 8. Synthetic Benchmark Dossier Disclosure

To maintain absolute regulatory transparency:
- **Synthetic Test Dossier**: The candidate dossier presets (including BOB-701 Oncology IND outline and Vioxx NDA 21-042 outline) and the test benchmark dataset used for evaluating the completeness scoring engine consist of **104 checkable ICH M4 entries** (57 PRESENT, 47 MISSING; yielding a raw completeness score of 54.81%, displayed and rounded to 55%).
- **Verification Purpose**: These datasets are strictly synthetic benchmark dossiers engineered against published ICH M4 CTD specifications to validate the gap detection engine, regression tests, and PDF parser. They do not represent confidential or actual sponsor submission files.
