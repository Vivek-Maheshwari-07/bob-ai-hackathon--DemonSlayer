"""Unified End-to-End Pipeline for CTD / ICH M4 RAG Checker (Module M4).

Orchestrates PDF extraction, parsing, hybrid retrieval, completeness scoring,
Gemini 2.5 Flash grounded regulatory reasoning, and actionable gap report generation.
"""

import sys
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

# Ensure backend directory is in sys.path when executed directly
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from app.m4_rag.completeness import CompletenessScorer
    from app.m4_rag.content_verifier import ContentVerifier, content_adequacy_score
    from app.m4_rag.dossier_parser import DossierParser
    from app.m4_rag.gap_checker import GapChecker
    from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner
    from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
    from app.m4_rag.pdf_extractor import CTDPDFExtractor
    from app.m4_rag.report_generator import ReportGenerator
    from app.m4_rag.retriever import ICHRetriever
    from app.m4_rag.safety_signal_link import apply_safety_signal_flags
    from app.m4_rag.schema import (
        DossierOutlineInput,
        GapReportOutput,
        GapStatus,
    )
except ImportError:
    from .completeness import CompletenessScorer
    from .content_verifier import ContentVerifier, content_adequacy_score
    from .dossier_parser import DossierParser
    from .gap_checker import GapChecker
    from .gemini_reasoner import GeminiGroundedReasoner
    from .knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
    from .pdf_extractor import CTDPDFExtractor
    from .report_generator import ReportGenerator
    from .retriever import ICHRetriever
    from .safety_signal_link import apply_safety_signal_flags
    from .schema import (
        DossierOutlineInput,
        GapReportOutput,
        GapStatus,
    )


class CTDRagCheckerPipeline:
    """Master pipeline executing ICH M4 CTD Dossier Readiness Check."""

    def __init__(
        self,
        kb: Optional[KnowledgeBaseLoader] = None,
        retriever: Optional[ICHRetriever] = None,
        gap_checker: Optional[GapChecker] = None,
        scorer: Optional[CompletenessScorer] = None,
        report_generator: Optional[ReportGenerator] = None,
        reasoner: Optional[GeminiGroundedReasoner] = None,
        content_verifier: Optional[ContentVerifier] = None,
    ):
        self.kb = kb or get_knowledge_base()
        self.retriever = retriever or ICHRetriever(self.kb)
        self.gap_checker = gap_checker or GapChecker(self.kb, self.retriever)
        self.scorer = scorer or CompletenessScorer(self.kb)
        self.report_generator = report_generator or ReportGenerator(self.scorer)
        self.reasoner = reasoner or GeminiGroundedReasoner()
        self.content_verifier = content_verifier or ContentVerifier()

    def run(
        self,
        input_data: Union[DossierOutlineInput, Dict[str, Any], List[Any], str],
        enable_reasoner: bool = True,
    ) -> GapReportOutput:
        """Executes full RAG gap evaluation on candidate dossier input.
        
        Args:
            input_data: Dossier outline in structured dict, list, text, or Pydantic format.
            enable_reasoner: Whether to invoke grounded reasoning narratives.
            
        Returns:
            Validated GapReportOutput ready for frontend consumption.
        """
        # Step 1: Parse and normalize candidate dossier outline
        normalized_outline: DossierOutlineInput = DossierParser.parse_input(input_data)

        # Step 2: Evaluate against verified ICH M4 requirements
        gap_items = self.gap_checker.evaluate(normalized_outline)

        # Step 2b: Cross-link Mode 1 (M2 PRR signal detection) — flag safety
        # sections for mandatory review when this drug has a CONFIRMED_SIGNAL.
        safety_signal_linkage = apply_safety_signal_flags(normalized_outline.drug_name, gap_items)

        # Step 2c: Tier 2 content-adequacy verification. Only runs for the
        # handful of sections that carry `content_checkpoints` in the KB, and
        # only against sections Tier 1 already found PRESENT/PARTIAL (a
        # MISSING section has no dossier text to check). Silently no-ops
        # (content_adequacy_score stays None) when Gemini is unavailable or a
        # section has no checkpoints defined, so it never regresses Tier 1.
        self._apply_content_verification(normalized_outline, gap_items)

        # Step 3: Compute completeness scores
        overall_score, _ = self.scorer.calculate(gap_items)

        # Step 4: Generate grounded reasoning insights via Gemini 2.5 Flash (if enabled)
        reasoning_insights: Optional[List[str]] = None
        if enable_reasoner:
            priority_gaps = [
                g for g in gap_items
                if g.status.value != "PRESENT" and g.criticality.value in ("CRITICAL", "MAJOR")
            ]
            try:
                reasoning_insights = self.reasoner.generate_reasoning_insights(
                    priority_gaps=priority_gaps,
                    overall_completeness=overall_score,
                    submission_title=normalized_outline.submission_title or "Candidate CTD Dossier",
                )
            except Exception:
                # The reasoner already fails soft to its own deterministic
                # fallback internally; this outer guard is defense-in-depth
                # so an unexpected error there degrades to the report
                # generator's own deterministic recommendations instead of
                # failing the whole request.
                reasoning_insights = None

        # Step 5: Assemble actionable gap report
        report = self.report_generator.generate_report(
            outline=normalized_outline,
            gap_items=gap_items,
            reasoning_insights=reasoning_insights,
            safety_signal_linkage=safety_signal_linkage,
        )

        return report

    def _apply_content_verification(
        self,
        outline: DossierOutlineInput,
        gap_items: List[Any],
    ) -> None:
        """Runs Tier 2 content-adequacy verification in place on `gap_items`.

        For each GapItem that is PRESENT/PARTIAL and whose ICH requirement
        defines `content_checkpoints`, looks up the actual matched dossier
        section (by the section_id Tier 1 recorded in match_evidence) and
        verifies its real text against those checkpoints. Anything else
        (MISSING items, sections without checkpoints, or a failed/unavailable
        Gemini call) is skipped silently — content_adequacy_score stays None.
        """
        dossier_by_id: Dict[str, Any] = {
            s.section_id.strip().upper(): s
            for s in outline.sections
            if s.section_id
        }

        for item in gap_items:
            if item.status not in (GapStatus.PRESENT, GapStatus.PARTIAL):
                continue

            req = self.kb.get_by_id(item.section_id)
            checkpoints = getattr(req, "content_checkpoints", None) if req else None
            if not checkpoints:
                continue

            matched_id = item.match_evidence.matched_dossier_section_id
            dossier_section = dossier_by_id.get((matched_id or "").strip().upper())
            if dossier_section is None:
                continue

            section_text = " ".join(
                part.strip()
                for part in (
                    dossier_section.title,
                    dossier_section.description,
                    dossier_section.content_summary,
                )
                if part and part.strip()
            )
            if not section_text:
                continue

            try:
                results = self.content_verifier.verify_section_content(section_text, checkpoints)
                score = content_adequacy_score(results)
            except Exception:
                # Defense in depth: ContentVerifier already fails soft
                # internally, this outer guard just guarantees Tier 1 never
                # breaks because of a Tier 2 error.
                results, score = [], None

            if score is not None:
                item.content_adequacy_score = score
                item.checkpoint_results = [r.to_dict() for r in results]

    def run_pdf(
        self,
        pdf_source: Union[str, bytes, BinaryIO],
        submission_title: str = "Candidate CTD Dossier (PDF)",
        enable_reasoner: bool = True,
        max_pages: Optional[int] = 300,
    ) -> GapReportOutput:
        """Executes full RAG gap evaluation from a raw PDF document."""
        outline = CTDPDFExtractor.extract_outline_from_pdf(
            pdf_source=pdf_source,
            submission_title=submission_title,
            max_pages=max_pages,
        )
        return self.run(outline, enable_reasoner=enable_reasoner)


