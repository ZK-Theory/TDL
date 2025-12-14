"""
Analysis workflows and results for financial market regime detection.
"""

from financial_tda.analysis.backtest import (
    KNOWN_CRISES,
    BacktestEngine,
    BacktestResults,
    CrisisPeriod,
    Detection,
    VolatilityBaseline,
    compute_lead_time,
    generate_backtest_report,
    is_valid_detection,
    prepare_backtest_data,
)
from financial_tda.analysis.windowed import (
    compute_window_distances,
    detect_topology_changes,
    extract_windowed_features,
    sliding_window_generator,
)

__all__ = [
    "sliding_window_generator",
    "extract_windowed_features",
    "compute_window_distances",
    "detect_topology_changes",
    "CrisisPeriod",
    "KNOWN_CRISES",
    "prepare_backtest_data",
    "Detection",
    "BacktestResults",
    "BacktestEngine",
    "VolatilityBaseline",
    "compute_lead_time",
    "is_valid_detection",
    "generate_backtest_report",
]
