"""Tests for Gemini 2.5 Flash Grounded Reasoner."""

import pytest
from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner
from app.m4_rag.schema import (
    CriticalityLevel,
    GapItem,
    GapStatus,
    MatchEvidence,
    MatchMethod,
)


def test_gemini_reasoner_offline_fallback():
    # When no API key is provided, the reasoner should execute deterministic fallback without failing
    reasoner = GeminiGroundedReasoner(api_key="")
    assert not reasoner.is_available

    priority_gaps = [
        GapItem(
            section_id="2.5",
            module_id=2,
            module_name="Module 2: CTD Summaries",
            title="Clinical Overview",
            status=GapStatus.PARTIAL,
            criticality=CriticalityLevel.CRITICAL,
            match_evidence=MatchEvidence(
                match_method=MatchMethod.EXACT,
                confidence_score=1.0,
                evidence_reasoning="Section marked as draft",
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
            action_item="Attach 3.2.S.4",
        ),
    ]

    insights = reasoner.generate_reasoning_insights(
        priority_gaps=priority_gaps,
        overall_completeness=45.0,
        submission_title="Test NDA",
    )
    assert len(insights) > 0
    assert any("critical" in i.lower() or "draft" in i.lower() or "barrier" in i.lower() for i in insights)


def test_gemini_reasoner_empty_gaps():
    reasoner = GeminiGroundedReasoner(api_key="")
    insights = reasoner.generate_reasoning_insights(
        priority_gaps=[],
        overall_completeness=100.0,
    )
    assert len(insights) == 1
    assert "100.0%" in insights[0]
