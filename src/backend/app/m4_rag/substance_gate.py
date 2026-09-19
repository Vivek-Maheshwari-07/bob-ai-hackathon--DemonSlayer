"""Tier 0 Substance Gate for CTD / ICH M4 RAG Checker (Module M4).

Tier 1 (gap_checker.py) verifies structural presence: does a required
section exist somewhere in the dossier outline, matched by exact ID or
semantic title/description similarity? Tier 2 (content_verifier.py) verifies
grounded content adequacy for a curated set of 8 sections via Gemini.

Neither catches the simplest failure mode of all: a section whose entire
"content" is a title and a self-reported status label ("PRESENT") with zero
actual narrative or technical documentation behind it. A matched header is
not the same thing as a matched requirement — a table of section IDs and
status labels can score 90%+ under Tier 1 alone while containing no real
regulatory documentation whatsoever.

This module is Tier 0: a cheap, deterministic, always-on floor that runs
BEFORE Tier 1's PRESENT/PARTIAL classification, for every one of the ~45 KB
requirements (not just the 8 sections with Tier 2 content_checkpoints). It
only fires when a section actually carries `body_text` — populated by
pdf_extractor.py from genuine multi-line document extraction, or explicitly
supplied by an API caller. Structured dict/API/quick-text submissions that
never set body_text are left untouched, so this never regresses inputs it
wasn't designed to police (a short one-line demo blurb is not the same
failure mode as a label-only 500-page filing).
"""

from typing import Dict, Optional, Set, Tuple

from app.m4_rag.schema import DossierSectionInput, GapStatus, ICHSectionRequirement

# TODO(calibration): these floors are order-of-magnitude estimates based on
# typical ICH CTD section scope, not measured against a real submission.
# Recalibrate against an actual Drugs@FDA approval package (e.g. the Vioxx or
# Avandia Medical/Chemistry Review PDF) once one has been fetched and
# word-counted section by section — these numbers should shift to match
# observed real-world section lengths rather than the estimates below.
MIN_CONTENT_WORDS: Dict[int, Dict[str, int]] = {
    1: {"CRITICAL": 40, "MAJOR": 30, "STANDARD": 10, "OPTIONAL": 10},   # admin — legitimately short
    2: {"CRITICAL": 150, "MAJOR": 100, "STANDARD": 20, "OPTIONAL": 20},  # summaries — moderate
    3: {"CRITICAL": 300, "MAJOR": 150, "STANDARD": 20, "OPTIONAL": 20},  # quality/CMC — data-heavy
    4: {"CRITICAL": 400, "MAJOR": 200, "STANDARD": 20, "OPTIONAL": 20},  # nonclinical study reports
    5: {"CRITICAL": 500, "MAJOR": 250, "STANDARD": 20, "OPTIONAL": 20},  # clinical study reports — heaviest
}

# TODO(calibration): also order-of-magnitude, pending the same real-package
# recalibration pass. A genuine filing with real Module 3/4/5 content spans
# hundreds to thousands of pages for those modules alone.
MIN_PLAUSIBLE_PAGES_IF_MODULE_PRESENT: Dict[int, int] = {3: 200, 4: 300, 5: 500}
SCALE_IMPLAUSIBILITY_RATIO = 0.05  # flag when actual pages < 5% of a plausible minimum


def substance_gate(
    section: Optional[DossierSectionInput],
    requirement: ICHSectionRequirement,
) -> Tuple[Optional[GapStatus], Optional[str]]:
    """Deterministic floor check: does a matched section carry any real content?

    Returns (GapStatus.MISSING, reason) when `section.body_text` was captured
    but its word count falls below the calibrated floor for the
    requirement's module + criticality — i.e. Tier 1 found a header/title
    match, but there is no substantive documentation behind it.

    Returns (None, None) — "gate passed, proceed to normal Tier 1/Tier 2
    evaluation" — when there is nothing to gate on (`section` is None, or its
    `body_text` was never captured, e.g. a dict/API/quick-text submission
    that only ever supplied a short `description`) or when the word count
    clears the floor.
    """
    if section is None or section.body_text is None:
        return None, None

    word_count = len(section.body_text.split())
    criticality_key = (
        requirement.criticality.value
        if hasattr(requirement.criticality, "value")
        else str(requirement.criticality)
    )
    floor = MIN_CONTENT_WORDS.get(requirement.module_id, {}).get(criticality_key, 0)

    if word_count < floor:
        plural = "" if word_count == 1 else "s"
        return (
            GapStatus.MISSING,
            f"Section header matched, but only {word_count} word{plural} of content found "
            f"(minimum {floor} expected for a {criticality_key}-tier Module {requirement.module_id} "
            f"section). Treated as MISSING: a title and status label are not documentation.",
        )
    return None, None


def document_scale_check(
    total_pages: Optional[int],
    total_word_count: Optional[int],
    modules_claimed: Set[int],
) -> Optional[str]:
    """Flags a PDF whose physical scale is implausible for the modules it claims to cover.

    Calibrated against real Drugs@FDA approval packages, where genuine
    Module 3/4/5 content alone typically spans hundreds to thousands of
    pages. Returns None when `total_pages` is unavailable (non-PDF input),
    no modules were claimed, or the document's scale is plausible for every
    claimed module.
    """
    if not total_pages or not modules_claimed:
        return None

    flagged = [
        f"Module {module_id}"
        for module_id in sorted(modules_claimed)
        if (expected_min := MIN_PLAUSIBLE_PAGES_IF_MODULE_PRESENT.get(module_id)) is not None
        and total_pages < expected_min * SCALE_IMPLAUSIBILITY_RATIO
    ]
    if not flagged:
        return None

    return (
        f"DOCUMENT SCALE WARNING: This submission is {total_pages} page(s) total "
        f"({total_word_count or 0} words extracted). A real CTD filing containing genuine "
        f"{', '.join(flagged)} content would typically span hundreds to thousands of pages for "
        f"those modules alone. This document's scale is inconsistent with substantive content in "
        f"the modules it claims to cover — treat any 'PRESENT' status in this filing with strong "
        f"suspicion; automated readiness scoring on this document is not meaningful."
    )
