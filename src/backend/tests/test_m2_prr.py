"""Tests for M2 PRR Signal Engine."""

import pytest
from app.m2_prr.prr_engine import (
    calculate_prr,
    classify_signal,
    run_prr_analysis,
    get_signals_only,
)
from app.m1_faers.faers_ingest import run_m1_pipeline


def test_prr_calculation_basic():
    result = calculate_prr(n_drug_event=100, n_drug_total=500, n_event_total=200, n_total=10000)
    assert result["prr"] > 0
    assert result["chi_square"] > 0
    assert 0.0 <= result["p_value"] <= 1.0
    assert result["lower_ci"] <= result["upper_ci"]


def test_prr_edge_case_zero_events():
    result = calculate_prr(n_drug_event=0, n_drug_total=500, n_event_total=200, n_total=10000)
    assert result["prr"] == 0.0
    assert result["chi_square"] == 0.0


def test_prr_edge_case_zero_denominator():
    result = calculate_prr(n_drug_event=10, n_drug_total=0, n_event_total=200, n_total=10000)
    assert result["prr"] == 0.0


def test_prr_edge_case_small_total():
    result = calculate_prr(n_drug_event=1, n_drug_total=1, n_event_total=1, n_total=1)
    assert result["prr"] == 0.0


def test_classify_signal_signal():
    assert classify_signal(prr=3.0, chi_square=5.0, n_drug_event=10) == "SIGNAL"


def test_classify_signal_noise_few_cases():
    assert classify_signal(prr=5.0, chi_square=10.0, n_drug_event=2) == "NOISE"


def test_classify_signal_noise_low_prr():
    assert classify_signal(prr=1.0, chi_square=1.0, n_drug_event=100) == "NOISE"


def test_classify_signal_weak():
    assert classify_signal(prr=1.6, chi_square=3.5, n_drug_event=10) == "WEAK_SIGNAL"


def test_run_prr_analysis_from_m1():
    m1 = run_m1_pipeline()
    ct = m1["contingency_table"]
    results = run_prr_analysis(ct)
    assert len(results) > 0
    # Results sorted by PRR descending
    prrs = [r["prr"] for r in results]
    assert prrs == sorted(prrs, reverse=True) or len(results) < 2
    # Each result has required fields
    for r in results[:5]:
        assert "drug_name" in r
        assert "event_term" in r
        assert "prr" in r
        assert "chi_square" in r
        assert "signal_status" in r
        assert r["signal_status"] in ("SIGNAL", "WEAK_SIGNAL", "NOISE")


def test_get_signals_only():
    m1 = run_m1_pipeline()
    ct = m1["contingency_table"]
    results = run_prr_analysis(ct)
    signals = get_signals_only(results)
    assert all(s["signal_status"] == "SIGNAL" for s in signals)
    # Rofecoxib MI should be a signal
    rof_mi = [s for s in signals if s["drug_name"] == "ROFECOXIB" and "MYOCARDIAL" in s["event_term"]]
    assert len(rof_mi) > 0, "Rofecoxib MI should be a confirmed signal"


def test_empty_contingency_table():
    import pandas as pd
    empty_ct = pd.DataFrame(columns=["drug_name", "event_term", "n_drug_event", "n_drug_total", "n_event_total", "n_total"])
    results = run_prr_analysis(empty_ct)
    assert results == []
