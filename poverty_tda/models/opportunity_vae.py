"""
Variational Autoencoder for opportunity landscape latent space learning.

This module implements a β-VAE for learning interpretable latent representations
of geographic mobility surfaces. The VAE learns to compress complex 2D mobility
landscapes into a low-dimensional latent space where dimensions correspond to
interpretable factors (urbanity, deprivation, connectivity, etc.).

Key Components:
- OpportunityVAE: VAE with CNN encoder/decoder for 2D surfaces
- VAELoss: Combined reconstruction + KL divergence loss
- OpportunityVAETrainer: Training pipeline with early stopping
- Latent space analysis: Interpolation, sampling, factor analysis

Applications:
- Counterfactual generation: "What if X region had Y's opportunity structure?"
- Policy simulation: Test interventions in latent space
- Dimension interpretability: Correlate latent dims with known factors

Architecture:
    Input: Mobility surface (batch, 1, H, W) - typically 64×64 or 128×128
    Encoder: CNN → mean (μ) and log-variance (log σ²) vectors
    Latent: Sample z ~ N(μ, σ²) via reparameterization trick
    Decoder: Transposed CNN → reconstructed surface (batch, 1, H, W)

Reference:
    Kingma & Welling (2014) "Auto-Encoding Variational Bayes"
    Higgins et al. (2017) "β-VAE: Learning Basic Visual Concepts with a
        Constrained Variational Framework"

Integration:
    - mobility_surface.py: Creates 500×500 surfaces (downsample for training)
    - morse_smale.py: Critical point extraction for topology-aware loss

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class OpportunityVAE(nn.Module):
    """
    Variational Autoencoder for mobility surface latent space learning.

    This VAE learns to encode 2D mobility surfaces into a low-dimensional
    latent space and reconstruct them. The latent space is designed to
    capture interpretable factors that drive economic mobility patterns.

    Architecture:
        Encoder: 4 conv layers (stride 2) → FC → μ and log_σ²
        Latent: z = μ + σ * ε where ε ~ N(0,1)
        Decoder: FC → 4 transposed conv layers (stride 2) → surface

    Args:
        input_size: Size of square input surface (e.g., 64, 128)
        latent_dim: Dimensionality of latent space (8-16 recommended)
        base_channels: Base number of channels in encoder (doubles each layer)
        activation: Activation function ('relu', 'leaky_relu', 'elu')

    Attributes:
        encoder: CNN that outputs μ and log_σ²
        decoder: Transposed CNN that reconstructs surface
        latent_dim: Size of latent code
        input_size: Expected input surface size

    Example:
        >>> vae = OpportunityVAE(input_size=64, latent_dim=12)
        >>> x = torch.randn(8, 1, 64, 64)  # batch of surfaces
        >>> x_recon, mu, logvar = vae(x)
        >>> print(f"Reconstruction shape: {x_recon.shape}")
    """

    def __init__(
        self,
        input_size: int = 64,
        latent_dim: int = 12,
        base_channels: int = 32,
        activation: Literal["relu", "leaky_relu", "elu"] = "leaky_relu",
    ):
        super().__init__()

        self.input_size = input_size
        self.latent_dim = latent_dim
        self.base_channels = base_channels

        # Select activation function
        if activation == "relu":
            self.act = nn.ReLU(inplace=True)
        elif activation == "leaky_relu":
            self.act = nn.LeakyReLU(0.2, inplace=True)
        elif activation == "elu":
            self.act = nn.ELU(inplace=True)
        else:
            raise ValueError(f"Unknown activation: {activation}")

        # Calculate encoded feature map size
        # After 4 stride-2 convolutions: size = input_size // 16
        self.encoded_size = input_size // 16
        if self.encoded_size < 1:
            raise ValueError(
                f"input_size={input_size} too small for 4 stride-2 layers. "
                f"Minimum input_size=16"
            )

        # Encoder: Input → Conv layers → Flatten → FC
        self.encoder_conv = nn.Sequential(
            # Layer 1: 1 → base_channels, size → size//2
            nn.Conv2d(1, base_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(base_channels),
            self.act,
            # Layer 2: base_channels → base_channels*2, size → size//4
            nn.Conv2d(
                base_channels, base_channels * 2, kernel_size=4, stride=2, padding=1
            ),
            nn.BatchNorm2d(base_channels * 2),
            self.act,
            # Layer 3: base_channels*2 → base_channels*4, size → size//8
            nn.Conv2d(
                base_channels * 2, base_channels * 4, kernel_size=4, stride=2, padding=1
            ),
            nn.BatchNorm2d(base_channels * 4),
            self.act,
            # Layer 4: base_channels*4 → base_channels*8, size → size//16
            nn.Conv2d(
                base_channels * 4, base_channels * 8, kernel_size=4, stride=2, padding=1
            ),
            nn.BatchNorm2d(base_channels * 8),
            self.act,
        )

        # Flattened feature size
        self.encoded_features = base_channels * 8 * self.encoded_size**2

        # FC layers to latent space
        self.fc_mu = nn.Linear(self.encoded_features, latent_dim)
        self.fc_logvar = nn.Linear(self.encoded_features, latent_dim)

        # Decoder: Latent → FC → Reshape → Transposed Conv layers
        self.fc_decode = nn.Linear(latent_dim, self.encoded_features)

        self.decoder_conv = nn.Sequential(
            # Layer 1: base_channels*8 → base_channels*4, size → size*2
            nn.ConvTranspose2d(
                base_channels * 8,
                base_channels * 4,
                kernel_size=4,
                stride=2,
                padding=1,
            ),
            nn.BatchNorm2d(base_channels * 4),
            self.act,
            # Layer 2: base_channels*4 → base_channels*2, size → size*2
            nn.ConvTranspose2d(
                base_channels * 4,
                base_channels * 2,
                kernel_size=4,
                stride=2,
                padding=1,
            ),
            nn.BatchNorm2d(base_channels * 2),
            self.act,
            # Layer 3: base_channels*2 → base_channels, size → size*2
            nn.ConvTranspose2d(
                base_channels * 2, base_channels, kernel_size=4, stride=2, padding=1
            ),
            nn.BatchNorm2d(base_channels),
            self.act,
            # Layer 4: base_channels → 1, size → size*2
            nn.ConvTranspose2d(base_channels, 1, kernel_size=4, stride=2, padding=1),
            # No activation on final layer - allow any range
        )

        logger.info(
            f"OpportunityVAE initialized: {input_size}×{input_size} input, "
            f"{latent_dim}D latent, {self.encoded_features} encoded features"
        )

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Encode input surface to latent distribution parameters.

        Args:
            x: Input tensor of shape (batch, 1, H, W)

        Returns:
            Tuple of (mu, logvar):
            - mu: Mean of latent distribution (batch, latent_dim)
            - logvar: Log-variance of latent distribution (batch, latent_dim)
        """
        # Conv layers
        h = self.encoder_conv(x)  # (batch, base*8, size/16, size/16)

        # Flatten
        h = h.view(h.size(0), -1)  # (batch, encoded_features)

        # Project to latent distribution
        mu = self.fc_mu(h)  # (batch, latent_dim)
        logvar = self.fc_logvar(h)  # (batch, latent_dim)

        return mu, logvar

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Reparameterization trick: z = μ + σ * ε, where ε ~ N(0, 1).

        This allows backpropagation through sampling by expressing the
        random variable z as a deterministic function of μ, σ, and ε.

        Args:
            mu: Mean tensor (batch, latent_dim)
            logvar: Log-variance tensor (batch, latent_dim)

        Returns:
            Sampled latent code z (batch, latent_dim)
        """
        std = torch.exp(0.5 * logvar)  # σ = exp(0.5 * log(σ²))
        eps = torch.randn_like(std)  # ε ~ N(0, 1)
        z = mu + std * eps  # z = μ + σ * ε
        return z

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent code to reconstructed surface.

        Args:
            z: Latent code tensor (batch, latent_dim)

        Returns:
            Reconstructed surface (batch, 1, H, W)
        """
        # FC layer to encoded features
        h = self.fc_decode(z)  # (batch, encoded_features)

        # Reshape to spatial feature map
        h = h.view(
            h.size(0), self.base_channels * 8, self.encoded_size, self.encoded_size
        )

        # Transposed conv layers
        x_recon = self.decoder_conv(h)  # (batch, 1, H, W)

        return x_recon

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass through VAE.

        Args:
            x: Input surface tensor (batch, 1, H, W)

        Returns:
            Tuple of (x_recon, mu, logvar):
            - x_recon: Reconstructed surface (batch, 1, H, W)
            - mu: Latent distribution mean (batch, latent_dim)
            - logvar: Latent distribution log-variance (batch, latent_dim)
        """
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        return x_recon, mu, logvar

    def sample(self, num_samples: int, device: torch.device) -> torch.Tensor:
        """
        Generate novel surfaces by sampling from prior p(z) = N(0, I).

        Args:
            num_samples: Number of samples to generate
            device: Device to create tensors on

        Returns:
            Generated surfaces (num_samples, 1, H, W)
        """
        z = torch.randn(num_samples, self.latent_dim, device=device)
        with torch.no_grad():
            samples = self.decode(z)
        return samples


class VAELoss(nn.Module):
    """
    Combined VAE loss: reconstruction + β-weighted KL divergence.

    The total loss balances two objectives:
    1. Reconstruction: How well does the decoder reconstruct the input?
    2. KL Divergence: How close is q(z|x) to the prior p(z) = N(0, I)?

    The β parameter (β-VAE) controls the trade-off:
    - β = 1.0: Standard VAE (Kingma & Welling 2014)
    - β > 1.0: Stronger independence between latent dimensions
    - β < 1.0: Prioritize reconstruction quality

    Args:
        beta: Weight for KL divergence term (default 1.0)
        reduction: How to reduce losses ('mean', 'sum')

    Reference:
        Higgins et al. (2017) "β-VAE: Learning Basic Visual Concepts"
    """

    def __init__(self, beta: float = 1.0, reduction: str = "mean"):
        super().__init__()
        self.beta = beta
        self.reduction = reduction

        if reduction not in ["mean", "sum"]:
            raise ValueError(f"reduction must be 'mean' or 'sum', got {reduction}")

    def forward(
        self,
        x_recon: torch.Tensor,
        x: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Compute VAE loss.

        Args:
            x_recon: Reconstructed surface (batch, 1, H, W)
            x: Original surface (batch, 1, H, W)
            mu: Latent mean (batch, latent_dim)
            logvar: Latent log-variance (batch, latent_dim)

        Returns:
            Tuple of (total_loss, recon_loss, kl_loss):
            - total_loss: recon_loss + beta * kl_loss
            - recon_loss: MSE reconstruction loss
            - kl_loss: KL divergence KL(q(z|x) || p(z))
        """
        # Reconstruction loss: MSE between input and output
        recon_loss = F.mse_loss(x_recon, x, reduction="none")
        recon_loss = recon_loss.view(recon_loss.size(0), -1).sum(dim=1)  # sum over HW

        if self.reduction == "mean":
            recon_loss = recon_loss.mean()
        else:
            recon_loss = recon_loss.sum()

        # KL divergence: KL(q(z|x) || N(0,I))
        # KL = -0.5 * Σ(1 + log(σ²) - μ² - σ²)
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1)

        if self.reduction == "mean":
            kl_loss = kl_loss.mean()
        else:
            kl_loss = kl_loss.sum()

        # Total loss
        total_loss = recon_loss + self.beta * kl_loss

        return total_loss, recon_loss, kl_loss


