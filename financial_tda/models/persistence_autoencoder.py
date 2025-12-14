"""
CNN Autoencoder for persistence image anomaly detection in financial markets.

This module implements a convolutional autoencoder that learns the normal topology
of stable market periods and detects anomalous topological patterns indicating
market stress or crisis events. The autoencoder is trained ONLY on normal periods,
so reconstruction errors on unseen data serve as anomaly scores.

Architecture:
    Encoder: Conv2d(32) → Conv2d(64) → Conv2d(128) → latent bottleneck
    Decoder: Symmetric transposed convolutions → reconstructed image
    Input: (batch, 1, H, W) persistence image
    Output: (batch, 1, H, W) reconstructed persistence image

Training Strategy:
    - Train ONLY on normal market periods (2004-2007, 2013-2019)
    - Validation on held-out normal periods
    - Test on crisis periods (2008 GFC, 2020 COVID, 2022 crypto winter)
    - High reconstruction error → topological anomaly → potential crisis

References:
    Adams, H., et al. (2017). Persistence images: A stable vector
        representation of persistent homology. JMLR, 18(1), 218-252.
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from numpy.typing import NDArray
from torch.utils.data import Dataset

if TYPE_CHECKING:
    from torch import Tensor
    from torch.optim import Optimizer
    from torch.optim.lr_scheduler import ReduceLROnPlateau

logger = logging.getLogger(__name__)


class PersistenceAutoencoder(nn.Module):
    """
    Convolutional autoencoder for persistence image anomaly detection.

    The autoencoder learns to reconstruct persistence images from normal market
    periods. During inference, high reconstruction errors indicate anomalous
    topological patterns that deviate from learned normal topology.

    Architecture:
        Encoder:
            - Conv2d(1 → 32, stride=2) + ReLU → H/2 × W/2
            - Conv2d(32 → 64, stride=2) + ReLU → H/4 × W/4
            - Conv2d(64 → 128, stride=2) + ReLU → H/8 × W/8  (rounded up)
            - Flatten → Linear → latent_dim

        Decoder:
            - Linear → Reshape to (128, H/8, W/8)
            - ConvTranspose2d(128 → 64, stride=2) + ReLU
            - ConvTranspose2d(64 → 32, stride=2) + ReLU
            - ConvTranspose2d(32 → 1, stride=2) + Sigmoid → (1, H, W)

    Args:
        input_size: Spatial dimensions of input image (H, W). Assumes square
            images. Default (50, 50) for standard persistence image resolution.
        latent_dim: Dimensionality of latent bottleneck. Default 32.
            Lower values enforce stronger compression, potentially improving
            anomaly sensitivity at cost of reconstruction fidelity.

    Attributes:
        input_size: Input image spatial dimensions.
        latent_dim: Latent space dimensionality.
        encoder: Sequential encoder CNN.
        decoder: Sequential decoder CNN.
        encoded_size: Spatial size after encoder convolutions (H/8, W/8).

    Examples:
        >>> model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=32)
        >>> # images: (batch, 1, 50, 50)
        >>> reconstructions = model(images)  # (batch, 1, 50, 50)
        >>> # Access latent representations
        >>> latents = model.encode(images)  # (batch, 32)
        >>> decoded = model.decode(latents)  # (batch, 1, 50, 50)

    Notes:
        - Uses strided convolutions for downsampling/upsampling
        - Works with any square image size (e.g., 48×48, 50×50, 56×56)
        - Sigmoid output ensures reconstructed images in [0, 1] range
        - Latent bottleneck enforces information compression for anomaly detection
    """

    def __init__(
        self,
        input_size: tuple[int, int] = (50, 50),
        latent_dim: int = 32,
    ):
        super().__init__()

        if input_size[0] != input_size[1]:
            raise ValueError(f"Only square images supported, got {input_size}")

        self.input_size = input_size
        self.latent_dim = latent_dim

        # Compute encoded spatial size after 3 stride-2 convolutions
        # Formula: out = (in + 2*pad - kernel) / stride + 1
        # For kernel=4, stride=2, padding=1: out = (in - 2) / 2
        h = input_size[0]
        for _ in range(3):
            h = (h + 2 * 1 - 4) // 2 + 1  # kernel=4, stride=2, padding=1
        self.encoded_size = h

        # =====================================================================
        # Encoder: Strided Conv → Strided Conv → Strided Conv → Flatten → Linear
        # =====================================================================
        self.encoder = nn.Sequential(
            # Layer 1: 1 → 32 channels, H/2 × W/2
            nn.Conv2d(1, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            # Layer 2: 32 → 64 channels, H/4 × W/4
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            # Layer 3: 64 → 128 channels, H/8 × W/8
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
        )

        # Fully connected bottleneck
        encoded_flat_size = 128 * self.encoded_size * self.encoded_size
        self.fc_encode = nn.Linear(encoded_flat_size, latent_dim)

        # =====================================================================
        # Decoder: Linear → Reshape → TransposedConv layers
        # =====================================================================
        self.fc_decode = nn.Linear(latent_dim, encoded_flat_size)

        # Decoder network - outputs close to input size, then adjust with final conv
        self.decoder_convs = nn.Sequential(
            # Layer 1: 128 → 64 channels, upsample 2x
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            # Layer 2: 64 → 32 channels, upsample 2x
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            # Layer 3: 32 → 32 channels, upsample 2x (gets to ~48x48)
            nn.ConvTranspose2d(32, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
        )

        # Final adjustment layer to match exact input size
        # Use regular conv with appropriate padding to reach target size
        # For 50x50: need to go from 48x48 to 50x50
        self.decoder_final = nn.Sequential(
            nn.Conv2d(32, 1, kernel_size=3, padding=1),  # Same size
            nn.Sigmoid(),  # Ensure [0, 1] range
        )

        logger.info(
            "Initialized PersistenceAutoencoder: input=%s, latent_dim=%d, "
            "encoded_size=%d",
            input_size,
            latent_dim,
            self.encoded_size,
        )

    def encode(self, x: Tensor) -> Tensor:
        """
        Encode persistence images to latent representations.

        Args:
            x: Input images of shape (batch, 1, H, W).

        Returns:
            Latent vectors of shape (batch, latent_dim).

        Examples:
            >>> model = PersistenceAutoencoder()
            >>> images = torch.randn(8, 1, 50, 50)
            >>> latents = model.encode(images)
            >>> print(latents.shape)  # (8, 32)
        """
        # Conv layers
        x = self.encoder(x)  # (batch, 128, H/8, W/8)

        # Flatten and project to latent space
        x = x.view(x.size(0), -1)  # (batch, 128 * H/8 * W/8)
        latent = self.fc_encode(x)  # (batch, latent_dim)

        return latent

    def decode(self, z: Tensor) -> Tensor:
        """
        Decode latent vectors to reconstructed persistence images.

        Args:
            z: Latent vectors of shape (batch, latent_dim).

        Returns:
            Reconstructed images of shape (batch, 1, H, W).

        Examples:
            >>> model = PersistenceAutoencoder()
            >>> latents = torch.randn(8, 32)
            >>> reconstructions = model.decode(latents)
            >>> print(reconstructions.shape)  # (8, 1, 50, 50)
        """
        # Project to encoded spatial size
        x = self.fc_decode(z)  # (batch, 128 * H/8 * W/8)

        # Reshape to 4D tensor
        x = x.view(x.size(0), 128, self.encoded_size, self.encoded_size)

        # Transposed conv layers
        x = self.decoder_convs(x)  # (batch, 32, ~H, ~W)

        # Adjust to exact input size with interpolation if needed
        if x.size(2) != self.input_size[0] or x.size(3) != self.input_size[1]:
            # Upsample/downsample to exact size
            x = F.interpolate(
                x,
                size=self.input_size,
                mode="bilinear",
                align_corners=False,
            )

        # Final conv to get single channel output
        reconstruction = self.decoder_final(x)  # (batch, 1, H, W)

        return reconstruction

    def forward(self, x: Tensor) -> Tensor:
        """
        Forward pass: encode then decode.

        Args:
            x: Input images of shape (batch, 1, H, W).

        Returns:
            Reconstructed images of shape (batch, 1, H, W).

        Examples:
            >>> model = PersistenceAutoencoder()
            >>> images = torch.randn(8, 1, 50, 50)
            >>> reconstructions = model(images)
            >>> print(reconstructions.shape)  # (8, 1, 50, 50)
            >>> # Compute reconstruction error
            >>> mse = F.mse_loss(reconstructions, images)
        """
        latent = self.encode(x)
        reconstruction = self.decode(latent)
        return reconstruction


# =============================================================================
# Dataset for Persistence Images
# =============================================================================


class PersistenceImageDataset(Dataset):
    """
    PyTorch Dataset for persistence images from time series windows.

    Loads pre-computed persistence images and normalizes them to [0, 1] range
    for training the autoencoder. Images should be computed from normal market
    periods ONLY (2004-2007, 2013-2019 excluding Aug 2015).

    Args:
        images: Array of persistence images of shape (n_samples, H, W) or
            (n_samples, 1, H, W). Will be normalized to [0, 1].
        normalize: Whether to normalize images to [0, 1]. Default True.

    Attributes:
        images: Normalized images tensor of shape (n_samples, 1, H, W).
        n_samples: Number of samples in dataset.

    Examples:
        >>> import numpy as np
        >>> # Load pre-computed persistence images from normal periods
        >>> normal_images = np.random.rand(100, 50, 50)  # (n_samples, H, W)
        >>> dataset = PersistenceImageDataset(normal_images)
        >>> print(len(dataset))  # 100
        >>> image = dataset[0]  # (1, 50, 50)
        >>> print(image.min(), image.max())  # Should be in [0, 1]

    Notes:
        - Images are stored as float32 tensors
        - Normalization is per-image (min-max scaling)
        - Original image shape is preserved (H, W)
    """

    def __init__(
        self,
        images: NDArray[np.floating] | Tensor,
        normalize: bool = True,
    ):
        if isinstance(images, np.ndarray):
            images = torch.from_numpy(images).float()
        else:
            images = images.float()

        # Ensure 4D: (n_samples, 1, H, W)
        if images.ndim == 3:
            images = images.unsqueeze(1)  # Add channel dimension
        elif images.ndim != 4:
            raise ValueError(
                f"Images must be 3D (n, H, W) or 4D (n, 1, H, W), got {images.ndim}D"
            )

        if images.size(1) != 1:
            raise ValueError(f"Expected 1 channel, got {images.size(1)}")

        # Normalize to [0, 1] per image
        if normalize:
            for i in range(images.size(0)):
                img = images[i, 0]  # (H, W)
                img_min = img.min()
                img_max = img.max()
                if img_max > img_min:
                    images[i, 0] = (img - img_min) / (img_max - img_min)
                # If constant image, already in [0, 1] (either all min or all max)

        self.images = images
        self.n_samples = len(images)

        logger.debug(
            "PersistenceImageDataset: %d samples, shape=%s, range=[%.4f, %.4f]",
            self.n_samples,
            tuple(images.shape[1:]),
            images.min().item(),
            images.max().item(),
        )

    def __len__(self) -> int:
        """Return number of samples."""
        return self.n_samples

    def __getitem__(self, idx: int) -> Tensor:
        """Return single image of shape (1, H, W)."""
        return self.images[idx]


# =============================================================================
# Early Stopping
# =============================================================================


class EarlyStopping:
    """
    Early stopping to prevent overfitting during training.

    Monitors validation loss and stops training if no improvement for
    patience epochs.

    Args:
        patience: Number of epochs to wait for improvement before stopping.
            Default 10.
        min_delta: Minimum change in monitored value to qualify as improvement.
            Default 1e-4.
        mode: 'min' for minimizing loss, 'max' for maximizing metric.
            Default 'min'.

    Attributes:
        best_loss: Best validation loss seen so far.
        counter: Number of epochs without improvement.
        early_stop: Boolean flag indicating whether to stop training.

    Examples:
        >>> early_stopping = EarlyStopping(patience=10)
        >>> for epoch in range(100):
        ...     val_loss = train_epoch(...)
        ...     early_stopping(val_loss)
        ...     if early_stopping.early_stop:
        ...         print(f"Early stopping at epoch {epoch}")
        ...         break
    """

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 1e-4,
        mode: str = "min",
    ):
        if mode not in {"min", "max"}:
            raise ValueError(f"mode must be 'min' or 'max', got {mode}")

        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_loss = float("inf") if mode == "min" else float("-inf")
        self.early_stop = False

    def __call__(self, val_loss: float) -> None:
        """Check if training should stop based on validation loss."""
        if self.mode == "min":
            improved = val_loss < (self.best_loss - self.min_delta)
        else:
            improved = val_loss > (self.best_loss + self.min_delta)

        if improved:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True


# =============================================================================
# Autoencoder Trainer
# =============================================================================


class AutoencoderTrainer:
    """
    Training pipeline for PersistenceAutoencoder on normal market periods.

    Implements complete training loop with MSE loss, Adam optimization,
    learning rate scheduling, and early stopping. Designed to train ONLY
    on normal periods (2004-2007, 2013-2019).

    Args:
        model: PersistenceAutoencoder instance to train.
        learning_rate: Initial learning rate for Adam. Default 1e-3.
        weight_decay: L2 regularization strength. Default 0.0.
        device: Device to train on ('cpu', 'cuda', 'mps'). If None, uses
            'cuda' if available, else 'cpu'.

    Attributes:
        model: Autoencoder model being trained.
        optimizer: Adam optimizer.
        scheduler: ReduceLROnPlateau learning rate scheduler.
        device: Training device.
        history: Training history dictionary.

    Examples:
        >>> model = PersistenceAutoencoder()
        >>> trainer = AutoencoderTrainer(model, learning_rate=1e-3)
        >>> # Train on normal periods only
        >>> train_dataset = PersistenceImageDataset(normal_images)
        >>> val_dataset = PersistenceImageDataset(normal_val_images)
        >>> history = trainer.train(
        ...     train_dataset, val_dataset,
        ...     num_epochs=100, batch_size=32, patience=10
        ... )
        >>> print(f"Best val loss: {history['best_val_loss']:.4f}")

    Notes:
        - Uses MSE reconstruction loss (F.mse_loss)
        - Learning rate reduces by 0.5 after 5 epochs without improvement
        - Early stopping with default patience=10 epochs
        - Training history includes train/val loss per epoch
    """

    def __init__(
        self,
        model: PersistenceAutoencoder,
        learning_rate: float = 1e-3,
        weight_decay: float = 0.0,
        device: str | None = None,
    ):
        self.model = model

        # Device setup
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model.to(self.device)

        # Optimizer
        self.optimizer: Optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )

        # Learning rate scheduler (reduce on plateau)
        self.scheduler: ReduceLROnPlateau = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            factor=0.5,
            patience=5,
        )

        # Training history
        self.history: dict[str, list[float] | float | int] = {
            "train_loss": [],
            "val_loss": [],
            "learning_rate": [],
            "best_val_loss": float("inf"),
            "best_epoch": 0,
        }

        logger.info(
            "AutoencoderTrainer initialized: lr=%.2e, device=%s", learning_rate, device
        )

    def train_epoch(self, train_loader: torch.utils.data.DataLoader) -> float:
        """
        Train for one epoch.

        Args:
            train_loader: DataLoader for training images.

        Returns:
            Average training loss for the epoch.
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for batch in train_loader:
            images = batch.to(self.device)  # (batch, 1, H, W)

            # Forward pass
            reconstructions = self.model(images)
            loss = F.mse_loss(reconstructions, images)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / n_batches
        return avg_loss

    def validate(self, val_loader: torch.utils.data.DataLoader) -> float:
        """
        Validate model on validation set.

        Args:
            val_loader: DataLoader for validation images.

        Returns:
            Average validation loss.
        """
        self.model.eval()
        total_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for batch in val_loader:
                images = batch.to(self.device)

                # Forward pass
                reconstructions = self.model(images)
                loss = F.mse_loss(reconstructions, images)

                total_loss += loss.item()
                n_batches += 1

        avg_loss = total_loss / n_batches
        return avg_loss

    def train(
        self,
        train_dataset: PersistenceImageDataset,
        val_dataset: PersistenceImageDataset,
        num_epochs: int = 100,
        batch_size: int = 32,
        patience: int = 10,
        verbose: bool = True,
    ) -> dict[str, list[float] | float | int]:
        """
        Complete training loop with early stopping.

        Args:
            train_dataset: Training dataset (NORMAL PERIODS ONLY).
            val_dataset: Validation dataset (NORMAL PERIODS ONLY).
            num_epochs: Maximum number of training epochs. Default 100.
            batch_size: Batch size for training. Default 32.
            patience: Early stopping patience (epochs). Default 10.
            verbose: Whether to print progress. Default True.

        Returns:
            Training history dictionary with keys:
                - train_loss: List of training losses per epoch
                - val_loss: List of validation losses per epoch
                - learning_rate: List of learning rates per epoch
                - best_val_loss: Best validation loss achieved
                - best_epoch: Epoch with best validation loss

        Examples:
            >>> trainer = AutoencoderTrainer(model)
            >>> history = trainer.train(
            ...     train_dataset, val_dataset,
            ...     num_epochs=100, batch_size=32, patience=10
            ... )
            >>> print(f"Training stopped at epoch {len(history['train_loss'])}")

        Notes:
            - Train ONLY on normal periods: 2004-2007, 2013-2019 (excl. Aug 2015)
            - Validation set should also be from normal periods
            - Early stopping prevents overfitting
            - Learning rate reduces automatically on plateau
        """
        # Data loaders
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
        )

        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
        )

        # Early stopping
        early_stopping = EarlyStopping(patience=patience, mode="min")

        if verbose:
            print(f"Training on device: {self.device}")
            print(
                f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}"
            )
            print(
                f"Batch size: {batch_size}, Epochs: {num_epochs}, Patience: {patience}"
            )
            print("-" * 70)

        for epoch in range(num_epochs):
            # Train
            train_loss = self.train_epoch(train_loader)

            # Validate
            val_loss = self.validate(val_loader)

            # Update history
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            current_lr = self.optimizer.param_groups[0]["lr"]
            self.history["learning_rate"].append(current_lr)

            # Track best model
            if val_loss < self.history["best_val_loss"]:
                self.history["best_val_loss"] = val_loss
                self.history["best_epoch"] = epoch

            # Learning rate scheduling
            self.scheduler.step(val_loss)

            # Early stopping
            early_stopping(val_loss)

            if verbose:
                print(
                    f"Epoch {epoch + 1:3d}/{num_epochs} | "
                    f"Train Loss: {train_loss:.6f} | "
                    f"Val Loss: {val_loss:.6f} | "
                    f"LR: {current_lr:.2e}"
                )

            if early_stopping.early_stop:
                if verbose:
                    print(f"\nEarly stopping at epoch {epoch + 1}")
                break

        if verbose:
            print("-" * 70)
            best_epoch = self.history["best_epoch"] + 1
            best_val_loss = self.history["best_val_loss"]
            print(
                f"Training complete. Best model at epoch {best_epoch} "
                f"with val_loss={best_val_loss:.6f}"
            )

        return self.history

    def save_model(self, path: str | Path) -> None:
        """
        Save model state dict to file.

        Args:
            path: Path to save model checkpoint.

        Examples:
            >>> trainer.save_model("checkpoints/autoencoder_best.pt")
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), path)
        logger.info("Model saved to %s", path)

    def load_model(self, path: str | Path) -> None:
        """
        Load model state dict from file.

        Args:
            path: Path to load model checkpoint from.

        Examples:
            >>> trainer.load_model("checkpoints/autoencoder_best.pt")
        """
        state_dict = torch.load(path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        logger.info("Model loaded from %s", path)


# =============================================================================
# Anomaly Detection Utilities
# =============================================================================


def compute_reconstruction_error(
    model: PersistenceAutoencoder,
    images: Tensor | NDArray[np.floating],
    device: str | None = None,
) -> NDArray[np.floating]:
    """
    Compute per-sample reconstruction errors for anomaly detection.

    Reconstruction error (MSE) measures how well the autoencoder can
    reconstruct each input image. High error indicates the image contains
    topological patterns that deviate from the normal patterns learned
    during training.

    Args:
        model: Trained PersistenceAutoencoder.
        images: Input images of shape (n_samples, H, W) or (n_samples, 1, H, W).
            Can be numpy array or torch tensor.
        device: Device to run inference on. If None, uses model's current device.

    Returns:
        Array of reconstruction errors (MSE) of shape (n_samples,).
        Higher values indicate more anomalous samples.

    Examples:
        >>> model = PersistenceAutoencoder()
        >>> # Train model on normal periods...
        >>> crisis_images = np.random.rand(20, 50, 50)
        >>> errors = compute_reconstruction_error(model, crisis_images)
        >>> print(errors.shape)  # (20,)
        >>> print(f"Mean error: {errors.mean():.6f}")
        >>> # High errors indicate crisis-like topology

    Notes:
        - Model is set to eval mode automatically
        - Computes per-pixel MSE: sum((input - output)^2) / n_pixels
        - Returns numpy array for easy thresholding and analysis
    """
    model.eval()

    # Convert to tensor if needed
    if isinstance(images, np.ndarray):
        images_tensor = torch.from_numpy(images).float()
    else:
        images_tensor = images.float()

    # Ensure 4D: (n_samples, 1, H, W)
    if images_tensor.ndim == 3:
        images_tensor = images_tensor.unsqueeze(1)

    if device is None:
        # Use model's device
        device_obj = next(model.parameters()).device
    else:
        device_obj = torch.device(device)

    images_tensor = images_tensor.to(device_obj)

    # Compute reconstructions
    with torch.no_grad():
        reconstructions = model(images_tensor)

        # Compute per-sample MSE
        errors = F.mse_loss(
            reconstructions, images_tensor, reduction="none"
        )  # (n, 1, H, W)

        # Average over spatial dimensions and channel
        errors = errors.mean(dim=(1, 2, 3))  # (n,)

    # Convert to numpy
    errors_np = errors.cpu().numpy()

    return errors_np


def fit_anomaly_threshold(
    model: PersistenceAutoencoder,
    normal_images: Tensor | NDArray[np.floating],
    percentile: float = 95.0,
    device: str | None = None,
) -> float:
    """
    Fit anomaly detection threshold from normal training data.

    The threshold is set at a specified percentile of reconstruction errors
    on normal-period images. By default (95th percentile), approximately 5%
    of normal samples will be flagged as anomalies (false positive rate).

    Args:
        model: Trained PersistenceAutoencoder (trained on normal periods ONLY).
        normal_images: Images from normal periods of shape (n_samples, H, W)
            or (n_samples, 1, H, W). Should be from training or validation set.
        percentile: Percentile for threshold (0-100). Default 95 gives ~5% FPR.
        device: Device to run inference on. If None, uses model's current device.

    Returns:
        Threshold value. Samples with error > threshold are anomalies.

    Examples:
        >>> model = PersistenceAutoencoder()
        >>> # Train on normal periods (2004-2007, 2013-2019)
        >>> normal_train_images = ...  # Shape: (n_normal, 50, 50)
        >>> threshold = fit_anomaly_threshold(model, normal_train_images, percentile=95)
        >>> print(f"Anomaly threshold (95th percentile): {threshold:.6f}")
        >>> # Now use this threshold to detect crises
        >>> crisis_images = ...
        >>> is_anomaly = detect_anomalies(model, crisis_images, threshold)

    Notes:
        - Higher percentile → fewer false positives, more false negatives
        - Lower percentile → more false positives, fewer false negatives
        - 95th percentile is standard for ~5% false positive rate
        - Threshold should be computed on NORMAL data only
    """
    # Compute reconstruction errors on normal data
    errors = compute_reconstruction_error(model, normal_images, device=device)

    # Compute threshold at specified percentile
    threshold = float(np.percentile(errors, percentile))

    logger.info(
        "Anomaly threshold fitted: %.6f at %.1f%% percentile (n=%d samples)",
        threshold,
        percentile,
        len(errors),
    )

    return threshold


def detect_anomalies(
    model: PersistenceAutoencoder,
    images: Tensor | NDArray[np.floating],
    threshold: float,
    device: str | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.floating]]:
    """
    Detect anomalies using reconstruction error threshold.

    Samples with reconstruction error exceeding the threshold are classified
    as anomalies. This identifies topological patterns that deviate from
    normal market behavior learned during training.

    Args:
        model: Trained PersistenceAutoencoder.
        images: Input images of shape (n_samples, H, W) or (n_samples, 1, H, W).
        threshold: Anomaly threshold from fit_anomaly_threshold().
        device: Device to run inference on. If None, uses model's current device.

    Returns:
        Tuple of (is_anomaly, anomaly_scores) where:
            - is_anomaly: Boolean mask of shape (n_samples,), True = anomaly
            - anomaly_scores: Reconstruction errors of shape (n_samples,) for ranking

    Examples:
        >>> model = PersistenceAutoencoder()
        >>> # Train and fit threshold on normal periods
        >>> threshold = fit_anomaly_threshold(model, normal_images, percentile=95)
        >>> # Detect crises
        >>> crisis_images = np.random.rand(50, 50, 50)  # 2008 GFC period
        >>> is_anomaly, scores = detect_anomalies(model, crisis_images, threshold)
        >>> print(f"Anomalies detected: {is_anomaly.sum()} / {len(is_anomaly)}")
        >>> print(f"Detection rate: {100 * is_anomaly.mean():.1f}%")
        >>> # Rank by anomaly severity
        >>> top_anomalies = np.argsort(scores)[-10:]  # 10 most anomalous

    Notes:
        - Returns both binary labels and continuous scores
        - Scores enable ranking samples by anomaly severity
        - Threshold determines sensitivity (higher → fewer detections)
        - High scores in crisis periods validate anomaly detection
    """
    # Compute reconstruction errors
    errors = compute_reconstruction_error(model, images, device=device)

    # Classify as anomalies if error > threshold
    is_anomaly = errors > threshold

    logger.debug(
        "Anomaly detection: %d / %d samples flagged (%.1f%%)",
        is_anomaly.sum(),
        len(is_anomaly),
        100 * is_anomaly.mean(),
    )

    return is_anomaly, errors


def validate_crisis_detection(
    model: PersistenceAutoencoder,
    threshold: float,
    crisis_data: dict[str, NDArray[np.floating]],
    normal_data: NDArray[np.floating] | None = None,
    device: str | None = None,
) -> dict[str, dict[str, float]]:
    """
    Validate anomaly detection performance on known crisis periods.

    Tests the autoencoder's ability to detect topological anomalies during
    historical market crises (2008 GFC, 2020 COVID, 2022 crypto winter).
    Computes true positive rate, false positive rate, and detection metrics.

    Args:
        model: Trained PersistenceAutoencoder.
        threshold: Anomaly threshold from fit_anomaly_threshold().
        crisis_data: Dictionary mapping crisis names to persistence images.
            Example: {"2008_GFC": images_array, "2020_COVID": images_array}
        normal_data: Optional normal-period images for FPR computation.
            If None, FPR is not computed.
        device: Device to run inference on. If None, uses model's current device.

    Returns:
        Dictionary with crisis names as keys and metrics dictionaries as values.
        Each metrics dict contains:
            - "true_positive_rate": % of crisis samples detected (0-100)
            - "n_detected": Number of crisis samples flagged
            - "n_total": Total number of crisis samples
            - "mean_anomaly_score": Mean reconstruction error
            - "max_anomaly_score": Maximum reconstruction error
            - "false_positive_rate": % of normal samples flagged
              (if normal_data provided)

    Examples:
        >>> model = PersistenceAutoencoder()
        >>> # Train and fit threshold on 2004-2007, 2013-2019
        >>> threshold = fit_anomaly_threshold(model, normal_images, percentile=95)
        >>> # Test on crises
        >>> crisis_data = {
        ...     "2008_GFC": gfc_images,  # September-October 2008
        ...     "2020_COVID": covid_images,  # March 2020
        ... }
        >>> results = validate_crisis_detection(model, threshold, crisis_data)
        >>> print(f"2008 GFC TPR: {results['2008_GFC']['true_positive_rate']:.1f}%")
        >>> print(f"2020 COVID TPR: {results['2020_COVID']['true_positive_rate']:.1f}%")

    Notes:
        - TPR > 80% indicates good crisis detection capability
        - FPR should be ~5% (matching threshold percentile)
        - High mean_anomaly_score during crises validates approach
        - Useful for comparing detection across different crisis types
    """
    results = {}

    # Compute FPR on normal data if provided
    fpr = None
    if normal_data is not None:
        is_anom_normal, _ = detect_anomalies(model, normal_data, threshold, device)
        fpr = float(100 * is_anom_normal.mean())
        logger.info("False positive rate on normal data: %.1f%%", fpr)

    # Validate each crisis period
    for crisis_name, crisis_images in crisis_data.items():
        is_anomaly, scores = detect_anomalies(model, crisis_images, threshold, device)

        metrics = {
            "true_positive_rate": float(100 * is_anomaly.mean()),
            "n_detected": int(is_anomaly.sum()),
            "n_total": int(len(is_anomaly)),
            "mean_anomaly_score": float(scores.mean()),
            "max_anomaly_score": float(scores.max()),
        }

        if fpr is not None:
            metrics["false_positive_rate"] = fpr

        results[crisis_name] = metrics

        logger.info(
            "%s: TPR=%.1f%% (%d/%d detected), mean_score=%.6f",
            crisis_name,
            metrics["true_positive_rate"],
            metrics["n_detected"],
            metrics["n_total"],
            metrics["mean_anomaly_score"],
        )

    return results


# =============================================================================
# Lead Time Analysis
# =============================================================================


def compute_lead_time(
    anomaly_flags: NDArray[np.bool_],
    crisis_peak_index: int,
) -> int | None:
    """
    Compute lead time: days before crisis peak when anomalies first detected.

    Lead time measures early warning capability - how many time steps (days/windows)
    before the crisis peak the autoencoder starts flagging anomalies.

    Args:
        anomaly_flags: Boolean array of shape (n_timesteps,) where True = anomaly.
            Should cover period leading up to and including crisis.
        crisis_peak_index: Index in anomaly_flags corresponding to crisis peak
            (e.g., Lehman collapse date, COVID market bottom).

    Returns:
        Lead time in time steps (days/windows) if anomalies detected before peak,
        or None if no anomalies detected before peak.

    Examples:
        >>> # Time series: 100 days before crisis peak
        >>> anomaly_flags = np.array([False]*85 + [True]*15)  # Flags start at day 85
        >>> crisis_peak = 99  # Day 100 (0-indexed)
        >>> lead_time = compute_lead_time(anomaly_flags, crisis_peak)
        >>> print(f"Early warning: {lead_time} days before crisis")  # 14 days
        >>> # No early warning case
        >>> no_warning = np.array([False]*100)
        >>> lead_time = compute_lead_time(no_warning, 99)
        >>> print(lead_time)  # None

    Notes:
        - Positive lead time indicates early warning capability
        - Longer lead time = earlier detection (more useful for risk management)
        - Compare lead times across different crises
        - Use with sliding window approach for real-time monitoring
    """
    if crisis_peak_index >= len(anomaly_flags) or crisis_peak_index < 0:
        max_idx = len(anomaly_flags)
        raise ValueError(
            f"crisis_peak_index {crisis_peak_index} out of range [0, {max_idx})"
        )

    # Find first anomaly before peak
    anomalies_before_peak = anomaly_flags[:crisis_peak_index]

    if not anomalies_before_peak.any():
        # No early warning
        return None

    # Find index of first anomaly
    first_anomaly_idx = int(np.argmax(anomalies_before_peak))

    # Lead time = days between first anomaly and peak
    lead_time = crisis_peak_index - first_anomaly_idx

    return lead_time
