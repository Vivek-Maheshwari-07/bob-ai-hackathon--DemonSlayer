"""Tests for M3 Digital Twin & PRR Trajectory Module (Real OpenFDA Pipeline)."""

import pytest
import os
import pandas as pd
from app.m3_digital_twin.trajectory import (
    generate_prr_trajectory,
    run_vioxx_backtest,
    run_drug_backtest,
    get_emerging_signals,
    DATA_DIR,
)


def test_vioxx_backtest_structure():
    bt = run_vioxx_backtest()
    assert bt["drug_name"] == "VIOXX"
    assert bt["event_term"] == "MYOCARDIAL INFARCTION"
    assert "trajectory" in bt
    assert len(bt["trajectory"]) > 0
    assert "first_signal_quarter" in bt
    assert "market_withdrawal_quarter" in bt
    assert "detection_lead_time_quarters" in bt
    assert "verdict" in bt
    assert "clinical_summary" in bt

    # Verified ground truth for VIOXX from real backtest summary
    assert bt["first_signal_quarter"] == "2004-01-31"
    assert bt["market_withdrawal_quarter"] == "2004-09-30"
    assert bt["detection_lead_time_quarters"] == 242
    assert bt["lead_time_days"] == 242
    assert bt["verdict"] == "EARLY_DETECTION"


def test_baycol_backtest_data_unavailable():
    """BAYCOL backtest must honestly report DATA_UNAVAILABLE_PRE_WITHDRAWAL without error

    because openFDA API records begin post-withdrawal (~2004 vs 2001-08-08 withdrawal).
    No fabricated detection date may be returned.
    """
    bt = run_drug_backtest("BAYCOL")
    assert bt["drug_name"] == "BAYCOL"
    assert bt["event_term"] == "RHABDOMYOLYSIS"
    assert bt["verdict"] == "DATA_UNAVAILABLE_PRE_WITHDRAWAL"
    assert bt["first_signal_quarter"] == "N/A"
    assert bt["detection_lead_time_quarters"] == "N/A"
    assert bt["market_withdrawal_quarter"] == "2001-08-08"
    assert len(bt["trajectory"]) > 0


def test_avandia_backtest_matches_summary_csv():
    """AVANDIA backtest values should match whatever backtest_summary.csv actually contains."""
    summary_path = os.path.join(DATA_DIR, "m3_digital_twin", "backtest_summary.csv")
    df = pd.read_csv(summary_path)
    avandia_row = df[df["drug"] == "AVANDIA"].iloc[0]

    bt = run_drug_backtest("AVANDIA")
    assert bt["drug_name"] == "AVANDIA"
    assert bt["event_term"] == str(avandia_row["target_term"])
    assert bt["first_signal_quarter"] == str(avandia_row["detection_date"])
    assert bt["market_withdrawal_quarter"] == str(avandia_row["real_world_action_date"])
    assert bt["verdict"] == str(avandia_row["verdict"])
    assert int(bt["lead_time_days"]) == int(avandia_row["lead_time_days"])


def test_generate_trajectory_vioxx():
    traj = generate_prr_trajectory("VIOXX", "MYOCARDIAL INFARCTION")
    assert len(traj) > 50
    # Monthly format YYYY-MM in quarter field
    assert traj[0]["quarter"] == "2003-05"
    signals = [t for t in traj if t["signal_status"] == "SIGNAL"]
    assert len(signals) > 0
    # Confirm January 2004 is flagged as signal
    jan_2004 = next((t for t in traj if t["quarter"] == "2004-01"), None)
    assert jan_2004 is not None
    assert jan_2004["signal_status"] == "SIGNAL"
    assert jan_2004["prr"] >= 2.0


def test_generate_trajectory_drug_alias_rofecoxib():
    traj = generate_prr_trajectory("ROFECOXIB")
    assert len(traj) > 0
    assert traj[0]["quarter"] == "2003-05"


def test_get_emerging_signals_insufficient_data():
    short_traj = [
        {"quarter": "2024-01", "prr": 2.5, "chi_square": 5.0, "n_cases": 10, "signal_status": "SIGNAL"},
    ]
    result = get_emerging_signals(short_traj)
    assert result == []


def test_get_emerging_signals_empty():
    result = get_emerging_signals([])
    assert result == []
