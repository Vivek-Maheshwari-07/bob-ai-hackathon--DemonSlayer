"""Gap Checker Engine for Module M4.

Performs hybrid deterministic and semantic gap analysis comparing candidate
CTD dossier outlines against all verified ICH M4 requirements.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.retriever import ICHRetriever
from app.m4_rag.schema import (
    CriticalityLevel,
    DossierOutlineInput,
    DossierSectionInput,
    GapItem,
    GapStatus,
    ICHSectionRequirement,
    MatchEvidence,
    MatchMethod,
)


class GapChecker:
    """Evaluates CTD dossier compliance against verified ICH M4 requirements."""

    # Keywords indicating a section is partial / incomplete / draft
    PARTIAL_KEYWORDS = re.compile(
        r"\b(draft|preliminary|in\s*progress|incomplete|tbd|to\s*be\s*provided|pending|interim|placeholder|partial|missing\s*data)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        kb: Optional[KnowledgeBaseLoader] = None,
        retriever: Optional[ICHRetriever] = None,
    ):
        self.kb = kb or get_knowledge_base()
        self.retriever = retriever or ICHRetriever(self.kb)

    def evaluate(self, outline: DossierOutlineInput) -> List[GapItem]:
        """Evaluates all verified ICH M4 requirements against the dossier outline.
        
        Returns:
            List of GapItem evaluations covering all ICH requirements in Modules 1-5.
        """
        ich_requirements: List[ICHSectionRequirement] = self.kb.get_all()
        dossier_sections: List[DossierSectionInput] = outline.sections

        # Index dossier sections by normalized section_id
        dossier_by_id: Dict[str, DossierSectionInput] = {}
        for s in dossier_sections:
            if s.section_id:
                dossier_by_id[s.section_id.strip().upper()] = s

        matched_dossier_indices: Set[int] = set()
        gap_results: List[GapItem] = []

        for req in ich_requirements:
            req_id_upper = req.section_id.upper()
            gap_item: Optional[GapItem] = None

            # 1. Deterministic Exact ID Match
            if req_id_upper in dossier_by_id:
                matched_sec = dossier_by_id[req_id_upper]
                gap_item = self._classify_matched_section(
                    req=req,
                    matched_sec=matched_sec,
                    method=MatchMethod.EXACT,
                    confidence=1.0,
                    evidence_prefix="Exact section ID match found in candidate dossier.",
                )
            else:
                # 2. Semantic Search across candidate dossier sections
                best_sec, best_score, best_idx = self._find_best_semantic_dossier_section(
                    req=req,
                    dossier_sections=dossier_sections,
                    exclude_indices=matched_dossier_indices,
                )

                if best_sec and best_score >= 0.50:
                    matched_dossier_indices.add(best_idx)
                    gap_item = self._classify_matched_section(
                        req=req,
                        matched_sec=best_sec,
                        method=MatchMethod.SEMANTIC,
                        confidence=best_score,
                        evidence_prefix=f"Semantic match ({best_score * 100:.1f}% confidence) for title/content.",
                    )
                else:
                    # 3. Missing Section
                    gap_item = GapItem(
                        section_id=req.section_id,
                        module_id=req.module_id,
                        module_name=req.module_name,
                        title=req.title,
                        status=GapStatus.MISSING,
                        criticality=req.criticality,
                        match_evidence=MatchEvidence(
                            match_method=MatchMethod.NONE,
                            confidence_score=0.0,
                            matched_dossier_section_id=None,
                            matched_dossier_title=None,
                            evidence_reasoning=(
                                f"Required section '{req.section_id} - {req.title}' "
                                f"was not detected in the candidate dossier outline."
                            ),
                        ),
                        action_item=(
                            f"Generate and attach Section {req.section_id} ({req.title}) "
                            f"complying with {req.source}: {req.requirement_text}"
                        ),
                        source_reference=req.source,
                    )

            gap_results.append(gap_item)

        return gap_results

    def _classify_matched_section(
        self,
        req: ICHSectionRequirement,
        matched_sec: DossierSectionInput,
        method: MatchMethod,
        confidence: float,
        evidence_prefix: str,
    ) -> GapItem:
        """Determines whether a matched section is PRESENT or PARTIAL based on content."""
        desc = (matched_sec.description or "").strip()
        status_hint = (matched_sec.status_hint or "").strip()
        combined_text = f"{desc} {status_hint}"

        is_partial = False
        gap_reason = ""

        # Check for explicit draft/partial indicators
        if self.PARTIAL_KEYWORDS.search(combined_text):
            is_partial = True
            gap_reason = "Section is flagged as draft, interim, or incomplete."
        elif desc.lower() in ("tbd", "todo", "wip", "n/a", "none", "pending", "draft", "placeholder"):
            is_partial = True
            gap_reason = "Section contains placeholder status instead of substantive documentation."
        elif method == MatchMethod.SEMANTIC and confidence < 0.65:
            is_partial = True
            gap_reason = f"Section title matched semantically with moderate confidence ({confidence * 100:.1f}%); verify full alignment with ICH section number {req.section_id}."

        if is_partial:
            return GapItem(
                section_id=req.section_id,
                module_id=req.module_id,
                module_name=req.module_name,
                title=req.title,
                status=GapStatus.PARTIAL,
                criticality=req.criticality,
                match_evidence=MatchEvidence(
                    match_method=method,
                    confidence_score=confidence,
                    matched_dossier_section_id=matched_sec.section_id or "N/A",
                    matched_dossier_title=matched_sec.title,
                    evidence_reasoning=f"{evidence_prefix} {gap_reason}",
                ),
                action_item=(
                    f"Complete and finalize Section {req.section_id} ({req.title}). "
                    f"Remediate: {gap_reason} Adhere to {req.source}."
                ),
                source_reference=req.source,
            )

        return GapItem(
            section_id=req.section_id,
            module_id=req.module_id,
            module_name=req.module_name,
            title=req.title,
            status=GapStatus.PRESENT,
            criticality=req.criticality,
            match_evidence=MatchEvidence(
                match_method=method,
                confidence_score=confidence,
                matched_dossier_section_id=matched_sec.section_id or "N/A",
                matched_dossier_title=matched_sec.title,
                evidence_reasoning=f"{evidence_prefix} Fully meets structural expectation.",
            ),
            action_item=None,
            source_reference=req.source,
        )

    def _find_best_semantic_dossier_section(
        self,
        req: ICHSectionRequirement,
        dossier_sections: List[DossierSectionInput],
        exclude_indices: Set[int],
    ) -> Tuple[Optional[DossierSectionInput], float, int]:
        """Finds candidate dossier section that best matches an ICH requirement semantically."""
        best_sec: Optional[DossierSectionInput] = None
        best_score = 0.0
        best_idx = -1

        query = f"Section {req.section_id} {req.title} {req.requirement_text} {' '.join(req.keywords)}"

        for idx, sec in enumerate(dossier_sections):
            if idx in exclude_indices:
                continue

            sec_text = f"{sec.section_id} {sec.title} {sec.description or ''}".strip()
            if not sec_text:
                continue

            # Compare using retriever vectorizer
            matches = self.retriever.semantic_search(sec_text, top_k=1, min_similarity=0.30)
            if matches:
                top_req, score = matches[0]
                if top_req.section_id == req.section_id and score > best_score:
                    best_score = score
                    best_sec = sec
                    best_idx = idx

        return best_sec, best_score, best_idx
