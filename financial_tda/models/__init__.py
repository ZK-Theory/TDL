"""
Machine learning models for financial regime detection.

This module provides classifiers for detecting market regimes (crisis vs normal)
using topological features extracted from financial time series.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Eager imports - no external dependencies beyond sklearn/pandas/numpy
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

# Lazy imports for PyTorch-dependent modules
# These will only load when explicitly accessed via getattr or direct import
if TYPE_CHECKING:
    from financial_tda.models.persistence_layers import (
        DeepSetPhi,
        Perslay,
        PowerWeight,
        create_perslay,
        pad_diagrams,
    )
    from financial_tda.models.rips_gnn import (
        RipsGNN,
        RipsGNNTrainer,
        RipsGraphDataset,
        build_rips_graph,
        compare_rips_vs_perslay,
        create_rips_dataset_from_embeddings,
        create_rips_gnn,
        train_val_test_split_temporal,
    )
    from financial_tda.models.tda_neural import (
        EarlyStopping,
        PersistenceDataset,
        PositionalEncoding,
        RegimeDetectionModel,
        TransformerRegimeDetector,
        collate_persistence_batch,
        compute_metrics,
        create_regime_detector,
        evaluate,
        train_epoch,
        train_model,
        train_test_split_temporal,
    )

__all__ = [
    # Always available (sklearn-based)
    "RegimeClassifier",
    "create_regime_labels",
    "prepare_features",
    "evaluate_classifier",
    "save_model",
    "load_model",
    "ChangePointDetector",
    "NormalPeriodCalibrator",
    "validate_on_crisis_dates",
    # Lazy-loaded (PyTorch-based) - will load on first access
    "Perslay",
    "DeepSetPhi",
    "PowerWeight",
    "create_perslay",
    "pad_diagrams",
    "RegimeDetectionModel",
    "TransformerRegimeDetector",
    "PositionalEncoding",
    "create_regime_detector",
    "PersistenceDataset",
    "collate_persistence_batch",
    "train_test_split_temporal",
    "train_epoch",
    "evaluate",
    "EarlyStopping",
    "train_model",
    "compute_metrics",
    "RipsGNN",
    "RipsGNNTrainer",
    "RipsGraphDataset",
    "build_rips_graph",
    "create_rips_gnn",
    "create_rips_dataset_from_embeddings",
    "train_val_test_split_temporal",
    "compare_rips_vs_perslay",
]


def __getattr__(name: str):
    """Lazy import PyTorch-dependent modules only when accessed."""
    # persistence_layers exports
    if name in (
        "Perslay",
        "DeepSetPhi",
        "PowerWeight",
        "create_perslay",
        "pad_diagrams",
    ):
        from financial_tda.models.persistence_layers import (
            DeepSetPhi,
            Perslay,
            PowerWeight,
            create_perslay,
            pad_diagrams,
        )

        return locals()[name]

    # rips_gnn exports
    if name in (
        "RipsGNN",
        "RipsGNNTrainer",
        "RipsGraphDataset",
        "build_rips_graph",
        "create_rips_gnn",
        "create_rips_dataset_from_embeddings",
        "train_val_test_split_temporal",
        "compare_rips_vs_perslay",
    ):
        from financial_tda.models.rips_gnn import (
            RipsGNN,
            RipsGNNTrainer,
            RipsGraphDataset,
            build_rips_graph,
            compare_rips_vs_perslay,
            create_rips_dataset_from_embeddings,
            create_rips_gnn,
            train_val_test_split_temporal,
        )

        return locals()[name]

    # tda_neural exports
    if name in (
        "EarlyStopping",
        "PersistenceDataset",
        "PositionalEncoding",
        "RegimeDetectionModel",
        "TransformerRegimeDetector",
        "collate_persistence_batch",
        "compute_metrics",
        "create_regime_detector",
        "evaluate",
        "train_epoch",
        "train_model",
        "train_test_split_temporal",
    ):
        from financial_tda.models.tda_neural import (
            EarlyStopping,
            PersistenceDataset,
            PositionalEncoding,
            RegimeDetectionModel,
            TransformerRegimeDetector,
            collate_persistence_batch,
            compute_metrics,
            create_regime_detector,
            evaluate,
            train_epoch,
            train_model,
            train_test_split_temporal,
        )

        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
