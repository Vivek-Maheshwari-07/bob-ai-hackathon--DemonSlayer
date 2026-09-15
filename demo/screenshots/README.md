# Application Screenshots & Trajectory Visualizations

This directory contains verified visual captures and analytical trajectories from the **PharmSignals** platform.

## Application Interface Screenshots

1. **PharmSignals Central Dashboard (`01-dashboard.png`)**:
   - High-level pharmacovigilance intelligence overview displaying key clinical metrics (222 Confirmed Signals, Peak PRR 1725.08x, CTD Submission Readiness percentage, Critical Gaps count).
   - Interactive Adverse Event Bubble Chart with $\text{PRR} = 2.0$ critical threshold reference line and High-Priority Signals Table.

2. **Signal Detection & Adverse Event Clustering Studio (`02-signal-detection.png`)**:
   - Multi-dimensional adverse event clustering powered by scikit-learn (StandardScaler, KMeans, PCA 2D projection) across 7 clinical and demographic features.
   - Interactive 2D clinical scatter landscape with 4 clinical cluster archetypes (*Acute Ischemia & High Mortality*, *General Systemic Reactions*, *Organ Toxicity & Hospitalization*, *Metabolic & Fluid Decompensation*).
   - Interactive 2×2 Contingency Table Calculator with real openFDA benchmark presets (*Vioxx/MI*, *Baycol/Rhabdomyolysis*, *Avandia/Heart Failure*).

3. **ICH M4 Dossier Submission Readiness Checker (`03-readiness-checker.png`)**:
   - Automated CTD dossier structure audit across Modules 1 to 5.
   - Circular Overall Completeness Score Gauge alongside horizontal module progress meters.
   - Filterable **Priority Regulatory Gap Matrix** with severity classification (`CRITICAL`, `MAJOR`, `STANDARD`), official ICH M4 citations, and actionable remediation roadmaps.

## Analytical Trajectory Benchmark Visualizations

- **`VIOXX_trajectory.png`**: Longitudinal monthly PRR walk-forward trajectory demonstrating **+242 days of early safety signal detection** prior to FDA market withdrawal.
- **`AVANDIA_trajectory.png`**: Longitudinal PRR trajectory demonstrating **+1,205 days of early detection lead time** for rosiglitazone congestive heart failure.
- **`BAYCOL_trajectory.png`**: Empirical analysis of electronic openFDA boundary constraints for pre-2004 cerivastatin reporting.