# =============================================================================
# LATENT SPACE UTILITIES
# =============================================================================


def encode_surfaces(
    model: OpportunityVAE, surfaces: NDArray[np.float64] | torch.Tensor
) -> NDArray[np.float64]:
    """
    Encode batch of surfaces to latent codes (using mean μ, not sampling).

    Args:
        model: Trained OpportunityVAE model
        surfaces: Array or tensor of surfaces:
            - If array: (N, H, W) - will add channel dimension
            - If tensor: (N, 1, H, W) or (N, H, W)

    Returns:
        Latent codes as numpy array (N, latent_dim)

    Example:
        >>> vae = OpportunityVAE(latent_dim=12)
        >>> surfaces = np.random.randn(10, 64, 64)
        >>> codes = encode_surfaces(vae, surfaces)
        >>> print(f"Encoded to {codes.shape}")
    """
    model.eval()
    device = next(model.parameters()).device

    # Convert to tensor if needed
    if isinstance(surfaces, np.ndarray):
        x = torch.from_numpy(surfaces).float()
    else:
        x = surfaces.float()

    # Add channel dimension if needed
    if x.dim() == 3:
        x = x.unsqueeze(1)  # (N, H, W) → (N, 1, H, W)

    x = x.to(device)

    # Encode (use mean μ, not sampling)
    with torch.no_grad():
        mu, _ = model.encode(x)

    return mu.cpu().numpy()


