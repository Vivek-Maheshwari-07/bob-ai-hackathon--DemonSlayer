"""Tests for Completeness Scorer in Module M4."""

import pytest
from app.m4_rag.completeness import CompletenessScorer
from app.m4_rag.schema import (
    CriticalityLevel,
    GapItem,
    GapStatus,
    MatchEvidence,
    MatchMethod,
)


def _make_dummy_gap(sec_id: str, mod_id: int, status: GapStatus, crit: CriticalityLevel = CriticalityLevel.MAJOR) -> GapItem:
    return GapItem(
        section_id=sec_id,
        module_id=mod_id,
        module_name=f"Module {mod_id}",
        title=f"Title {sec_id}",
        status=status,
        criticality=crit,
        match_evidence=MatchEvidence(
            match_method=MatchMethod.EXACT,
            confidence_score=1.0 if status == GapStatus.PRESENT else 0.5,
            evidence_reasoning="Test reason",
        ),
    )


def test_completeness_all_present():
    scorer = CompletenessScorer()
    items = [
        _make_dummy_gap("1.1", 1, GapStatus.PRESENT),
        _make_dummy_gap("2.5", 2, GapStatus.PRESENT),
        _make_dummy_gap("3.2.S.1", 3, GapStatus.PRESENT),
        _make_dummy_gap("4.2.1", 4, GapStatus.PRESENT),
        _make_dummy_gap("5.3.5", 5, GapStatus.PRESENT),
    ]
    overall, modules = scorer.calculate(items)
    assert overall == 100.0
    for mod_key in ["module_1", "module_2", "module_3", "module_4", "module_5"]:
        assert modules[mod_key].completeness_percentage == 100.0


def test_completeness_mixed_weights():
    scorer = CompletenessScorer()
    # Module 2 has 1 PRESENT (1.0) and 1 PARTIAL (0.5) -> (1.5 / 2.0) = 75.0%
    items = [
        _make_dummy_gap("2.4", 2, GapStatus.PRESENT),
        _make_dummy_gap("2.5", 2, GapStatus.PARTIAL),
    ]
    overall, modules = scorer.calculate(items)
    assert modules["module_2"].completeness_percentage == 75.0
    assert modules["module_2"].present_count == 1
    assert modules["module_2"].partial_count == 1
    assert modules["module_2"].missing_count == 0


def test_completeness_missing_zero():
    scorer = CompletenessScorer()
    items = [
        _make_dummy_gap("5.3.5", 5, GapStatus.MISSING, CriticalityLevel.CRITICAL),
    ]
    overall, modules = scorer.calculate(items)
    assert modules["module_5"].completeness_percentage == 0.0
    assert modules["module_5"].critical_missing_count == 1
