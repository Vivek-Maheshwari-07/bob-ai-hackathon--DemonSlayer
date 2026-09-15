"""FastAPI Endpoints for Modules M1, M2, M3: Signal Detection (Real OpenFDA Pipeline)."""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    import httpx
except ImportError:
    httpx = None

from app.m1_faers.faers_ingest import run_m1_pipeline
from app.m2_prr.prr_engine import (
    calculate_prr,
    classify_signal,
    get_signals_only,
    DEFAULT_PRR_THRESHOLD,
    DEFAULT_CHI_SQUARE_THRESHOLD,
    DEFAULT_MIN_CASES,
)
from app.m3_digital_twin.trajectory import (
    generate_prr_trajectory,
    run_vioxx_backtest,
    run_drug_backtest,
)

router = APIRouter(prefix="/signals", tags=["Module M2: Signal Detection"])

# Cache M1+M2 results at module level
_cached_results: Optional[List[Dict[str, Any]]] = None
_cached_drugs: Optional[List[str]] = None


class CustomPRRRequest(BaseModel):
    drug_name: str = Field(default="CANDIDATE-DRUG", description="Suspect drug name")
    event_term: str = Field(default="SUSPECTED REACTION", description="Target adverse event term")
    # Supports both (a, b, c, d) 2x2 cells OR (n_de, n_dt, n_et, n_total) margins
    a: Optional[float] = Field(default=None, description="Cell a: Drug + Event count")
    b: Optional[float] = Field(default=None, description="Cell b: Drug + Other Events count")
    c: Optional[float] = Field(default=None, description="Cell c: Other Drugs + Event count")
    d: Optional[float] = Field(default=None, description="Cell d: Other Drugs + Other Events count")
    a_drug_event: Optional[float] = Field(default=None, description="Alias for cell a")
    b_drug_other_events: Optional[float] = Field(default=None, description="Alias for cell b")
    c_other_drugs_event: Optional[float] = Field(default=None, description="Alias for cell c")
    d_other_drugs_other_events: Optional[float] = Field(default=None, description="Alias for cell d")
    n_drug_event: Optional[float] = Field(default=None, description="Alias for cell a")
    n_drug_total: Optional[float] = Field(default=None, description="Total reports for drug (a + b)")
    n_event_total: Optional[float] = Field(default=None, description="Total reports for event (a + c)")
    n_total: Optional[float] = Field(default=None, description="Grand total reports (a + b + c + d)")
    prr_threshold: float = Field(default=DEFAULT_PRR_THRESHOLD, description="PRR signal threshold")
    chi_square_threshold: float = Field(default=DEFAULT_CHI_SQUARE_THRESHOLD, description="Chi-square signal threshold")
    min_cases: int = Field(default=DEFAULT_MIN_CASES, description="Minimum case count threshold")


# Known real-pipeline drug names — Gemini enrichment is for ARBITRARY (non-preset) pairs only
_KNOWN_PRESET_DRUGS = {"ROFECOXIB", "VIOXX", "CERIVASTATIN", "BAYCOL", "ROSIGLITAZONE", "AVANDIA"}


def _gemini_interpret_arbitrary_pair(
    drug_name: str,
    event_term: str,
    prr: float,
    chi_square: float,
    n_cases: int,
    signal_status: str,
) -> Optional[str]:
    """Calls Gemini 2.5 Flash to provide a clinical interpretation for an arbitrary drug-event pair.

    Only called when the drug is NOT one of the known preset drugs (Vioxx/Baycol/Avandia),
    since those already have deterministic expert context. Falls back to None if the API key
    is not set or the call fails — the caller will then use the deterministic explanation.
    """
    if httpx is None:
        return None
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key.strip():
        return None

    prompt = (
        f"You are IBM Bob, a pharmacovigilance expert assistant.\n"
        f"A custom 2×2 contingency table analysis just returned these VERIFIED statistical results:\n"
        f"- Drug: {drug_name}\n"
        f"- Adverse Event: {event_term}\n"
        f"- PRR (Proportional Reporting Ratio): {prr:.4f}\n"
        f"- Pearson Chi-Square: {chi_square:.4f}\n"
        f"- Case Count (a): {n_cases}\n"
        f"- Evans Signal Classification: {signal_status}\n\n"
        f"Provide a concise 2–3 sentence clinical interpretation of these specific numbers. "
        f"State clearly whether the criteria for a confirmed signal are met (PRR ≥ 2.0, χ² ≥ 4.0, a ≥ 3). "
        f"Do NOT invent regulatory history, causal claims, or clinical findings not derivable from these numbers alone."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
        }
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                    if text:
                        return text.strip()
    except Exception:
        pass

    return None