def interpolate_latent(
    model: OpportunityVAE,
    z1: NDArray[np.float64] | torch.Tensor,
    z2: NDArray[np.float64] | torch.Tensor,
    steps: int = 10,
) -> NDArray[np.float64]:
    """
    Linearly interpolate between two latent codes and decode.

    Creates a smooth transition between two opportunity landscapes by
    interpolating in latent space. This is useful for counterfactual
    analysis: "What does the transition from rural to urban look like?"

    Args:
        model: Trained OpportunityVAE model
        z1: Starting latent code (latent_dim,) or (1, latent_dim)
        z2: Ending latent code (latent_dim,) or (1, latent_dim)
        steps: Number of interpolation steps (including endpoints)

    Returns:
        Interpolated surfaces as numpy array (steps, H, W)

    Example:
        >>> vae = OpportunityVAE()
        >>> z1 = encode_surfaces(vae, rural_surface)
        >>> z2 = encode_surfaces(vae, urban_surface)
        >>> transition = interpolate_latent(vae, z1[0], z2[0], steps=20)
    """
    model.eval()
    device = next(model.parameters()).device

    # Convert to tensor if needed
    if isinstance(z1, np.ndarray):
        z1 = torch.from_numpy(z1).float()
    if isinstance(z2, np.ndarray):
        z2 = torch.from_numpy(z2).float()

    # Ensure (1, latent_dim) shape
    if z1.dim() == 1:
        z1 = z1.unsqueeze(0)
    if z2.dim() == 1:
        z2 = z2.unsqueeze(0)

    z1 = z1.to(device)
    z2 = z2.to(device)

    # Linear interpolation: z(t) = (1-t)*z1 + t*z2, t ∈ [0, 1]
    alphas = torch.linspace(0, 1, steps, device=device)
    z_interp = torch.stack(
        [(1 - alpha) * z1 + alpha * z2 for alpha in alphas], dim=0
    )  # (steps, 1, latent_dim)
    z_interp = z_interp.squeeze(1)  # (steps, latent_dim)

    # Decode interpolated codes
    with torch.no_grad():
        surfaces = model.decode(z_interp)  # (steps, 1, H, W)

    # Remove channel dimension for output
    surfaces = surfaces.squeeze(1).cpu().numpy()  # (steps, H, W)

    return surfaces


