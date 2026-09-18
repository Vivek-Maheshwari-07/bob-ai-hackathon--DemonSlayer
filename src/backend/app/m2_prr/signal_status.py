"""Shared Signal Status Lookup for Module M2.

Provides a single cached source of PRR signal results (built from the
M1 FAERS pipeline) that both the signal-detection API and other modules
(e.g. M4 CTD dossier checker) can query to determine whether a given
drug currently has a CONFIRMED_SIGNAL.
"""

from typing import Any, Dict, List, Optional

from app.m1_faers.faers_ingest import run_m1_pipeline
from app.m2_prr.prr_engine import calculate_prr, classify_signal

_cached_results: Optional[List[Dict[str, Any]]] = None
_cached_drugs: Optional[List[str]] = None


def get_cached_prr_results() -> List[Dict[str, Any]]:
    """Returns cached PRR results computed from the real M1+M2 pipeline."""
    global _cached_results, _cached_drugs
    if _cached_results is None:
        m1 = run_m1_pipeline()
        ct = m1["contingency_table"]
        results = []
        for _, row in ct.iterrows():
            drug = str(row["drug_name"])
            event = str(row["event_term"])
            n_de = float(row.get("n_drug_event", 0))
            n_d = float(row.get("n_drug_total", 0))
            n_e = float(row.get("n_event_total", 0))
            n = float(row.get("n_total", 0))

            stats_result = calculate_prr(n_de, n_d, n_e, n)
            status_val = classify_signal(
                prr=stats_result["prr"],
                chi_square=stats_result["chi_square"],
                n_drug_event=int(n_de),
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
                "signal_status": status_val,
            })

        results.sort(key=lambda x: (-x["prr"], -x["n_drug_event"]))
        _cached_results = results
        _cached_drugs = m1["drugs"]
    return _cached_results


def get_cached_drugs() -> List[str]:
    """Returns the list of unique drug names in the cached dataset."""
    get_cached_prr_results()
    return _cached_drugs or []


def get_drug_signal_status(drug_name: str) -> Dict[str, Any]:
    """Determines whether a drug has an active CONFIRMED_SIGNAL.

    Returns a dict with:
        drug_name: normalized (uppercase) drug name.
        has_confirmed_signal: True if any drug-event pair for this drug is
            classified as "SIGNAL" (the platform's confirmed-signal status).
        confirmed_events: list of the confirmed drug-event signal records.
    """
    drug_upper = (drug_name or "").strip().upper()
    if not drug_upper:
        return {"drug_name": "", "has_confirmed_signal": False, "confirmed_events": []}

    results = get_cached_prr_results()
    confirmed = [
        r for r in results
        if r["drug_name"].upper() == drug_upper and r["signal_status"] == "SIGNAL"
    ]
    # Rank by case count (n_drug_event) rather than raw PRR — PRR alone can spike
    # for rare/low-volume event terms, which buries the clinically meaningful,
    # high-volume signals (e.g. Vioxx + Myocardial Infarction) further down.
    confirmed.sort(key=lambda x: -x["n_drug_event"])

    return {
        "drug_name": drug_upper,
        "has_confirmed_signal": len(confirmed) > 0,
        "confirmed_events": confirmed,
    }