def check_ctd_dossier(
    input_data: Union[DossierOutlineInput, Dict[str, Any], List[Any], str],
    enable_reasoner: bool = True,
) -> GapReportOutput:
    """Convenience functional wrapper for CTD readiness checking."""
    pipeline = CTDRagCheckerPipeline()
    return pipeline.run(input_data, enable_reasoner=enable_reasoner)


def check_ctd_pdf(
    pdf_source: Union[str, bytes, BinaryIO],
    submission_title: str = "Candidate CTD Dossier (PDF)",
    enable_reasoner: bool = True,
    max_pages: Optional[int] = 300,
) -> GapReportOutput:
    """Convenience functional wrapper for CTD PDF readiness checking."""
    pipeline = CTDRagCheckerPipeline()
    return pipeline.run_pdf(
        pdf_source=pdf_source,
        submission_title=submission_title,
        enable_reasoner=enable_reasoner,
        max_pages=max_pages,
    )


if __name__ == "__main__":
    try:
        from app.m4_rag.presets import PRESET_DOSSIERS
    except ImportError:
        from presets import PRESET_DOSSIERS

    print("=" * 60)
    print("ICH M4 CTD DOSSIER READINESS CHECKER (STANDALONE RUN)")
    print("=" * 60)
    pipe = CTDRagCheckerPipeline()
    sample = PRESET_DOSSIERS["VIOXX_NDA_21042"]
    print(f"Auditing dossier: {sample['submission_title']}")
    rep = pipe.run(sample, enable_reasoner=False)
    print("Audit completed successfully!")
    print(f"  Overall Completeness Score : {rep.overall_completeness}%")
    print(f"  Total Sections Evaluated   : {rep.total_sections_evaluated}")
    print(f"  Sections Present           : {rep.present_total}")
    print(f"  Sections Missing           : {rep.missing_total}")
    print(f"  Critical / Major Gaps      : {len(rep.priority_gaps)}")
    print("=" * 60)
