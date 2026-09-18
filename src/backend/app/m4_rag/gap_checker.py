"""Gap Checker Engine for Module M4.

Performs hybrid deterministic and semantic gap analysis comparing candidate
CTD dossier outlines against all verified ICH M4 requirements.
"""

import re
from typing import Dict, List, Optional, Set

from scipy.optimize import linear_sum_assignment

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

    # Minimum cosine similarity for a semantic match to count as a real hit
    # rather than "no match" (requirement stays MISSING).
    SEMANTIC_MATCH_THRESHOLD = 0.50
    # Below this confidence, an accepted semantic match is downgraded to
    # PARTIAL rather than PRESENT (title matched, but low enough confidence
    # to warrant manual verification).
    SEMANTIC_PARTIAL_CONFIDENCE = 0.65

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
        dossier_index_by_id: Dict[str, int] = {}
        for idx, s in enumerate(dossier_sections):
            if s.section_id:
                key = s.section_id.strip().upper()
                dossier_by_id[key] = s
                dossier_index_by_id[key] = idx

        gap_item_by_req_id: Dict[str, GapItem] = {}
        matched_dossier_indices: Set[int] = set()
        unmatched_requirements: List[ICHSectionRequirement] = []

        # 1. Deterministic Exact ID Match pass
        for req in ich_requirements:
            req_id_upper = req.section_id.upper()
            if req_id_upper in dossier_by_id:
                matched_sec = dossier_by_id[req_id_upper]
                gap_item_by_req_id[req.section_id] = self._classify_matched_section(
                    req=req,
                    matched_sec=matched_sec,
                    method=MatchMethod.EXACT,
                    confidence=1.0,
                    evidence_prefix="Exact section ID match found in candidate dossier.",
                )
                matched_dossier_indices.add(dossier_index_by_id[req_id_upper])
            else:
                unmatched_requirements.append(req)

        # 2. Global optimal semantic matching for everything the exact pass
        # missed. Rather than assigning greedily in KB (JSON) order — which
        # can permanently lock an ambiguous section to the wrong, earlier
        # requirement — this scores every remaining candidate section
        # against every remaining requirement in one batch and solves for
        # the assignment that maximizes total similarity (Hungarian
        # algorithm), so the KB's iteration order can no longer affect which
        # section a requirement gets matched to.
        candidate_indices = [
            idx for idx, sec in enumerate(dossier_sections)
            if idx not in matched_dossier_indices
            and f"{sec.section_id} {sec.title} {sec.description or ''}".strip()
        ]

        if unmatched_requirements and candidate_indices:
            section_texts = [
                f"{dossier_sections[idx].section_id} {dossier_sections[idx].title} {dossier_sections[idx].description or ''}".strip()
                for idx in candidate_indices
            ]
            sim_matrix = self.retriever.batch_similarity(section_texts, unmatched_requirements)

            row_indices, col_indices = linear_sum_assignment(-sim_matrix)
            for row, col in zip(row_indices, col_indices):
                score = float(sim_matrix[row, col])
                if score < self.SEMANTIC_MATCH_THRESHOLD:
                    continue
                req = unmatched_requirements[col]
                sec_idx = candidate_indices[row]
                sec = dossier_sections[sec_idx]
                gap_item_by_req_id[req.section_id] = self._classify_matched_section(
                    req=req,
                    matched_sec=sec,
                    method=MatchMethod.SEMANTIC,
                    confidence=score,
                    evidence_prefix=f"Semantic match ({score * 100:.1f}% confidence) for title/content.",
                )
                matched_dossier_indices.add(sec_idx)

        # 3. Anything still unmatched is a genuine gap.
        gap_results: List[GapItem] = []
        for req in ich_requirements:
            if req.section_id in gap_item_by_req_id:
                gap_results.append(gap_item_by_req_id[req.section_id])
                continue

            gap_results.append(
                GapItem(
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
            )

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
        elif desc.lower() in ("todo", "wip", "n/a", "none"):
            is_partial = True
            gap_reason = "Section contains placeholder status instead of substantive documentation."
        elif method == MatchMethod.SEMANTIC and confidence < self.SEMANTIC_PARTIAL_CONFIDENCE:
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
