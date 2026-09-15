"""Tests for Module M1 Adverse Event Clustering Engine (scikit-learn)."""

import pytest
from app.m1_faers.clustering import compute_adverse_event_clusters


def test_compute_adverse_event_clusters_default():
    result = compute_adverse_event_clusters(n_clusters=4, force_refresh=True)
    assert "clusters" in result
    assert "points" in result
    assert "metadata" in result

    clusters = result["clusters"]
    points = result["points"]
    metadata = result["metadata"]

    assert len(clusters) == 4
    assert len(points) > 0
    assert metadata["algorithm"] == "K-Means Clustering (scikit-learn)"
    assert len(metadata["variance_explained_ratio"]) == 2

    # Verify cluster properties
    for c in clusters:
        assert "cluster_id" in c
        assert "cluster_name" in c
        assert "clinical_theme" in c
        assert "severity_level" in c
        assert "avg_death_rate" in c
        assert "avg_hospitalization_rate" in c
        assert "avg_prr" in c
        assert "top_events" in c
        assert len(c["top_events"]) > 0
        assert c["event_count"] > 0

    # Verify points properties
    for p in points[:10]:
        assert "drug_name" in p
        assert "event_term" in p
        assert "cluster_id" in p
        assert "pca_x" in p
        assert "pca_y" in p
        assert "prr" in p
        assert "cases" in p
        assert "death_rate" in p
        assert "hospitalization_rate" in p
        assert "signal_status" in p


def test_compute_adverse_event_clusters_drug_filter():
    result = compute_adverse_event_clusters(n_clusters=3, drug_filter="VIOXX", force_refresh=True)
    assert len(result["clusters"]) == 3
    assert len(result["points"]) > 0
    # Every point should be VIOXX
    for p in result["points"]:
        assert p["drug_name"] == "VIOXX"


def test_compute_adverse_event_clusters_k_bounds():
    # Test k=2 and k=5
    res2 = compute_adverse_event_clusters(n_clusters=2, force_refresh=True)
    assert len(res2["clusters"]) == 2

    res5 = compute_adverse_event_clusters(n_clusters=5, force_refresh=True)
    assert len(res5["clusters"]) == 5