def sample_latent_space(
    model: OpportunityVAE, n_samples: int = 10, device: torch.device | None = None
) -> NDArray[np.float64]:
    """
    Sample novel opportunity landscapes from prior p(z) = N(0, I).

    Generates new mobility surfaces by sampling random latent codes
    from the standard normal distribution. This can reveal the diversity
    of opportunity structures captured by the model.

    Args:
        model: Trained OpportunityVAE model
        n_samples: Number of samples to generate
        device: Device to use (defaults to model device)

    Returns:
        Generated surfaces as numpy array (n_samples, H, W)

    Example:
        >>> vae = OpportunityVAE()
        >>> novel_surfaces = sample_latent_space(vae, n_samples=20)
    """
    if device is None:
        device = next(model.parameters()).device

    surfaces = model.sample(n_samples, device)  # (n_samples, 1, H, W)
    surfaces = surfaces.squeeze(1).cpu().numpy()  # (n_samples, H, W)

    return surfaces


# =============================================================================
# TRAINING PIPELINE
# =============================================================================


class OpportunityVAETrainer:
    """
    Training pipeline for OpportunityVAE with early stopping and logging.

    This trainer handles the complete training workflow including:
    - Train/validation split and data loading
    - Optimization with Adam and learning rate scheduling
    - Early stopping to prevent overfitting
    - Metric tracking (reconstruction loss, KL divergence separately)
    - Model checkpointing

    Args:
        model: OpportunityVAE model to train
        beta: β parameter for VAE loss (default 1.0)
        lr: Initial learning rate (default 1e-4)
        device: Device to train on ('cuda' or 'cpu')

    Attributes:
        model: The VAE model being trained
        optimizer: Adam optimizer
        scheduler: ReduceLROnPlateau scheduler
        criterion: VAELoss module
        device: Training device
        history: Dict tracking training metrics

    Example:
        >>> vae = OpportunityVAE(latent_dim=12)
        >>> trainer = OpportunityVAETrainer(vae, beta=1.0, lr=1e-4)
        >>> history = trainer.train(train_loader, val_loader, epochs=100)
    """

    def __init__(
        self,
        model: OpportunityVAE,
        beta: float = 1.0,
        lr: float = 1e-4,
        device: str | torch.device = "cpu",
    ):
        self.model = model
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)

        # Loss function
        self.criterion = VAELoss(beta=beta, reduction="mean")

        # Optimizer: Adam with default parameters
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        # Learning rate scheduler: reduce on validation loss plateau
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            factor=0.5,
            patience=10,
            min_lr=1e-7,
        )

        # Training history
        self.history: dict[str, list] = {
            "train_loss": [],
            "train_recon": [],
            "train_kl": [],
            "val_loss": [],
            "val_recon": [],
            "val_kl": [],
            "lr": [],
        }

        logger.info(
            f"OpportunityVAETrainer initialized: β={beta}, lr={lr}, device={device}"
        )

    def train_epoch(self, train_loader: torch.utils.data.DataLoader) -> dict:
        """
        Train for one epoch.

        Args:
            train_loader: DataLoader for training data

        Returns:
            Dict with epoch metrics: loss, recon_loss, kl_loss
        """
        self.model.train()

        total_loss = 0.0
        total_recon = 0.0
        total_kl = 0.0
        n_batches = 0

        for batch in train_loader:
            # Move to device
            x = (
                batch.to(self.device)
                if torch.is_tensor(batch)
                else batch[0].to(self.device)
            )

            # Forward pass
            x_recon, mu, logvar = self.model(x)
            loss, recon_loss, kl_loss = self.criterion(x_recon, x, mu, logvar)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # Accumulate metrics
            total_loss += loss.item()
            total_recon += recon_loss.item()
            total_kl += kl_loss.item()
            n_batches += 1

        # Average metrics
        avg_loss = total_loss / n_batches
        avg_recon = total_recon / n_batches
        avg_kl = total_kl / n_batches

        return {
            "loss": avg_loss,
            "recon_loss": avg_recon,
            "kl_loss": avg_kl,
        }

    def validate(self, val_loader: torch.utils.data.DataLoader) -> dict:
        """
        Validate on validation set.

        Args:
            val_loader: DataLoader for validation data

        Returns:
            Dict with validation metrics: loss, recon_loss, kl_loss
        """
        self.model.eval()

        total_loss = 0.0
        total_recon = 0.0
        total_kl = 0.0
        n_batches = 0

        with torch.no_grad():
            for batch in val_loader:
                # Move to device
                x = (
                    batch.to(self.device)
                    if torch.is_tensor(batch)
                    else batch[0].to(self.device)
                )

                # Forward pass
                x_recon, mu, logvar = self.model(x)
                loss, recon_loss, kl_loss = self.criterion(x_recon, x, mu, logvar)

                # Accumulate metrics
                total_loss += loss.item()
                total_recon += recon_loss.item()
                total_kl += kl_loss.item()
                n_batches += 1

        # Average metrics
        avg_loss = total_loss / n_batches
        avg_recon = total_recon / n_batches
        avg_kl = total_kl / n_batches

        return {
            "loss": avg_loss,
            "recon_loss": avg_recon,
            "kl_loss": avg_kl,
        }

    def train(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: torch.utils.data.DataLoader,
        epochs: int = 100,
        early_stopping_patience: int = 20,
        checkpoint_path: Path | str | None = None,
    ) -> dict:
        """
        Train VAE with early stopping.

        Args:
            train_loader: DataLoader for training data
            val_loader: DataLoader for validation data
            epochs: Maximum number of epochs
            early_stopping_patience: Epochs to wait before early stopping
            checkpoint_path: Path to save best model (optional)

        Returns:
            Training history dict with all metrics

        Example:
            >>> trainer = OpportunityVAETrainer(vae)
            >>> history = trainer.train(
            ...     train_loader, val_loader, epochs=100,
            ...     checkpoint_path='best_vae.pt'
            ... )
        """
        logger.info(
            f"Starting training: {epochs} max epochs, "
            f"early stopping patience={early_stopping_patience}"
        )

        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            # Train epoch
            train_metrics = self.train_epoch(train_loader)

            # Validate
            val_metrics = self.validate(val_loader)

            # Update learning rate based on validation loss
            self.scheduler.step(val_metrics["loss"])

            # Record metrics
            self.history["train_loss"].append(train_metrics["loss"])
            self.history["train_recon"].append(train_metrics["recon_loss"])
            self.history["train_kl"].append(train_metrics["kl_loss"])
            self.history["val_loss"].append(val_metrics["loss"])
            self.history["val_recon"].append(val_metrics["recon_loss"])
            self.history["val_kl"].append(val_metrics["kl_loss"])
            self.history["lr"].append(self.optimizer.param_groups[0]["lr"])

            # Log progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} | "
                    f"Train Loss: {train_metrics['loss']:.4f} "
                    f"(Recon: {train_metrics['recon_loss']:.4f}, "
                    f"KL: {train_metrics['kl_loss']:.4f}) | "
                    f"Val Loss: {val_metrics['loss']:.4f} "
                    f"(Recon: {val_metrics['recon_loss']:.4f}, "
                    f"KL: {val_metrics['kl_loss']:.4f}) | "
                    f"LR: {self.history['lr'][-1]:.2e}"
                )

            # Early stopping and checkpointing
            if val_metrics["loss"] < best_val_loss:
                best_val_loss = val_metrics["loss"]
                patience_counter = 0

                # Save checkpoint
                if checkpoint_path is not None:
                    checkpoint_path = Path(checkpoint_path)
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    torch.save(
                        {
                            "epoch": epoch,
                            "model_state_dict": self.model.state_dict(),
                            "optimizer_state_dict": self.optimizer.state_dict(),
                            "scheduler_state_dict": self.scheduler.state_dict(),
                            "best_val_loss": best_val_loss,
                            "history": self.history,
                        },
                        checkpoint_path,
                    )
                    logger.info(f"Saved checkpoint to {checkpoint_path}")
            else:
                patience_counter += 1

                if patience_counter >= early_stopping_patience:
                    logger.info(
                        f"Early stopping triggered at epoch {epoch + 1}. "
                        f"Best val loss: {best_val_loss:.4f}"
                    )
                    break

        logger.info(f"Training complete. Best val loss: {best_val_loss:.4f}")
        return self.history

    def load_checkpoint(self, checkpoint_path: Path | str):
        """
        Load model from checkpoint.

        Args:
            checkpoint_path: Path to checkpoint file
        """
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.history = checkpoint["history"]
        logger.info(f"Loaded checkpoint from {checkpoint_path}")


