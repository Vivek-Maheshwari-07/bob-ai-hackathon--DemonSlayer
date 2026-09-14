"""Tests for Dossier Outline Parser in Module M4."""

import pytest
from app.m4_rag.dossier_parser import DossierParser
from app.m4_rag.schema import DossierOutlineInput, DossierSectionInput


def test_normalize_section_id():
    assert DossierParser.normalize_section_id("Module 2.5") == "2.5"
    assert DossierParser.normalize_section_id("m3.2.s.1") == "3.2.S.1"
    assert DossierParser.normalize_section_id("Section 4.2.1") == "4.2.1"
    assert DossierParser.normalize_section_id("mod 5.3.5") == "5.3.5"
    assert DossierParser.normalize_section_id("3.2.p.8") == "3.2.P.8"
    assert DossierParser.normalize_section_id(" 1.1 ") == "1.1"
    assert DossierParser.normalize_section_id("3_2_s_4") == "3.2.S.4"


def test_parse_dict_valid():
    payload = {
        "submission_title": "Investigational NDA - OncoCare",
        "drug_name": "OncoCare-X",
        "target_region": "FDA / US",
        "sections": [
            {
                "section_id": "Module 2.5",
                "title": "Clinical Overview",
                "description": "Critical analysis of clinical development and benefit-risk profile.",
            },
            {
                "section_id": "3.2.S.1",
                "title": "General Information",
                "description": "Nomenclature and physical characteristics.",
            },
        ],
    }
    parsed = DossierParser.parse_input(payload)
    assert isinstance(parsed, DossierOutlineInput)
    assert parsed.submission_title == "Investigational NDA - OncoCare"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].section_id == "2.5"
    assert parsed.sections[1].section_id == "3.2.S.1"


def test_parse_duplicate_sections_merged():
    payload = {
        "sections": [
            {"section_id": "2.5", "title": "Clinical Overview", "description": "Part 1"},
            {"section_id": "Module 2.5", "title": "Clinical Overview", "description": "Part 2 with extra details"},
        ]
    }
    parsed = DossierParser.parse_input(payload)
    assert len(parsed.sections) == 1
    assert parsed.sections[0].section_id == "2.5"
    # Should keep the longer or merged description
    assert "Part 2 with extra details" in parsed.sections[0].description


def test_parse_raw_text_outline():
    raw_text = """
    1.1 Forms and Administrative Information - Complete FDA 356h
    2.5 Clinical Overview - Overall benefit-risk balance
    3.2.S.4 Control of Drug Substance - Release specifications and validation
    4.2.3 Toxicology Study Reports - 28-day repeat dose GLP studies
    5.3.5 Reports of Efficacy and Safety Studies - Phase 3 CSRs
    """
    parsed = DossierParser.parse_input(raw_text)
    assert len(parsed.sections) == 5
    sec_ids = [s.section_id for s in parsed.sections]
    assert "1.1" in sec_ids
    assert "2.5" in sec_ids
    assert "3.2.S.4" in sec_ids
    assert "4.2.3" in sec_ids
    assert "5.3.5" in sec_ids


def test_parse_malformed_and_empty_inputs():
    # Empty string
    assert len(DossierParser.parse_input("").sections) == 0

    # Empty dict
    assert len(DossierParser.parse_input({}).sections) == 0

    # None / garbage input
    assert len(DossierParser.parse_input(None).sections) == 0

    # Malformed section entries (e.g. empty strings inside sections array)
    dirty_payload = {
        "sections": [
            {"section_id": "", "title": "", "description": ""},
            {"section_id": "2.5", "title": "Clinical Overview"},
        ]
    }
    parsed = DossierParser.parse_input(dirty_payload)
    assert len(parsed.sections) == 1
    assert parsed.sections[0].section_id == "2.5"
