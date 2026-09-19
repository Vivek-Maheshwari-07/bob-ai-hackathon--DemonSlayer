"""Tier 2 Content-Adequacy Verifier powered by Google Gemini 2.5 Flash (Module M4).

Tier 1 (gap_checker.py) only verifies that a required CTD section is
structurally present in the dossier outline. Tier 2 goes one level deeper:
given the actual matched dossier section text, it checks whether the
section's *content* substantively answers a fixed set of ICH-grounded
checkpoint questions (e.g. "does this CSR state a primary endpoint?").

Reuses the same Gemini HTTP client pattern, strict-grounding prompt style,
and try/except fallback-safe behavior as gemini_reasoner.py so Tier 2 can be
skipped silently (score=None) without ever crashing Tier 1's report.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None


class CheckpointResult:
    """Single grounded checkpoint verification result."""

    def __init__(self, id: str, question: str, answer: str, quote: Optional[str] = None):
        self.id = id
        self.question = question
        self.answer = answer  # "YES" / "NO" / "UNCLEAR"
        self.quote = quote

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "quote": self.quote,
        }


class ContentVerifier:
    """Verifies content adequacy of a dossier section against ICH checkpoints via Gemini 2.5 Flash."""

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

    def verify_section_content(
        self, section_text: str, checkpoints: List[dict]
    ) -> List[CheckpointResult]:
        """Verifies all checkpoints for a section in a single batched, strictly-grounded LLM call.

        Returns an empty list if Gemini is unavailable or the call fails —
        callers should treat an empty result as "Tier 2 skipped", never as
        "all checkpoints failed".
        """
        if not checkpoints:
            return []
        if not self.is_available or not (section_text or "").strip():
            return []

        try:
            return self._call_gemini_api(section_text, checkpoints)
        except Exception:
            return []

    def _call_gemini_api(
        self, section_text: str, checkpoints: List[dict]
    ) -> List[CheckpointResult]:
        """Invokes Gemini 2.5 Flash once with all checkpoint questions for this section."""
        questions_block = "\n".join(
            f'{i + 1}. [id={cp["id"]}] {cp["question"]}'
            for i, cp in enumerate(checkpoints)
        )

        prompt = (
            "You are a strict regulatory document auditor. You will be given ONLY the text "
            "of one CTD dossier section, followed by a numbered list of yes/no questions.\n\n"
            "SECTION TEXT (the ONLY source of truth):\n"
            "-----\n"
            f"{section_text}\n"
            "-----\n\n"
            "QUESTIONS:\n"
            f"{questions_block}\n\n"
            "STRICT INSTRUCTIONS:\n"
            "1. Answer each question using ONLY the section text above. Do not infer, assume, "
            "or use outside knowledge of what such a section would typically contain.\n"
            "2. For each question, answer YES only if the section text explicitly and unambiguously "
            "states the requested information. Answer NO if it is absent. Answer UNCLEAR if the text "
            "is ambiguous.\n"
            "3. When the answer is YES or UNCLEAR, quote the exact supporting sentence (or the closest "
            "short verbatim excerpt) from the section text. When the answer is NO, quote must be null.\n"
            "4. Respond with ONLY a JSON array (no markdown fences, no commentary), one object per "
            "question, in this exact shape:\n"
            '[{"id": "<checkpoint id>", "answer": "YES|NO|UNCLEAR", "quote": "<verbatim quote or null>"}]'
        )

        url = self.GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1024},
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                return []
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return []
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return []
            raw_text = parts[0].get("text", "").strip()

        parsed = self._parse_json_array(raw_text)
        if parsed is None:
            return []

        by_id = {item.get("id"): item for item in parsed if isinstance(item, dict)}
        results: List[CheckpointResult] = []
        for cp in checkpoints:
            entry = by_id.get(cp["id"])
            if not entry:
                continue
            answer = str(entry.get("answer", "UNCLEAR")).strip().upper()
            if answer not in ("YES", "NO", "UNCLEAR"):
                answer = "UNCLEAR"
            quote = entry.get("quote")
            if isinstance(quote, str) and not quote.strip():
                quote = None
            results.append(
                CheckpointResult(id=cp["id"], question=cp["question"], answer=answer, quote=quote)
            )
        return results

    @staticmethod
    def _parse_json_array(raw_text: str) -> Optional[List[Any]]:
        """Extracts and parses a JSON array from the model's raw text response."""
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, list) else None
        except (ValueError, TypeError):
            pass

        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, list) else None
            except (ValueError, TypeError):
                return None
        return None


def content_adequacy_score(results: List[CheckpointResult]) -> Optional[float]:
    """Computes the fraction of checkpoints answered YES.

    Returns None (skip Tier 2) when there are no results, e.g. Gemini was
    unavailable or the call failed — callers must not treat that as a score
    of 0.0.
    """
    if not results:
        return None
    yes_count = sum(1 for r in results if r.answer == "YES")
    return round(yes_count / len(results), 4)
