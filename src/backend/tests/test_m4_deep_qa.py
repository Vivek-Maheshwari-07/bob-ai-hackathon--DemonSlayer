"""Comprehensive Deep QA & Exhaustive Edge Case Test Suite for M4 (CTD / ICH M4 RAG Checker).

Covers:
- Phase 4: ICH M4 Knowledge Base QA & Integrity
- Phase 5: PDF Ingestion & Robustness across edge-case documents
- Phase 6: Section Detection & Normalization
- Phase 7: Deterministic Exact Matching
- Phase 8: Vector Representation & Embeddings
- Phase 9: Vector Store & Retriever indexing/retrieval
- Phase 10: RAG Controlled Query Relevance
- Phase 11-14: Gemini 2.5 Flash Grounding, Schemas & Structured Output
- Phase 15-16: PRESENT/PARTIAL/MISSING & Anti-Hallucination
- Phase 17-18: Token Efficiency & Deterministic Completeness Calculation
- Phase 19: Gap Report Generation & Frontend Compatibility
- Phase 20-23: Gemini Failure, Timeout, Rate-Limit & Free-Tier Resilience
- Phase 24-26: Full M4 Pipeline Integration & E2E Verification
"""

import io
import json
import pytest
from unittest.mock import MagicMock, patch

from app.m4_rag.completeness import CompletenessScorer
from app.m4_rag.dossier_parser import DossierParser
from app.m4_rag.gap_checker import GapChecker
from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner
from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.pdf_extractor import CTDPDFExtractor
from app.m4_rag.pipeline import CTDRagCheckerPipeline, check_ctd_dossier, check_ctd_pdf
from app.m4_rag.report_generator import ReportGenerator
from app.m4_rag.retriever import ICHRetriever
from app.m4_rag.schema import (
    CriticalityLevel,
    DossierOutlineInput,
    DossierSectionInput,
    GapItem,
    GapReportOutput,
    GapStatus,
    ICHSectionRequirement,
    MatchEvidence,
    MatchMethod,
    ModuleCompleteness,
)


# ============================================================================
# PHASE 4: ICH M4 KNOWLEDGE BASE QA
# ============================================================================
class TestPhase4KnowledgeBaseQA:
    def test_knowledge_base_completeness_and_structure(self):
        kb = get_knowledge_base()
        all_reqs = kb.get_all()
        assert len(all_reqs) >= 20, f"Expected at least 20 verified ICH sections, found {len(all_reqs)}"

        seen_ids = set()
        for req in all_reqs:
            # Check fields
            assert req.section_id, "section_id must not be empty"
            assert req.section_id not in seen_ids, f"Duplicate section_id: {req.section_id}"
            seen_ids.add(req.section_id)

            assert 1 <= req.module_id <= 5, f"Invalid module_id: {req.module_id}"
            assert req.module_name, "module_name must not be empty"
            assert req.title, f"title missing for {req.section_id}"
            assert len(req.requirement_text) >= 10, f"Requirement text too short for {req.section_id}"
            assert req.source, f"source missing for {req.section_id}"
            assert isinstance(req.criticality, CriticalityLevel)
            assert req.weight > 0

    def test_all_five_ctd_modules_represented(self):
        kb = get_knowledge_base()
        for mod_id in range(1, 6):
            mod_reqs = kb.get_by_module(mod_id)
            assert len(mod_reqs) > 0, f"Module {mod_id} has no verified requirements in KB!"

    def test_knowledge_base_no_fabricated_data(self):
        kb = get_knowledge_base()
        # Verify key canonical sections exist
        assert kb.get_by_id("1.0") is not None
        assert kb.get_by_id("2.5") is not None
        assert kb.get_by_id("3.2.S.1") is not None
        assert kb.get_by_id("4.2.1") is not None
        assert kb.get_by_id("5.3.5") is not None
        # Verify fake section does not exist
        assert kb.get_by_id("9.9.9") is None
        assert kb.get_by_id("3.99.FAKE") is None


