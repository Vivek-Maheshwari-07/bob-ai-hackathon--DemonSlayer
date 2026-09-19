"""Tests for Tier 2 content-adequacy verification (content_verifier.py + pipeline wiring)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.m4_rag.content_verifier import CheckpointResult, ContentVerifier, content_adequacy_score
from app.m4_rag.pipeline import CTDRagCheckerPipeline
from app.m4_rag.schema import GapStatus


@pytest.fixture(autouse=True)
def _stub_embedding_model():
    """All the sections used in this test file exact-ID-match, so semantic
    matching (and its sentence-transformers network download) is never
    actually needed. Stub it out so these tests stay hermetic/offline."""
    fake_model = MagicMock()
    fake_model.encode.side_effect = lambda texts, **kwargs: np.zeros((len(texts), 8))
    with patch("app.m4_rag.retriever._get_embedding_model", return_value=fake_model):
        yield

CHECKPOINTS_5_3_5 = [
    {"id": "population_defined", "question": "Is the patient population defined?", "required_by": "ICH E3 §9.3.1-9.3.2"},
    {"id": "study_design_stated", "question": "Is the study design stated?", "required_by": "ICH E3 §9.1"},
    {"id": "primary_endpoint_stated", "question": "Is a primary endpoint defined?", "required_by": "ICH E3 §9.5.3"},
]

THIN_5_3_5_TEXT = (
    "Reports of Efficacy and Safety Studies. Clinical study reports were conducted for the product."
)

ADEQUATE_5_3_5_TEXT = (
    "Reports of Efficacy and Safety Studies. This section presents two pivotal Phase 3, randomized, "
    "double-blind, placebo-controlled trials in adult patients aged 18-75 with osteoarthritis "
    "(inclusion: confirmed diagnosis per ACR criteria; exclusion: prior GI bleed). The primary "
    "efficacy endpoint was the change from baseline in WOMAC pain subscale at Week 12."
)


def _fake_answers(default="NO", overrides=None):
    """Builds a fake verify_section_content that answers deterministically per
    checkpoint id: `default` for every checkpoint, unless overridden."""
    overrides = overrides or {}

    def _verify(section_text, checkpoints):
        return [
            CheckpointResult(
                id=cp["id"],
                question=cp["question"],
                answer=overrides.get(cp["id"], default),
                quote="matched excerpt" if overrides.get(cp["id"], default) == "YES" else None,
            )
            for cp in checkpoints
        ]

    return _verify


def test_content_adequacy_score_none_when_no_results():
    assert content_adequacy_score([]) is None


def test_content_adequacy_score_computes_fraction():
    results = [
        CheckpointResult(id="a", question="q", answer="YES"),
        CheckpointResult(id="b", question="q", answer="NO"),
        CheckpointResult(id="c", question="q", answer="YES"),
        CheckpointResult(id="d", question="q", answer="UNCLEAR"),
    ]
    assert content_adequacy_score(results) == 0.5


def test_verifier_unavailable_returns_empty():
    verifier = ContentVerifier(api_key="")
    assert not verifier.is_available
    results = verifier.verify_section_content(ADEQUATE_5_3_5_TEXT, CHECKPOINTS_5_3_5)
    assert results == []


def test_verifier_no_checkpoints_returns_empty():
    verifier = ContentVerifier(api_key="fake-key")
    assert verifier.verify_section_content(ADEQUATE_5_3_5_TEXT, []) == []


def test_pipeline_thin_5_3_5_section_scores_low_and_downgrades_completeness():
    """A 5.3.5 section with no age range, no phase, no primary endpoint should
    score low on Tier 2 and get downgraded toward MISSING in the weighted
    completeness formula, even if Tier 1 called it PRESENT/PARTIAL."""
    pipeline = CTDRagCheckerPipeline()

    with patch.object(
        ContentVerifier,
        "verify_section_content",
        side_effect=_fake_answers(default="NO"),
    ):
        report = pipeline.run(
            {
                "submission_title": "Thin Vioxx Test Dossier",
                "drug_name": "VIOXX",
                "sections": [
                    {
                        "section_id": "5.3.5",
                        "title": "Reports of Efficacy and Safety Studies",
                        "description": THIN_5_3_5_TEXT,
                    },
                ],
            },
            enable_reasoner=False,
        )

    item = next(g for g in report.priority_gaps + report.present_sections + report.partial_sections + report.missing_sections if g.section_id == "5.3.5")
    assert item.content_adequacy_score is not None
    assert item.content_adequacy_score < 0.4
    # Downgraded to effective MISSING -> module 5 should reflect a 0.0 contribution for this section.
    assert report.modules["module_5"].completeness_percentage < 50.0


def test_pipeline_adequate_5_3_5_section_scores_high():
    """A 5.3.5 section that explicitly states population, design, and primary
    endpoint should score high on Tier 2 content adequacy."""
    pipeline = CTDRagCheckerPipeline()

    with patch.object(
        ContentVerifier,
        "verify_section_content",
        side_effect=_fake_answers(default="YES"),
    ):
        report = pipeline.run(
            {
                "submission_title": "Adequate Vioxx Test Dossier",
                "drug_name": "VIOXX",
                "sections": [
                    {
                        "section_id": "5.3.5",
                        "title": "Reports of Efficacy and Safety Studies",
                        "description": ADEQUATE_5_3_5_TEXT,
                    },
                ],
            },
            enable_reasoner=False,
        )

    item = next(g for g in report.priority_gaps + report.present_sections + report.partial_sections + report.missing_sections if g.section_id == "5.3.5")
    assert item.content_adequacy_score is not None
    assert item.content_adequacy_score >= 0.8


def test_pipeline_skips_tier2_when_gemini_unavailable_no_regression():
    """With no GEMINI_API_KEY, Tier 2 must no-op cleanly: content_adequacy_score
    stays None and the Tier 1 report still generates without error."""
    pipeline = CTDRagCheckerPipeline(content_verifier=ContentVerifier(api_key=""))

    report = pipeline.run(
        {
            "submission_title": "No-Key Test Dossier",
            "drug_name": "VIOXX",
            "sections": [
                {
                    "section_id": "5.3.5",
                    "title": "Reports of Efficacy and Safety Studies",
                    "description": ADEQUATE_5_3_5_TEXT,
                },
            ],
        },
        enable_reasoner=False,
    )

    item = next(g for g in report.priority_gaps + report.present_sections + report.partial_sections + report.missing_sections if g.section_id == "5.3.5")
    assert item.content_adequacy_score is None
    assert item.checkpoint_results is None


def test_pipeline_skips_tier2_for_sections_without_checkpoints():
    """A section with no content_checkpoints in the KB (e.g. 1.1) should never
    invoke Tier 2, regardless of Gemini availability."""
    pipeline = CTDRagCheckerPipeline()

    with patch.object(ContentVerifier, "verify_section_content") as mock_verify:
        report = pipeline.run(
            {
                "submission_title": "Admin Section Test Dossier",
                "sections": [
                    {
                        "section_id": "1.1",
                        "title": "Forms and Administrative Information",
                        "description": "FDA Form 356h submitted.",
                    },
                ],
            },
            enable_reasoner=False,
        )
    mock_verify.assert_not_called()

    item = next(g for g in report.present_sections + report.partial_sections if g.section_id == "1.1")
    assert item.content_adequacy_score is None
