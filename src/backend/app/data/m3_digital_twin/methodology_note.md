# Digital Twin: Signal Trajectory Projection & Historical Backtest

## Overview
The Digital Twin simulates continuous, time-sliced PRR signal detection across historical reporting horizons, stepping forward monthly and recomputing the cumulative contingency table, PRR, and χ² at each cutoff.

## Detection Rule
A signal is registered at the earliest month where all criteria (PRR ≥ 2.0, a ≥ 3, χ² ≥ 4.0) are met and remain met for 2 additional consecutive months.

## Forward Projection
Monthly volume trends from the last 12 months are modelled (linear vs exponential, selected by R²) and projected 6 months forward.

## Known Limitations

> **Static Background Approximation:** Global background counts (N_reaction and N_total) represent current full-database totals, not what they were at each historical point in time. This backtest approximates historical PRR using today's static background as a stand-in for the true contemporaneous background.

> **Baycol Data Availability:** FAERS electronic data begins ~2004, after Baycol's August 2001 withdrawal. The backtest validates signal-detection logic (Baycol IS flagged as a real signal once data exists) but cannot validate early-detection lead time for this drug.
