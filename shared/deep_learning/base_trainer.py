"""Base trainer class for all TDA deep learning models.

All four domain trainers (RipsGNNTrainer, AutoencoderTrainer,
OpportunityVAETrainer, SpatialGNNTrainer) follow the same pattern:
Adam optimizer, ReduceLROnPlateau scheduler, history dict, early stopping.
This base class provides that shared scaffold. Domain trainers subclass it
and implement train_epoch() and validate().

Usage::

    class MyDomainTrainer(BaseTrainer):
        def train_epoch(self) -> dict[str, float]:
            ...
        def validate(self) -> dict[str, float]:
            ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import torch
import torch.nn as nn

if TYPE_CHECKING:
    from torch.optim import Optimizer
    from torch.optim.lr_scheduler import ReduceLROnPlateau

logger = logging.getLogger(__name__)


class EarlyStopping:
    """Monitor a metric and signal when training should stop.

    Args:
        patience: Number of epochs without improvement before stopping.
        min_delta: Minimum change in monitored metric to qualify as improvement.
        mode: 'min' if lower is better (loss), 'max' if higher is better (accuracy).
    """

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 1e-4,
        mode: str = "min",
    ) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.best_value: float = float("inf") if mode == "min" else float("-inf")
        self.counter: int = 0
        self.should_stop: bool = False

    def __call__(self, value: float) -> None:
        """Update state given latest monitored metric value.

        Args:
            value: Current epoch metric value.
        """
        improved = (
            value < self.best_value - self.min_delta if self.mode == "min" else value > self.best_value + self.min_delta
        )
        if improved:
            self.best_value = value
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True

    def reset(self) -> None:
        """Reset state for a new training run."""
        self.best_value = float("inf") if self.mode == "min" else float("-inf")
        self.counter = 0
        self.should_stop = False


class BaseTrainer(ABC):
    """Abstract base trainer for TDA deep learning models.

    Provides shared infrastructure:
    - Adam optimizer with configurable learning rate and weight decay
    - ReduceLROnPlateau learning rate scheduler
    - History dict tracking train/val metrics per epoch
    - Early stopping with configurable patience
    - Device-agnostic model placement

    Subclasses must implement:
    - train_epoch() -> dict[str, float]
    - validate() -> dict[str, float]

    Args:
        model: PyTorch model to train.
        learning_rate: Initial learning rate for Adam.
        weight_decay: L2 regularisation coefficient.
        device: Device string ('cuda', 'cpu') or None for auto-detect.
        scheduler_patience: Epochs without improvement before LR reduction.
        scheduler_factor: Factor by which LR is reduced.
        early_stopping_patience: Epochs without improvement before stopping.
            Set to 0 to disable early stopping.
    """

    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        device: str | None = None,
        scheduler_patience: int = 5,
        scheduler_factor: float = 0.5,
        early_stopping_patience: int = 10,
    ) -> None:
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = model.to(self.device)
        self.optimizer: Optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        self.scheduler: ReduceLROnPlateau = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            patience=scheduler_patience,
            factor=scheduler_factor,
        )
        self.early_stopping: EarlyStopping | None = (
            EarlyStopping(patience=early_stopping_patience) if early_stopping_patience > 0 else None
        )
        self.history: dict[str, list[float]] = {}

    def _init_history(self, keys: list[str]) -> None:
        """Initialise history dict with empty lists for given metric keys.

        Call this in subclass __init__ with the metrics your trainer tracks.

        Args:
            keys: Metric names, e.g. ['train_loss', 'val_loss', 'val_acc'].
        """
        self.history = {k: [] for k in keys}

    def _record(self, metrics: dict[str, float]) -> None:
        """Append epoch metrics to history.

        Args:
            metrics: Dict of metric_name → value for this epoch.
        """
        for key, value in metrics.items():
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(value)

    @abstractmethod
    def train_epoch(self) -> dict[str, float]:
        """Run one training epoch.

        Returns:
            Dict of training metrics for this epoch, e.g. {'train_loss': 0.42}.
        """

    @abstractmethod
    def validate(self) -> dict[str, float]:
        """Evaluate on validation data.

        Returns:
            Dict of validation metrics for this epoch, e.g. {'val_loss': 0.51}.
        """

    def train(
        self,
        epochs: int = 100,
        val_metric: str = "val_loss",
        verbose: bool = True,
        log_every: int = 10,
    ) -> dict[str, list[float]]:
        """Run the full training loop.

        Args:
            epochs: Maximum number of training epochs.
            val_metric: Key from validate() output to use for LR scheduling
                and early stopping. Must be in the validate() return dict.
            verbose: Whether to log progress.
            log_every: Log frequency in epochs.

        Returns:
            History dict mapping metric names to per-epoch value lists.
        """
        logger.info("Training on %s for up to %d epochs", self.device, epochs)

        for epoch in range(1, epochs + 1):
            train_metrics = self.train_epoch()
            val_metrics = self.validate()

            all_metrics = {**train_metrics, **val_metrics}
            self._record(all_metrics)

            if val_metric not in val_metrics:
                raise KeyError(
                    f"Validation metric '{val_metric}' not found in validate() output for "
                    f"{self.__class__.__name__}. Available metrics: {list(val_metrics.keys())}"
                )
            val_value = val_metrics[val_metric]
            self.scheduler.step(val_value)

            if self.early_stopping is not None:
                self.early_stopping(val_value)
                if self.early_stopping.should_stop:
                    logger.info("Early stopping at epoch %d", epoch)
                    break

            if verbose and epoch % log_every == 0:
                metric_str = "  ".join(f"{k}={v:.4f}" for k, v in all_metrics.items())
                logger.info("Epoch %d/%d  %s", epoch, epochs, metric_str)

        return self.history

    def save(self, path: str) -> None:
        """Save model state dict.

        Args:
            path: File path for the checkpoint (.pt or .pth).
        """
        torch.save(self.model.state_dict(), path)
        logger.info("Saved model to %s", path)

    def load(self, path: str) -> None:
        """Load model state dict.

        Args:
            path: File path of the checkpoint to load.
        """
        state = torch.load(path, map_location=self.device)
        self.model.load_state_dict(state)
        logger.info("Loaded model from %s", path)
