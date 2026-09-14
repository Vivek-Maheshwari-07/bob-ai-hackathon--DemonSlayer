"""Grounded Regulatory Reasoner powered by Google Gemini 2.5 Flash (Module M4).

Integrates Google Gemini 2.5 Flash for explainable, source-grounded gap reasoning
using exclusively retrieved ICH M4 knowledge. Includes strict quota optimization,
rate-limit safeguards, and deterministic offline fallback.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from app.m4_rag.schema import (
    CriticalityLevel,
    GapItem,
    GapStatus,
)


class GeminiGroundedReasoner:
    """Provides grounded regulatory reasoning and remediation narratives via Gemini 2.5 Flash."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        timeout: float = 20.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or ""
        self.model = model
        self.timeout = timeout

    @property
    def is_available(self) -> bool:
        """Checks if Google Gemini API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def generate_reasoning_insights(
        self,
        priority_gaps: List[GapItem],
        overall_completeness: float,
        submission_title: str = "Candidate CTD Dossier",
    ) -> List[str]:
        """Generates grounded regulatory reasoning insights.
        
        Uses Google Gemini 2.5 Flash if configured; falls back to deterministic rule-based
        reasoning grounded directly in ICH M4 reference texts to respect free-tier quotas.
        """
        if not priority_gaps:
            return [
                f"Full ICH M4 compliance achieved ({overall_completeness:.1f}%). All mandatory sections for Modules 1 through 5 are represented."
            ]

        if self.is_available:
            try:
                insights = self._call_gemini_api(
                    priority_gaps=priority_gaps,
                    overall_completeness=overall_completeness,
                    submission_title=submission_title,
                )
                if insights:
                    return insights
            except Exception:
                # Fall through gracefully to deterministic fallback if API call fails or rate-limited
                pass

        return self._deterministic_fallback_insights(priority_gaps, overall_completeness)

    def _call_gemini_api(
        self,
        priority_gaps: List[GapItem],
        overall_completeness: float,
        submission_title: str,
    ) -> List[str]:
        """Invokes Google Gemini 2.5 Flash with strictly bounded ICH M4 context."""
        # Build ground-truth context block
        context_lines = []
        for gap in priority_gaps[:6]:
            context_lines.append(
                f"- Section {gap.section_id} ({gap.title}) [{gap.module_name}] "
                f"Status: {gap.status.value}, Criticality: {gap.criticality.value}. "
                f"Source: {gap.source_reference}. "
                f"Evidence: {gap.match_evidence.evidence_reasoning}"
            )
        context_str = "\n".join(context_lines)

        prompt = (
            f"You are a Senior Regulatory Affairs Specialist performing an ICH M4 CTD Readiness Review.\n"
            f"Submission Title: {submission_title}\n"
            f"Readiness Score: {overall_completeness:.1f}%\n\n"
            f"EVALUATED ICH M4 GAPS (Ground Truth):\n{context_str}\n\n"
            f"STRICT INSTRUCTIONS:\n"
            f"1. Base your response ONLY on the provided ICH M4 gaps above.\n"
            f"2. DO NOT invent or assume any section numbers or regulatory requirements not listed.\n"
            f"3. Provide 2-3 concise, bulleted strategic recommendations for the regulatory team.\n"
            f"4. Format each bullet point as a single sentence starting with an action verb."
        )

        url = self.GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 512,
            },
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text_content = parts[0].get("text", "")
                        lines = [
                            line.lstrip("*-• ").strip()
                            for line in text_content.strip().splitlines()
                            if line.strip() and not line.startswith("#")
                        ]
                        return lines[:4]

        return []

    def evaluate_section_with_gemini(
        self,
        dossier_title: str,
        dossier_desc: str,
        ich_requirement: Any,
    ) -> Optional[Dict[str, Any]]:
        """Evaluates an ambiguous candidate dossier section against an ICH requirement using Gemini 2.5 Flash.
        
        Takes Relevant Dossier Evidence + Relevant ICH M4 Evidence -> returns PRESENT/PARTIAL/MISSING with evidence reasoning.
        """
        if not self.is_available:
            return None

        prompt = (
            f"Evaluate whether the candidate dossier section satisfies the official ICH M4 requirement.\n\n"
            f"ICH M4 Ground Truth Requirement:\n"
            f"- Section ID: {ich_requirement.section_id}\n"
            f"- Title: {ich_requirement.title}\n"
            f"- Module: {ich_requirement.module_name}\n"
            f"- Requirement: {ich_requirement.requirement_text}\n"
            f"- Source: {ich_requirement.source}\n\n"
            f"Candidate Dossier Evidence:\n"
            f"- Title: {dossier_title}\n"
            f"- Content Summary: {dossier_desc}\n\n"
            f"Instructions:\n"
            f"Determine if the status is PRESENT (complete), PARTIAL (draft/incomplete), or MISSING (unrelated/insufficient).\n"
            f"Format response as:\n"
            f"STATUS: <PRESENT/PARTIAL/MISSING>\n"
            f"REASON: <One sentence explanation grounded strictly in the ICH M4 requirement above>"
        )

        url = self.GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0]["content"]["parts"][0]["text"].strip()
                        status_val = "PARTIAL"
                        reason_val = text
                        for line in text.splitlines():
                            if line.upper().startswith("STATUS:"):
                                raw_st = line.split(":", 1)[1].strip().upper()
                                if raw_st in ("PRESENT", "PARTIAL", "MISSING"):
                                    status_val = raw_st
                            elif line.upper().startswith("REASON:"):
                                reason_val = line.split(":", 1)[1].strip()
                        return {
                            "status": status_val,
                            "reason": reason_val,
                        }
        except Exception:
            pass

        return None

    def _deterministic_fallback_insights(
        self, priority_gaps: List[GapItem], overall_completeness: float
    ) -> List[str]:
        """Deterministic, hallucination-free reasoning synthesized from verified ICH M4 sources."""
        insights: List[str] = []

        crit_missing = [
            g for g in priority_gaps
            if g.status == GapStatus.MISSING and g.criticality == CriticalityLevel.CRITICAL
        ]
        major_missing = [
            g for g in priority_gaps
            if g.status == GapStatus.MISSING and g.criticality == CriticalityLevel.MAJOR
        ]
        partials = [g for g in priority_gaps if g.status == GapStatus.PARTIAL]

        if crit_missing:
            sec_list = ", ".join([f"M{g.module_id} Sec {g.section_id}" for g in crit_missing[:3]])
            insights.append(
                f"Immediate filing barrier: {len(crit_missing)} critical ICH M4 sections ({sec_list}) are completely absent and must be drafted according to ICH guidelines."
            )

        if partials:
            sec_list = ", ".join([f"Sec {g.section_id}" for g in partials[:3]])
            insights.append(
                f"Documentation readiness risk: {len(partials)} sections ({sec_list}) contain preliminary or placeholder data that require formal finalization."
            )

        if major_missing and len(insights) < 3:
            sec_list = ", ".join([f"Sec {g.section_id}" for g in major_missing[:3]])
            insights.append(
                f"Regulatory review risk: {len(major_missing)} major technical sections ({sec_list}) should be provided to ensure full dossier readiness."
            )

        return insights