# ============================================================================
# PHASE 5: PDF INGESTION TESTING & EDGE CASES
# ============================================================================
class TestPhase5PDFIngestion:
    def test_empty_pdf_stream(self):
        # Empty stream should fail gracefully without crashing
        outline = CTDPDFExtractor.extract_outline_from_pdf(b"")
        assert isinstance(outline, DossierOutlineInput)
        assert len(outline.sections) == 0

    def test_corrupted_pdf_bytes(self):
        corrupted = b"NOT_A_REAL_PDF_HEADER_12345_CORRUPTED"
        outline = CTDPDFExtractor.extract_outline_from_pdf(corrupted)
        assert isinstance(outline, DossierOutlineInput)
        assert len(outline.sections) == 0

    def test_unsupported_file_type_handling(self):
        text_data = b"PLAIN TEXT DATA WITHOUT PDF STRUCTURE"
        outline = CTDPDFExtractor.extract_outline_from_pdf(text_data)
        assert isinstance(outline, DossierOutlineInput)

    def test_text_heavy_and_unusual_formatting_parsing(self):
        raw_text = """
        === TABLE OF CONTENTS ===
        Module 1.0 - Administrative Information (Cover letter and application forms)
        Section 2.5 : Clinical Overview - Benefit-Risk Assessment of Phase 3 Data
        # 3.2.S.1 General Information on Drug Substance (API Structure & PhysChem)
        4.2.1 Pharmacology: Primary Pharmacodynamics in Animal Models
        5.3.5 Reports of Efficacy and Safety Studies (Double Blind Pivotal Trials)
        """
        outline = DossierParser.parse_input(raw_text)
        assert len(outline.sections) == 5
        sec_ids = [s.section_id for s in outline.sections]
        assert "1.0" in sec_ids
        assert "2.5" in sec_ids
        assert "3.2.S.1" in sec_ids
        assert "4.2.1" in sec_ids
        assert "5.3.5" in sec_ids


# ============================================================================
# PHASE 6: SECTION DETECTION & NORMALIZATION
# ============================================================================
class TestPhase6SectionDetection:
    @pytest.mark.parametrize(
        "raw_input,expected_norm",
        [
            ("Module 3.2.s.1", "3.2.S.1"),
            ("m3.2.p.5", "3.2.P.5"),
            ("Sec. 5.3.5", "5.3.5"),
            ("  2.5  ", "2.5"),
            ("MODULE 4.2.1", "4.2.1"),
            ("mod 1.0", "1.0"),
            ("3.2.a.1", "3.2.A.1"),
            ("3_2_s_2", "3.2.S.2"),
            ("3-2-P-1", "3.2.P.1"),
        ],
    )
    def test_section_normalization_variations(self, raw_input, expected_norm):
        norm = DossierParser.normalize_section_id(raw_input)
        assert norm == expected_norm

    def test_malformed_and_unknown_section_ids(self):
        assert DossierParser.normalize_section_id("") == ""
        assert DossierParser.normalize_section_id(None) == ""
        # Unknown or free text
        parsed = DossierParser.parse_input("Unknown Background Information without section ID")
        assert len(parsed.sections) == 1
        assert parsed.sections[0].section_id == ""

    def test_duplicate_sections_are_merged_deterministically(self):
        outline_input = DossierOutlineInput(
            submission_title="Test Duplicate Dossier",
            sections=[
                DossierSectionInput(section_id="2.5", title="Clinical Overview", description="Short desc"),
                DossierSectionInput(section_id="2.5", title="Clinical Overview Detailed", description="Comprehensive Phase 3 clinical summary with efficacy data"),
            ],
        )
        parsed = DossierParser.parse_input(outline_input)
        assert len(parsed.sections) == 1
        assert parsed.sections[0].section_id == "2.5"
        assert "Comprehensive Phase 3" in parsed.sections[0].description


# ============================================================================
# PHASE 7: EXACT MATCHING DETERMINISTIC TEST
# ============================================================================
class TestPhase7ExactMatching:
    def test_exact_match_deterministic(self):
        retriever = ICHRetriever()
        req, evidence = retriever.find_best_requirement_for_dossier_section(
            section_id="3.2.S.1",
            title="General Information on Drug Substance",
        )
        assert req is not None
        assert req.section_id == "3.2.S.1"
        assert evidence.match_method == MatchMethod.EXACT
        assert evidence.confidence_score == 1.0

    def test_unknown_section_no_exact_match(self):
        retriever = ICHRetriever()
        req, evidence = retriever.find_best_requirement_for_dossier_section(
            section_id="99.99.UNKNOWN",
            title="Random Unrelated Study",
            description="Random unrelated topic",
        )
        # Should not falsely exact match
        assert evidence.match_method != MatchMethod.EXACT


