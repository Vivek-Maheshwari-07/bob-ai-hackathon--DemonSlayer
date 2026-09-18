"""Cross-links Mode 1 (M2 PRR Signal Detection) with Mode 2 (M4 CTD Dossier Checker).

When a drug has an active CONFIRMED_SIGNAL from the FAERS/PRR pipeline, the
CTD dossier for that same drug must flag its safety-related sections —
Module 2.7 (Clinical Summary, incl. 2.7.4 Summary of Clinical Safety) and
Module 5.3.6 (Reports of Postmarketing Experience / PSUR-PBRER, the
Module 5 clinical safety update section) — as requiring mandatory review.
"""

import logging
from typing import Any, Dict, List, Optional

from app.m2_prr.signal_status import get_drug_signal_status
from app.m4_rag.schema import GapItem

logger = logging.getLogger(__name__)

# ICH M4 section IDs treated as "safety-related" for the purposes of this linkage.
SAFETY_FLAG_SECTION_IDS = ["2.7", "5.3.6"]


def apply_safety_signal_flags(
    drug_name: Optional[str],
    gap_items: List[GapItem],
) -> Dict[str, Any]:
    """Flags safety-related gap items when the drug has a confirmed FAERS signal.

    Mutates the matching GapItem entries in-place (sets requires_safety_update
    and safety_update_reason) and returns a summary dict describing the
    linkage, suitable for surfacing as a banner in the gap report / frontend.
    """
    drug_upper = (drug_name or "").strip().upper()
    if not drug_upper:
        return {
            "drug_name": "",
            "has_confirmed_signal": False,
            "flagged_section_ids": [],
            "confirmed_events": [],
            "message": None,
        }

    try:
        status = get_drug_signal_status(drug_upper)
    except Exception:
        # Signal pipeline unavailable — never let this break the dossier
        # check, but log it: silently returning "no signal" here would
        # otherwise look identical to a drug that's genuinely clean, which
        # is a real false-negative risk in a safety-critical cross-link.
        logger.exception(
            "safety_signal_link: get_drug_signal_status(%r) failed; "
            "reporting no confirmed signal as a fail-soft default.",
            drug_upper,
        )
        return {
            "drug_name": drug_upper,
            "has_confirmed_signal": False,
            "flagged_section_ids": [],
            "confirmed_events": [],
            "message": None,
        }

    if not status["has_confirmed_signal"]:
        return {
            "drug_name": drug_upper,
            "has_confirmed_signal": False,
            "flagged_section_ids": [],
            "confirmed_events": [],
            "message": None,
        }

    top_events = status["confirmed_events"][:3]
    events_str = "; ".join(
        f"{e['event_term']} (PRR={e['prr']:.2f})" for e in top_events
    )
    reason = (
        f"CONFIRMED_SIGNAL on file for {drug_upper} ({events_str}). "
        f"Mandatory safety review required for this section before submission."
    )

    for item in gap_items:
        if item.section_id in SAFETY_FLAG_SECTION_IDS:
            item.requires_safety_update = True
            item.safety_update_reason = reason

    return {
        "drug_name": drug_upper,
        "has_confirmed_signal": True,
        "flagged_section_ids": list(SAFETY_FLAG_SECTION_IDS),
        "confirmed_events": top_events,
        "message": (
            f"Active safety signal detected for {drug_upper} — "
            f"Module 2.7 (Summary of Clinical Safety) and Module 5.3.6 "
            f"(Postmarketing Safety Update) require mandatory review."
        ),
    }
