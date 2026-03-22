"""Shared deep learning utilities for TDA research.

Domain-agnostic building blocks used across financial_tda, poverty_tda,
and trajectory_tda. Domain-specific model architectures live in each
domain's models/ package.

Modules:
    base_trainer: BaseTrainer with common optimizer/scheduler/early-stopping logic.
    losses: Reusable loss functions (VAELoss, PersistenceLoss).
    persistence_layers: Differentiable layers for learning on persistence diagrams.
    simplicial: Utilities for simplicial complex neural networks (TopoModelX hooks).
    graph_utils: Shared graph construction helpers for torch-geometric.
"""

from __future__ import annotations

from shared.deep_learning.base_trainer import BaseTrainer, EarlyStopping
from shared.deep_learning.losses import PersistenceLoss, TopologicalFairnessLoss, VAELoss
from shared.deep_learning.persistence_layers import (
    GaussianPersLayer,
    LifetimeWeightedSum,
    PersFormerLayer,
    PersLayWeight,
    RationalHatPersLayer,
)

__all__ = [
    "BaseTrainer",
    "EarlyStopping",
    "GaussianPersLayer",
    "LifetimeWeightedSum",
    "PersFormerLayer",
    "PersLayWeight",
    "PersistenceLoss",
    "RationalHatPersLayer",
    "TopologicalFairnessLoss",
    "VAELoss",
]