class CustomPRRResponse(BaseModel):
    drug_name: str
    event_term: str
    n_drug_event: int
    n_drug_total: int
    n_event_total: int
    n_total: int
    contingency_table: Dict[str, int]
    metrics: Dict[str, float]
    signal_status: str
    is_signal: bool
    explanation: str
    bob_interpretation: Optional[str] = None


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


@router.post(
    "/calculate",
    response_model=CustomPRRResponse,
    summary="Calculate PRR & Chi-Square on Custom 2x2 Contingency Table",
    description="Calculates Evans Proportional Reporting Ratio and Pearson Chi-Square for custom user-provided case numbers or 2x2 cell values.",
)
async def calculate_custom_prr(
    payload: CustomPRRRequest = Body(...),
) -> CustomPRRResponse:
    """Calculates PRR, chi-square, confidence intervals, and signal status on custom user inputs."""
    try:
        # Resolve cell 'a' / n_drug_event
        a_val = payload.a if payload.a is not None else (
            payload.a_drug_event if payload.a_drug_event is not None else (
                payload.n_drug_event if payload.n_drug_event is not None else 0.0
            )
        )
        b_val = payload.b if payload.b is not None else payload.b_drug_other_events
        c_val = payload.c if payload.c is not None else payload.c_other_drugs_event
        d_val = payload.d if payload.d is not None else payload.d_other_drugs_other_events

        # Resolve margins
        if payload.n_drug_total is not None and payload.n_event_total is not None and payload.n_total is not None:
            n_dt = payload.n_drug_total
            n_et = payload.n_event_total
            n_tot = payload.n_total
            b = max(n_dt - a_val, 0.0)
            c = max(n_et - a_val, 0.0)
            d = max(n_tot - n_dt - c, 0.0)
            a = a_val
        elif b_val is not None and c_val is not None and d_val is not None:
            a = a_val
            b = b_val
            c = c_val
            d = d_val
            n_dt = a + b
            n_et = a + c
            n_tot = a + b + c + d
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either (a, b, c, d) cells or (n_drug_event, n_drug_total, n_event_total, n_total) margins.",
            )

        stats_res = calculate_prr(n_drug_event=a, n_drug_total=n_dt, n_event_total=n_et, n_total=n_tot)
        status_val = classify_signal(
            prr=stats_res["prr"],
            chi_square=stats_res["chi_square"],
            n_drug_event=int(a),
            prr_threshold=payload.prr_threshold,
            chi_sq_threshold=payload.chi_square_threshold,
            min_cases=payload.min_cases,
        )

        is_sig = (status_val == "SIGNAL")

        if is_sig:
            explanation = (
                f"CONFIRMED SAFETY SIGNAL: PRR = {stats_res['prr']:.2f} (≥ {payload.prr_threshold}), "
                f"Chi² = {stats_res['chi_square']:.2f} (≥ {payload.chi_square_threshold}, p = {stats_res['p_value']:.4f}), "
                f"and case count N = {int(a)} (≥ {payload.min_cases}). Disproportionate reporting confirmed."
            )
        elif status_val == "WEAK_SIGNAL":
            explanation = (
                f"WEAK / BORDERLINE SIGNAL: PRR = {stats_res['prr']:.2f}, Chi² = {stats_res['chi_square']:.2f}. "
                f"Meets elevated PRR trend but marginal on statistical thresholds or sample size."
            )
        else:
            explanation = (
                f"NO SIGNAL / NOISE: PRR = {stats_res['prr']:.2f}, Chi² = {stats_res['chi_square']:.2f}, cases = {int(a)}. "
                f"Does not satisfy standard pharmacovigilance disproportionality thresholds."
            )

        # For arbitrary (non-preset) drug-event pairs, try a live Gemini call to give a
        # clinical interpretation grounded in the real computed numbers. The deterministic
        # explanation above is always the guaranteed fallback.
        drug_upper = payload.drug_name.strip().upper()
        is_arbitrary = not any(k in drug_upper for k in _KNOWN_PRESET_DRUGS)
        bob_interp: Optional[str] = None
        if is_arbitrary:
            bob_interp = _gemini_interpret_arbitrary_pair(
                drug_name=payload.drug_name,
                event_term=payload.event_term,
                prr=stats_res["prr"],
                chi_square=stats_res["chi_square"],
                n_cases=int(a),
                signal_status=status_val,
            )

        return CustomPRRResponse(
            drug_name=payload.drug_name.upper(),
            event_term=payload.event_term.upper(),
            n_drug_event=int(a),
            n_drug_total=int(n_dt),
            n_event_total=int(n_et),
            n_total=int(n_tot),
            contingency_table={
                "a_drug_event": int(a),
                "b_drug_other_events": int(b),
                "c_other_drugs_event": int(c),
                "d_other_drugs_other_events": int(d),
            },
            metrics=stats_res,
            signal_status=status_val,
            is_signal=is_sig,
            explanation=explanation,
            bob_interpretation=bob_interp,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom PRR calculation error: {str(e)}")


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
