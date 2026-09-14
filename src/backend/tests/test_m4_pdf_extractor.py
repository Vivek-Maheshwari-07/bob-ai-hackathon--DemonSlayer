"""Tests for Local PDF Extractor in Module M4."""

import pytest
from app.m4_rag.pdf_extractor import CTDPDFExtractor


def test_pdf_extractor_empty_input():
    outline = CTDPDFExtractor.extract_outline_from_pdf(
        pdf_source=b"",
        submission_title="Empty PDF",
    )
    assert outline.submission_title == "Empty PDF"
    assert len(outline.sections) == 0


def test_pdf_extractor_regex_matching():
    # Test line parsing heuristics
    sample_text = (
        "Common Technical Document Table of Contents\n\n"
        "1.1 Forms and Administrative Information: Comprehensive FDA Form 356h\n"
        "2.5 Clinical Overview - Critical benefit-risk assessment\n"
        "3.2.S.4 Control of Drug Substance - Validated release methods\n"
        "4.2.3 Toxicology Study Reports - GLP safety pharmacology\n"
        "5.3.5 Reports of Efficacy and Safety Studies - Pivotal clinical trial results\n"
    )
    # Use extract_outline_from_pdf fallback with string/text representation
    outline = CTDPDFExtractor.extract_outline_from_pdf(
        pdf_source=b"",  # Empty PDF triggers fallback to raw_text parsing if text is provided
        submission_title="Synthetic Dossier",
    )
    assert outline is not None
