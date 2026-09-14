"""Tests for Report Generator in Module M4."""

import pytest
from app.m4_rag.report_generator import ReportGenerator
from app.m4_rag.schema import (
    CriticalityLevel,
    DossierOutlineInput,
    GapItem,
    GapStatus,
    MatchEvidence,
    MatchMethod,
)


def test_report_generator_structure():
    gen = ReportGenerator()
    outline = DossierOutlineInput(
        submission_title="Test NDA Submission",
        drug_name="Candidate-101",
        target_region="FDA",
    )
    gap_items = [
        GapItem(
            section_id="2.5",
            module_id=2,
            module_name="Module 2: CTD Summaries",
            title="Clinical Overview",
            status=GapStatus.PRESENT,
            criticality=CriticalityLevel.CRITICAL,
            match_evidence=MatchEvidence(
                match_method=MatchMethod.EXACT,
                confidence_score=1.0,
                evidence_reasoning="Found exact match",
            ),
        ),
        GapItem(
            section_id="3.2.S.4",
            module_id=3,
            module_name="Module 3: Quality",
            title="Control of Drug Substance",
            status=GapStatus.MISSING,
            criticality=CriticalityLevel.CRITICAL,
            match_evidence=MatchEvidence(
                match_method=MatchMethod.NONE,
                confidence_score=0.0,
                evidence_reasoning="Missing section",
            ),
            action_item="Attach 3.2.S.4 specifications.",
        ),
    ]

    report = gen.generate_report(outline, gap_items)
    assert report.submission_title == "Test NDA Submission"
    assert report.drug_name == "Candidate-101"
    assert report.total_sections_evaluated == 2
    assert report.present_total == 1
    assert report.missing_total == 1
    assert report.critical_gaps_count == 1
    assert len(report.priority_gaps) == 1
    assert report.priority_gaps[0].section_id == "3.2.S.4"
    assert len(report.recommended_actions) > 0
    assert len(report.limitations) > 0
