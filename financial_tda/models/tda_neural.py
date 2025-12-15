"""
Neural network models for topological time-series analysis.

This module implements deep learning architectures that combine Perslay
persistence diagram vectorization with temporal sequence modeling (LSTM/Transformer)
for financial regime detection and crisis prediction.

Architecture:
    Time Series → Persistence Diagrams → Perslay → LSTM/Transformer → Classification

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series:
        Landscapes of crashes. Physica A, 491, 820-834.
    Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural
        Computation, 9(8), 1735-1780.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import torch
import torch.nn as nn

from financial_tda.models.persistence_layers import Perslay

if TYPE_CHECKING:
    from torch import Tensor

logger = logging.getLogger(__name__)

# Type aliases
SequenceModelType = Literal["lstm", "transformer"]


class RegimeDetectionModel(nn.Module):
    """
    End-to-end model for financial regime detection using persistence diagrams.

    Combines Perslay persistence diagram vectorization with LSTM temporal
    modeling to classify time-series windows as crisis or normal regimes.

    Architecture:
        1. Perslay layer: Vectorize each time window's persistence diagram
        2. LSTM: Model temporal dependencies across windows
        3. Classification head: Binary output (crisis vs normal)

    Args:
        perslay: Pre-configured Perslay layer for diagram vectorization.
        sequence_model: Type of temporal model ("lstm" or "transformer").
            Default "lstm".
        hidden_dim: Hidden state dimension for LSTM/Transformer. Default 64.
        num_layers: Number of LSTM/Transformer layers. Default 2.
        dropout: Dropout probability for regularization. Default 0.2.
        num_classes: Number of output classes. Default 2 (binary classification).
        bidirectional: Whether to use bidirectional LSTM. Default False.
            Only applicable when sequence_model="lstm".

    Attributes:
        perslay: Persistence diagram vectorization layer.
        sequence_model_type: Type of sequence model used.
        sequence_model: LSTM or Transformer encoder.
        classifier: Classification head (linear layer).

    Examples:
        >>> from financial_tda.models.persistence_layers import create_perslay
        >>> perslay = create_perslay(output_dim=32, perm_op="mean")
        >>> model = RegimeDetectionModel(
        ...     perslay=perslay,
        ...     sequence_model="lstm",
        ...     hidden_dim=64,
        ...     num_layers=2
        ... )
        >>> # diagram_sequences: List of (T, n_points, 2) for each sample
        >>> logits = model(diagram_sequences)  # (batch_size, 2)
    """

    def __init__(
        self,
        perslay: Perslay,
        sequence_model: SequenceModelType = "lstm",
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_classes: int = 2,
        bidirectional: bool = False,
    ):
        super().__init__()

        if sequence_model not in {"lstm", "transformer"}:
            raise ValueError(
                f"Invalid sequence_model: {sequence_model}. Use 'lstm' or 'transformer'"
            )

        self.perslay = perslay
        self.sequence_model_type = sequence_model
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        # Build sequence model
        if sequence_model == "lstm":
            self.sequence_model = nn.LSTM(
                input_size=perslay.output_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                bidirectional=bidirectional,
            )
            classifier_input_dim = hidden_dim * (2 if bidirectional else 1)

        elif sequence_model == "transformer":
            # Transformer encoder layer
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=perslay.output_dim,
                nhead=4,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                batch_first=True,
            )
            self.sequence_model = nn.TransformerEncoder(
                encoder_layer,
                num_layers=num_layers,
            )
            classifier_input_dim = perslay.output_dim

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(classifier_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

        msg = (
            "Initialized RegimeDetectionModel: perslay_dim=%d, %s(hidden=%d, "
            "layers=%d), classes=%d"
        )
        logger.info(
            msg, perslay.output_dim, sequence_model, hidden_dim, num_layers, num_classes
        )

    def forward(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """
        Forward pass for regime detection.

        Args:
            diagram_sequences: List of diagram sequences, one per sample.
                Each sequence is a list of T persistence diagram tensors,
                where each diagram has shape (n_points, 2).
                Format: [[diag_t0, diag_t1, ..., diag_tT], ...]
                Length: batch_size sequences

        Returns:
            Logits of shape (batch_size, num_classes).

        Raises:
            ValueError: If diagram_sequences is empty or has inconsistent lengths.
        """
        if not diagram_sequences:
            raise ValueError("diagram_sequences cannot be empty")

        batch_size = len(diagram_sequences)
        seq_length = len(diagram_sequences[0])

        # Validate sequence lengths
        if not all(len(seq) == seq_length for seq in diagram_sequences):
            raise ValueError("All sequences must have the same length")

        # Vectorize persistence diagrams using Perslay
        # Process each time step across all samples in batch
        perslay_features = []
        for t in range(seq_length):
            # Collect diagrams at time t from all samples
            diagrams_at_t = [diagram_sequences[i][t] for i in range(batch_size)]
            # Vectorize: (batch_size, perslay_output_dim)
            features_at_t = self.perslay(diagrams_at_t)
            perslay_features.append(features_at_t)

        # Stack into (batch_size, seq_length, perslay_output_dim)
        perslay_features = torch.stack(perslay_features, dim=1)

        # Apply sequence model
        if self.sequence_model_type == "lstm":
            # LSTM: (batch, seq, hidden)
            _, (h_n, c_n) = self.sequence_model(perslay_features)
            # Use final hidden state from last layer
            # h_n shape: (num_layers * num_directions, batch, hidden)
            if self.sequence_model.bidirectional:
                # Concatenate forward and backward final hidden states
                final_hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)
            else:
                final_hidden = h_n[-1]  # (batch, hidden)

        elif self.sequence_model_type == "transformer":
            # Transformer: (batch, seq, d_model)
            transformer_out = self.sequence_model(perslay_features)
            # Use mean pooling over sequence
            final_hidden = transformer_out.mean(dim=1)  # (batch, d_model)

        # Classification
        logits = self.classifier(final_hidden)  # (batch, num_classes)

        return logits

    def predict_proba(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """
        Predict class probabilities using softmax.

        Args:
            diagram_sequences: List of diagram sequences (see forward()).

        Returns:
            Probabilities of shape (batch_size, num_classes).
        """
        logits = self.forward(diagram_sequences)
        probs = torch.softmax(logits, dim=1)
        return probs

    def predict(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """
        Predict class labels (argmax).

        Args:
            diagram_sequences: List of diagram sequences (see forward()).

        Returns:
            Class labels of shape (batch_size,).
        """
        logits = self.forward(diagram_sequences)
        predictions = torch.argmax(logits, dim=1)
        return predictions


class TransformerRegimeDetector(nn.Module):
    """
    Transformer-based regime detection model with positional encoding.

    Alternative to RegimeDetectionModel with explicit positional encoding
    for better temporal awareness in Transformer architectures.

    Args:
        perslay: Pre-configured Perslay layer.
        d_model: Transformer model dimension. Default 64.
        nhead: Number of attention heads. Default 4.
        num_layers: Number of Transformer encoder layers. Default 2.
        dim_feedforward: Dimension of feedforward network. Default 256.
        dropout: Dropout probability. Default 0.2.
        max_seq_length: Maximum sequence length for positional encoding.
            Default 100.
        num_classes: Number of output classes. Default 2.

    Examples:
        >>> perslay = create_perslay(output_dim=64, perm_op="mean")
        >>> model = TransformerRegimeDetector(
        ...     perslay=perslay,
        ...     d_model=64,
        ...     nhead=4,
        ...     num_layers=3
        ... )
    """

    def __init__(
        self,
        perslay: Perslay,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 256,
        dropout: float = 0.2,
        max_seq_length: int = 100,
        num_classes: int = 2,
    ):
        super().__init__()

        if perslay.output_dim != d_model:
            # Add projection layer if dimensions don't match
            self.projection = nn.Linear(perslay.output_dim, d_model)
        else:
            self.projection = nn.Identity()

        self.perslay = perslay
        self.d_model = d_model
        self.num_classes = num_classes

        # Positional encoding
        self.positional_encoding = PositionalEncoding(
            d_model=d_model,
            max_len=max_seq_length,
            dropout=dropout,
        )

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
        )

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes),
        )

        logger.info(
            "Initialized TransformerRegimeDetector: d_model=%d, nhead=%d, layers=%d",
            d_model,
            nhead,
            num_layers,
        )

    def forward(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """
        Forward pass with positional encoding.

        Args:
            diagram_sequences: List of diagram sequences (see RegimeDetectionModel).

        Returns:
            Logits of shape (batch_size, num_classes).
        """
        if not diagram_sequences:
            raise ValueError("diagram_sequences cannot be empty")

        batch_size = len(diagram_sequences)
        seq_length = len(diagram_sequences[0])

        # Vectorize diagrams
        perslay_features = []
        for t in range(seq_length):
            diagrams_at_t = [diagram_sequences[i][t] for i in range(batch_size)]
            features_at_t = self.perslay(diagrams_at_t)
            perslay_features.append(features_at_t)

        # Stack and project: (batch, seq, d_model)
        perslay_features = torch.stack(perslay_features, dim=1)
        projected = self.projection(perslay_features)

        # Add positional encoding
        encoded = self.positional_encoding(projected)

        # Transformer
        transformer_out = self.transformer(encoded)

        # Global pooling (mean over sequence)
        pooled = transformer_out.mean(dim=1)  # (batch, d_model)

        # Classification
        logits = self.classifier(pooled)

        return logits

    def predict_proba(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """Predict class probabilities."""
        logits = self.forward(diagram_sequences)
        return torch.softmax(logits, dim=1)

    def predict(self, diagram_sequences: list[list[Tensor]]) -> Tensor:
        """Predict class labels."""
        logits = self.forward(diagram_sequences)
        return torch.argmax(logits, dim=1)


class PositionalEncoding(nn.Module):
    """
    Sinusoidal positional encoding for Transformer models.

    Adds positional information to input embeddings using sine and cosine
    functions of different frequencies, as described in "Attention is All You Need".

    Args:
        d_model: Model dimension.
        max_len: Maximum sequence length.
        dropout: Dropout probability. Default 0.1.

    References:
        Vaswani, A., et al. (2017). Attention is All You Need. NeurIPS 2017.
    """

    def __init__(self, d_model: int, max_len: int = 100, dropout: float = 0.1):
        super().__init__()

        self.dropout = nn.Dropout(p=dropout)

        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float()
            * (-torch.log(torch.tensor(10000.0)) / d_model)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        # Register as buffer (not a parameter)
        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: Tensor) -> Tensor:
        """
        Add positional encoding to input.

        Args:
            x: Input tensor of shape (batch_size, seq_length, d_model).

        Returns:
            Encoded tensor of shape (batch_size, seq_length, d_model).
        """
        seq_length = x.size(1)
        x = x + self.pe[:, :seq_length, :]
        return self.dropout(x)


def create_regime_detector(
    perslay: Perslay,
    model_type: SequenceModelType = "lstm",
    hidden_dim: int = 64,
    num_layers: int = 2,
    dropout: float = 0.2,
    num_classes: int = 2,
    **kwargs,
) -> RegimeDetectionModel | TransformerRegimeDetector:
    """
    Factory function to create regime detection models.

    Args:
        perslay: Pre-configured Perslay layer.
        model_type: Type of sequence model ("lstm" or "transformer").
        hidden_dim: Hidden dimension for LSTM or Transformer. Default 64.
        num_layers: Number of layers. Default 2.
        dropout: Dropout probability. Default 0.2.
        num_classes: Number of output classes. Default 2.
        **kwargs: Additional model-specific arguments:
            - bidirectional: For LSTM models (default False)
            - nhead: For Transformer models (default 4)
            - use_positional_encoding: Use TransformerRegimeDetector
              variant with explicit positional encoding (default False)

    Returns:
        Configured regime detection model.

    Examples:
        >>> from financial_tda.models.persistence_layers import create_perslay
        >>> perslay = create_perslay(output_dim=32)
        >>>
        >>> # LSTM model
        >>> lstm_model = create_regime_detector(
        ...     perslay, model_type="lstm", hidden_dim=64
        ... )
        >>>
        >>> # Transformer with positional encoding
        >>> transformer_model = create_regime_detector(
        ...     perslay,
        ...     model_type="transformer",
        ...     hidden_dim=64,
        ...     use_positional_encoding=True,
        ...     nhead=4
        ... )
    """
    if model_type == "transformer" and kwargs.get("use_positional_encoding", False):
        # Use TransformerRegimeDetector with positional encoding
        nhead = kwargs.get("nhead", 4)
        max_seq_length = kwargs.get("max_seq_length", 100)

        model = TransformerRegimeDetector(
            perslay=perslay,
            d_model=perslay.output_dim,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            max_seq_length=max_seq_length,
            num_classes=num_classes,
        )
    else:
        # Use standard RegimeDetectionModel
        bidirectional = kwargs.get("bidirectional", False)

        model = RegimeDetectionModel(
            perslay=perslay,
            sequence_model=model_type,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            num_classes=num_classes,
            bidirectional=bidirectional,
        )

    logger.info(
        "Created regime detector: type=%s, hidden=%d, layers=%d",
        model_type,
        hidden_dim,
        num_layers,
    )

    return model


# =============================================================================
# Dataset and Data Loading
# =============================================================================


class PersistenceDataset(torch.utils.data.Dataset):
    """
    Dataset for persistence diagram sequences with labels.

    Stores sequences of persistence diagrams along with their corresponding
    labels for regime classification. Each sample is a temporal sequence of
    diagrams representing a windowed view of financial time series.

    Args:
        diagram_sequences: List of diagram sequences. Each sequence is a list
            of T persistence diagram tensors of shape (n_points, 2).
        labels: Tensor of labels of shape (n_samples,).
        sequence_names: Optional list of sequence identifiers for tracking.

    Attributes:
        diagram_sequences: Stored diagram sequences.
        labels: Stored labels.
        sequence_names: Optional sequence identifiers.

    Examples:
        >>> sequences = [[torch.rand(10, 2) for _ in range(5)] for _ in range(100)]
        >>> labels = torch.randint(0, 2, (100,))
        >>> dataset = PersistenceDataset(sequences, labels)
        >>> print(len(dataset))  # 100
        >>> seq, label = dataset[0]
        >>> print(len(seq))  # 5 time windows
    """

    def __init__(
        self,
        diagram_sequences: list[list[Tensor]],
        labels: Tensor,
        sequence_names: list[str] | None = None,
    ):
        if len(diagram_sequences) != len(labels):
            raise ValueError(
                f"Number of sequences ({len(diagram_sequences)}) must match "
                f"number of labels ({len(labels)})"
            )

        self.diagram_sequences = diagram_sequences
        self.labels = labels
        self.sequence_names = sequence_names

        # Validate sequences
        if diagram_sequences:
            seq_length = len(diagram_sequences[0])
            for i, seq in enumerate(diagram_sequences):
                if len(seq) != seq_length:
                    raise ValueError(
                        f"All sequences must have same length. "
                        f"Sequence 0 has {seq_length}, sequence {i} has {len(seq)}"
                    )

        logger.debug(
            "Created PersistenceDataset: %d sequences, %d time windows each",
            len(diagram_sequences),
            seq_length if diagram_sequences else 0,
        )

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self.diagram_sequences)

    def __getitem__(self, idx: int) -> tuple[list[Tensor], Tensor]:
        """
        Get a single sample.

        Args:
            idx: Sample index.

        Returns:
            Tuple of (diagram_sequence, label) where diagram_sequence is a
            list of T persistence diagram tensors.
        """
        return self.diagram_sequences[idx], self.labels[idx]


def collate_persistence_batch(
    batch: list[tuple[list[Tensor], Tensor]],
) -> tuple[list[list[Tensor]], Tensor]:
    """
    Collate function for DataLoader with persistence diagram sequences.

    Args:
        batch: List of (diagram_sequence, label) tuples from PersistenceDataset.

    Returns:
        Tuple of (diagram_sequences, labels) where:
            - diagram_sequences: List of diagram sequences (length = batch_size)
            - labels: Tensor of labels (batch_size,)
    """
    diagram_sequences = [item[0] for item in batch]
    labels = torch.stack([item[1] for item in batch])
    return diagram_sequences, labels


def train_test_split_temporal(
    diagram_sequences: list[list[Tensor]],
    labels: Tensor,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[PersistenceDataset, PersistenceDataset, PersistenceDataset]:
    """
    Split data into train/val/test sets with temporal ordering preserved.

    IMPORTANT: This function performs a simple chronological split to prevent
    future leakage. For financial time series, the training set should come
    from earlier time periods than validation and test sets.

    Args:
        diagram_sequences: List of diagram sequences.
        labels: Tensor of labels.
        train_ratio: Fraction of data for training. Default 0.7.
        val_ratio: Fraction of data for validation. Default 0.15.
        test_ratio: Fraction of data for testing. Default 0.15.

    Returns:
        Tuple of (train_dataset, val_dataset, test_dataset).

    Raises:
        ValueError: If ratios don't sum to 1.0.

    Examples:
        >>> sequences = [[torch.rand(5, 2) for _ in range(10)] for _ in range(100)]
        >>> labels = torch.randint(0, 2, (100,))
        >>> train, val, test = train_test_split_temporal(sequences, labels)
        >>> print(len(train), len(val), len(test))  # 70, 15, 15
    """
    if not torch.isclose(
        torch.tensor(train_ratio + val_ratio + test_ratio), torch.tensor(1.0)
    ):
        raise ValueError(
            f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
        )

    n_samples = len(diagram_sequences)
    n_train = int(n_samples * train_ratio)
    n_val = int(n_samples * val_ratio)

    # Chronological split
    train_sequences = diagram_sequences[:n_train]
    train_labels = labels[:n_train]

    val_sequences = diagram_sequences[n_train : n_train + n_val]
    val_labels = labels[n_train : n_train + n_val]

    test_sequences = diagram_sequences[n_train + n_val :]
    test_labels = labels[n_train + n_val :]

    train_dataset = PersistenceDataset(train_sequences, train_labels)
    val_dataset = PersistenceDataset(val_sequences, val_labels)
    test_dataset = PersistenceDataset(test_sequences, test_labels)

    logger.info(
        "Temporal split: train=%d, val=%d, test=%d",
        len(train_dataset),
        len(val_dataset),
        len(test_dataset),
    )

    return train_dataset, val_dataset, test_dataset


# =============================================================================
# Training Loop and Utilities
# =============================================================================


def train_epoch(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    clip_grad: float | None = None,
) -> tuple[float, float]:
    """
    Train model for one epoch.

    Args:
        model: Model to train.
        dataloader: Training data loader.
        optimizer: Optimizer.
        criterion: Loss function.
        device: Device to train on.
        clip_grad: Gradient clipping threshold. If None, no clipping.

    Returns:
        Tuple of (average_loss, accuracy).
    """
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for diagram_sequences, labels in dataloader:
        labels = labels.to(device)

        # Forward pass
        optimizer.zero_grad()
        logits = model(diagram_sequences)
        loss = criterion(logits, labels)

        # Backward pass
        loss.backward()

        # Gradient clipping
        if clip_grad is not None:
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip_grad)

        optimizer.step()

        # Metrics
        total_loss += loss.item() * len(labels)
        predictions = torch.argmax(logits, dim=1)
        correct += (predictions == labels).sum().item()
        total += len(labels)

    avg_loss = total_loss / total
    accuracy = correct / total

    return avg_loss, accuracy


def evaluate(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, Tensor, Tensor]:
    """
    Evaluate model on validation/test set.

    Args:
        model: Model to evaluate.
        dataloader: Data loader.
        criterion: Loss function.
        device: Device to evaluate on.

    Returns:
        Tuple of (average_loss, accuracy, all_predictions, all_labels).
    """
    model.eval()
    total_loss = 0.0
    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for diagram_sequences, labels in dataloader:
            labels = labels.to(device)

            logits = model(diagram_sequences)
            loss = criterion(logits, labels)

            total_loss += loss.item() * len(labels)
            predictions = torch.argmax(logits, dim=1)

            all_predictions.append(predictions.cpu())
            all_labels.append(labels.cpu())

    avg_loss = total_loss / len(dataloader.dataset)
    all_predictions = torch.cat(all_predictions)
    all_labels = torch.cat(all_labels)
    accuracy = (all_predictions == all_labels).float().mean().item()

    return avg_loss, accuracy, all_predictions, all_labels


class EarlyStopping:
    """
    Early stopping to prevent overfitting.

    Monitors validation loss and stops training if no improvement for
    patience epochs.

    Args:
        patience: Number of epochs to wait for improvement. Default 10.
        min_delta: Minimum change to qualify as improvement. Default 0.0.
        mode: "min" for loss (lower is better) or "max" for accuracy.
            Default "min".

    Attributes:
        counter: Number of epochs without improvement.
        best_score: Best validation score seen so far.
        early_stop: Whether to stop training.

    Examples:
        >>> early_stopping = EarlyStopping(patience=5)
        >>> for epoch in range(100):
        ...     val_loss = train_and_validate()
        ...     early_stopping(val_loss)
        ...     if early_stopping.early_stop:
        ...         print(f"Early stopping at epoch {epoch}")
        ...         break
    """

    def __init__(self, patience: int = 10, min_delta: float = 0.0, mode: str = "min"):
        if mode not in {"min", "max"}:
            raise ValueError(f"mode must be 'min' or 'max', got {mode}")

        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, score: float) -> None:
        """
        Check if training should stop based on validation score.

        Args:
            score: Current validation score (loss or accuracy).
        """
        if self.best_score is None:
            self.best_score = score
        elif self._is_improvement(score):
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True

    def _is_improvement(self, score: float) -> bool:
        """Check if score is an improvement over best_score."""
        if self.mode == "min":
            return score < self.best_score - self.min_delta
        else:  # mode == "max"
            return score > self.best_score + self.min_delta


def train_model(
    model: nn.Module,
    train_dataset: PersistenceDataset,
    val_dataset: PersistenceDataset,
    num_epochs: int = 50,
    batch_size: int = 16,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-5,
    clip_grad: float | None = 1.0,
    patience: int = 10,
    device: torch.device | None = None,
    verbose: bool = True,
) -> dict:
    """
    Train regime detection model with early stopping and learning rate scheduling.

    Args:
        model: Model to train.
        train_dataset: Training dataset.
        val_dataset: Validation dataset.
        num_epochs: Maximum number of epochs. Default 50.
        batch_size: Batch size for training. Default 16.
        learning_rate: Initial learning rate. Default 1e-3.
        weight_decay: L2 regularization coefficient. Default 1e-5.
        clip_grad: Gradient clipping threshold. Default 1.0.
        patience: Early stopping patience. Default 10.
        device: Device to train on. If None, uses cuda if available.
        verbose: Whether to print training progress. Default True.

    Returns:
        Dictionary containing training history:
            - train_loss: List of training losses per epoch
            - train_acc: List of training accuracies per epoch
            - val_loss: List of validation losses per epoch
            - val_acc: List of validation accuracies per epoch
            - best_epoch: Epoch with best validation loss
            - best_val_loss: Best validation loss achieved

    Examples:
        >>> model = create_regime_detector(perslay, model_type="lstm")
        >>> train_ds, val_ds, test_ds = train_test_split_temporal(sequences, labels)
        >>> history = train_model(model, train_ds, val_ds, num_epochs=50)
        >>> print(f"Best val loss: {history['best_val_loss']:.4f}")
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = model.to(device)

    # Create data loaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_persistence_batch,
    )

    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_persistence_batch,
    )

    # Optimizer and loss
    optimizer = torch.optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    criterion = nn.CrossEntropyLoss()

    # Learning rate scheduler (reduce on plateau)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    # Early stopping
    early_stopping = EarlyStopping(patience=patience, mode="min")

    # Training history
    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "best_epoch": 0,
        "best_val_loss": float("inf"),
    }

    if verbose:
        print(f"Training on device: {device}")
        print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
        print(f"Batch size: {batch_size}, Epochs: {num_epochs}")
        print("-" * 70)

    for epoch in range(num_epochs):
        # Train
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, criterion, device, clip_grad
        )

        # Validate
        val_loss, val_acc, _, _ = evaluate(model, val_loader, criterion, device)

        # Update history
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        # Check for best model
        if val_loss < history["best_val_loss"]:
            history["best_val_loss"] = val_loss
            history["best_epoch"] = epoch

        # Learning rate scheduling
        scheduler.step(val_loss)

        # Early stopping
        early_stopping(val_loss)

        if verbose:
            current_lr = optimizer.param_groups[0]["lr"]
            print(
                f"Epoch {epoch + 1:3d}/{num_epochs} | "
                f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
                f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | "
                f"LR: {current_lr:.2e}"
            )

        if early_stopping.early_stop:
            if verbose:
                print(f"\nEarly stopping at epoch {epoch + 1}")
            break

    if verbose:
        print("-" * 70)
        best_epoch = history["best_epoch"] + 1
        best_val_loss = history["best_val_loss"]
        print(f"Best model at epoch {best_epoch} with val_loss={best_val_loss:.4f}")

    return history


