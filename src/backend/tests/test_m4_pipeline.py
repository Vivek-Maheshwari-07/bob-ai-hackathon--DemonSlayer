"""Tests for CTDRagCheckerPipeline End-to-End."""

import pytest
from app.m4_rag.pipeline import CTDRagCheckerPipeline, check_ctd_dossier
from app.m4_rag.schema import GapStatus, CriticalityLevel


def test_pipeline_with_partial_dossier():
    pipeline = CTDRagCheckerPipeline()
    candidate = {
        "submission_title": "Oncology Phase 3 Submission",
        "drug_name": "Antineo-1",
        "target_region": "FDA / US",
        "sections": [
            {"section_id": "1.1", "title": "Forms", "description": "FDA Form 356h complete"},
            {"section_id": "2.3", "title": "QOS", "description": "Comprehensive quality summary"},
            {"section_id": "2.5", "title": "Clinical Overview", "description": "Draft benefit risk summary", "status_hint": "Draft"},
            {"section_id": "3.2.S.1", "title": "General Info", "description": "Full chemical structure and properties"},
            {"section_id": "4.2.3", "title": "Toxicology", "description": "Complete 6-month GLP repeat dose studies"},
            {"section_id": "5.3.5", "title": "CSRs", "description": "Pivotal double-blind trial results"},
        ]
    }

    report = pipeline.run(candidate, enable_reasoner=True)
    assert report.submission_title == "Oncology Phase 3 Submission"
    assert report.drug_name == "Antineo-1"
    assert report.total_sections_evaluated >= 40
    assert report.present_total > 0
    assert report.partial_total >= 1  # 2.5 was marked Draft
    assert report.missing_total > 0
    assert 0.0 < report.overall_completeness < 100.0

    # Verify module breakdown
    for m in range(1, 6):
        mod_key = f"module_{m}"
        assert mod_key in report.modules
        mod_info = report.modules[mod_key]
        assert mod_info.total_required > 0

    assert len(report.recommended_actions) > 0
    assert len(report.limitations) == 3


def test_pipeline_with_empty_dossier():
    report = check_ctd_dossier({}, enable_reasoner=False)
    assert report.overall_completeness == 0.0
    assert report.present_total == 0
    assert report.missing_total == report.total_sections_evaluated
    assert report.critical_gaps_count > 0


def test_pipeline_with_raw_text_dossier():
    raw_text = """
    1.1 Forms and Administrative Information - Fully executed
    2.5 Clinical Overview - Final benefit-risk assessment
    3.2.S.4 Control of Drug Substance - Validated release assays
    4.2.3 Toxicology Study Reports - Complete GLP safety reports
    5.3.5 Reports of Efficacy and Safety Studies - Phase 3 CSRs
    """
    report = check_ctd_dossier(raw_text, enable_reasoner=True)
    assert report.present_total >= 5
    assert report.overall_completeness > 5.0
