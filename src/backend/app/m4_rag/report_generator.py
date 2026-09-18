"""Gap Report Generator for CTD / ICH M4 RAG Checker (Module M4).

Aggregates evaluations, scoring, priority gaps, and actionable
remediation recommendations into a structured, frontend-friendly report.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx as _httpx
except ImportError:
    _httpx = None

from app.m4_rag.completeness import CompletenessScorer
from app.m4_rag.schema import (
    CriticalityLevel,
    DossierOutlineInput,
    GapItem,
    GapReportOutput,
    GapStatus,
    ModuleCompleteness,
)


class ReportGenerator:
    """Generates structured ICH M4 gap analysis reports."""

    CRITICALITY_ORDER = {
        CriticalityLevel.CRITICAL: 1,
        CriticalityLevel.MAJOR: 2,
        CriticalityLevel.STANDARD: 3,
        CriticalityLevel.OPTIONAL: 4,
    }

    def __init__(self, scorer: Optional[CompletenessScorer] = None):
        self.scorer = scorer or CompletenessScorer()

    def generate_report(
        self,
        outline: DossierOutlineInput,
        gap_items: List[GapItem],
        reasoning_insights: Optional[List[str]] = None,
        safety_signal_linkage: Optional[Dict[str, Any]] = None,
    ) -> GapReportOutput:
        """Constructs full GapReportOutput.

        Args:
            outline: Candidate dossier outline input.
            gap_items: Full list of evaluated ICH requirements.
            reasoning_insights: Optional LLM-grounded narrative insights.
            safety_signal_linkage: Optional Mode 1 (M2 PRR) signal cross-link summary.

        Returns:
            Validated GapReportOutput instance.
        """
        overall_score, module_scores = self.scorer.calculate(gap_items)

        present_list = [item for item in gap_items if item.status == GapStatus.PRESENT]
        partial_list = [item for item in gap_items if item.status == GapStatus.PARTIAL]
        missing_list = [item for item in gap_items if item.status in (GapStatus.MISSING, GapStatus.INSUFFICIENT_EVIDENCE)]

        # Priority gaps: Missing or Partial items, ordered by Criticality then section ID
        priority_gaps = [
            item for item in gap_items
            if item.status != GapStatus.PRESENT and item.criticality in (CriticalityLevel.CRITICAL, CriticalityLevel.MAJOR)
        ]
        priority_gaps.sort(
            key=lambda x: (self.CRITICALITY_ORDER.get(x.criticality, 99), x.module_id, x.section_id)
        )

        critical_gaps_count = sum(
            1 for item in gap_items
            if item.status != GapStatus.PRESENT and item.criticality == CriticalityLevel.CRITICAL
        )

        # Build prioritized actionable recommendations
        recommended_actions = self._build_recommendations(
            priority_gaps=priority_gaps,
            module_scores=module_scores,
            reasoning_insights=reasoning_insights,
        )

        # Standard assessment limitations
        limitations = [
            "Assessment evaluates structural presence, section organization, and summary descriptions against ICH M4 (M4, M4Q, M4S, M4E) guidelines.",
            "Evaluation does not replace formal regulatory agency filing validation or full medical/scientific review of raw clinical datasets.",
            "Regional Module 1 requirements are assessed against general ICH regional specifications and should be tailored for target jurisdiction (e.g. FDA 21 CFR vs EMA Notice to Applicants).",
        ]

        now_iso = datetime.now(timezone.utc).isoformat()

        return GapReportOutput(
            submission_title=outline.submission_title or "Candidate CTD Dossier",
            drug_name=outline.drug_name or "",
            target_region=outline.target_region or "Global / ICH",
            overall_completeness=overall_score,
            total_sections_evaluated=len(gap_items),
            present_total=len(present_list),
            partial_total=len(partial_list),
            missing_total=len(missing_list),
            critical_gaps_count=critical_gaps_count,
            modules=module_scores,
            present_sections=present_list,
            partial_sections=partial_list,
            missing_sections=missing_list,
            priority_gaps=priority_gaps,
            recommended_actions=recommended_actions,
            limitations=limitations,
            timestamp=now_iso,
            safety_signal_linkage=safety_signal_linkage,
        )

    def _build_recommendations(
        self,
        priority_gaps: List[GapItem],
        module_scores: Dict[str, ModuleCompleteness],
        reasoning_insights: Optional[List[str]] = None,
    ) -> List[str]:
        """Synthesizes prioritized remediation steps.

        Attempts a live Gemini call to narrate the ACTUAL priority_gaps list already computed
        (grounded — never lets Bob invent gaps, only explains the real ones computed above).
        Falls back to the deterministic bullet list if the API is unavailable.
        """
        actions: List[str] = []

        if reasoning_insights:
            for insight in reasoning_insights:
                if insight and insight.strip():
                    actions.append(insight.strip())

        # Attempt live Gemini narrative for the computed gaps (grounded, not hallucinated)
        gemini_narrative = self._gemini_narrate_gaps(priority_gaps)
        if gemini_narrative:
            actions.extend(gemini_narrative)

        if not actions:
            # Deterministic fallback — always runs if Gemini is unavailable
            actions = self._deterministic_recommendations(priority_gaps, module_scores)

        return actions

    def _deterministic_recommendations(
        self,
        priority_gaps: List[GapItem],
        module_scores: Dict[str, ModuleCompleteness],
    ) -> List[str]:
        """Deterministic fallback: always-available remediation steps."""
        actions: List[str] = []

        # Top critical missing items
        crit_missing = [g for g in priority_gaps if g.status == GapStatus.MISSING and g.criticality == CriticalityLevel.CRITICAL]
        if crit_missing:
            crit_ids = ", ".join([f"Section {g.section_id} ({g.title})" for g in crit_missing[:5]])
            actions.append(
                f"[CRITICAL BLOCKER] Remedy {len(crit_missing)} missing core ICH requirements immediately before filing: {crit_ids}."
            )

        # Partial items needing finalization
        partials = [g for g in priority_gaps if g.status == GapStatus.PARTIAL]
        if partials:
            partial_ids = ", ".join([f"Section {g.section_id}" for g in partials[:4]])
            actions.append(
                f"[ACTION REQUIRED] Finalize draft / preliminary documentation in {len(partials)} sections: {partial_ids}."
            )

        # Module-specific recommendations
        for mod_key, mod_data in module_scores.items():
            if mod_data.completeness_percentage < 60.0:
                actions.append(
                    f"[{mod_data.module_name.upper()}] Readiness is currently at {mod_data.completeness_percentage:.1f}%. Prioritize nonclinical/clinical/quality deliverables for this module."
                )

        if not actions:
            actions.append("All core ICH M4 sections are verified and complete. Ready for formal submission readiness audit.")

        return actions

    def _gemini_narrate_gaps(self, priority_gaps: List[GapItem]) -> List[str]:
        """Uses Gemini 2.5 Flash to narrate ONLY the actual computed gaps — never invents new ones.

        Falls back to [] if the API key is unset or the call fails (caller uses deterministic fallback).
        """
        if _httpx is None:
            return []
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key.strip():
            return []
        if not priority_gaps:
            return []

        # Build a grounded context block from the ACTUAL computed gaps
        gap_lines = []
        for gap in priority_gaps[:8]:
            gap_lines.append(
                f"- [{gap.criticality.value}] Section {gap.section_id} ({gap.title}) "
                f"in {gap.module_name}: status={gap.status.value}. ICH ref: {gap.source_reference}."
            )
        gaps_block = "\n".join(gap_lines)

        prompt = (
            f"You are a Senior Regulatory Affairs Specialist reviewing an ICH M4 CTD dossier gap analysis.\n\n"
            f"The following gaps were COMPUTED by the automated ICH M4 RAG engine (ground truth — do not alter or invent gaps):\n"
            f"{gaps_block}\n\n"
            f"STRICT INSTRUCTIONS:\n"
            f"1. Write 2–4 concise, actionable remediation recommendations BASED SOLELY on the gaps listed above.\n"
            f"2. DO NOT invent section numbers, regulatory citations, or gaps not present in the list above.\n"
            f"3. Each recommendation must start with an action verb and reference specific section IDs from the list.\n"
            f"4. Return plain text, one recommendation per line, no markdown headers."
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
            }
            with _httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                        if text:
                            lines = [
                                line.lstrip("*-•0123456789. ").strip()
                                for line in text.strip().splitlines()
                                if line.strip()
                            ]
                            return [f"[BOB RECOMMENDATION] {l}" for l in lines[:4] if l]
        except Exception:
            pass

        return []
