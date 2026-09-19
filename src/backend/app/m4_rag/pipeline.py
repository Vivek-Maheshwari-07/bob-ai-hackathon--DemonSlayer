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
    from app.m4_rag.guideline_grounded_checker import GuidelineGroundedChecker
    from app.m4_rag.knowledge.guideline_excerpts_loader import get_guideline_excerpts
    from app.m4_rag.dossier_parser import DossierParser
    from app.m4_rag.gap_checker import GapChecker
    from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner
    from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
    from app.m4_rag.pdf_extractor import CTDPDFExtractor
    from app.m4_rag.report_generator import ReportGenerator
    from app.m4_rag.retriever import ICHRetriever
    from app.m4_rag.safety_signal_link import apply_safety_signal_flags
    from app.m4_rag.substance_gate import document_scale_check
    from app.m4_rag.schema import (
        DossierOutlineInput,
        GapReportOutput,
        GapStatus,
    )
except ImportError:
    from .completeness import CompletenessScorer
    from .guideline_grounded_checker import GuidelineGroundedChecker
    from .knowledge.guideline_excerpts_loader import get_guideline_excerpts
    from .dossier_parser import DossierParser
    from .gap_checker import GapChecker
    from .gemini_reasoner import GeminiGroundedReasoner
    from .knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
    from .pdf_extractor import CTDPDFExtractor
    from .report_generator import ReportGenerator
    from .retriever import ICHRetriever
    from .safety_signal_link import apply_safety_signal_flags
    from .substance_gate import document_scale_check
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
        guideline_checker: Optional[GuidelineGroundedChecker] = None,
        guideline_excerpts: Optional[Dict[str, dict]] = None,
    ):
        self.kb = kb or get_knowledge_base()
        self.retriever = retriever or ICHRetriever(self.kb)
        self.gap_checker = gap_checker or GapChecker(self.kb, self.retriever)
        self.scorer = scorer or CompletenessScorer(self.kb)
        self.report_generator = report_generator or ReportGenerator(self.scorer)
        self.reasoner = reasoner or GeminiGroundedReasoner()
        # guideline_grounded_checker.py is the single, consolidated
        # content-verification tier, replacing the earlier separate Tier 2
        # (content_checkpoints/content_verifier.py) and Tier 3
        # (exemplar_corpus/authenticity_checker.py) proposals.
        self.guideline_checker = guideline_checker or GuidelineGroundedChecker()
        self.guideline_excerpts = guideline_excerpts if guideline_excerpts is not None else get_guideline_excerpts()

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

        # Step 2c: Guideline-grounded content check (consolidated tier). Runs
        # strictly after the substance gate: only for sections that (a)
        # passed it (substance_gate_reason is None — a gate-forced-MISSING
        # section has no real text worth checking) and (b) have a real ICH
        # guideline excerpt for their section_id. Silently no-ops
        # (guideline_verdict stays None) when ANTHROPIC_API_KEY is
        # unavailable, the SDK call fails, or no excerpt exists yet, so this
        # degrades cleanly to Tier 1 + substance-gate-only behavior.
        self._apply_guideline_check(normalized_outline, gap_items)

        # Step 2d: Tier 0 document-scale sanity check. Only meaningful when
        # this outline came from a real PDF (source_page_count is set by
        # CTDPDFExtractor); stays None for dict/text/API inputs, so this
        # never affects those paths. modules_claimed is read from
        # match_evidence rather than post-gate status, since a section the
        # substance gate just downgraded to MISSING was still "claimed" by
        # the document.
        modules_claimed = {
            g.module_id for g in gap_items
            if g.match_evidence.matched_dossier_section_id is not None
        }
        scale_warning = document_scale_check(
            total_pages=normalized_outline.source_page_count,
            total_word_count=normalized_outline.source_total_word_count,
            modules_claimed=modules_claimed,
        )

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
            scale_warning=scale_warning,
        )

        return report

    @staticmethod
    def _dossier_by_id(outline: DossierOutlineInput) -> Dict[str, Any]:
        return {s.section_id.strip().upper(): s for s in outline.sections if s.section_id}

    @staticmethod
    def _build_section_text(dossier_section: Any) -> str:
        """Assembles the best available real text for a matched dossier section."""
        return " ".join(
            part.strip()
            for part in (
                dossier_section.title,
                dossier_section.description,
                dossier_section.content_summary,
            )
            if part and part.strip()
        )

    def _apply_guideline_check(
        self,
        outline: DossierOutlineInput,
        gap_items: List[Any],
    ) -> None:
        """Runs the consolidated guideline-grounded check in place on `gap_items`.

        For each GapItem that is PRESENT/PARTIAL, passed the substance gate
        (substance_gate_reason is None), has real body_text captured, and has
        a real guideline excerpt for its section_id, compares the candidate's
        actual text against that excerpt via Claude Haiku. Anything else
        (MISSING items, gate-forced-MISSING items, sections with no excerpt,
        or a failed/unavailable Anthropic call) is skipped silently —
        guideline_verdict stays None, so a missing ANTHROPIC_API_KEY or an
        unpopulated excerpt corpus degrades the whole system cleanly to
        Tier 1 + substance-gate-only behavior.

        Deliberately requires real `body_text` (not the short `description`
        preview): comparing a one-line demo blurb against the actual ICH
        guideline text would read as INSUFFICIENT/EMPTY for virtually every
        pre-existing structured/API dossier, regressing them the moment a
        real API key is configured.
        """
        if not self.guideline_excerpts:
            return

        dossier_by_id = self._dossier_by_id(outline)

        for item in gap_items:
            if item.status not in (GapStatus.PRESENT, GapStatus.PARTIAL):
                continue
            if getattr(item, "substance_gate_reason", None) is not None:
                continue

            excerpt_record = self.guideline_excerpts.get(item.section_id.strip().upper())
            if not excerpt_record:
                continue

            matched_id = item.match_evidence.matched_dossier_section_id
            dossier_section = dossier_by_id.get((matched_id or "").strip().upper())
            if dossier_section is None:
                continue

            section_text = (dossier_section.body_text or "").strip()
            if not section_text:
                continue

            try:
                result = self.guideline_checker.check_against_guideline(
                    candidate_section={
                        "section_id": item.section_id,
                        "title": dossier_section.title,
                        "body_text": section_text,
                    },
                    excerpt_record=excerpt_record,
                )
            except Exception:
                # Defense in depth: GuidelineGroundedChecker already fails
                # soft internally, this outer guard just guarantees prior
                # tiers never break because of a checker error.
                result = None

            if result is not None:
                item.guideline_verdict = result.verdict
                item.guideline_check_evidence = result.to_dict()

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
