"""Tests for ICH M4 Retriever."""

import pytest
from app.m4_rag.retriever import ICHRetriever
from app.m4_rag.schema import MatchMethod


def test_retriever_exact_match():
    retriever = ICHRetriever()
    req = retriever.exact_match("2.5")
    assert req is not None
    assert req.section_id == "2.5"
    assert "Clinical Overview" in req.title


def test_retriever_semantic_search():
    retriever = ICHRetriever()
    results = retriever.semantic_search("toxicology single dose and repeat dose animal safety", top_k=3)
    assert len(results) > 0
    top_req, score = results[0]
    assert score > 0.30
    assert top_req.section_id in ["4.2.3", "2.4", "2.6"]


def test_retriever_best_match_flow():
    retriever = ICHRetriever()

    # Exact match flow
    req, evidence = retriever.find_best_requirement_for_dossier_section(
        section_id="3.2.S.4",
        title="Control of Drug Substance",
        description="Release specifications and method validation",
    )
    assert req is not None
    assert evidence.match_method == MatchMethod.EXACT
    assert evidence.confidence_score == 1.0

    # Semantic match flow (no section ID, just title and description)
    req_sem, evidence_sem = retriever.find_best_requirement_for_dossier_section(
        section_id="",
        title="Drug Substance Specifications and Batch Analyses",
        description="Analytical procedures and release testing for the active ingredient",
    )
    assert req_sem is not None
    assert evidence_sem.match_method == MatchMethod.SEMANTIC
    assert evidence_sem.confidence_score >= 0.40

    # Low confidence / unknown query flow (no guessing)
    req_none, evidence_none = retriever.find_best_requirement_for_dossier_section(
        section_id="99.99",
        title="Random Unrelated Architecture Notes",
        description="Kubernetes cluster setup and database migrations",
        min_confidence=0.70,
    )
    assert req_none is None
    assert evidence_none.match_method == MatchMethod.NONE
    assert "Insufficient evidence" in evidence_none.evidence_reasoning
