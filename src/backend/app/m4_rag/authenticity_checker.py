"""Tier 3 Content-Authenticity Checker powered by Google Gemini 2.5 Flash (Module M4).

Tier 1 (gap_checker.py) checks structural presence. The substance gate
(substance_gate.py) checks that a matched section has enough words behind it
to not be a bare title/status-label row. Tier 2 (content_verifier.py) checks
whether a section's content explicitly answers a fixed set of ICH-grounded
checkpoint questions.

None of those catch a well-written but hollow section: plausible regulatory
language, correctly keyworded, long enough to clear the substance gate, and
even able to answer Tier 2's yes/no checkpoint questions in the abstract —
but containing zero actual concrete data points (no real numbers, dates,
species, sample sizes, endpoints, p-values) that a genuine study report
would contain. Tier 3 catches this by grounding the judgment in a comparison
against REAL exemplar text from an actual regulatory document, rather than
judging the candidate in isolation.

Reuses the same Gemini HTTP client pattern, strict-grounding prompt style,
and try/except fallback-safe behavior as gemini_reasoner.py / content_verifier.py,
so Tier 3 can be skipped silently (result=None) without ever crashing Tier 1's
report — whether because Gemini is unavailable, or because the exemplar
corpus has no (non-placeholder) exemplars for this section yet.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

VALID_VERDICTS = ("SUBSTANTIVE", "GENERIC", "INSUFFICIENT")


class AuthenticityResult:
    """Grounded Tier 3 verdict comparing a candidate section against real exemplar text."""

    def __init__(
        self,
        verdict: str,
        missing_data_points: List[str],
        candidate_citation: Optional[str],
        exemplar_citations: List[str],
        reasoning: str,
    ):
        self.verdict = verdict  # SUBSTANTIVE / GENERIC / INSUFFICIENT
        self.missing_data_points = missing_data_points  # up to 3 named missing data-point types
        self.candidate_citation = candidate_citation
        self.exemplar_citations = exemplar_citations
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "missing_data_points": self.missing_data_points,
            "candidate_citation": self.candidate_citation,
            "exemplar_citations": self.exemplar_citations,
            "reasoning": self.reasoning,
        }


class AuthenticityChecker:
    """Compares a candidate dossier section against real exemplar text via Gemini 2.5 Flash."""

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
        """Checks if Google Gemini API key is configured and httpx is available."""
        return bool(self.api_key and self.api_key.strip() and httpx is not None)

    def check_content_authenticity(
        self,
        candidate_section: Dict[str, str],
        exemplars: List[Dict[str, str]],
    ) -> Optional[AuthenticityResult]:
        """Runs one grounded Gemini comparison of a candidate section against real exemplars.

        `candidate_section` is {"section_id", "title", "text"}. `exemplars` is
        a list of {"source_citation", "exemplar_text"} dicts (from
        ExemplarRetriever.retrieve()).

        Returns None — "skip Tier 3 for this section" — when Gemini is
        unavailable, there are no exemplars to compare against, the
        candidate has no text, or the call/parse fails for any reason.
        Never raises.
        """
        if not exemplars:
            return None
        if not self.is_available or not (candidate_section.get("text") or "").strip():
            return None

        try:
            return self._call_gemini_api(candidate_section, exemplars)
        except Exception:
            return None

    def _call_gemini_api(
        self,
        candidate_section: Dict[str, str],
        exemplars: List[Dict[str, str]],
    ) -> Optional[AuthenticityResult]:
        exemplars_block = "\n\n".join(
            f'EXEMPLAR {i + 1} (source: "{ex.get("source_citation", "Unknown source")}"):\n'
            f'{ex.get("exemplar_text", "")}'
            for i, ex in enumerate(exemplars)
        )

        prompt = (
            "You are a strict regulatory document auditor performing an authenticity check. "
            "You will be shown a CANDIDATE section from a submitted CTD dossier, and one or more "
            "REAL EXEMPLAR excerpts drawn from actual, previously-approved regulatory documents "
            "for the same ICH CTD section type. Your job is to judge whether the candidate reads "
            "like genuine regulatory documentation, by comparing it against the real exemplar(s) "
            "— not by judging the candidate in isolation.\n\n"
            f"CANDIDATE SECTION (section {candidate_section.get('section_id', '?')} — "
            f"{candidate_section.get('title', '')}):\n"
            "-----\n"
            f"{candidate_section.get('text', '')}\n"
            "-----\n\n"
            "REAL EXEMPLAR EXCERPT(S) — genuine text from real regulatory documents:\n"
            "-----\n"
            f"{exemplars_block}\n"
            "-----\n\n"
            "STRICT INSTRUCTIONS:\n"
            "1. Compare the CANDIDATE against the EXEMPLAR(S) specifically for the presence of "
            "concrete, verifiable data points that a genuine section of this type would contain "
            "(e.g. specific numbers, dates, sample sizes, species, doses, endpoints, statistical "
            "results, p-values, named studies) — the kind of detail the exemplar(s) actually "
            "contain and generic filler text would not.\n"
            "2. Quote a short supporting excerpt from the CANDIDATE (or note that none exists) as "
            "'candidate_citation', and quote a short supporting excerpt from the EXEMPLAR(S) as "
            "'exemplar_citations' (a list, one short quote per exemplar used), so both sides of the "
            "comparison are grounded in an exact excerpt rather than your own paraphrase.\n"
            "3. Classify the candidate with exactly one verdict:\n"
            "   - SUBSTANTIVE: the candidate contains real, concrete data points comparable in kind "
            "to the exemplar(s), not just plausible-sounding language.\n"
            "   - GENERIC: the candidate is well-written, correctly keyworded, and superficially "
            "plausible, but contains no (or almost no) concrete data points — it could describe "
            "almost any product of this type.\n"
            "   - INSUFFICIENT: the candidate is off-topic, contradicts the section's purpose, or "
            "is too thin/vague to compare at all.\n"
            "4. List up to 3 specific types of concrete data points that are present in the "
            "exemplar(s) but missing from the candidate, as 'missing_data_points' (an empty list "
            "if the verdict is SUBSTANTIVE and nothing meaningful is missing).\n"
            "5. Do not invent facts about the candidate or the exemplar(s); base every judgment "
            "strictly on the text shown above.\n"
            "6. Respond with ONLY a single JSON object (no markdown fences, no commentary), in "
            "this exact shape:\n"
            '{"verdict": "SUBSTANTIVE|GENERIC|INSUFFICIENT", '
            '"missing_data_points": ["...", "..."], '
            '"candidate_citation": "<short quote or null>", '
            '"exemplar_citations": ["<short quote>", "..."], '
            '"reasoning": "<one sentence>"}'
        )

        url = self.GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None
            raw_text = parts[0].get("text", "").strip()

        parsed = self._parse_json_object(raw_text)
        if not isinstance(parsed, dict):
            return None

        verdict = str(parsed.get("verdict", "")).strip().upper()
        if verdict not in VALID_VERDICTS:
            return None

        missing_points = parsed.get("missing_data_points") or []
        if not isinstance(missing_points, list):
            missing_points = []
        missing_points = [str(p).strip() for p in missing_points if str(p).strip()][:3]

        exemplar_citations = parsed.get("exemplar_citations") or []
        if not isinstance(exemplar_citations, list):
            exemplar_citations = []
        exemplar_citations = [str(c).strip() for c in exemplar_citations if str(c).strip()]

        candidate_citation = parsed.get("candidate_citation")
        if isinstance(candidate_citation, str) and not candidate_citation.strip():
            candidate_citation = None

        return AuthenticityResult(
            verdict=verdict,
            missing_data_points=missing_points,
            candidate_citation=candidate_citation,
            exemplar_citations=exemplar_citations,
            reasoning=str(parsed.get("reasoning", "")).strip(),
        )

    @staticmethod
    def _parse_json_object(raw_text: str) -> Optional[Any]:
        """Extracts and parses a JSON object from the model's raw text response."""
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except (ValueError, TypeError):
            pass

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except (ValueError, TypeError):
                return None
        return None
