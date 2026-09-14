"""Module M2: PRR Signal Engine.

Calculates Proportional Reporting Ratio (PRR), chi-square statistics,
and applies configurable signal detection thresholds to rank drug safety signals.

PRR Formula (Evans et al., 2001):
    PRR = (n_drug_event / n_drug_total) / (n_event_total / n_total)
    Chi-square corrects for expected vs observed counts.

Signal criteria (standard FDA/EMA threshold):
    PRR >= 2.0 AND chi_square >= 4.0 AND n_drug_event >= 3
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from scipy import stats


# ─── Default signal detection thresholds ──────────────────────────────────
DEFAULT_PRR_THRESHOLD = 2.0
DEFAULT_CHI_SQUARE_THRESHOLD = 4.0
DEFAULT_MIN_CASES = 3


def calculate_prr(
    n_drug_event: float,
    n_drug_total: float,
    n_event_total: float,
    n_total: float,
) -> Dict[str, float]:
    """Calculates PRR and chi-square for a single drug-event cell.

    Args:
        n_drug_event: Reports of this specific drug+event pair.
        n_drug_total: Total reports mentioning this drug.
        n_event_total: Total reports mentioning this event (all drugs).
        n_total: Grand total of all reports.

    Returns:
        Dict with prr, log_prr, chi_square, p_value, lower_ci, upper_ci.
        Returns sentinel values on edge cases (zero denominators etc.).
    """
    # Edge case guards
    if n_drug_event < 1 or n_drug_total < 1 or n_event_total < 1 or n_total < 2:
        return {
            "prr": 0.0,
            "log_prr": float("-inf"),
            "chi_square": 0.0,
            "p_value": 1.0,
            "lower_ci": 0.0,
            "upper_ci": 0.0,
        }

    # Proportional Reporting Ratio
    a = n_drug_event                           # Drug+Event
    b = n_drug_total - n_drug_event            # Drug+NoEvent
    c = n_event_total - n_drug_event           # NoDrug+Event
    d = n_total - n_drug_total - c            # NoDrug+NoEvent

    b = max(b, 0)
    c = max(c, 0)
    d = max(d, 0)

    p_drug_event = a / n_drug_total
    p_ref_event = n_event_total / n_total

    if p_ref_event <= 0:
        return {
            "prr": 0.0,
            "log_prr": float("-inf"),
            "chi_square": 0.0,
            "p_value": 1.0,
            "lower_ci": 0.0,
            "upper_ci": 0.0,
        }

    prr = p_drug_event / p_ref_event

    # Log PRR
    log_prr = np.log(prr) if prr > 0 else float("-inf")

    # 95% CI using log-normal approximation (standard method)
    se_log_prr = np.sqrt(1/a - 1/n_drug_total + 1/c - 1/n_event_total) if (a > 0 and c > 0) else float("inf")
    lower_ci = np.exp(log_prr - 1.96 * se_log_prr) if np.isfinite(se_log_prr) else 0.0
    upper_ci = np.exp(log_prr + 1.96 * se_log_prr) if np.isfinite(se_log_prr) else float("inf")

    # Chi-square test (2x2 contingency table)
    try:
        expected_a = (n_drug_total * n_event_total) / n_total
        observed = [[a, b], [c, d]]
        chi2, p_val, _, _ = stats.chi2_contingency(observed, correction=False)
    except Exception:
        chi2, p_val = 0.0, 1.0

    return {
        "prr": round(float(prr), 4),
        "log_prr": round(float(log_prr), 4),
        "chi_square": round(float(chi2), 4),
        "p_value": round(float(p_val), 6),
        "lower_ci": round(float(lower_ci), 4),
        "upper_ci": round(float(min(upper_ci, 9999.0)), 4),
    }


def classify_signal(
    prr: float,
    chi_square: float,
    n_drug_event: int,
    prr_threshold: float = DEFAULT_PRR_THRESHOLD,
    chi_sq_threshold: float = DEFAULT_CHI_SQUARE_THRESHOLD,
    min_cases: int = DEFAULT_MIN_CASES,
) -> str:
    """Applies standard pharmacovigilance signal criteria.

    Criteria (Evans et al., 2001 / FDA pharmacovigilance guidance):
        SIGNAL: PRR >= threshold AND chi_sq >= threshold AND n >= min_cases
        WEAK_SIGNAL: PRR >= threshold but other criteria marginal
        NOISE: Insufficient evidence

    Returns:
        One of: "SIGNAL", "WEAK_SIGNAL", "NOISE"
    """
    if n_drug_event < min_cases:
        return "NOISE"
    if prr >= prr_threshold and chi_square >= chi_sq_threshold:
        return "SIGNAL"
    if prr >= prr_threshold * 0.75:
        return "WEAK_SIGNAL"
    return "NOISE"


def run_prr_analysis(
    contingency_table: pd.DataFrame,
    prr_threshold: float = DEFAULT_PRR_THRESHOLD,
    chi_sq_threshold: float = DEFAULT_CHI_SQUARE_THRESHOLD,
    min_cases: int = DEFAULT_MIN_CASES,
    max_signals: int = 100,
) -> List[Dict[str, Any]]:
    """Runs full PRR signal analysis over a contingency table from M1.

    Args:
        contingency_table: Output from M1 build_contingency_table().
        prr_threshold: PRR threshold for signal classification.
        chi_sq_threshold: Chi-square threshold for signal classification.
        min_cases: Minimum case count threshold.
        max_signals: Maximum number of ranked results to return.

    Returns:
        List of signal dicts sorted by PRR descending, with status classification.
    """
    if contingency_table is None or contingency_table.empty:
        return []

    results = []

    for _, row in contingency_table.iterrows():
        drug = str(row["drug_name"])
        event = str(row["event_term"])
        n_de = float(row.get("n_drug_event", 0))
        n_d = float(row.get("n_drug_total", 0))
        n_e = float(row.get("n_event_total", 0))
        n = float(row.get("n_total", 0))

        stats_result = calculate_prr(n_de, n_d, n_e, n)
        signal_status = classify_signal(
            prr=stats_result["prr"],
            chi_square=stats_result["chi_square"],
            n_drug_event=int(n_de),
            prr_threshold=prr_threshold,
            chi_sq_threshold=chi_sq_threshold,
            min_cases=min_cases,
        )

        results.append({
            "drug_name": drug,
            "event_term": event,
            "n_drug_event": int(n_de),
            "n_drug_total": int(n_d),
            "n_event_total": int(n_e),
            "n_total": int(n),
            "prr": stats_result["prr"],
            "log_prr": stats_result["log_prr"],
            "chi_square": stats_result["chi_square"],
            "p_value": stats_result["p_value"],
            "lower_ci_95": stats_result["lower_ci"],
            "upper_ci_95": stats_result["upper_ci"],
            "signal_status": signal_status,
        })

    # Rank by PRR descending, then by n_drug_event descending
    results.sort(key=lambda x: (-x["prr"], -x["n_drug_event"]))

    return results[:max_signals]


def get_signals_only(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters to only SIGNAL classified drug-event pairs."""
    return [r for r in results if r["signal_status"] == "SIGNAL"]


def get_signals_for_drug(results: List[Dict[str, Any]], drug_name: str) -> List[Dict[str, Any]]:
    """Returns all PRR results for a specific drug."""
    return [r for r in results if r["drug_name"].upper() == drug_name.upper()]