# =============================================================================
# LATENT SPACE INTERPRETABILITY ANALYSIS
# =============================================================================


def analyze_latent_dimensions(
    model: OpportunityVAE,
    surfaces: NDArray[np.float64] | torch.Tensor,
    surface_metadata: dict | None = None,
    n_traversal_steps: int = 11,
) -> dict:
    """
    Analyze what each latent dimension captures through traversals.

    For each latent dimension, this function:
    1. Encodes a reference surface to get its latent code
    2. Creates traversals by varying one dimension at a time
    3. Decodes the traversals to see what changes in the surface

    This helps identify what each dimension represents (e.g., urbanity,
    deprivation level, connectivity, geographic scale).

    Args:
        model: Trained OpportunityVAE model
        surfaces: Reference surface(s) to analyze (H, W) or (N, H, W)
        surface_metadata: Optional dict with surface properties for correlation
            (e.g., {'urban_fraction': 0.8, 'deprivation_score': 0.3})
        n_traversal_steps: Number of steps for each dimension traversal
            (default 11, centered at 0 with range [-2σ, +2σ])

    Returns:
        Dict with analysis results:
        - 'latent_codes': Encoded latent codes (N, latent_dim)
        - 'traversals': Dict mapping dim_idx → traversal surfaces (steps, H, W)
        - 'dimension_stats': Statistics per dimension (mean, std, range)
        - 'correlations': Correlations with metadata (if provided)

    Example:
        >>> vae = OpportunityVAE(latent_dim=12)
        >>> surface = load_mobility_surface('london.npy')
        >>> metadata = {'urban_fraction': 0.9, 'avg_deprivation': 0.25}
        >>> analysis = analyze_latent_dimensions(vae, surface, metadata)
        >>> print(f"Dimension 0 stats: {analysis['dimension_stats'][0]}")
    """
    model.eval()
    device = next(model.parameters()).device

    # Ensure surfaces is (N, H, W)
    if isinstance(surfaces, np.ndarray):
        surfaces_np = surfaces
        if surfaces.ndim == 2:
            surfaces_np = surfaces[np.newaxis, :]  # (H, W) → (1, H, W)
    else:
        surfaces_np = surfaces.cpu().numpy()
        if surfaces_np.ndim == 2:
            surfaces_np = surfaces_np[np.newaxis, :]

    # Encode surfaces to get latent codes
    latent_codes = encode_surfaces(model, surfaces_np)  # (N, latent_dim)

    # Compute statistics per dimension
    dimension_stats = {}
    for dim in range(latent_codes.shape[1]):
        dim_values = latent_codes[:, dim]
        dimension_stats[dim] = {
            "mean": float(np.mean(dim_values)),
            "std": float(np.std(dim_values)),
            "min": float(np.min(dim_values)),
            "max": float(np.max(dim_values)),
            "median": float(np.median(dim_values)),
        }

    # Create traversals: vary each dimension while keeping others fixed
    # Use first surface as reference
    z_ref = latent_codes[0].copy()  # (latent_dim,)
    traversals = {}

    for dim in range(len(z_ref)):
        # Create range around reference value: [-2σ, +2σ]
        z_dim_range = np.linspace(-2.0, 2.0, n_traversal_steps)

        # Create latent codes for this dimension's traversal
        z_traversal = np.tile(z_ref, (n_traversal_steps, 1))  # (steps, latent_dim)
        z_traversal[:, dim] = z_dim_range  # Vary only this dimension

        # Decode to surfaces
        z_traversal_tensor = torch.from_numpy(z_traversal).float().to(device)
        with torch.no_grad():
            surfaces_traversal = model.decode(z_traversal_tensor)  # (steps, 1, H, W)

        surfaces_traversal = (
            surfaces_traversal.squeeze(1).cpu().numpy()
        )  # (steps, H, W)
        traversals[dim] = surfaces_traversal

    # Correlate with metadata if provided
    correlations = {}
    if surface_metadata is not None and len(surface_metadata) > 0:
        # For each metadata key, compute correlation with each latent dimension
        for meta_key, meta_values in surface_metadata.items():
            if isinstance(meta_values, (int, float)):
                # Single value - can't correlate
                continue
            if isinstance(meta_values, (list, np.ndarray)):
                meta_array = np.asarray(meta_values)
                if len(meta_array) == len(latent_codes):
                    # Compute correlation for each dimension
                    dim_correlations = {}
                    for dim in range(latent_codes.shape[1]):
                        corr = np.corrcoef(latent_codes[:, dim], meta_array)[0, 1]
                        dim_correlations[dim] = float(corr)
                    correlations[meta_key] = dim_correlations

    analysis = {
        "latent_codes": latent_codes,
        "traversals": traversals,
        "dimension_stats": dimension_stats,
        "correlations": correlations,
        "n_surfaces": len(latent_codes),
        "latent_dim": latent_codes.shape[1],
    }

    logger.info(
        f"Latent space analysis complete: {len(latent_codes)} surfaces, "
        f"{latent_codes.shape[1]} dimensions, "
        f"{len(traversals)} traversals generated"
    )

    return analysis


