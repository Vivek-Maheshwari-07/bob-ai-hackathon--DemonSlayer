"""Tests for M2 PRR Signal Engine (Real OpenFDA Pipeline)."""

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
    # VIOXX MI should be a confirmed signal
    vioxx_mi = [s for s in signals if s["drug_name"] == "VIOXX" and "MYOCARDIAL" in s["event_term"]]
    assert len(vioxx_mi) > 0, "Vioxx MI should be a confirmed signal in real openFDA data"


def test_empty_contingency_table():
    import pandas as pd
    empty_ct = pd.DataFrame(columns=["drug_name", "event_term", "n_drug_event", "n_drug_total", "n_event_total", "n_total"])
    results = run_prr_analysis(empty_ct)
    assert results == []


def test_end_to_end_vioxx_mi_hand_verified_prr_chi2():
    """Critical regression test: VIOXX + MYOCARDIAL INFARCTION end-to-end PRR & Chi-Square.

    Must match hand-verified ground truth from real raw 2x2 contingency cells:
        a = 17,938 (VIOXX + MI)
        b = 26,341 (VIOXX + other reactions) -> n_drug_total = 44,279
        c = 155,582 (other drugs + MI)       -> n_event_total = 173,520
        d = 20,492,829 (other drugs + other) -> n_total = 20,692,690
        PRR = (a / (a + b)) / (c / (c + d)) = 53.7655 -> 53.77
        Chi-Square = 839,918.65
    """
    m1 = run_m1_pipeline()
    ct = m1["contingency_table"]
    matches = ct[(ct["drug_name"] == "VIOXX") & (ct["event_term"] == "MYOCARDIAL INFARCTION")]
    assert not matches.empty, "VIOXX + MYOCARDIAL INFARCTION must be present in real contingency table"

    row = matches.iloc[0]
    n_de = float(row["n_drug_event"])
    n_dt = float(row["n_drug_total"])
    n_et = float(row["n_event_total"])
    n_t = float(row["n_total"])

    stats_res = calculate_prr(n_de, n_dt, n_et, n_t)

    assert abs(stats_res["prr"] - 53.77) < 0.01, f"Expected PRR ~ 53.77, got {stats_res['prr']}"
    assert abs(stats_res["chi_square"] - 839918.65) < 0.05, f"Expected Chi2 ~ 839918.65, got {stats_res['chi_square']}"
    assert stats_res["p_value"] < 0.0001
    assert classify_signal(stats_res["prr"], stats_res["chi_square"], int(n_de)) == "SIGNAL"


def test_end_to_end_baycol_rhabdomyolysis_verified():
    """Verification for BAYCOL + RHABDOMYOLYSIS real values:

    PRR = 20.15, chi-square = 145.89, a = 8.
    """
    m1 = run_m1_pipeline()
    ct = m1["contingency_table"]
    matches = ct[(ct["drug_name"] == "BAYCOL") & (ct["event_term"] == "RHABDOMYOLYSIS")]
    assert not matches.empty, "BAYCOL + RHABDOMYOLYSIS must be present in real contingency table"

    row = matches.iloc[0]
    n_de = float(row["n_drug_event"])
    n_dt = float(row["n_drug_total"])
    n_et = float(row["n_event_total"])
    n_t = float(row["n_total"])

    assert n_de == 8
    stats_res = calculate_prr(n_de, n_dt, n_et, n_t)
    assert abs(stats_res["prr"] - 20.15) < 0.01
    assert abs(stats_res["chi_square"] - 145.89) < 0.05
    assert classify_signal(stats_res["prr"], stats_res["chi_square"], int(n_de)) == "SIGNAL"
