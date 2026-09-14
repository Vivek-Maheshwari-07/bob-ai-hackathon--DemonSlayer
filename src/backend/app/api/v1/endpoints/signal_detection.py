"""FastAPI Endpoints for Modules M1, M2, M3: Signal Detection (Real OpenFDA Pipeline)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.m1_faers.faers_ingest import run_m1_pipeline
from app.m2_prr.prr_engine import calculate_prr, classify_signal, get_signals_only
from app.m3_digital_twin.trajectory import (
    generate_prr_trajectory,
    run_vioxx_backtest,
    run_drug_backtest,
)

router = APIRouter(prefix="/signals", tags=["Module M2: Signal Detection"])

# Cache M1+M2 results at module level
_cached_results: Optional[List[Dict[str, Any]]] = None
_cached_drugs: Optional[List[str]] = None


def _get_prr_results() -> List[Dict[str, Any]]:
    """Returns cached PRR results computed from real M1+M2 pipeline."""
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


@router.get(
    "/",
    summary="List All PRR Signal Results",
    description="Returns full ranked list of drug safety signals from M1+M2 pipeline. Signals ranked by PRR descending.",
)
async def get_all_signals(
    drug: Optional[str] = Query(default=None, description="Filter by drug name (case-insensitive)"),
    status_filter: Optional[str] = Query(default=None, description="Filter by signal status: SIGNAL, WEAK_SIGNAL, NOISE"),
    signals_only: bool = Query(default=False, description="Return only confirmed SIGNAL entries"),
) -> List[Dict[str, Any]]:
    """Returns PRR signal results with optional filters."""
    try:
        results = _get_prr_results()
        if signals_only:
            results = get_signals_only(results)
        if drug:
            results = [r for r in results if r["drug_name"].upper() == drug.upper()]
        if status_filter:
            results = [r for r in results if r["signal_status"] == status_filter.upper()]
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal analysis error: {str(e)}")


@router.get(
    "/drugs",
    summary="List Available Drugs in Dataset",
)
async def get_available_drugs() -> List[str]:
    """Returns list of unique drug names in the dataset."""
    try:
        _get_prr_results()  # Ensure cached
        global _cached_drugs
        return _cached_drugs or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/summary",
    summary="Signal Detection Summary",
    description="Returns high-level summary statistics for the signal detection pipeline.",
)
async def get_signal_summary() -> Dict[str, Any]:
    """Returns summary statistics of signal analysis."""
    try:
        results = _get_prr_results()
        signal_count = sum(1 for r in results if r["signal_status"] == "SIGNAL")
        weak_count = sum(1 for r in results if r["signal_status"] == "WEAK_SIGNAL")
        noise_count = sum(1 for r in results if r["signal_status"] == "NOISE")
        return {
            "total_drug_event_pairs": len(results),
            "confirmed_signals": signal_count,
            "weak_signals": weak_count,
            "noise": noise_count,
            "top_signals": [r for r in results if r["signal_status"] == "SIGNAL"][:10],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/trajectory/{drug_name}/{event_term}",
    summary="PRR Trajectory for Drug-Event Pair",
    description="Returns time-series PRR trajectory data for a specific drug-event pair from real openFDA backtest data.",
)
async def get_prr_trajectory(drug_name: str, event_term: str) -> Dict[str, Any]:
    """Returns PRR time-series trajectory for a drug-event pair."""
    try:
        trajectory = generate_prr_trajectory(drug_name, event_term)
        return {
            "drug_name": drug_name.upper(),
            "event_term": event_term.upper(),
            "trajectory": trajectory,
            "total_quarters": len(trajectory),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/vioxx-backtest",
    summary="Vioxx (Rofecoxib) Historical PRR Backtest",
    description=(
        "Returns the real openFDA PRR signal trajectory for Vioxx myocardial "
        "infarction, demonstrating how early pharmacovigilance monitoring detected "
        "the cardiovascular safety signal 242 days before market withdrawal."
    ),
)
async def get_vioxx_backtest() -> Dict[str, Any]:
    """Returns the historical Vioxx signal backtest analysis."""
    try:
        return run_vioxx_backtest()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/backtest/{drug_name}",
    summary="Drug Safety Signal Historical Backtest",
    description="Returns walk-forward digital-twin backtest analysis for any supported drug (VIOXX, BAYCOL, AVANDIA).",
)
async def get_drug_backtest(drug_name: str) -> Dict[str, Any]:
    """Returns historical backtest analysis for the requested drug."""
    try:
        return run_drug_backtest(drug_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
