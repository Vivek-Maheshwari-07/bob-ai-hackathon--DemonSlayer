"""Completeness Scorer for CTD / ICH M4 RAG Checker (Module M4).

Performs deterministic, reproducible scoring of CTD dossier completeness
both overall and module-by-module (Modules 1 to 5).
"""

from typing import Dict, List, Optional, Tuple
from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.schema import (
    CriticalityLevel,
    GapItem,
    GapStatus,
    ICHSectionRequirement,
    ModuleCompleteness,
)


class CompletenessScorer:
    """Calculates deterministic completeness metrics for CTD dossiers."""

    # Transparent scoring weights (per-section status score)
    WEIGHT_PRESENT = 1.0
    WEIGHT_PARTIAL = 0.5
    WEIGHT_MISSING = 0.0

    # Regulatory-criticality weights: a missing/partial CRITICAL section (a
    # direct Refusal-to-File blocker) counts for more than a STANDARD one, so
    # the headline readiness score reflects filing risk rather than a flat
    # section count.
    CRITICALITY_WEIGHTS = {
        CriticalityLevel.CRITICAL: 3.0,
        CriticalityLevel.MAJOR: 2.0,
        CriticalityLevel.STANDARD: 1.0,
        CriticalityLevel.OPTIONAL: 0.5,
    }

    # Tier 2 content-adequacy downgrade thresholds: when a section has a
    # content_adequacy_score (grounded checkpoint verification ran), that
    # score overrides the Tier-1 structural status for scoring purposes.
    # Sections with content_adequacy_score=None (no checkpoints for that
    # section, or Gemini unavailable/failed) keep their original Tier-1
    # status score unchanged — Tier 2 is additive, never a regression.
    CONTENT_ADEQUACY_PRESENT_THRESHOLD = 0.8
    CONTENT_ADEQUACY_PARTIAL_THRESHOLD = 0.4

    # Tier 3 content-authenticity downgrade: the grounded verdict from
    # comparing a section against real exemplar text is the last tier in the
    # pipeline (Tier 1 -> substance gate -> Tier 2 -> Tier 3 -> final status),
    # so when it ran (authenticity_verdict is not None) it is the final word
    # on effective status, overriding whatever Tier 1/2 decided. SUBSTANTIVE
    # leaves the prior tiers' effective status untouched. Sections where
    # Tier 3 never ran (no exemplars yet, section didn't pass the substance
    # gate, or Gemini unavailable) keep falling through to the Tier 2 / Tier 1
    # logic below, unchanged.
    AUTHENTICITY_STATUS_OVERRIDE = {
        "GENERIC": WEIGHT_PARTIAL,
        "INSUFFICIENT": WEIGHT_MISSING,
    }

    # Consolidated guideline-grounded check (guideline_grounded_checker.py):
    # the current, single content-verification tier run after the substance
    # gate. Same override semantics as Tier 3 above — GENERIC downgrades to
    # PARTIAL, INSUFFICIENT/EMPTY downgrade to MISSING, SUBSTANTIVE (or no
    # verdict at all, i.e. the check didn't run) leaves the substance-gated
    # Tier 1 status unchanged.
    GUIDELINE_STATUS_OVERRIDE = {
        "GENERIC": WEIGHT_PARTIAL,
        "INSUFFICIENT": WEIGHT_MISSING,
        "EMPTY": WEIGHT_MISSING,
    }

    MODULE_NAMES = {
        1: "Module 1: Administrative Information",
        2: "Module 2: CTD Summaries",
        3: "Module 3: Quality",
        4: "Module 4: Nonclinical Study Reports",
        5: "Module 5: Clinical Study Reports",
    }

    def __init__(self, kb: Optional[KnowledgeBaseLoader] = None):
        self.kb = kb or get_knowledge_base()

    def _effective_status_score(self, item: GapItem) -> float:
        """Returns the per-item status score used in the weighted formula.

        Tier precedence (last tier that actually ran wins): the consolidated
        guideline-grounded verdict, if present, is final. Otherwise falls
        back to the legacy Tier 3 authenticity verdict if present (kept for
        backward compatibility with anything still setting it directly), then
        Tier 2 content-adequacy score, then the original Tier-1/substance-gate
        PRESENT/PARTIAL/MISSING status, unchanged.
        """
        guideline_verdict = getattr(item, "guideline_verdict", None)
        if guideline_verdict in self.GUIDELINE_STATUS_OVERRIDE:
            return self.GUIDELINE_STATUS_OVERRIDE[guideline_verdict]

        verdict = getattr(item, "authenticity_verdict", None)
        if verdict in self.AUTHENTICITY_STATUS_OVERRIDE:
            return self.AUTHENTICITY_STATUS_OVERRIDE[verdict]
        # A SUBSTANTIVE verdict (or no verdict at all, i.e. neither check ran)
        # falls through deliberately, leaving whatever Tier 2 / Tier 1 already
        # decided unchanged.

        score = getattr(item, "content_adequacy_score", None)
        if score is not None:
            if score >= self.CONTENT_ADEQUACY_PRESENT_THRESHOLD:
                return self.WEIGHT_PRESENT
            if score >= self.CONTENT_ADEQUACY_PARTIAL_THRESHOLD:
                return self.WEIGHT_PARTIAL
            return self.WEIGHT_MISSING

        if item.status == GapStatus.PRESENT:
            return self.WEIGHT_PRESENT
        if item.status == GapStatus.PARTIAL:
            return self.WEIGHT_PARTIAL
        return self.WEIGHT_MISSING

    def calculate(
        self, gap_items: List[GapItem]
    ) -> Tuple[float, Dict[str, ModuleCompleteness]]:
        """Calculates overall completeness percentage and module-wise breakdown.

        Formula (criticality-weighted):
            earned_points = sum(criticality_weight(item) * status_score(item))
            max_points = sum(criticality_weight(item))
            completeness = (earned_points / max_points) * 100

        where status_score is 1.0 / 0.5 / 0.0 for PRESENT / PARTIAL / MISSING,
        and criticality_weight scales CRITICAL sections higher than STANDARD
        ones, so a missing filing-blocker section drags the score down more
        than a missing supporting document would.

        Returns:
            Tuple of (overall_completeness_percentage, module_metrics_dict)
        """
        # Group gap items by module
        module_items: Dict[int, List[GapItem]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        for item in gap_items:
            if 1 <= item.module_id <= 5:
                module_items[item.module_id].append(item)

        module_results: Dict[str, ModuleCompleteness] = {}
        total_earned = 0.0
        total_possible = 0.0

        for mod_id in range(1, 6):
            items = module_items[mod_id]
            total_req = len(items)

            present_cnt = sum(1 for i in items if i.status == GapStatus.PRESENT)
            partial_cnt = sum(1 for i in items if i.status == GapStatus.PARTIAL)
            missing_cnt = sum(1 for i in items if i.status in (GapStatus.MISSING, GapStatus.INSUFFICIENT_EVIDENCE))
            crit_missing_cnt = sum(
                1 for i in items
                if i.status != GapStatus.PRESENT and i.criticality == CriticalityLevel.CRITICAL
            )

            mod_earned = 0.0
            mod_possible = 0.0
            for i in items:
                w = self.CRITICALITY_WEIGHTS.get(i.criticality, 1.0)
                mod_earned += w * self._effective_status_score(i)
                mod_possible += w * self.WEIGHT_PRESENT

            mod_pct = (mod_earned / mod_possible * 100.0) if mod_possible > 0 else 0.0
            mod_pct = round(mod_pct, 2)

            total_earned += mod_earned
            total_possible += mod_possible

            mod_key = f"module_{mod_id}"
            module_results[mod_key] = ModuleCompleteness(
                module_id=mod_id,
                module_name=self.MODULE_NAMES.get(mod_id, f"Module {mod_id}"),
                total_required=total_req,
                present_count=present_cnt,
                partial_count=partial_cnt,
                missing_count=missing_cnt,
                critical_missing_count=crit_missing_cnt,
                completeness_percentage=mod_pct,
            )

        overall_pct = (total_earned / total_possible * 100.0) if total_possible > 0 else 0.0
        overall_pct = round(overall_pct, 2)

        return overall_pct, module_results
