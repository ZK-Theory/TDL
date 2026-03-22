"""Differentiable layers for learning on persistence diagrams.

Implements the Perslay framework (Carrière et al. 2020) and related
approaches for incorporating persistent homology into neural network
training. These layers are domain-agnostic — they consume persistence
diagrams and output fixed-dimensional feature vectors.

References:
    Carrière, M., Chazal, F., Ike, Y., Lacombe, T., Royer, M., & Umeda, Y. (2020).
    Perslay: A neural network layer for persistence diagrams and new graph
    topological signatures. AISTATS 2020.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import torch
import torch.nn as nn

if TYPE_CHECKING:
    from torch import Tensor

logger = logging.getLogger(__name__)


def _validate_diagram(diagram: Tensor) -> None:
    """Check diagram has shape (..., 2) with birth < death and finite values."""
    if diagram.ndim < 2 or diagram.shape[-1] != 2:  # noqa: PLR2004
        raise ValueError(f"Diagram must have shape (..., 2); got {diagram.shape}")

    # Enforce finite entries; infinite deaths should be clipped beforehand.
    if not torch.isfinite(diagram).all():
        raise ValueError("Diagram entries must be finite; clip infinite death values before calling.")

    # Enforce birth < death for all points.
    birth = diagram[..., 0]
    death = diagram[..., 1]
    if not (birth < death).all():
        raise ValueError("All persistence points must satisfy birth < death.")
class PersLayWeight(nn.Module):
    """Learnable weight function for Perslay aggregation.

    Maps each (birth, death) pair to a scalar weight, downweighting
    short-lived (noisy) features and upweighting significant ones.

    Args:
        hidden_dim: Width of the MLP computing weights.
    """

    def __init__(self, hidden_dim: int = 32) -> None:
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, diagram: Tensor) -> Tensor:
        """Compute per-point weights.

        Args:
            diagram: Persistence diagram, shape (batch, n_points, 2).

        Returns:
            Weights, shape (batch, n_points, 1).
        """
        _validate_diagram(diagram)
        return self.mlp(diagram)


class GaussianPersLayer(nn.Module):
    """Perslay with Gaussian kernel feature map.

    Each persistence point is embedded via a Gaussian kernel centred
    at learnable centres, then aggregated by sum. This is equivalent
    to a differentiable persistence image.

    Args:
        n_centres: Number of Gaussian centres (output dimension per diagram).
        sigma: Initial bandwidth of Gaussian kernels.
        learn_sigma: Whether to learn sigma jointly with centres.
    """

    def __init__(
        self,
        n_centres: int = 64,
        sigma: float = 0.1,
        learn_sigma: bool = True,
    ) -> None:
        super().__init__()
        self.n_centres = n_centres
        # Centres initialised on [0,1]^2 grid
        grid = torch.rand(n_centres, 2)
        self.centres = nn.Parameter(grid)
        log_sigma = torch.tensor(math.log(sigma))
        if learn_sigma:
            self.log_sigma = nn.Parameter(log_sigma)
        else:
            self.register_buffer("log_sigma", log_sigma)

    def forward(self, diagram: Tensor) -> Tensor:
        """Embed a batch of persistence diagrams.

        Args:
            diagram: Shape (batch, n_points, 2). Infinite death values
                should be clipped before passing in.

        Returns:
            Feature vectors, shape (batch, n_centres).
        """
        _validate_diagram(diagram)
        sigma = self.log_sigma.exp()
        # diagram: (batch, n_pts, 2); centres: (n_centres, 2)
        diff = diagram.unsqueeze(2) - self.centres.unsqueeze(0).unsqueeze(0)
        # (batch, n_pts, n_centres)
        kernel = torch.exp(-diff.pow(2).sum(-1) / (2 * sigma**2))
        return kernel.sum(dim=1)  # (batch, n_centres)


class RationalHatPersLayer(nn.Module):
    """Perslay with rational hat (tent) feature map.

    Computationally lighter than Gaussian kernel; works well when
    persistence diagrams have many short-lived features to suppress.

    Args:
        n_centres: Number of output features.
        r: Radius of the hat function.
    """

    def __init__(self, n_centres: int = 32, r: float = 0.1) -> None:
        super().__init__()
        self.n_centres = n_centres
        self.centres = nn.Parameter(torch.rand(n_centres, 2))
        self.r = nn.Parameter(torch.tensor(r))

    def forward(self, diagram: Tensor) -> Tensor:
        """Embed a batch of persistence diagrams.

        Args:
            diagram: Shape (batch, n_points, 2).

        Returns:
            Feature vectors, shape (batch, n_centres).
        """
        _validate_diagram(diagram)
        diff = diagram.unsqueeze(2) - self.centres.unsqueeze(0).unsqueeze(0)
        dist = diff.norm(dim=-1)  # (batch, n_pts, n_centres)
        r = self.r.abs() + 1e-6
        hat = torch.clamp(1.0 - dist / r, min=0.0)
        return hat.sum(dim=1)  # (batch, n_centres)


class LifetimeWeightedSum(nn.Module):
    """Aggregate persistence diagram by sum weighted by feature lifetime.

    A simple non-parametric baseline: represents each diagram as a
    weighted sum of (birth, death, lifetime) feature vectors.

    Args:
        output_dim: Projection dimension after weighted sum.
    """

    def __init__(self, output_dim: int = 32) -> None:
        super().__init__()
        self.proj = nn.Linear(3, output_dim)

    def forward(self, diagram: Tensor) -> Tensor:
        """Aggregate diagram into fixed-size vector.

        Args:
            diagram: Shape (batch, n_points, 2).

        Returns:
            Feature vectors, shape (batch, output_dim).
        """
        _validate_diagram(diagram)
        birth = diagram[..., 0]
        death = diagram[..., 1]
        lifetime = (death - birth).unsqueeze(-1)
        # (batch, n_pts, 3): birth, death, lifetime
        augmented = torch.cat([diagram, lifetime], dim=-1)
        # Weight each point by its lifetime before summing
        weighted = augmented * lifetime
        summed = weighted.sum(dim=1)  # (batch, 3)
        return self.proj(summed)  # (batch, output_dim)


class PersFormerLayer(nn.Module):
    """Transformer attention over persistence diagram points (PersFormer-style).

    Treats each persistence point as a token and applies multi-head
    self-attention, enabling the model to learn cross-feature interactions
    within a diagram. Based on the PersFormer approach (Zhao et al. 2023).

    Args:
        embed_dim: Dimension to project (birth, death) pairs into.
        num_heads: Number of attention heads.
        dropout: Dropout on attention weights.
    """

    def __init__(
        self,
        embed_dim: int = 64,
        num_heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Linear(2, embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, diagram: Tensor) -> Tensor:
        """Apply attention over persistence points.

        Args:
            diagram: Shape (batch, n_points, 2).

        Returns:
            Aggregated feature vector, shape (batch, embed_dim).
        """
        _validate_diagram(diagram)
        x = self.input_proj(diagram)  # (batch, n_pts, embed_dim)
        attn_out, _ = self.attn(x, x, x)
        x = self.norm(x + attn_out)
        x = self.out_proj(x)
        return x.mean(dim=1)  # (batch, embed_dim) — mean-pool over points
