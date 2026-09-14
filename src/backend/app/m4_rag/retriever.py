"""Retriever engine for ICH M4 RAG Checker (Module M4).

Provides exact section ID resolution and TF-IDF / vector space semantic
similarity retrieval grounded in the verified ICH M4 knowledge base.
"""

from typing import List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.schema import (
    ICHSectionRequirement,
    MatchEvidence,
    MatchMethod,
)


class ICHRetriever:
    """Hybrid exact + semantic retriever grounded in indexed ICH M4 guidelines."""

    def __init__(self, kb: Optional[KnowledgeBaseLoader] = None):
        self.kb = kb or get_knowledge_base()
        self._requirements: List[ICHSectionRequirement] = self.kb.get_all()
        self._corpus_texts: List[str] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._build_index()

    def _build_index(self) -> None:
        """Constructs vector search index across the verified ICH M4 corpus."""
        self._corpus_texts = []
        for req in self._requirements:
            keywords_str = " ".join(req.keywords)
            doc = (
                f"Section {req.section_id} {req.title}. "
                f"Module {req.module_id} {req.module_name}. "
                f"{req.requirement_text} {keywords_str}"
            )
            self._corpus_texts.append(doc)

        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(self._corpus_texts)

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
        """Searches ICH M4 knowledge base using cosine similarity.
        
        Returns:
            List of (ICHSectionRequirement, similarity_score) sorted descending.
        """
        if not query or not query.strip() or self._vectorizer is None:
            return []

        query_vec = self._vectorizer.transform([query.strip()])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Top indices
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
