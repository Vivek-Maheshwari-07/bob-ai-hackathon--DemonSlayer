"""Live openFDA FAERS Lookup.

Unlike the pre-loaded VIOXX/BAYCOL/AVANDIA benchmark pipeline (M1 ingestion of
static CSV snapshots), this module queries the real openFDA `drug/event.json`
API live, for an arbitrary drug name, and reuses the existing verified
`calculate_prr` / `classify_signal` engine from prr_engine.py on the resulting
counts — no PRR/chi-square math is duplicated here.
"""

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

from app.m2_prr.prr_engine import calculate_prr, classify_signal, DEFAULT_MIN_CASES

OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"
OPENFDA_TIMEOUT_SECONDS = 8.0

# The unfiltered grand-total report count changes extremely slowly (it's the
# whole FAERS database), so caching it avoids one redundant outbound openFDA
# call on every single live lookup.
_GRAND_TOTAL_CACHE_TTL_SECONDS = 3600
_cached_grand_total: Optional[int] = None
_cached_grand_total_at: float = 0.0

# openFDA's search syntax is Lucene-like; strip characters that could break out
# of the quoted field or inject query operators (this is a public, read-only
# third-party API, but sanitizing untrusted input into any query string is
# good hygiene regardless).
_UNSAFE_CHARS = re.compile(r'["\\:()\[\]{}]')


def _sanitize_term(term: str) -> str:
    return _UNSAFE_CHARS.sub("", term).strip()


def _openfda_count(client: "httpx.Client", search_query: Optional[str] = None) -> int:
    """Returns the total report count for a search query (0 if openFDA finds no matches)."""
    params: Dict[str, Any] = {"limit": 1}
    if search_query:
        params["search"] = search_query
    resp = client.get(OPENFDA_EVENT_URL, params=params)
    if resp.status_code == 404:
        return 0
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("meta", {}).get("results", {}).get("total", 0))


def _openfda_grand_total(client: "httpx.Client") -> int:
    """Returns the unfiltered FAERS report grand total, cached for an hour."""
    global _cached_grand_total, _cached_grand_total_at
    now = time.monotonic()
    if _cached_grand_total is not None and (now - _cached_grand_total_at) < _GRAND_TOTAL_CACHE_TTL_SECONDS:
        return _cached_grand_total

    total = _openfda_count(client)
    _cached_grand_total = total
    _cached_grand_total_at = now
    return total


def _openfda_top_event_term(client: "httpx.Client", drug_query: str) -> Optional[str]:
    """Auto-discovers the most frequently reported adverse event for a drug."""
    resp = client.get(
        OPENFDA_EVENT_URL,
        params={"search": drug_query, "count": "patient.reaction.reactionmeddrapt.exact"},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["term"] if results else None


def lookup_live_signal(
    drug_name: str,
    event_term: Optional[str] = None,
    min_cases: int = DEFAULT_MIN_CASES,
) -> Dict[str, Any]:
    """Queries openFDA live for a drug (and optional event) and computes a real-time PRR signal.

    Always returns a well-formed result dict (never raises) so a live demo
    failure degrades gracefully instead of surfacing a 500. `success=False`
    entries carry a human-readable `error` explaining why no signal could be
    computed (openFDA unreachable, drug not found, or too few reports).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_drug = _sanitize_term(drug_name or "")
    clean_event = _sanitize_term(event_term) if event_term else None

    base: Dict[str, Any] = {
        "drug_name": clean_drug.upper(),
        "event_term": clean_event.upper() if clean_event else None,
        "source": "LIVE_OPENFDA_API",
        "queried_at": now_iso,
    }

    if not clean_drug:
        return {**base, "success": False, "error": "drug_name is required."}

    if httpx is None:
        return {**base, "success": False, "error": "httpx is not installed on the server; live lookup unavailable."}

    try:
        with httpx.Client(timeout=OPENFDA_TIMEOUT_SECONDS) as client:
            drug_query = f'patient.drug.medicinalproduct:"{clean_drug}"'
            n_drug_total = _openfda_count(client, drug_query)

            if n_drug_total == 0:
                return {
                    **base,
                    "success": False,
                    "error": (
                        f"No openFDA FAERS reports found for drug '{clean_drug}'. "
                        f"Try the exact medicinal product name (e.g. IBUPROFEN, METFORMIN)."
                    ),
                }

            resolved_event = clean_event
            if not resolved_event:
                resolved_event = _openfda_top_event_term(client, drug_query)
                if not resolved_event:
                    return {
                        **base,
                        "success": False,
                        "error": f"Drug '{clean_drug}' has reports but no adverse event terms were returned by openFDA.",
                    }
                base["event_term"] = resolved_event.upper()

            event_query = f'patient.reaction.reactionmeddrapt:"{resolved_event}"'
            n_event_total = _openfda_count(client, event_query)
            n_drug_event = _openfda_count(client, f"{drug_query} AND {event_query}")
            n_total = _openfda_grand_total(client)
    except httpx.TimeoutException:
        return {**base, "success": False, "error": "openFDA API request timed out. Please try again."}
    except httpx.HTTPError as e:
        return {**base, "success": False, "error": f"openFDA API is unreachable: {e}"}

    if n_drug_event < min_cases:
        return {
            **base,
            "success": False,
            "error": (
                f"Only {n_drug_event} co-reported case(s) found for {base['drug_name']} + "
                f"{base['event_term']} (minimum {min_cases} required for a reliable PRR signal)."
            ),
            "n_drug_total": n_drug_total,
            "n_event_total": n_event_total,
            "n_drug_event": n_drug_event,
            "n_total": n_total,
        }

    stats_res = calculate_prr(
        n_drug_event=n_drug_event,
        n_drug_total=n_drug_total,
        n_event_total=n_event_total,
        n_total=n_total,
    )
    signal_status = classify_signal(
        prr=stats_res["prr"],
        chi_square=stats_res["chi_square"],
        n_drug_event=n_drug_event,
        min_cases=min_cases,
    )
    is_signal = signal_status == "SIGNAL"

    b = max(n_drug_total - n_drug_event, 0)
    c = max(n_event_total - n_drug_event, 0)
    d = max(n_total - n_drug_total - c, 0)

    if is_signal:
        explanation = (
            f"LIVE CONFIRMED SIGNAL: PRR = {stats_res['prr']:.2f}, Chi² = {stats_res['chi_square']:.2f}, "
            f"case count = {n_drug_event}. Computed live from current openFDA FAERS data."
        )
    elif signal_status == "WEAK_SIGNAL":
        explanation = (
            f"LIVE WEAK/BORDERLINE SIGNAL: PRR = {stats_res['prr']:.2f}, Chi² = {stats_res['chi_square']:.2f}. "
            f"Computed live from current openFDA FAERS data."
        )
    else:
        explanation = (
            f"LIVE RESULT — NO SIGNAL: PRR = {stats_res['prr']:.2f}, Chi² = {stats_res['chi_square']:.2f}, "
            f"cases = {n_drug_event}. Does not meet disproportionality thresholds."
        )

    return {
        **base,
        "success": True,
        "n_drug_total": n_drug_total,
        "n_event_total": n_event_total,
        "n_drug_event": n_drug_event,
        "n_total": n_total,
        "contingency_table": {
            "a_drug_event": n_drug_event,
            "b_drug_other_events": b,
            "c_other_drugs_event": c,
            "d_other_drugs_other_events": d,
        },
        "metrics": stats_res,
        "signal_status": signal_status,
        "is_signal": is_signal,
        "explanation": explanation,
    }