def generate_counterfactual(
    model: OpportunityVAE,
    source_surface: NDArray[np.float64],
    target_surface: NDArray[np.float64],
    intervention_dims: list[int] | None = None,
    intervention_strength: float = 1.0,
) -> tuple[NDArray[np.float64], dict]:
    """
    Generate counterfactual surface by transferring latent factors.

    Creates a "what if" scenario by taking a source surface and modifying
    specific latent dimensions to match a target surface. This simulates
    policy interventions by asking: "What if source had target's X?"

    Args:
        model: Trained OpportunityVAE model
        source_surface: Original surface (H, W)
        target_surface: Target surface to borrow factors from (H, W)
        intervention_dims: List of dimension indices to transfer from target
            If None, transfers all dimensions
        intervention_strength: Strength of intervention (0=source, 1=target)
            Can be >1 for amplified interventions

    Returns:
        Tuple of (counterfactual_surface, details):
        - counterfactual_surface: Generated surface (H, W)
        - details: Dict with source_code, target_code, intervened_code

    Example:
        >>> # "What if rural area had urban connectivity?"
        >>> vae = OpportunityVAE()
        >>> rural = load_surface('rural_region.npy')
        >>> urban = load_surface('london_urban.npy')
        >>> # Transfer dimension 3 (connectivity) from urban to rural
        >>> counterfactual, _ = generate_counterfactual(
        ...     vae, rural, urban, intervention_dims=[3], intervention_strength=1.0
        ... )
    """
    model.eval()

    # Encode both surfaces
    z_source = encode_surfaces(model, source_surface[np.newaxis, :])  # (1, latent_dim)
    z_target = encode_surfaces(model, target_surface[np.newaxis, :])  # (1, latent_dim)

    z_source = z_source[0]  # (latent_dim,)
    z_target = z_target[0]  # (latent_dim,)

    # Create intervened latent code
    z_intervened = z_source.copy()

    if intervention_dims is None:
        # Transfer all dimensions
        intervention_dims = list(range(len(z_source)))

    # Transfer specified dimensions
    for dim in intervention_dims:
        # Interpolate: z_new = z_source + strength * (z_target - z_source)
        z_intervened[dim] = z_source[dim] + intervention_strength * (
            z_target[dim] - z_source[dim]
        )

    # Decode intervened code
    device = next(model.parameters()).device
    z_intervened_tensor = torch.from_numpy(z_intervened).float().unsqueeze(0).to(device)

    with torch.no_grad():
        counterfactual = model.decode(z_intervened_tensor)  # (1, 1, H, W)

    counterfactual = counterfactual.squeeze().cpu().numpy()  # (H, W)

    details = {
        "source_code": z_source,
        "target_code": z_target,
        "intervened_code": z_intervened,
        "intervention_dims": intervention_dims,
        "intervention_strength": intervention_strength,
        "latent_changes": {
            dim: float(z_intervened[dim] - z_source[dim]) for dim in intervention_dims
        },
    }

    logger.info(
        f"Generated counterfactual: intervened on {len(intervention_dims)} dimensions "
        f"with strength {intervention_strength}"
    )

    return counterfactual, details


