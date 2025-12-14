"""
Machine learning models for financial regime detection.

This module provides classifiers for detecting market regimes (crisis vs normal)
using topological features extracted from financial time series.
"""

from financial_tda.models.change_point_detector import (
    ChangePointDetector,
    NormalPeriodCalibrator,
    validate_on_crisis_dates,
)
from financial_tda.models.regime_classifier import (
    RegimeClassifier,
    create_regime_labels,
    evaluate_classifier,
    load_model,
    prepare_features,
    save_model,
)

__all__ = [
    "RegimeClassifier",
    "create_regime_labels",
    "prepare_features",
    "evaluate_classifier",
    "save_model",
    "load_model",
    "ChangePointDetector",
    "NormalPeriodCalibrator",
    "validate_on_crisis_dates",
]
