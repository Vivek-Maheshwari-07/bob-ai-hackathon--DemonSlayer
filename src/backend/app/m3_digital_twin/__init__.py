"""Module M3: Digital Twin & PRR Trajectory / Vioxx Backtest."""

from app.m3_digital_twin.trajectory import (
    generate_prr_trajectory,
    run_vioxx_backtest,
    get_emerging_signals,
)

__all__ = [
    "generate_prr_trajectory",
    "run_vioxx_backtest",
    "get_emerging_signals",
]
