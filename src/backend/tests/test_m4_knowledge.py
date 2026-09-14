"""Tests for ICH M4 Knowledge Base loader and data integrity."""

import pytest
from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.schema import CriticalityLevel


def test_knowledge_base_singleton_loads():
    kb = get_knowledge_base()
    assert kb.total_count >= 30, f"Expected at least 30 verified ICH sections, found {kb.total_count}"


def test_all_five_modules_represented():
    kb = get_knowledge_base()
    for m in range(1, 6):
        mod_reqs = kb.get_by_module(m)
        assert len(mod_reqs) > 0, f"Module {m} must contain verified requirements"


def test_key_ich_sections_present():
    kb = get_knowledge_base()

    # Module 1
    assert kb.get_by_id("1.1") is not None
    assert kb.get_by_id("1.4") is not None

    # Module 2
    qos = kb.get_by_id("2.3")
    assert qos is not None
    assert "Quality Overall Summary" in qos.title
    assert qos.criticality == CriticalityLevel.CRITICAL

    clin_ov = kb.get_by_id("2.5")
    assert clin_ov is not None
    assert "Clinical Overview" in clin_ov.title

    # Module 3
    s4 = kb.get_by_id("3.2.S.4")
    assert s4 is not None
    assert "Control of Drug Substance" in s4.title

    p8 = kb.get_by_id("3.2.P.8")
    assert p8 is not None
    assert "Stability" in p8.title

    # Module 4
    tox = kb.get_by_id("4.2.3")
    assert tox is not None
    assert "Toxicology" in tox.title

    # Module 5
    csr = kb.get_by_id("5.3.5")
    assert csr is not None
    assert "Efficacy and Safety" in csr.title


def test_case_insensitive_lookup():
    kb = get_knowledge_base()
    assert kb.get_by_id("3.2.s.1") is not None
    assert kb.get_by_id("3.2.S.1") is not None
    assert kb.get_by_id("  2.5  ") is not None


def test_unknown_section_lookup():
    kb = get_knowledge_base()
    assert kb.get_by_id("9.9.9") is None
    assert kb.get_by_id("UNKNOWN") is None
