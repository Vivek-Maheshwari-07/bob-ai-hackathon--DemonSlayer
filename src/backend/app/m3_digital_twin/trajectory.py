"""Module M3: Digital Twin + Real PRR Trajectory & Historical Backtest.

Loads time-series PRR trajectory data and historical backtesting analysis
derived from actual openFDA FAERS monthly time-slices for VIOXX, BAYCOL, and AVANDIA.
"""

import os
from typing import Any, Dict, List, Optional
import pandas as pd


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

DRUG_ALIASES = {
    "ROFECOXIB": "VIOXX",
    "CERIVASTATIN": "BAYCOL",
    "ROSIGLITAZONE": "AVANDIA",
}


def _normalize_drug_name(drug_name: str) -> str:
    cleaned = drug_name.strip().upper()
    return DRUG_ALIASES.get(cleaned, cleaned)


def generate_prr_trajectory(
    drug_name: str,
    event_term: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Loads real monthly PRR trajectory for a drug from openFDA backtest data.

    Maps:
      - year_month -> 'quarter' (JSON key kept as 'quarter' for frontend compatibility;
        actual time series granularity is monthly YYYY-MM)
      - a_cumulative -> 'n_cases'
      - signal_met (bool) -> 'signal_status' ('SIGNAL' or 'NOISE')
      - is_projected -> passed through directly

    Args:
        drug_name: Name of drug (e.g. 'VIOXX', 'BAYCOL', 'AVANDIA', or alias 'ROFECOXIB').
        event_term: Optional adverse event term filter (for backward compatibility).
        data_dir: Optional path to directory containing m3_digital_twin/.

    Returns:
        List of monthly trajectory dicts.
    """
    if data_dir is None:
        data_dir = DATA_DIR

    norm_drug = _normalize_drug_name(drug_name)
    traj_file = os.path.join(data_dir, "m3_digital_twin", f"{norm_drug}_trajectory.csv")

    if not os.path.exists(traj_file):
        raise FileNotFoundError(f"Trajectory file not found for drug '{norm_drug}': {traj_file}")

    df = pd.read_csv(traj_file)
    trajectory: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        is_signal = bool(row.get("signal_met", False))
        is_proj = bool(row.get("is_projected", False))
        a_cumulative = row["a_cumulative"]
        drug_total_cumulative = row.get("drug_total_cumulative", 0)
        trajectory.append({
            # Key kept as 'quarter' for frontend compatibility; true granularity is monthly (YYYY-MM)
            "quarter": str(row["year_month"]),
            "prr": round(float(row["prr"]), 4),
            "chi_square": round(float(row["chi_square"]), 4),
            "n_cases": 0 if pd.isna(a_cumulative) else int(a_cumulative),
            "signal_status": "SIGNAL" if is_signal else "NOISE",
            "is_projected": is_proj,
            "drug_total_cumulative": 0 if pd.isna(drug_total_cumulative) else int(drug_total_cumulative),
        })

    return trajectory


def run_drug_backtest(drug_name: str, data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Reads backtest_summary.csv and returns standardized backtest report for the drug.

    Handles real outcomes:
      - VIOXX: early detection (+242 days before 2004-09-30 withdrawal)
      - BAYCOL: DATA_UNAVAILABLE_PRE_WITHDRAWAL (openFDA data starts post-withdrawal ~2004; detection_date is 'N/A')
      - AVANDIA: dynamic values read directly from backtest_summary.csv (+1205 days before 2007-05-21 boxed warning)

    Args:
        drug_name: Name of drug ('VIOXX', 'BAYCOL', 'AVANDIA', or alias).
        data_dir: Optional path to directory containing m3_digital_twin/.

    Returns:
        Dict with detection metadata, trajectory, and clinical summary.
    """
    if data_dir is None:
        data_dir = DATA_DIR

    norm_drug = _normalize_drug_name(drug_name)
    summary_file = os.path.join(data_dir, "m3_digital_twin", "backtest_summary.csv")

    if not os.path.exists(summary_file):
        raise FileNotFoundError(f"Backtest summary file not found: {summary_file}")

    df = pd.read_csv(summary_file, keep_default_na=False)
    df["drug_upper"] = df["drug"].astype(str).str.strip().str.upper()
    matches = df[df["drug_upper"] == norm_drug]

    if matches.empty:
        raise ValueError(f"No backtest summary available for drug '{norm_drug}' in {summary_file}")

    row = matches.iloc[0]
    target_term = str(row["target_term"])
    raw_detection = str(row["detection_date"]).strip()
    detection_date = "N/A" if raw_detection in ("", "nan", "NaN", "None", "N/A") else raw_detection
    real_world_action_date = str(row["real_world_action_date"]).strip()
    lead_time_raw = str(row["lead_time_days"]).strip()
    verdict = str(row["verdict"]).strip()

    # Parse numeric lead time if available, otherwise preserve 'N/A'
    if lead_time_raw in ("", "nan", "NaN", "None", "N/A"):
        lead_time_val: Any = "N/A"
    elif lead_time_raw.isdigit() or (lead_time_raw.startswith("-") and lead_time_raw[1:].isdigit()):
        lead_time_val = int(lead_time_raw)
    else:
        try:
            lead_time_val = int(float(lead_time_raw))
        except (ValueError, TypeError):
            lead_time_val = lead_time_raw

    # Load real trajectory
    traj = generate_prr_trajectory(norm_drug, data_dir=data_dir)

    # First signal PRR
    first_signal = next((t for t in traj if t["signal_status"] == "SIGNAL"), None)
    first_signal_prr = first_signal["prr"] if first_signal else 0.0

    # Clinical summaries reflecting verified openFDA reality
    if norm_drug == "VIOXX":
        clinical_summary = (
            "Vioxx (Rofecoxib) was withdrawn from the market on September 30, 2004 due to excess "
            "cardiovascular risk. Monthly walk-forward digital-twin backtesting on real openFDA FAERS data "
            "detected a sustained myocardial infarction signal (PRR ≥ 2.0, χ² ≥ 4.0, a ≥ 3) on January 31, 2004, "
            "providing 242 days (~8 months) of early detection lead time prior to the manufacturer's voluntary withdrawal."
        )
    elif norm_drug == "BAYCOL":
        clinical_summary = (
            "Baycol (Cerivastatin) was withdrawn from the market on August 8, 2001 due to fatal rhabdomyolysis. "
            "Public openFDA FAERS API records begin in 2004, after the withdrawal occurred. "
            "This is a genuine historical data-availability limitation (DATA_UNAVAILABLE_PRE_WITHDRAWAL) of openFDA, "
            "not an analytical or detection failure."
        )
    elif norm_drug == "AVANDIA":
        clinical_summary = (
            f"Avandia (Rosiglitazone) received an FDA Boxed Warning on {real_world_action_date} for congestive heart failure. "
            f"Monthly walk-forward digital-twin backtesting detected a sustained cardiac failure signal on {detection_date}, "
            f"providing {lead_time_raw} days of early detection lead time before the regulatory boxed warning."
        )
    else:
        clinical_summary = (
            f"Digital twin backtest evaluation for {norm_drug} on {target_term}: "
            f"verdict {verdict}, detection date {detection_date}, lead time {lead_time_raw} days."
        )

    return {
        "drug_name": norm_drug,
        "event_term": target_term,
        "trajectory": traj,
        "first_signal_quarter": detection_date,
        "first_signal_prr": first_signal_prr,
        "market_withdrawal_quarter": real_world_action_date,
        # NOTE: Unit mismatch flag - this field holds DAYS (not quarters) from real backtest computation
        "detection_lead_time_quarters": lead_time_val,
        "lead_time_days": lead_time_val,
        "verdict": verdict,
        "clinical_summary": clinical_summary,
        "source_note": (
            "Computed from actual openFDA FAERS monthly time-series and verified regulatory action dates. "
            "Real pipeline backtest output."
        ),
    }


def run_vioxx_backtest(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Returns the Vioxx (Rofecoxib) MI signal backtest reconstruction.

    Thin backward-compatibility wrapper around run_drug_backtest('VIOXX').
    """
    return run_drug_backtest("VIOXX", data_dir=data_dir)


def get_emerging_signals(
    drug_results: List[Dict[str, Any]],
    quarters_window: int = 4,
) -> List[Dict[str, Any]]:
    """Identifies emerging signals with increasing PRR trend over recent time slices.

    Args:
        drug_results: List of trajectory dicts from generate_prr_trajectory().
        quarters_window: Number of recent periods to evaluate for trend.

    Returns:
        List of emerging signal assessments.
    """
    if not drug_results or len(drug_results) < quarters_window:
        return []

    recent = drug_results[-quarters_window:]
    prr_values = [r["prr"] for r in recent]

    # Strictly increasing: a flat/plateaued PRR trend is not "emerging."
    is_increasing = all(prr_values[i] < prr_values[i + 1] for i in range(len(prr_values) - 1))
    latest = recent[-1]
    previous_statuses = [r["signal_status"] for r in recent[:-1]]
    was_below_threshold = any(s != "SIGNAL" for s in previous_statuses)

    if is_increasing and latest["signal_status"] == "SIGNAL" and was_below_threshold:
        return [{
            "emerging": True,
            "first_signal_quarter": latest["quarter"],
            "current_prr": latest["prr"],
            "prr_trend": [r["prr"] for r in recent],
            "quarters_analyzed": quarters_window,
            "assessment": "Emerging signal detected: PRR has been increasing and recently crossed the detection threshold.",
        }]

    return []