# ============================================================================
# PHASE 8 & 9: EMBEDDINGS & VECTOR RETRIEVER
# ============================================================================
class TestPhase8And9EmbeddingsAndRetriever:
    def test_vector_search_relevance(self):
        retriever = ICHRetriever()
        # Query for toxicology / nonclinical
        results = retriever.semantic_search("Toxicology studies single and repeat dose toxicity", top_k=3)
        assert len(results) > 0
        top_req, score = results[0]
        assert top_req.module_id == 4  # Nonclinical module
        assert score >= 0.30

    def test_empty_and_unrelated_queries(self):
        retriever = ICHRetriever()
        assert retriever.semantic_search("") == []
        assert retriever.semantic_search("   ") == []

        # Unrelated text
        results = retriever.semantic_search("Aerospace jet engine flight avionics software", top_k=1, min_similarity=0.70)
        assert len(results) == 0  # Should not match high threshold


# ============================================================================
# PHASE 10: RAG RETRIEVAL TESTING
# ============================================================================
class TestPhase10RAGTesting:
    def test_rag_controlled_relevance_levels(self):
        retriever = ICHRetriever()
        # High relevance
        res_high = retriever.semantic_search("Drug Substance Stability testing protocol accelerated", top_k=1)
        assert len(res_high) > 0
        assert "stability" in res_high[0][0].title.lower() or "stability" in res_high[0][0].requirement_text.lower()


# ============================================================================
# PHASE 11 - 14: GEMINI REASONER, GROUNDING & STRUCTURED OUTPUT
# ============================================================================
class TestPhase11To14GeminiReasoner:
    def test_gemini_offline_deterministic_fallback(self):
        # When no API key is provided, falls back cleanly to deterministic reasoning
        reasoner = GeminiGroundedReasoner(api_key="")
        assert not reasoner.is_available

        gaps = [
            GapItem(
                section_id="2.5",
                module_id=2,
                module_name="Module 2: CTD Summaries",
                title="Clinical Overview",
                status=GapStatus.MISSING,
                criticality=CriticalityLevel.CRITICAL,
                match_evidence=MatchEvidence(
                    match_method=MatchMethod.NONE,
                    confidence_score=0.0,
                    evidence_reasoning="Section absent",
                ),
                source_reference="ICH M4E(R2)",
            )
        ]
        insights = reasoner.generate_reasoning_insights(gaps, overall_completeness=45.0)
        assert len(insights) > 0
        assert "critical" in insights[0].lower() or "barrier" in insights[0].lower()

    @patch("httpx.Client.post")
    def test_gemini_grounded_mock_response(self, mock_post):
        # Mock successful Gemini API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Draft Section 2.5 immediately.\nPrioritize pivotal clinical trial summary in 5.3.5."
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        reasoner = GeminiGroundedReasoner(api_key="test_mock_key")
        assert reasoner.is_available

        gaps = [
            GapItem(
                section_id="2.5",
                module_id=2,
                module_name="Module 2: CTD Summaries",
                title="Clinical Overview",
                status=GapStatus.MISSING,
                criticality=CriticalityLevel.CRITICAL,
                match_evidence=MatchEvidence(
                    match_method=MatchMethod.NONE,
                    confidence_score=0.0,
                    evidence_reasoning="Section absent",
                ),
                source_reference="ICH M4E(R2)",
            )
        ]
        insights = reasoner.generate_reasoning_insights(gaps, overall_completeness=50.0)
        assert len(insights) == 2
        assert "Draft Section 2.5" in insights[0]


