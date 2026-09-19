"""Tests for the Tier 0 substance gate (substance_gate.py + gap_checker/pipeline wiring).

Covers the "substance-blindness" bug: a dossier consisting only of a table of
section IDs, titles, and status labels (no real narrative/technical content)
previously scored 96%/88% complete because Tier 1 treats a matched
header+status-label as equivalent to real documentation. The gate adds a
cheap, deterministic, always-on floor that runs before Tier 1's PRESENT/
PARTIAL classification and forces MISSING when a matched section's real
body_text falls short of a calibrated word-count floor for its module and
criticality.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.m4_rag.knowledge.loader import get_knowledge_base
from app.m4_rag.pipeline import CTDRagCheckerPipeline
from app.m4_rag.schema import CriticalityLevel, DossierSectionInput, GapStatus, ICHSectionRequirement
from app.m4_rag.substance_gate import document_scale_check, substance_gate

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _stub_embedding_model():
    """Every dossier in this file matches KB sections by exact section ID, so
    semantic matching (and its sentence-transformers network download) is
    never actually needed. Stub it out so these tests stay hermetic/offline."""
    fake_model = MagicMock()
    fake_model.encode.side_effect = lambda texts, **kwargs: np.zeros((len(texts), 8))
    with patch("app.m4_rag.retriever._get_embedding_model", return_value=fake_model):
        yield


def _requirement(module_id: int, criticality: CriticalityLevel) -> ICHSectionRequirement:
    return ICHSectionRequirement(
        section_id="X.Y",
        module_id=module_id,
        module_name=f"Module {module_id}",
        title="Test Section",
        requirement_text="Test requirement.",
        criticality=criticality,
        source="Test Source",
    )


def _words(n: int) -> str:
    return " ".join(["word"] * n)


# ─── substance_gate() unit tests ───────────────────────────────────────────


def test_substance_gate_skips_when_body_text_not_captured():
    """A short structured/API description with no body_text is untouched —
    the gate has nothing to judge and must not invent a failure."""
    section = DossierSectionInput(section_id="5.3.5", title="CSR", description="short blurb")
    status, reason = substance_gate(section, _requirement(5, CriticalityLevel.CRITICAL))
    assert status is None
    assert reason is None


def test_substance_gate_skips_when_section_is_none():
    status, reason = substance_gate(None, _requirement(1, CriticalityLevel.CRITICAL))
    assert status is None
    assert reason is None


def test_substance_gate_forces_missing_below_floor():
    section = DossierSectionInput(section_id="5.3.5", title="CSR", body_text=_words(12))
    status, reason = substance_gate(section, _requirement(5, CriticalityLevel.CRITICAL))
    assert status == GapStatus.MISSING
    assert "12 word" in reason
    assert "500" in reason


def test_substance_gate_passes_when_word_count_clears_floor():
    section = DossierSectionInput(section_id="1.1", title="Forms", body_text=_words(50))
    status, reason = substance_gate(section, _requirement(1, CriticalityLevel.CRITICAL))  # floor=40
    assert status is None
    assert reason is None


def test_substance_gate_floor_scales_with_module_and_criticality():
    # Same word count (60) clears the Module 1 CRITICAL floor (40) but not
    # the Module 5 CRITICAL floor (500).
    section = DossierSectionInput(section_id="X", title="X", body_text=_words(60))
    status_m1, _ = substance_gate(section, _requirement(1, CriticalityLevel.CRITICAL))
    status_m5, _ = substance_gate(section, _requirement(5, CriticalityLevel.CRITICAL))
    assert status_m1 is None
    assert status_m5 == GapStatus.MISSING


# ─── document_scale_check() unit tests ─────────────────────────────────────


def test_document_scale_check_flags_thin_module5_claim():
    warning = document_scale_check(total_pages=5, total_word_count=300, modules_claimed={5})
    assert warning is not None
    assert "Module 5" in warning
    assert "5 page" in warning


def test_document_scale_check_none_without_page_count():
    assert document_scale_check(total_pages=None, total_word_count=0, modules_claimed={5}) is None


def test_document_scale_check_none_without_claimed_modules():
    assert document_scale_check(total_pages=5, total_word_count=100, modules_claimed=set()) is None


def test_document_scale_check_none_when_scale_is_plausible():
    assert document_scale_check(total_pages=600, total_word_count=400_000, modules_claimed={5}) is None


# ─── End-to-end regression: label-only PDF fixtures ────────────────────────


def _build_label_only_pdf_bytes() -> bytes:
    """Builds a synthetic 5-page PDF containing ONLY a table of every KB
    section's ID, title, and a self-reported status label — no narrative or
    technical content behind any row. Mirrors the reported bug fixtures
    (ctd_m4_55_percent_completeness_test.pdf / m4_55_percent_completeness_demo.pdf),
    which are not available in this environment, so this reconstructs the
    same failure mode from the live ICH M4 knowledge base directly.
    """
    kb = get_knowledge_base()
    requirements = kb.get_all()
    rows_per_page = -(-len(requirements) // 5)  # ceil, spread evenly across 5 pages

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 10)
    y = 750
    for i, req in enumerate(requirements):
        status_label = "PRESENT" if req.criticality.value in ("CRITICAL", "MAJOR") else "MISSING"
        c.drawString(50, y, f"{req.section_id}   {req.title}   {status_label}")
        y -= 20
        if (i + 1) % rows_per_page == 0 and (i + 1) < len(requirements):
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 750
    c.save()
    return buf.getvalue()


def test_label_only_pdf_scores_low_and_raises_scale_warning():
    pipeline = CTDRagCheckerPipeline()
    pdf_bytes = _build_label_only_pdf_bytes()

    report = pipeline.run_pdf(
        pdf_bytes,
        submission_title="Label-Only Completeness Test",
        enable_reasoner=False,
    )

    # Previously this kind of table-only dossier scored 96%/88%; with the
    # substance gate wired in, a title+status-label row carries zero real
    # body_text and every matched section is forced to MISSING.
    assert report.overall_completeness < 15.0
    assert report.scale_warning is not None
    assert "Module" in report.scale_warning

    gated = [g for g in report.missing_sections if g.substance_gate_reason]
    assert len(gated) > 0
    assert all(g.status == GapStatus.MISSING for g in gated)


def test_label_only_pdf_second_fixture_variant_also_scores_low():
    """A second variant (different row ordering/status mix) — regression
    coverage against both reported fixtures' failure mode, since neither
    original file is available in this environment."""
    pipeline = CTDRagCheckerPipeline()
    kb = get_knowledge_base()
    requirements = list(reversed(kb.get_all()))
    rows_per_page = -(-len(requirements) // 5)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 10)
    y = 750
    for i, req in enumerate(requirements):
        c.drawString(50, y, f"{req.section_id}   {req.title}   PRESENT")
        y -= 20
        if (i + 1) % rows_per_page == 0 and (i + 1) < len(requirements):
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 750
    c.save()
    pdf_bytes = buf.getvalue()

    report = pipeline.run_pdf(
        pdf_bytes,
        submission_title="Label-Only Completeness Demo",
        enable_reasoner=False,
    )

    assert report.overall_completeness < 15.0
    assert report.scale_warning is not None


# ─── Critical false-positive check: genuinely substantive content ─────────


def test_substance_gate_does_not_false_trigger_on_legitimate_vioxx_content():
    """Reuses the Vioxx NDA 21-042 scenario's section IDs/titles/drug name,
    but with genuinely substantive body_text for each section (the kind of
    real narrative a full submission would contain, clearing the calibrated
    floor for that section's module+criticality). Confirms the gate does NOT
    force any of these to MISSING — the critical false-positive check."""
    pipeline = CTDRagCheckerPipeline()

    csr_paragraph = (
        "This report presents the pivotal Phase 3, randomized, double-blind, "
        "placebo- and active-comparator-controlled trials of rofecoxib in adult "
        "and geriatric patients with osteoarthritis and acute post-surgical dental "
        "pain, conducted across multiple centers in North America and Europe. "
        "The study population comprised patients aged 18 to 85 meeting American "
        "College of Rheumatology criteria for osteoarthritis of the knee or hip, "
        "excluding those with active peptic ulcer disease or prior cardiovascular "
        "events. The primary efficacy endpoint was the mean change from baseline "
        "in the WOMAC pain subscale at Week 6, with secondary endpoints including "
        "patient global assessment and investigator global assessment of disease "
        "activity. A total of 2,756 patients were randomized in a 1:1:1 ratio to "
        "rofecoxib 25 mg, ibuprofen 800 mg three times daily, or placebo, with "
        "stratification by baseline disease severity. Patient disposition showed "
        "2,412 patients completed the full treatment period, with discontinuations "
        "primarily attributed to lack of efficacy and gastrointestinal adverse "
        "events. Demographic and baseline characteristics were balanced across "
        "treatment arms, with a mean age of 63 years and 68 percent female "
        "representation. Serious adverse events, including three cardiovascular "
        "thrombotic events and one death from myocardial infarction, were "
        "adjudicated by an independent safety committee and are tabulated in the "
        "integrated summary of safety alongside gastrointestinal perforation, "
        "ulceration, and bleeding rates compared with the active comparator arm."
    ) * 3  # ~648 words, comfortably clears the 500-word Module 5 CRITICAL floor

    toxicology_paragraph = (
        "Repeat-dose good laboratory practice toxicology studies were conducted "
        "in Sprague-Dawley rats and cynomolgus monkeys receiving oral rofecoxib "
        "at 2, 10, and 50 mg/kg/day for durations of 28 days, 13 weeks, and 26 "
        "weeks, with satellite groups assessed for toxicokinetics and reversibility "
        "following a 4-week recovery period. Core battery safety pharmacology "
        "endpoints spanning the central nervous, cardiovascular, and respiratory "
        "systems were evaluated via functional observational battery, telemetered "
        "blood pressure and electrocardiogram monitoring in conscious dogs, and "
        "whole-body plethysmography in rats, with no test-article-related effects "
        "on respiratory rate or tidal volume observed at any dose tested. A dose-"
        "dependent increase in renal papillary changes and gastric mucosal erosion "
        "was observed at the high dose in both species, consistent with the known "
        "class effect of cyclooxygenase inhibition, establishing a no-observed-"
        "adverse-effect level of 10 mg/kg/day in rats and 5 mg/kg/day in monkeys. "
        "All pivotal studies were conducted under full GLP compliance with "
        "quality assurance unit audit certification, and the oral route of "
        "administration matched the intended clinical dosing route."
    ) * 4  # ~656 words, comfortably clears the 400-word Module 4 CRITICAL floor

    quality_paragraph = (
        "This section provides the nomenclature, molecular structure, and "
        "physicochemical properties of rofecoxib drug substance, including its "
        "chemical name, molecular formula, and characterization by infrared, "
        "nuclear magnetic resonance, and mass spectrometry, along with a "
        "discussion of polymorphism, solubility across the physiological pH "
        "range, and hygroscopicity data supporting the proposed manufacturing "
        "and storage conditions for the active pharmaceutical ingredient."
    ) * 6  # ~342 words, comfortably clears the 300-word Module 3 CRITICAL floor

    clinical_overview_paragraph = (
        "This clinical overview presents an integrated benefit-risk assessment "
        "of rofecoxib for osteoarthritis and acute pain, focusing on upper "
        "gastrointestinal tolerability relative to non-selective NSAIDs and the "
        "pre-market pooled cardiovascular relative risk observed across the "
        "Phase 3 program, with reference to the pivotal efficacy and safety "
        "study reports summarized elsewhere in this submission."
    ) * 4  # ~208 words, comfortably clears the 150-word Module 2 CRITICAL floor

    admin_text = (
        "This section contains the completed FDA Form 356h application for "
        "approval to market rofecoxib, together with the administrative cover "
        "letter, application tracking correspondence, and the applicant's "
        "regional compliance declarations required for a new drug application, "
        "along with the officer signatures and submission date certifying "
        "that all enclosed materials meet regional filing requirements."
    )  # clears the 40-word Module 1 CRITICAL floor

    report = pipeline.run(
        {
            "submission_title": "Vioxx (Rofecoxib) NDA 21-042 Safety Audit",
            "drug_name": "VIOXX",
            "target_region": "FDA / US",
            "sections": [
                {
                    "section_id": "1.1",
                    "title": "Forms and Administrative Information",
                    "body_text": admin_text,
                },
                {
                    "section_id": "2.3",
                    "title": "Quality Overall Summary",
                    "body_text": quality_paragraph,
                },
                {
                    "section_id": "2.5",
                    "title": "Clinical Overview",
                    "body_text": clinical_overview_paragraph,
                },
                {
                    "section_id": "3.2.S.1",
                    "title": "General Information on Drug Substance",
                    "body_text": quality_paragraph,
                },
                {
                    "section_id": "4.2.3",
                    "title": "Toxicology Study Reports",
                    "body_text": toxicology_paragraph,
                },
                {
                    "section_id": "5.3.5",
                    "title": "Reports of Efficacy and Safety Studies",
                    "body_text": csr_paragraph,
                },
            ],
        },
        enable_reasoner=False,
    )

    for section_id in ("1.1", "2.3", "2.5", "3.2.S.1", "4.2.3", "5.3.5"):
        item = next(
            g
            for g in report.present_sections + report.partial_sections + report.missing_sections
            if g.section_id == section_id
        )
        assert item.substance_gate_reason is None, (
            f"Section {section_id} was false-positively gated: {item.substance_gate_reason}"
        )
        assert item.status != GapStatus.MISSING, (
            f"Section {section_id} with genuinely substantive content was incorrectly forced MISSING"
        )


# ─── Fixture-file regression: tests/fixtures/*.pdf ─────────────────────────
# See tests/fixtures/README.md — these are reconstructions of the originally
# reported label-only fixtures (not present in this environment), built from
# the live KB to reproduce the same failure mode from an actual PDF file on
# disk rather than an in-memory buffer.


@pytest.mark.parametrize(
    "fixture_name",
    ["ctd_m4_55_percent_completeness_test.pdf", "m4_55_percent_completeness_demo.pdf"],
)
def test_fixture_pdf_scores_below_15_percent_with_scale_warning(fixture_name):
    fixture_path = FIXTURES_DIR / fixture_name
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    pipeline = CTDRagCheckerPipeline()
    with open(fixture_path, "rb") as f:
        report = pipeline.run_pdf(
            f.read(),
            submission_title=f"Fixture Regression: {fixture_name}",
            enable_reasoner=False,
        )

    assert report.overall_completeness < 15.0, (
        f"{fixture_name} scored {report.overall_completeness}% — the substance gate "
        f"should have collapsed this label-only table to well under 15%"
    )
    assert report.scale_warning is not None, f"{fixture_name} should raise a document-scale warning"
