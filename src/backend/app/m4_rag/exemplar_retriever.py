"""Tier 3 Exemplar Retriever for CTD / ICH M4 RAG Checker (Module M4).

Tier 3 (authenticity_checker.py) needs something real to compare a candidate
section against — a curated set of genuine excerpts from real regulatory
documents (exemplar_corpus.json). This module loads that corpus, embeds it
once using the SAME sentence-transformers setup already used for Tier 1
matching (retriever.py's shared model + embedding pattern, so no second
model gets loaded into memory), and retrieves the top-k most relevant
exemplars for a given candidate section.

The corpus is expected to ship mostly/entirely as TODO placeholders
(exemplar_text="") until real source text has been sourced and verified —
see knowledge/exemplar_corpus.json. Records with empty exemplar_text are
skipped at load time, so an empty/placeholder corpus makes `retrieve()`
return [] for every section_id, which is exactly what makes Tier 3 a clean,
silent no-op in that state (the same graceful-degradation contract Tier 2
has around a missing Gemini key).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from app.m4_rag import retriever as _retriever_module

DEFAULT_CORPUS_PATH = Path(__file__).parent / "knowledge" / "exemplar_corpus.json"


class ExemplarRecord:
    """A single real-regulatory-text exemplar for one ICH M4 section."""

    def __init__(self, section_id: str, source_citation: str, exemplar_text: str):
        self.section_id = section_id
        self.source_citation = source_citation
        self.exemplar_text = exemplar_text

    def to_dict(self) -> Dict[str, str]:
        return {
            "section_id": self.section_id,
            "source_citation": self.source_citation,
            "exemplar_text": self.exemplar_text,
        }


class ExemplarRetriever:
    """Retrieves the most relevant real-text exemplars for a candidate section."""

    def __init__(
        self,
        corpus_path: Optional[Path] = None,
        corpus: Optional[List[dict]] = None,
    ):
        """Loads the exemplar corpus and builds a per-section embedding index.

        `corpus` (a raw list of {section_id, source_citation, exemplar_text}
        dicts) can be passed directly — mainly for tests — bypassing the JSON
        file entirely. Records with blank/missing exemplar_text are dropped
        at load time (they carry nothing to embed or compare against).
        """
        self._model: Optional["SentenceTransformer"] = None
        self._by_section: Dict[str, List[ExemplarRecord]] = {}
        self._embeddings_by_section: Dict[str, np.ndarray] = {}

        raw_records = corpus if corpus is not None else self._load_corpus_file(
            corpus_path or DEFAULT_CORPUS_PATH
        )
        records = [
            ExemplarRecord(
                section_id=str(r.get("section_id", "")).strip(),
                source_citation=str(r.get("source_citation", "")).strip(),
                exemplar_text=str(r.get("exemplar_text", "")).strip(),
            )
            for r in raw_records
        ]
        # Drop placeholder/empty records — nothing to embed or compare.
        records = [r for r in records if r.section_id and r.exemplar_text]

        for record in records:
            self._by_section.setdefault(record.section_id.upper(), []).append(record)

        if records:
            self._build_index()

    @staticmethod
    def _load_corpus_file(path: Path) -> List[dict]:
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        return data.get("exemplars", []) if isinstance(data, dict) else (data or [])

    def _build_index(self) -> None:
        """Embeds every non-placeholder exemplar's text, grouped by section_id."""
        self._model = _retriever_module._get_embedding_model()
        for section_id, records in self._by_section.items():
            texts = [r.exemplar_text for r in records]
            embeddings = self._model.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            )
            self._embeddings_by_section[section_id] = np.asarray(embeddings)

    @property
    def is_available(self) -> bool:
        """True when at least one real (non-placeholder) exemplar was loaded."""
        return bool(self._by_section)

    def has_exemplars_for(self, section_id: str) -> bool:
        return bool(section_id) and section_id.strip().upper() in self._by_section

    def retrieve(
        self,
        section_id: str,
        candidate_text: str = "",
        top_k: int = 2,
    ) -> List[ExemplarRecord]:
        """Returns up to `top_k` exemplars for this exact section_id.

        Exemplars are scoped to the exact section_id (this is a small,
        deliberately curated per-section corpus, not a fuzzy cross-section
        index — we never want to compare a 5.3.5 candidate against a 4.2.1
        exemplar). Within that section's exemplars, results are ranked by
        cosine similarity between `candidate_text` and each exemplar's text,
        so the most comparable real excerpt(s) are used for the Tier 3 check.
        Returns [] when there are no (non-placeholder) exemplars for this
        section_id — the caller treats that as "skip Tier 3 here".
        """
        key = (section_id or "").strip().upper()
        records = self._by_section.get(key)
        if not records:
            return []

        if len(records) <= top_k or not (candidate_text or "").strip():
            return records[:top_k]

        query_vec = self._model.encode(
            [candidate_text.strip()], normalize_embeddings=True, show_progress_bar=False
        )[0]
        scores = self._embeddings_by_section[key] @ query_vec
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [records[i] for i in top_indices]