# ============================================================================
# PHASE 15 & 16: PRESENT / PARTIAL / MISSING & ANTI-HALLUCINATION
# ============================================================================
class TestPhase15And16ClassificationAndAntiHallucination:
    def test_classification_states(self):
        checker = GapChecker()

        outline = DossierOutlineInput(
            submission_title="Test Classification Dossier",
            sections=[
                # TEST A: Clear PRESENT
                DossierSectionInput(section_id="1.0", title="Administrative Information", description="Full administrative documentation with cover letter"),
                # TEST B: PARTIAL (draft indicator)
                DossierSectionInput(section_id="2.5", title="Clinical Overview", description="Preliminary draft in progress. Pending final study lock.", status_hint="draft"),
                # TEST C: MISSING (e.g. 3.2.S.1 not provided)
            ],
        )

        gaps = checker.evaluate(outline)
        gaps_by_id = {g.section_id: g for g in gaps}

        # 1.0 should be PRESENT
        assert gaps_by_id["1.0"].status == GapStatus.PRESENT
        # 2.5 should be PARTIAL
        assert gaps_by_id["2.5"].status == GapStatus.PARTIAL
        # 3.2.S.1 should be MISSING
        assert gaps_by_id["3.2.S.1"].status == GapStatus.MISSING

    def test_anti_hallucination_on_fake_sections(self):
        checker = GapChecker()
        outline = DossierOutlineInput(
            submission_title="Fake Section Dossier",
            sections=[
                DossierSectionInput(section_id="99.9.FAKE", title="Fake Imaginary Drug Data", description="Unrelated manufactured text"),
            ],
        )
        gaps = checker.evaluate(outline)
        # All evaluated gaps MUST strictly match verified ICH sections only
        for gap in gaps:
            assert gap.section_id != "99.9.FAKE"
            assert gap.module_id in (1, 2, 3, 4, 5)


# ============================================================================
# PHASE 17 & 18: COMPLETENESS CALCULATION
# ============================================================================
class TestPhase17And18CompletenessCalculation:
    def test_100_percent_dossier(self):
        kb = get_knowledge_base()
        all_reqs = kb.get_all()
        # All sections present
        gaps = [
            GapItem(
                section_id=r.section_id,
                module_id=r.module_id,
                module_name=r.module_name,
                title=r.title,
                status=GapStatus.PRESENT,
                criticality=r.criticality,
                match_evidence=MatchEvidence(match_method=MatchMethod.EXACT, confidence_score=1.0, evidence_reasoning="Full match"),
                source_reference=r.source,
            )
            for r in all_reqs
        ]
        scorer = CompletenessScorer(kb)
        overall, modules = scorer.calculate(gaps)
        assert overall == 100.0
        for m in modules.values():
            assert m.completeness_percentage == 100.0
            assert m.missing_count == 0

    def test_0_percent_dossier(self):
        kb = get_knowledge_base()
        all_reqs = kb.get_all()
        # All sections missing
        gaps = [
            GapItem(
                section_id=r.section_id,
                module_id=r.module_id,
                module_name=r.module_name,
                title=r.title,
                status=GapStatus.MISSING,
                criticality=r.criticality,
                match_evidence=MatchEvidence(match_method=MatchMethod.NONE, confidence_score=0.0, evidence_reasoning="None"),
                source_reference=r.source,
            )
            for r in all_reqs
        ]
        scorer = CompletenessScorer(kb)
        overall, modules = scorer.calculate(gaps)
        assert overall == 0.0
        for m in modules.values():
            assert m.completeness_percentage == 0.0
            assert m.present_count == 0

    def test_partial_scoring_weight(self):
        kb = get_knowledge_base()
        all_reqs = kb.get_all()
        # All sections partial -> should be exactly 50.0%
        gaps = [
            GapItem(
                section_id=r.section_id,
                module_id=r.module_id,
                module_name=r.module_name,
                title=r.title,
                status=GapStatus.PARTIAL,
                criticality=r.criticality,
                match_evidence=MatchEvidence(match_method=MatchMethod.EXACT, confidence_score=0.5, evidence_reasoning="Partial"),
                source_reference=r.source,
            )
            for r in all_reqs
        ]
        scorer = CompletenessScorer(kb)
        overall, _ = scorer.calculate(gaps)
        assert overall == 50.0

    def test_empty_gap_items_division_by_zero_safety(self):
        scorer = CompletenessScorer()
        overall, modules = scorer.calculate([])
        assert overall == 0.0
        assert len(modules) == 5


