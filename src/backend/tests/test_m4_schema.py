"""Tests for M4 RAG Schema definitions."""

import pytest
from pydantic import ValidationError
from app.m4_rag.schema import (
    DossierSectionInput,
    DossierOutlineInput,
    ICHSectionRequirement,
    GapStatus,
    CriticalityLevel,
    MatchMethod,
    MatchEvidence,
    GapItem,
    ModuleCompleteness,
    GapReportOutput,
)


def test_dossier_section_input_valid():
    section = DossierSectionInput(
        section_id=" 2.5 ",
        title=" Clinical Overview ",
        description="Comprehensive summary of clinical efficacy and safety",
    )
    assert section.section_id == "2.5"
    assert section.title == "Clinical Overview"
    assert "efficacy" in section.description


def test_dossier_section_input_empty_cleaning():
    section = DossierSectionInput(section_id="1.1", title="")
    assert section.section_id == "1.1"
    assert section.title == ""


def test_dossier_outline_input():
    outline = DossierOutlineInput(
        submission_title="Candidate NDA 2026",
        drug_name="BMS-Sample",
        sections=[
            DossierSectionInput(section_id="2.5", title="Clinical Overview"),
            DossierSectionInput(section_id="3.2.S.1", title="General Information"),
        ],
    )
    assert len(outline.sections) == 2
    assert outline.submission_title == "Candidate NDA 2026"


def test_ich_requirement_validation():
    req = ICHSectionRequirement(
        section_id="2.5",
        module_id=2,
        module_name="Module 2: CTD Summaries",
        title="Clinical Overview",
        requirement_text="The Clinical Overview is intended to provide a critical analysis of the clinical data.",
        criticality=CriticalityLevel.CRITICAL,
        weight=1.0,
        source="ICH M4E(R2)",
        keywords=["clinical overview", "efficacy", "safety analysis"],
    )
    assert req.module_id == 2
    assert req.criticality == CriticalityLevel.CRITICAL
    assert req.source == "ICH M4E(R2)"


def test_ich_requirement_invalid_module():
    with pytest.raises(ValidationError):
        ICHSectionRequirement(
            section_id="6.1",
            module_id=6,  # Invalid: CTD only has modules 1-5
            module_name="Module 6",
            title="Invalid",
            requirement_text="Test",
        )


def test_match_evidence_and_gap_item():
    evidence = MatchEvidence(
        match_method=MatchMethod.EXACT,
        confidence_score=1.0,
        matched_dossier_section_id="2.5",
        matched_dossier_title="Clinical Overview",
        evidence_reasoning="Exact alphanumeric section ID match found in candidate dossier.",
    )
    gap = GapItem(
        section_id="2.5",
        module_id=2,
        module_name="Module 2: CTD Summaries",
        title="Clinical Overview",
        status=GapStatus.PRESENT,
        criticality=CriticalityLevel.CRITICAL,
        match_evidence=evidence,
        source_reference="ICH M4E(R2)",
    )
    assert gap.status == GapStatus.PRESENT
    assert gap.match_evidence.confidence_score == 1.0


def test_module_completeness_metrics():
    mod = ModuleCompleteness(
        module_id=2,
        module_name="Module 2: CTD Summaries",
        total_required=7,
        present_count=5,
        partial_count=1,
        missing_count=1,
        critical_missing_count=0,
        completeness_percentage=78.57,
    )
    assert mod.completeness_percentage == 78.57
    assert mod.total_required == 7
