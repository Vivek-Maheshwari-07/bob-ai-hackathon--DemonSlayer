"""Tests for the consolidated guideline-grounded content checker
(guideline_grounded_checker.py + pipeline/completeness wiring).

This is the single content-verification tier that replaced the earlier
separate Tier 2 (content_checkpoints/content_verifier.py) and Tier 3
(exemplar_corpus/authenticity_checker.py) proposals: it compares a candidate
section's real body_text against the actual ICH guideline requirement
excerpt for that section_id (knowledge/guideline_excerpts.json) via Claude
Haiku, run strictly after the substance gate.

Since a live ANTHROPIC_API_KEY isn't available in this environment, these
tests mock GuidelineGroundedChecker.check_against_guideline to exercise the
pipeline wiring/downgrade logic deterministically — the same pattern used
for the earlier Tier 2/3 tests.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.m4_rag.completeness import CompletenessScorer
from app.m4_rag.guideline_grounded_checker import GuidelineCheckResult, GuidelineGroundedChecker
from app.m4_rag.knowledge.guideline_excerpts_loader import get_guideline_excerpts
from app.m4_rag.pipeline import CTDRagCheckerPipeline
from app.m4_rag.schema import GapStatus


@pytest.fixture(autouse=True)
def _stub_embedding_model():
    """Sections in this file exact-ID-match, so semantic matching (and its
    sentence-transformers network download) is never actually needed. Stub
    it out so these tests stay hermetic/offline."""
    fake_model = MagicMock()
    fake_model.encode.side_effect = lambda texts, **kwargs: np.zeros((len(texts), 8))
    with patch("app.m4_rag.retriever._get_embedding_model", return_value=fake_model):
        yield


GENERIC_CANDIDATE_TEXT = (
    "This report presents the clinical study results supporting the efficacy "
    "and safety of the product in the intended patient population. The study "
    "was designed in accordance with applicable regulatory guidance and was "
    "conducted at multiple qualified clinical sites by experienced "
    "investigators. Patients meeting the protocol-specified criteria were "
    "enrolled and treated according to the approved study design, with "
    "appropriate oversight from the sponsor and the independent monitoring "
    "committee throughout the conduct of the trial. Efficacy was assessed "
    "using validated and clinically meaningful measures, and the results "
    "demonstrate a favorable outcome consistent with the therapeutic goals "
    "of the program. Safety was carefully monitored throughout the study "
    "period, with adverse events collected, reviewed, and reported in "
    "accordance with standard pharmacovigilance practice. The overall "
    "benefit-risk profile observed in this study supports the continued "
    "development and potential approval of the product for the proposed "
    "indication."
) * 3  # ~450+ words, comfortably clears the 500-word Module 5 CRITICAL substance-gate floor when repeated

# Recompute to guarantee the floor is cleared regardless of exact wording above.
GENERIC_CANDIDATE_TEXT = GENERIC_CANDIDATE_TEXT + (" Additional boilerplate language. " * 60)

SUBSTANTIVE_CANDIDATE_TEXT = (
    "This report presents the pivotal Phase 3, randomized, double-blind, "
    "placebo-controlled trial of rofecoxib in 2,756 adult and geriatric "
    "patients aged 18 to 85 with osteoarthritis of the knee or hip, "
    "conducted at 94 centers across North America and Europe. The primary "
    "efficacy endpoint was the mean change from baseline in the WOMAC pain "
    "subscale at Week 12, which showed a statistically significant "
    "improvement of -3.8 points (95% CI: -4.5, -3.1; p<0.001) versus "
    "placebo. Patient disposition showed 2,412 patients completed the "
    "12-week treatment period, with discontinuation reasons tabulated by "
    "treatment arm. Demographic and baseline characteristics were balanced "
    "across arms, with a mean age of 63 years. Serious adverse events, "
    "including three cardiovascular thrombotic events, were adjudicated by "
    "an independent safety committee and are tabulated alongside "
    "gastrointestinal perforation, ulceration, and bleeding rates observed "
    "in 1.4% of rofecoxib-treated patients versus 2.9% of the ibuprofen "
    "comparator arm."
) * 5  # comfortably clears the 500-word Module 5 CRITICAL substance-gate floor


def _run_pipeline_for_5_3_5(section_body_text: str, mocked_verdict, requirements_absent=None):
    pipeline = CTDRagCheckerPipeline()
    assert "5.3.5" in pipeline.guideline_excerpts, "5.3.5 must have a real (non-placeholder) excerpt for this test"

    fake_result = None
    if mocked_verdict is not None:
        fake_result = GuidelineCheckResult(
            verdict=mocked_verdict,
            requirements_present=[],
            requirements_absent=requirements_absent or [],
            citation="ICH E3 §11.2, §12.3",
            reasoning=f"Mocked {mocked_verdict} verdict for wiring test.",
        )

    with patch.object(
        GuidelineGroundedChecker, "check_against_guideline", return_value=fake_result
    ) as mock_check:
        report = pipeline.run(
            {
                "submission_title": "Guideline Checker Wiring Test",
                "drug_name": "VIOXX",
                "sections": [
                    {
                        "section_id": "5.3.5",
                        "title": "Reports of Efficacy and Safety Studies",
                        "body_text": section_body_text,
                    },
                ],
            },
            enable_reasoner=False,
        )

    item = next(
        g
        for g in report.present_sections + report.partial_sections + report.missing_sections
        if g.section_id == "5.3.5"
    )
    return report, item, mock_check


# ─── GENERIC candidate: downgrades even though it clears the substance gate ─


def test_generic_candidate_downgrades_effective_status_to_partial():
    report, item, mock_check = _run_pipeline_for_5_3_5(
        GENERIC_CANDIDATE_TEXT,
        mocked_verdict="GENERIC",
        requirements_absent=[
            "Patient disposition reported: enrolled/completed/discontinued with reasons (E3 §10.1)",
            "Demographic and baseline characteristics tabulated by treatment group (E3 §11.2)",
        ],
    )

    assert mock_check.called
    # Passed the substance gate and Tier 1 matched it structurally — without
    # the guideline check, this would be PRESENT.
    assert item.substance_gate_reason is None
    assert item.status == GapStatus.PRESENT

    assert item.guideline_verdict == "GENERIC"
    assert item.guideline_check_evidence is not None
    assert item.guideline_check_evidence["citation"] == "ICH E3 §11.2, §12.3"
    assert len(item.guideline_check_evidence["requirements_absent"]) == 2

    scorer = CompletenessScorer()
    assert scorer._effective_status_score(item) == CompletenessScorer.WEIGHT_PARTIAL


def test_empty_verdict_downgrades_effective_status_to_missing():
    report, item, mock_check = _run_pipeline_for_5_3_5(GENERIC_CANDIDATE_TEXT, mocked_verdict="EMPTY")
    assert mock_check.called
    assert item.guideline_verdict == "EMPTY"

    scorer = CompletenessScorer()
    assert scorer._effective_status_score(item) == CompletenessScorer.WEIGHT_MISSING


def test_insufficient_verdict_downgrades_effective_status_to_missing():
    report, item, mock_check = _run_pipeline_for_5_3_5(GENERIC_CANDIDATE_TEXT, mocked_verdict="INSUFFICIENT")
    assert mock_check.called
    assert item.guideline_verdict == "INSUFFICIENT"

    scorer = CompletenessScorer()
    assert scorer._effective_status_score(item) == CompletenessScorer.WEIGHT_MISSING


# ─── Critical false-positive guard: genuinely substantive Vioxx-scenario content ─


def test_substantive_verdict_does_not_downgrade_real_content():
    report, item, mock_check = _run_pipeline_for_5_3_5(SUBSTANTIVE_CANDIDATE_TEXT, mocked_verdict="SUBSTANTIVE")
    assert mock_check.called
    assert item.guideline_verdict == "SUBSTANTIVE"
    assert item.status == GapStatus.PRESENT

    scorer = CompletenessScorer()
    assert scorer._effective_status_score(item) == CompletenessScorer.WEIGHT_PRESENT


def test_downgrade_ordering_end_to_end():
    """Same candidate text and excerpt; only the mocked verdict changes —
    overall readiness must strictly decrease as the verdict worsens."""
    report_substantive, _, _ = _run_pipeline_for_5_3_5(SUBSTANTIVE_CANDIDATE_TEXT, "SUBSTANTIVE")
    report_generic, _, _ = _run_pipeline_for_5_3_5(SUBSTANTIVE_CANDIDATE_TEXT, "GENERIC")
    report_insufficient, _, _ = _run_pipeline_for_5_3_5(SUBSTANTIVE_CANDIDATE_TEXT, "INSUFFICIENT")

    assert (
        report_substantive.overall_completeness
        > report_generic.overall_completeness
        > report_insufficient.overall_completeness
        == 0.0
    )


# ─── Graceful degradation: ANTHROPIC_API_KEY unset / no excerpt / gate-forced-MISSING ─


def test_pipeline_degrades_cleanly_without_anthropic_api_key():
    """With no ANTHROPIC_API_KEY, the whole system must degrade to Tier 1 +
    substance gate only — no errors, guideline_verdict stays None."""
    pipeline = CTDRagCheckerPipeline(guideline_checker=GuidelineGroundedChecker(api_key=""))
    assert not pipeline.guideline_checker.is_available

    report = pipeline.run(
        {
            "submission_title": "No Anthropic Key Test",
            "sections": [
                {
                    "section_id": "5.3.5",
                    "title": "Reports of Efficacy and Safety Studies",
                    "body_text": SUBSTANTIVE_CANDIDATE_TEXT,
                },
            ],
        },
        enable_reasoner=False,
    )
    item = next(g for g in report.present_sections + report.partial_sections if g.section_id == "5.3.5")
    assert item.guideline_verdict is None
    assert item.guideline_check_evidence is None
    assert item.status == GapStatus.PRESENT


def test_pipeline_degrades_cleanly_without_gemini_api_key_independently():
    """GEMINI_API_KEY is a wholly separate concern (only the reasoner's
    narrative insights use it) — it must not affect the guideline-grounded
    check or Tier 1/substance-gate scoring at all."""
    from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner

    pipeline = CTDRagCheckerPipeline(reasoner=GeminiGroundedReasoner(api_key=""))
    assert not pipeline.reasoner.is_available

    report = pipeline.run(
        {
            "submission_title": "No Gemini Key Test",
            "sections": [
                {"section_id": "1.1", "title": "Forms", "description": "FDA Form 356h and cover letter."},
            ],
        },
        enable_reasoner=True,
    )
    # Deterministic fallback still produces recommendations; nothing crashes.
    assert report.overall_completeness >= 0.0
    assert len(report.recommended_actions) > 0


def test_guideline_check_skips_sections_forced_missing_by_substance_gate():
    pipeline = CTDRagCheckerPipeline()
    fake_result = GuidelineCheckResult(
        verdict="SUBSTANTIVE", requirements_present=[], requirements_absent=[],
        citation="should never be reached", reasoning="",
    )
    with patch.object(
        GuidelineGroundedChecker, "check_against_guideline", return_value=fake_result
    ) as mock_check:
        report = pipeline.run(
            {
                "submission_title": "Thin Section Test",
                "sections": [
                    {"section_id": "5.3.5", "title": "CSR", "body_text": "Only a few words here."},
                ],
            },
            enable_reasoner=False,
        )
    mock_check.assert_not_called()
    item = next(g for g in report.missing_sections if g.section_id == "5.3.5")
    assert item.substance_gate_reason is not None
    assert item.guideline_verdict is None


def test_guideline_check_skips_sections_without_excerpt():
    """A section with no guideline_excerpts entry (e.g. 1.1) must never
    invoke the checker, even with a real key and passing the substance gate."""
    pipeline = CTDRagCheckerPipeline()
    assert "1.1" not in pipeline.guideline_excerpts

    with patch.object(GuidelineGroundedChecker, "check_against_guideline") as mock_check:
        report = pipeline.run(
            {
                "submission_title": "No Excerpt Test",
                "sections": [
                    {
                        "section_id": "1.1",
                        "title": "Forms and Administrative Information",
                        "body_text": "FDA Form 356h and administrative cover letter. " * 20,
                    },
                ],
            },
            enable_reasoner=False,
        )
    mock_check.assert_not_called()
    item = next(g for g in report.present_sections + report.partial_sections if g.section_id == "1.1")
    assert item.guideline_verdict is None


def test_guideline_check_skips_sections_without_body_text():
    """Structured/API dossiers that never set body_text must never trigger
    the guideline check, even when a real excerpt exists for that section_id."""
    pipeline = CTDRagCheckerPipeline()
    with patch.object(GuidelineGroundedChecker, "check_against_guideline") as mock_check:
        report = pipeline.run(
            {
                "submission_title": "No Body Text Test",
                "sections": [
                    {
                        "section_id": "5.3.5",
                        "title": "Reports of Efficacy and Safety Studies",
                        "description": "Pivotal Phase 3 osteoarthritis and acute pain clinical study reports.",
                    },
                ],
            },
            enable_reasoner=False,
        )
    mock_check.assert_not_called()
    item = next(g for g in report.present_sections + report.partial_sections if g.section_id == "5.3.5")
    assert item.guideline_verdict is None


# ─── Knowledge-base loader unit tests ──────────────────────────────────────


def test_guideline_excerpts_loaded_for_expected_sections():
    excerpts = get_guideline_excerpts()
    expected = {
        "5.3.5", "2.7", "5.3.3", "5.3.4", "5.3.6", "5.2", "1.3", "1.4",
        "4.2.1", "4.2.3", "3.2.S.3", "3.2.S.4", "3.2.S.7", "3.2.P.5", "3.2.P.8", "3.2.A.2",
    }
    assert expected.issubset(set(excerpts.keys()))
    for section_id in expected:
        assert excerpts[section_id]["excerpt_text"].strip()
        assert excerpts[section_id]["citation"].strip()


def test_guideline_checker_skips_without_excerpt_text():
    checker = GuidelineGroundedChecker(api_key="fake-key")
    result = checker.check_against_guideline(
        candidate_section={"section_id": "X", "title": "X", "body_text": "some text"},
        excerpt_record={"section_id": "X", "excerpt_text": "", "key_requirements": []},
    )
    assert result is None


def test_guideline_checker_skips_without_api_key():
    checker = GuidelineGroundedChecker(api_key="")
    assert not checker.is_available
    result = checker.check_against_guideline(
        candidate_section={"section_id": "5.3.5", "title": "CSR", "body_text": "some text"},
        excerpt_record=get_guideline_excerpts()["5.3.5"],
    )
    assert result is None
