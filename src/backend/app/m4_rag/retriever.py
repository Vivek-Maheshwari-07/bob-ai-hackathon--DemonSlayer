"""Retriever engine for ICH M4 RAG Checker (Module M4).

Provides exact section ID resolution and dense embedding-based semantic
similarity retrieval (sentence-transformers) grounded in the verified
ICH M4 knowledge base.
"""

from typing import List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.schema import (
    ICHSectionRequirement,
    MatchEvidence,
    MatchMethod,
)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Loaded lazily and shared across ICHRetriever instances — the model is
# expensive to load but stateless/thread-safe to reuse for encoding.
_shared_embedding_model: Optional[SentenceTransformer] = None

# The knowledge base content is static per-process, but a fresh ICHRetriever
# (and therefore a fresh embedding pass) is created on every M4 pipeline run.
# Cache the encoded corpus per KnowledgeBaseLoader instance (keyed by the
# object itself, not id(), to avoid stale hits if an old instance is GC'd
# and its id reused) so repeated requests don't re-embed on every call.
_corpus_embedding_cache: dict = {}


def _get_embedding_model() -> SentenceTransformer:
    global _shared_embedding_model
    if _shared_embedding_model is None:
        _shared_embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _shared_embedding_model


class ICHRetriever:
    """Hybrid exact + semantic retriever grounded in indexed ICH M4 guidelines."""

    def __init__(self, kb: Optional[KnowledgeBaseLoader] = None):
        self.kb = kb or get_knowledge_base()
        self._requirements: List[ICHSectionRequirement] = self.kb.get_all()
        self._corpus_texts: List[str] = []
        self._model: SentenceTransformer = _get_embedding_model()
        self._embeddings: Optional[np.ndarray] = None
        self._build_index()

    def _build_index(self) -> None:
        """Encodes the verified ICH M4 corpus into normalized sentence embeddings."""
        cached = _corpus_embedding_cache.get(self.kb)
        if cached is not None:
            self._corpus_texts, self._embeddings = cached
            return

        self._corpus_texts = []
        for req in self._requirements:
            keywords_str = " ".join(req.keywords)
            doc = (
                f"Section {req.section_id} {req.title}. "
                f"Module {req.module_id} {req.module_name}. "
                f"{req.requirement_text} {keywords_str}"
            )
            self._corpus_texts.append(doc)

        embeddings = self._model.encode(
            self._corpus_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        self._embeddings = np.asarray(embeddings)
        _corpus_embedding_cache[self.kb] = (self._corpus_texts, self._embeddings)

    def exact_match(self, section_id: str) -> Optional[ICHSectionRequirement]:
        """Performs deterministic, case-insensitive section ID lookup."""
        if not section_id:
            return None
        return self.kb.get_by_id(section_id)

    def semantic_search(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.30,
    ) -> List[Tuple[ICHSectionRequirement, float]]:
        """Searches the ICH M4 knowledge base using embedding cosine similarity.

        Returns:
            List of (ICHSectionRequirement, similarity_score) sorted descending.
        """
        if not query or not query.strip() or self._embeddings is None:
            return []

        query_vec = self._model.encode(
            [query.strip()],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        # Embeddings are L2-normalized, so the dot product is cosine similarity.
        scores = self._embeddings @ query_vec

        top_indices = np.argsort(scores)[::-1][:top_k]
        results: List[Tuple[ICHSectionRequirement, float]] = []

        for idx in top_indices:
            score = float(scores[idx])
            if score >= min_similarity:
                results.append((self._requirements[idx], round(score, 4)))

        return results

    def find_best_requirement_for_dossier_section(
        self,
        section_id: str,
        title: str,
        description: str = "",
        min_confidence: float = 0.40,
    ) -> Tuple[Optional[ICHSectionRequirement], MatchEvidence]:
        """Resolves a candidate dossier section to the best-matching ICH requirement.
        
        Applies:
            1. Deterministic exact section ID lookup.
            2. High-precision semantic vector fallback.
            3. Controlled insufficient evidence if confidence is low.
        """
        # Step 1: Exact Match
        if section_id:
            exact_req = self.exact_match(section_id)
            if exact_req:
                return exact_req, MatchEvidence(
                    match_method=MatchMethod.EXACT,
                    confidence_score=1.0,
                    matched_dossier_section_id=section_id,
                    matched_dossier_title=title,
                    evidence_reasoning=(
                        f"Exact deterministic match for ICH section '{exact_req.section_id}' "
                        f"({exact_req.title}) in {exact_req.module_name}."
                    ),
                )

        # Step 2: Semantic Match
        search_query = f"{section_id} {title} {description}".strip()
        semantic_matches = self.semantic_search(
            search_query, top_k=1, min_similarity=min_confidence
        )

        if semantic_matches:
            best_req, sim_score = semantic_matches[0]
            return best_req, MatchEvidence(
                match_method=MatchMethod.SEMANTIC,
                confidence_score=sim_score,
                matched_dossier_section_id=section_id or "N/A",
                matched_dossier_title=title,
                evidence_reasoning=(
                    f"Semantic vector match with {sim_score * 100:.1f}% confidence "
                    f"to ICH '{best_req.section_id} - {best_req.title}'."
                ),
            )

        # Step 3: Insufficient Evidence / No Match
        return None, MatchEvidence(
            match_method=MatchMethod.NONE,
            confidence_score=0.0,
            matched_dossier_section_id=section_id or "N/A",
            matched_dossier_title=title,
            evidence_reasoning="Insufficient evidence in the indexed ICH M4 knowledge.",
        )
