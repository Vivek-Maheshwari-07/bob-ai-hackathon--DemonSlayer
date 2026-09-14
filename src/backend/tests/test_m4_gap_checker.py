"""Tests for ICH M4 Gap Checker."""

import pytest
from app.m4_rag.dossier_parser import DossierParser
from app.m4_rag.gap_checker import GapChecker
from app.m4_rag.schema import GapStatus, CriticalityLevel, MatchMethod


def test_gap_checker_full_present_dossier():
    checker = GapChecker()
    # Build a dossier with exact sections
    payload = {
        "submission_title": "Full Dossier",
        "sections": [
            {"section_id": "1.0", "title": "Comprehensive TOC", "description": "Full module index"},
            {"section_id": "1.1", "title": "Forms", "description": "FDA Form 356h and cover letter"},
            {"section_id": "1.2", "title": "Labeling", "description": "SmPC and Package Insert"},
            {"section_id": "1.3", "title": "Experts", "description": "CVs and expert signatures"},
            {"section_id": "1.4", "title": "RMP", "description": "Risk management and pharmacovigilance plan"},
            {"section_id": "2.1", "title": "TOC", "description": "CTD Table of contents"},
            {"section_id": "2.2", "title": "Intro", "description": "Introduction to drug substance"},
            {"section_id": "2.3", "title": "QOS", "description": "Quality overall summary with CQAs"},
            {"section_id": "2.4", "title": "Nonclinical Overview", "description": "Safety pharmacology and tox overview"},
            {"section_id": "2.5", "title": "Clinical Overview", "description": "Efficacy and safety benefit-risk"},
            {"section_id": "2.6", "title": "Nonclin Summary", "description": "Written and tabulated animal summaries"},
            {"section_id": "2.7", "title": "Clinical Summary", "description": "Clinical pharmacology and safety summaries"},
            {"section_id": "3.1", "title": "Module 3 TOC", "description": "Quality TOC"},
            {"section_id": "3.2.S.1", "title": "General Info", "description": "Nomenclature and physical attributes"},
            {"section_id": "3.2.S.2", "title": "Manufacture", "description": "Process flow and in-process controls"},
            {"section_id": "3.2.S.3", "title": "Characterisation", "description": "Impurity profiling and structure"},
            {"section_id": "3.2.S.4", "title": "Control of DS", "description": "Specifications and batch analysis"},
            {"section_id": "3.2.S.5", "title": "Reference Standards", "description": "Primary reference qualification"},
            {"section_id": "3.2.S.6", "title": "Container Closure", "description": "Primary packaging suitability"},
            {"section_id": "3.2.S.7", "title": "Stability", "description": "Long term stability data"},
            {"section_id": "3.2.P.1", "title": "Description", "description": "Dosage form composition"},
            {"section_id": "3.2.P.2", "title": "Development", "description": "QbD formulation development"},
            {"section_id": "3.2.P.3", "title": "Manufacture DP", "description": "Batch formula and process validation"},
            {"section_id": "3.2.P.4", "title": "Excipients", "description": "Control and certificates for excipients"},
            {"section_id": "3.2.P.5", "title": "Control of DP", "description": "Finished product release testing"},
            {"section_id": "3.2.P.6", "title": "DP Standards", "description": "Reference materials"},
            {"section_id": "3.2.P.7", "title": "Packaging", "description": "Blister packaging and leachables"},
            {"section_id": "3.2.P.8", "title": "DP Stability", "description": "24 month real-time stability"},
            {"section_id": "3.2.A", "title": "Appendices", "description": "Facilities and viral safety"},
            {"section_id": "3.3", "title": "Literature", "description": "Module 3 references"},
            {"section_id": "4.1", "title": "M4 TOC", "description": "Nonclinical TOC"},
            {"section_id": "4.2.1", "title": "Pharmacology", "description": "Primary and secondary PD reports"},
            {"section_id": "4.2.2", "title": "PK", "description": "ADME nonclinical reports"},
            {"section_id": "4.2.3", "title": "Toxicology", "description": "GLP repeat dose and carcinogenicity"},
            {"section_id": "4.3", "title": "M4 References", "description": "Nonclinical references"},
            {"section_id": "5.1", "title": "M5 TOC", "description": "Clinical TOC"},
            {"section_id": "5.2", "title": "Study Listing", "description": "Tabular listing of all clinical trials"},
            {"section_id": "5.3.1", "title": "Biopharmaceutics", "description": "Bioavailability and BE reports"},
            {"section_id": "5.3.2", "title": "Human Biomaterials", "description": "Plasma protein binding and CYP assays"},
            {"section_id": "5.3.3", "title": "Human PK", "description": "Phase 1 PK SAD MAD reports"},
            {"section_id": "5.3.4", "title": "Human PD", "description": "Exposure response modeling"},
            {"section_id": "5.3.5", "title": "Efficacy & Safety", "description": "Pivotal Phase 3 CSRs"},
            {"section_id": "5.3.6", "title": "Postmarketing", "description": "PSUR / PBRER reports"},
            {"section_id": "5.3.7", "title": "CRFs", "description": "Death and SAE listings"},
            {"section_id": "5.4", "title": "M5 References", "description": "Clinical references"},
        ]
    }
    outline = DossierParser.parse_input(payload)
    results = checker.evaluate(outline)

    # Every required section should be PRESENT
    assert len(results) >= 40
    missing = [r for r in results if r.status == GapStatus.MISSING]
    assert len(missing) == 0, f"Expected 0 missing, got {[m.section_id for m in missing]}"


def test_gap_checker_partial_detection():
    checker = GapChecker()
    payload = {
        "sections": [
            {
                "section_id": "2.5",
                "title": "Clinical Overview",
                "description": "Draft document - in progress pending phase 3 unblinding",
                "status_hint": "Draft",
            },
            {
                "section_id": "3.2.S.4",
                "title": "Control of Drug Substance",
                "description": "TBD - specifications pending",
            },
        ]
    }
    outline = DossierParser.parse_input(payload)
    results = checker.evaluate(outline)

    r_25 = next(r for r in results if r.section_id == "2.5")
    assert r_25.status == GapStatus.PARTIAL
    assert "draft" in r_25.match_evidence.evidence_reasoning.lower()

    r_s4 = next(r for r in results if r.section_id == "3.2.S.4")
    assert r_s4.status == GapStatus.PARTIAL


def test_gap_checker_missing_detection():
    checker = GapChecker()
    payload = {
        "sections": [
            {"section_id": "2.5", "title": "Clinical Overview", "description": "Comprehensive document"}
        ]
    }
    outline = DossierParser.parse_input(payload)
    results = checker.evaluate(outline)

    r_tox = next(r for r in results if r.section_id == "4.2.3")
    assert r_tox.status == GapStatus.MISSING
    assert r_tox.criticality == CriticalityLevel.CRITICAL
    assert r_tox.action_item is not None
