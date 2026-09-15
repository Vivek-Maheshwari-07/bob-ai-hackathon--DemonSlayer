# Application Screenshots & Trajectory Visualizations

This directory contains verified visual captures and analytical trajectories from the **PharmSignals** platform.

## Application Interface Screenshots

1. **PharmSignals Central Dashboard (`01-dashboard-overview.png` / `01-dashboard.png`)**:
   - High-level pharmacovigilance intelligence overview displaying key clinical metrics (222 Confirmed Signals, Peak PRR 1725.08x, CTD Submission Readiness percentage, Critical Gaps count).
   - Interactive Adverse Event Bubble Chart with $\text{PRR} = 2.0$ critical threshold reference line.

2. **High-Priority Signals Registry (`02-high-priority-signals.png`)**:
   - Ranked FAERS surveillance table sorted by Proportional Reporting Ratio (PRR) descending with Pearson $\chi^2$ statistics, Case Counts ($a$), and 95% Confidence Intervals.

3. **Adverse Event Clustering Studio (`03-clustering-studio.png` / `02-signal-detection.png`)**:
   - Multi-dimensional adverse event clustering powered by scikit-learn (`StandardScaler`, `KMeans`, `PCA` 2D projection) across 7 clinical and demographic features.
   - Interactive 2D clinical scatter landscape with 4 clinical cluster archetypes (*Cluster 1: Acute Ischemia & High Mortality*, *Cluster 2: General Systemic & Moderate Reactions*, *Cluster 3: Organ Toxicity & Hospitalization*, *Cluster 4: Metabolic & Fluid Decompensation*).

4. **2×2 Contingency Table Analysis (`04-contingency-analysis.png`)**:
   - Interactive 2×2 Contingency Table Calculator with real openFDA benchmark presets (*Vioxx / MI*, *Baycol / Rhabdomyolysis*, *Avandia / Heart Failure*) and Evans criterion statistical evaluation.

5. **Historical Longitudinal Validation & Lead Time (`05-historical-backtest.png`)**:
   - M3 Digital Twin simulation showcasing walk-forward longitudinal PRR trajectory for Vioxx (Myocardial Infarction) crossing threshold at `2004-01-31` ahead of FDA market action `2004-09-30` (**+242 days early detection lead time**).

6. **ICH M4 Dossier Submission Readiness Checker (`03-readiness-checker.png`)**:
   - Automated CTD dossier structure audit across Modules 1 to 5.
   - Circular Overall Completeness Score Gauge alongside horizontal module progress meters.
   - Filterable **Priority Regulatory Gap Matrix** with severity classification (`CRITICAL`, `MAJOR`, `STANDARD`), official ICH M4 citations, and actionable remediation roadmaps.

## Analytical Trajectory Benchmark Visualizations

- **`VIOXX_trajectory.png`**: Longitudinal monthly PRR walk-forward trajectory demonstrating **+242 days of early safety signal detection** prior to FDA market withdrawal.
- **`AVANDIA_trajectory.png`**: Longitudinal PRR trajectory demonstrating **+1,205 days of early detection lead time** for rosiglitazone congestive heart failure.
- **`BAYCOL_trajectory.png`**: Empirical analysis of electronic openFDA boundary constraints for pre-2004 cerivastatin reporting.