# =============================================================================
# Evaluation Metrics
# =============================================================================


def compute_metrics(
    predictions: Tensor,
    labels: Tensor,
    probabilities: Tensor | None = None,
) -> dict[str, float]:
    """
    Compute classification metrics.

    Args:
        predictions: Predicted class labels of shape (n_samples,).
        labels: True class labels of shape (n_samples,).
        probabilities: Class probabilities of shape (n_samples, n_classes).
            If provided, computes AUC-ROC. Optional.

    Returns:
        Dictionary containing:
            - accuracy: Overall accuracy
            - precision: Precision score (macro average)
            - recall: Recall score (macro average)
            - f1: F1 score (macro average)
            - auc_roc: AUC-ROC score (if probabilities provided, binary only)

    Examples:
        >>> preds = torch.tensor([0, 1, 1, 0])
        >>> labels = torch.tensor([0, 1, 0, 0])
        >>> probs = torch.tensor([[0.8, 0.2], [0.3, 0.7], [0.4, 0.6], [0.9, 0.1]])
        >>> metrics = compute_metrics(preds, labels, probs)
        >>> print(f"Accuracy: {metrics['accuracy']:.3f}")
    """
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    predictions_np = predictions.cpu().numpy()
    labels_np = labels.cpu().numpy()

    metrics = {
        "accuracy": accuracy_score(labels_np, predictions_np),
        "precision": precision_score(
            labels_np, predictions_np, average="macro", zero_division=0
        ),
        "recall": recall_score(
            labels_np, predictions_np, average="macro", zero_division=0
        ),
        "f1": f1_score(labels_np, predictions_np, average="macro", zero_division=0),
    }

    # AUC-ROC (binary classification only)
    if probabilities is not None and probabilities.shape[1] == 2:
        probs_np = probabilities.cpu().numpy()
        try:
            metrics["auc_roc"] = roc_auc_score(labels_np, probs_np[:, 1])
        except ValueError:
            # If only one class present in labels
            metrics["auc_roc"] = float("nan")

    return metrics