def compute_latent_distance_matrix(
    model: OpportunityVAE, surfaces: NDArray[np.float64]
) -> NDArray[np.float64]:
    """
    Compute pairwise distance matrix in latent space.

    Useful for clustering similar opportunity landscapes and identifying
    regions with similar underlying opportunity structures.

    Args:
        model: Trained OpportunityVAE model
        surfaces: Array of surfaces (N, H, W)

    Returns:
        Distance matrix (N, N) - Euclidean distances in latent space

    Example:
        >>> vae = OpportunityVAE()
        >>> surfaces = load_all_regional_surfaces()  # (100, 64, 64)
        >>> distances = compute_latent_distance_matrix(vae, surfaces)
        >>> # Find most similar regions
        >>> region_1 = 42
        >>> similar = np.argsort(distances[region_1])[1:6]  # Top 5 similar
    """
    # Encode all surfaces
    latent_codes = encode_surfaces(model, surfaces)  # (N, latent_dim)

    # Compute pairwise Euclidean distances
    # Using broadcasting: ||a - b||^2 = ||a||^2 + ||b||^2 - 2*a·b
    squared_norms = np.sum(latent_codes**2, axis=1, keepdims=True)  # (N, 1)
    # Ensure numerical stability by clipping negative values
    squared_distances = (
        squared_norms + squared_norms.T - 2 * latent_codes @ latent_codes.T
    )
    squared_distances = np.maximum(squared_distances, 0)  # Clip numerical errors
    distances = np.sqrt(squared_distances)

    return distances


