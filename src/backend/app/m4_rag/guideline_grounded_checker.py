"""Guideline-Grounded Content Checker powered by Claude Haiku (Module M4).

This is the consolidated content-verification tier: it replaces the earlier
separate Tier 2 (content_checkpoints/content_verifier.py, Gemini) and Tier 3
(exemplar_corpus/authenticity_checker.py, Gemini) proposals with a single
grounded check against the ACTUAL ICH guideline requirement text for a
section (knowledge/guideline_excerpts.json), run via Claude Haiku.

Runs strictly after the substance gate (substance_gate.py): a section the
gate already forced to MISSING has no real text worth checking against a
guideline. For sections that pass the gate, this checker compares the
candidate's real body_text against the guideline excerpt for that
section_id and returns a SUBSTANTIVE / GENERIC / INSUFFICIENT / EMPTY
verdict, plus which key_requirements are present (with quoted candidate
evidence) and which are absent.

Wrapped entirely in try/except -> graceful no-op: if ANTHROPIC_API_KEY is
unset, the anthropic SDK isn't installed, the API call fails, or no excerpt
exists for the candidate's section_id, this returns None and the caller
keeps the prior tier's status untouched. This is deliberately the same
fail-open contract as gemini_reasoner.py / content_verifier.py have around
GEMINI_API_KEY, so an unpopulated/misconfigured key never breaks Tier 1.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from app.core.config import settings
except Exception:  # pragma: no cover - config import shouldn't fail, but never let it break this module
    settings = None

VALID_VERDICTS = ("SUBSTANTIVE", "GENERIC", "INSUFFICIENT", "EMPTY")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class GuidelineCheckResult:
    """Grounded verdict comparing a candidate section against its real ICH guideline excerpt."""

    def __init__(
        self,
        verdict: str,
        requirements_present: List[Dict[str, str]],
        requirements_absent: List[str],
        citation: str,
        reasoning: str = "",
    ):
        self.verdict = verdict  # SUBSTANTIVE / GENERIC / INSUFFICIENT / EMPTY
        self.requirements_present = requirements_present  # [{"requirement": str, "evidence": str}]
        self.requirements_absent = requirements_absent  # [str]
        self.citation = citation
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "requirements_present": self.requirements_present,
            "requirements_absent": self.requirements_absent,
            "citation": self.citation,
            "reasoning": self.reasoning,
        }


class GuidelineGroundedChecker:
    """Compares a candidate CTD section's real text against its ICH guideline excerpt via Claude Haiku."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, timeout: float = 20.0):
        self.api_key = (
            api_key
            or os.getenv("ANTHROPIC_API_KEY")
            or (getattr(settings, "ANTHROPIC_API_KEY", "") if settings is not None else "")
            or ""
        )
        self.model = model
        self.timeout = timeout

    @property
    def is_available(self) -> bool:
        """Checks if the Anthropic API key is configured and the SDK is installed."""
        return bool(self.api_key and self.api_key.strip() and anthropic is not None)

    def check_against_guideline(
        self,
        candidate_section: Dict[str, str],
        excerpt_record: Dict[str, Any],
    ) -> Optional[GuidelineCheckResult]:
        """Runs one grounded Claude Haiku comparison of a candidate section against its guideline excerpt.

        `candidate_section` is {"section_id", "title", "body_text"}.
        `excerpt_record` is one entry from guideline_excerpts.json
        ({"section_id", "guideline_name", "citation", "excerpt_text",
        "key_requirements"}).

        Returns None — "skip this tier, keep the prior tier's status" — when
        Claude is unavailable, there's no excerpt or candidate text, or the
        call/parse fails for any reason. Never raises.
        """
        if not excerpt_record or not (excerpt_record.get("excerpt_text") or "").strip():
            return None
        if not self.is_available or not (candidate_section.get("body_text") or "").strip():
            return None

        try:
            return self._call_claude(candidate_section, excerpt_record)
        except Exception:
            return None

    def _call_claude(
        self,
        candidate_section: Dict[str, str],
        excerpt_record: Dict[str, Any],
    ) -> Optional[GuidelineCheckResult]:
        key_requirements = excerpt_record.get("key_requirements") or []
        requirements_block = "\n".join(f"- {r}" for r in key_requirements) or "(none listed)"

        prompt = (
            "You are a strict regulatory document auditor. You will be shown the actual ICH "
            "guideline requirement text for one CTD section, followed by a candidate section's "
            "real text submitted in a dossier. Judge the candidate ONLY against the guideline "
            "excerpt shown — do not invent requirements beyond it, and do not invent evidence "
            "that is not literally present in the candidate text.\n\n"
            f"ICH GUIDELINE EXCERPT (citation: {excerpt_record.get('citation', 'Unknown')}):\n"
            "-----\n"
            f"{excerpt_record.get('excerpt_text', '')}\n"
            "-----\n\n"
            "KEY REQUIREMENTS DERIVED FROM THIS EXCERPT:\n"
            f"{requirements_block}\n\n"
            f"CANDIDATE SECTION (section {candidate_section.get('section_id', '?')} — "
            f"{candidate_section.get('title', '')}):\n"
            "-----\n"
            f"{candidate_section.get('body_text', '')}\n"
            "-----\n\n"
            "STRICT INSTRUCTIONS:\n"
            "1. For each key requirement listed above, determine whether the candidate text "
            "literally and explicitly addresses it. If yes, quote the exact supporting sentence "
            "or phrase from the candidate as evidence — never paraphrase or infer evidence that "
            "isn't literally there.\n"
            "2. Classify the candidate with exactly one verdict:\n"
            "   - SUBSTANTIVE: most/all key requirements are explicitly addressed with concrete, "
            "specific content (real numbers, named studies, specific criteria) — not just "
            "plausible-sounding language.\n"
            "   - GENERIC: the candidate is well-written and correctly keyworded but is vague or "
            "generic where the guideline calls for something concrete — few or no requirements "
            "are genuinely, concretely satisfied.\n"
            "   - INSUFFICIENT: the candidate is off-topic, contradicts the section's purpose, or "
            "addresses at most a trivial fraction of the requirements.\n"
            "   - EMPTY: the candidate text contains no substantive content at all relevant to "
            "this guideline (e.g. only a title, a status label, or boilerplate).\n"
            "3. Respond with ONLY a single JSON object (no markdown fences, no commentary), in "
            "this exact shape:\n"
            '{"verdict": "SUBSTANTIVE|GENERIC|INSUFFICIENT|EMPTY", '
            '"requirements_present": [{"requirement": "<one from the list above>", '
            '"evidence": "<exact quote from candidate>"}], '
            '"requirements_absent": ["<one from the list above>", "..."], '
            '"reasoning": "<one sentence>"}'
        )

        client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        parsed = self._parse_json_object(raw_text)
        if not isinstance(parsed, dict):
            return None

        verdict = str(parsed.get("verdict", "")).strip().upper()
        if verdict not in VALID_VERDICTS:
            return None

        requirements_present_raw = parsed.get("requirements_present") or []
        requirements_present: List[Dict[str, str]] = []
        if isinstance(requirements_present_raw, list):
            for entry in requirements_present_raw:
                if isinstance(entry, dict) and entry.get("requirement"):
                    requirements_present.append(
                        {
                            "requirement": str(entry.get("requirement", "")).strip(),
                            "evidence": str(entry.get("evidence", "")).strip(),
                        }
                    )

        requirements_absent_raw = parsed.get("requirements_absent") or []
        requirements_absent = (
            [str(r).strip() for r in requirements_absent_raw if str(r).strip()]
            if isinstance(requirements_absent_raw, list)
            else []
        )

        return GuidelineCheckResult(
            verdict=verdict,
            requirements_present=requirements_present,
            requirements_absent=requirements_absent,
            citation=excerpt_record.get("citation", ""),
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


def check_against_guideline(
    candidate_section: Dict[str, str],
    excerpt_record: Dict[str, Any],
    checker: Optional[GuidelineGroundedChecker] = None,
) -> Optional[GuidelineCheckResult]:
    """Module-level convenience wrapper matching the requested function signature."""
    checker = checker or GuidelineGroundedChecker()
    return checker.check_against_guideline(candidate_section, excerpt_record)
