"""Tests for M3 Digital Twin & PRR Trajectory Module."""

import pytest
from app.m3_digital_twin.trajectory import (
    generate_prr_trajectory,
    run_vioxx_backtest,
    get_emerging_signals,
    VIOXX_MI_TRAJECTORY,
)


def test_vioxx_backtest_structure():
    bt = run_vioxx_backtest()
    assert "drug_name" in bt
    assert "event_term" in bt
    assert "trajectory" in bt
    assert "first_signal_quarter" in bt
    assert "market_withdrawal_quarter" in bt
    assert "detection_lead_time_quarters" in bt
    assert bt["first_signal_quarter"] == "2000-Q3"
    assert bt["detection_lead_time_quarters"] == 16


def test_vioxx_trajectory_has_signal():
    traj = VIOXX_MI_TRAJECTORY
    signals = [t for t in traj if t["signal_status"] == "SIGNAL"]
    assert len(signals) > 10


def test_generate_trajectory_vioxx():
    traj = generate_prr_trajectory("ROFECOXIB", "MYOCARDIAL INFARCTION")
    assert len(traj) > 0
    assert traj[0]["quarter"] == "1999-Q3"


def test_generate_trajectory_synthetic():
    traj = generate_prr_trajectory("TESTDRUG", "TESTEVENT")
    assert len(traj) > 0
    for point in traj:
        assert "quarter" in point
        assert "prr" in point
        assert "chi_square" in point
        assert "n_cases" in point
        assert "signal_status" in point
        assert point["signal_status"] in ("SIGNAL", "WEAK_SIGNAL", "NOISE")


def test_get_emerging_signals_insufficient_data():
    short_traj = [
        {"quarter": "2024-Q1", "prr": 2.5, "chi_square": 5.0, "n_cases": 10, "signal_status": "SIGNAL"},
    ]
    result = get_emerging_signals(short_traj)
    assert result == []


def test_get_emerging_signals_empty():
    result = get_emerging_signals([])
    assert result == []