# ============================================================================
# PHASE 19: GAP REPORT & RECOMMENDATIONS
# ============================================================================
class TestPhase19GapReport:
    def test_report_generation_structure(self):
        pipeline = CTDRagCheckerPipeline()
        report = pipeline.run(
            input_data={
                "submission_title": "Phase 19 Test Dossier",
                "drug_name": "TestDrug-19",
                "target_region": "FDA / EMA",
                "sections": [
                    {"section_id": "1.0", "title": "Admin", "description": "Complete"},
                    {"section_id": "2.5", "title": "Clinical Overview", "description": "Draft placeholder", "status_hint": "draft"},
                ],
            }
        )
        assert isinstance(report, GapReportOutput)
        assert report.total_sections_evaluated >= 20
        assert report.overall_completeness > 0
        assert report.modules is not None
        assert len(report.modules) == 5
        assert len(report.priority_gaps) > 0
        assert len(report.recommended_actions) > 0
        assert len(report.limitations) > 0

        # Validate JSON serialization
        report_json = report.model_dump_json()
        data = json.loads(report_json)
        assert "overall_completeness" in data
        assert "modules" in data


# ============================================================================
# PHASE 20 - 23: GEMINI FAILURE & RATE LIMIT RESILIENCE
# ============================================================================
class TestPhase20To23GeminiFailureResilience:
    @patch("httpx.Client.post")
    def test_gemini_429_rate_limit_fallback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Quota exceeded"
        mock_post.return_value = mock_response

        reasoner = GeminiGroundedReasoner(api_key="mock_key")
        gaps = [
            GapItem(
                section_id="3.2.S.1",
                module_id=3,
                module_name="Module 3: Quality",
                title="Drug Substance",
                status=GapStatus.MISSING,
                criticality=CriticalityLevel.CRITICAL,
                match_evidence=MatchEvidence(match_method=MatchMethod.NONE, confidence_score=0.0, evidence_reasoning="Missing"),
                source_reference="ICH M4Q(R1)",
            )
        ]
        # Should gracefully fall back to deterministic insights without raising an exception
        insights = reasoner.generate_reasoning_insights(gaps, 20.0)
        assert len(insights) > 0

    @patch("httpx.Client.post", side_effect=Exception("Connection Timeout"))
    def test_gemini_timeout_fallback(self, mock_post):
        reasoner = GeminiGroundedReasoner(api_key="mock_key")
        gaps = [
            GapItem(
                section_id="5.3.5",
                module_id=5,
                module_name="Module 5: Clinical",
                title="Clinical Study Reports",
                status=GapStatus.MISSING,
                criticality=CriticalityLevel.CRITICAL,
                match_evidence=MatchEvidence(match_method=MatchMethod.NONE, confidence_score=0.0, evidence_reasoning="Missing"),
                source_reference="ICH M4E(R2)",
            )
        ]
        insights = reasoner.generate_reasoning_insights(gaps, 10.0)
        assert len(insights) > 0


# ============================================================================
# PHASE 24 - 26: FULL M4 INTEGRATION & E2E PIPELINE
# ============================================================================
class TestPhase24To26M4IntegrationAndE2E:
    def test_full_e2e_pipeline_execution(self):
        pipeline = CTDRagCheckerPipeline()
        realistic_dossier = {
            "submission_title": "E2E Monoclonal Antibody CTD Dossier",
            "drug_name": "mAb-2026",
            "target_region": "Global ICH",
            "sections": [
                {"section_id": "1.0", "title": "Administrative Information", "description": "Complete administrative documentation"},
                {"section_id": "2.2", "title": "CTD Introduction", "description": "Introduction to pharmacological class"},
                {"section_id": "2.5", "title": "Clinical Overview", "description": "Clinical overview and benefit-risk"},
                {"section_id": "3.2.S.1", "title": "General Information API", "description": "Chemical and biological structure"},
                {"section_id": "3.2.P.1", "title": "Description and Composition of Drug Product", "description": "Dosage form and formulation"},
                {"section_id": "4.2.1", "title": "Pharmacology", "description": "Primary and secondary pharmacodynamics"},
                {"section_id": "5.3.5", "title": "Reports of Efficacy and Safety Studies", "description": "Interim draft Phase 3 report", "status_hint": "draft"},
            ],
        }

        report = pipeline.run(realistic_dossier)
        assert report.submission_title == "E2E Monoclonal Antibody CTD Dossier"
        assert report.present_total >= 5
        assert report.partial_total >= 1
        assert report.overall_completeness > 10.0
        assert len(report.priority_gaps) > 0