def visualize_latent_space_2d(
    model: OpportunityVAE,
    surfaces: NDArray[np.float64],
    method: Literal["pca", "tsne", "umap"] = "pca",
    labels: NDArray | None = None,
) -> tuple[NDArray[np.float64], dict]:
    """
    Project latent space to 2D for visualization.

    Uses dimensionality reduction (PCA, t-SNE, or UMAP) to visualize
    high-dimensional latent codes in 2D. Useful for understanding the
    overall structure of the latent space.

    Args:
        model: Trained OpportunityVAE model
        surfaces: Array of surfaces (N, H, W)
        method: Dimensionality reduction method ('pca', 'tsne', 'umap')
        labels: Optional labels for coloring points (N,)

    Returns:
        Tuple of (coords_2d, metadata):
        - coords_2d: 2D coordinates (N, 2)
        - metadata: Dict with method info and variance explained (for PCA)

    Example:
        >>> vae = OpportunityVAE()
        >>> surfaces = load_surfaces()
        >>> labels = get_region_labels()  # urban/rural/mixed
        >>> coords_2d, meta = visualize_latent_space_2d(
        ...     vae, surfaces, method='tsne', labels=labels
        ... )
        >>> # Plot with matplotlib
        >>> plt.scatter(coords_2d[:, 0], coords_2d[:, 1], c=labels)
    """
    # Encode to latent space
    latent_codes = encode_surfaces(model, surfaces)  # (N, latent_dim)

    metadata = {"method": method, "n_samples": len(latent_codes)}

    if method == "pca":
        from sklearn.decomposition import PCA

        pca = PCA(n_components=2)
        coords_2d = pca.fit_transform(latent_codes)
        metadata["explained_variance_ratio"] = pca.explained_variance_ratio_.tolist()
        metadata["total_variance_explained"] = float(
            np.sum(pca.explained_variance_ratio_)
        )

    elif method == "tsne":
        from sklearn.manifold import TSNE

        tsne = TSNE(n_components=2, random_state=42)
        coords_2d = tsne.fit_transform(latent_codes)
        metadata["kl_divergence"] = float(tsne.kl_divergence_)

    elif method == "umap":
        try:
            import umap

            reducer = umap.UMAP(n_components=2, random_state=42)
            coords_2d = reducer.fit_transform(latent_codes)
        except ImportError:
            logger.warning("UMAP not installed, falling back to PCA")
            from sklearn.decomposition import PCA

            pca = PCA(n_components=2)
            coords_2d = pca.fit_transform(latent_codes)
            metadata["method"] = "pca (umap unavailable)"
            metadata["explained_variance_ratio"] = (
                pca.explained_variance_ratio_.tolist()
            )

    else:
        raise ValueError(f"Unknown method: {method}. Use 'pca', 'tsne', or 'umap'")

    logger.info(f"Projected latent space to 2D using {method}")

    return coords_2d, metadata
