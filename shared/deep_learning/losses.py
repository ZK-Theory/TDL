"""Reusable loss functions for TDA deep learning models.

VAELoss: currently duplicated in poverty_tda only; extracted here for reuse.
PersistenceLoss: penalises spurious topological features; useful when learning
    representations should be topologically consistent.
TopologicalFairnessLoss: for Paper 10 — penalises topological divergence
    between subgroup prediction-error distributions.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


class VAELoss(nn.Module):
    """Combined reconstruction + KL divergence loss for variational autoencoders.

    L = reconstruction_loss + beta * KL(q(z|x) || p(z))

    The beta parameter controls the weight of the KL term (beta-VAE formulation).
    Setting beta=1 recovers the standard ELBO.

    Args:
        beta: Weight of the KL divergence term. Values > 1 encourage
            disentangled latent representations.
        reconstruction: Loss type for reconstruction term. 'mse' for
            continuous data (persistence images); 'bce' for binary masks.
    """

    def __init__(
        self,
        beta: float = 1.0,
        reconstruction: str = "mse",
    ) -> None:
        super().__init__()
        if reconstruction not in {"mse", "bce"}:
            msg = f"reconstruction must be 'mse' or 'bce', got {reconstruction!r}"
            raise ValueError(msg)
        self.beta = beta
        self.reconstruction = reconstruction

    def forward(
        self,
        x_recon: Tensor,
        x_target: Tensor,
        mu: Tensor,
        logvar: Tensor,
    ) -> tuple[Tensor, Tensor, Tensor]:
        """Compute VAE loss.

        Args:
            x_recon: Reconstructed input from decoder. Shape (batch, *spatial).
            x_target: Original input. Same shape as x_recon.
            mu: Latent mean from encoder. Shape (batch, latent_dim).
            logvar: Log-variance from encoder. Shape (batch, latent_dim).

        Returns:
            Tuple of (total_loss, recon_loss, kl_loss), all scalar tensors.
        """
        if self.reconstruction == "mse":
            recon_loss = F.mse_loss(x_recon, x_target, reduction="mean")
        else:
            recon_loss = F.binary_cross_entropy(x_recon, x_target, reduction="mean")

        # KL divergence: -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())

        total_loss = recon_loss + self.beta * kl_loss
        return total_loss, recon_loss, kl_loss


class PersistenceLoss(nn.Module):
    """Penalise topologically spurious features in learned representations.

    Encourages a representation to preserve only features with persistence
    above a threshold, pushing short-lived features toward the diagonal.
    Useful when the downstream task should respect topological structure.

    This is a soft regulariser, not a differentiable TDA computation.
    For true differentiable persistence, use giotto-tda or TopologyLayer.

    Args:
        threshold: Minimum persistence (death - birth) to treat as signal.
            Features below threshold are penalised.
        weight: Loss weight when combining with a task loss.
    """

    def __init__(self, threshold: float = 0.1, weight: float = 0.01) -> None:
        super().__init__()
        self.threshold = threshold
        self.weight = weight

    def forward(self, birth: Tensor, death: Tensor) -> Tensor:
        """Compute persistence regularisation loss.

        Args:
            birth: Birth values of topological features. Shape (n_features,).
            death: Death values. Same shape as birth. May contain inf for
                infinite bars; these are excluded from the loss.

        Returns:
            Scalar loss penalising short-lived features.
        """
        finite_mask = torch.isfinite(death)
        if not finite_mask.any():
            return death.new_zeros(())

        persistence = (death - birth)[finite_mask]
        # Penalise features below threshold: ReLU(threshold - persistence)
        penalty = F.relu(self.threshold - persistence)
        return self.weight * penalty.mean()


class TopologicalFairnessLoss(nn.Module):
    """Penalise topological divergence between subgroup prediction-error distributions.

    For Paper 10 (topological fairness analysis): a differentiable training-time
    proxy ensuring a trajectory forecasting model's residuals have similar
    topological structure across demographic subgroups.

    The exact post-hoc evaluation uses Wasserstein distances between subgroup
    persistence diagrams (see trajectory_tda/validation/wasserstein_null_tests.py).

    Args:
        n_groups: Number of demographic subgroups.
        weight: Scaling factor for the fairness penalty.
    """

    def __init__(self, n_groups: int = 2, weight: float = 0.05) -> None:
        super().__init__()
        self.n_groups = n_groups
        self.weight = weight

    def forward(self, residuals: Tensor, group_labels: Tensor) -> Tensor:
        """Compute fairness penalty as variance in group-level error moments.

        Args:
            residuals: Prediction errors, shape (batch,) or (batch, output_dim).
            group_labels: Integer group membership, shape (batch,).

        Returns:
            Scalar fairness penalty.
        """
        group_means = []
        group_vars = []
        for g in range(self.n_groups):
            mask = group_labels == g
            if mask.sum() < 2:  # noqa: PLR2004
                continue
            g_res = residuals[mask]
            group_means.append(g_res.mean())
            group_vars.append(g_res.var())

        if len(group_means) < 2:  # noqa: PLR2004
            # Return a scalar zero to avoid shape (1,) broadcasting issues
            return residuals.new_zeros(())

        means = torch.stack(group_means)
        variances = torch.stack(group_vars)
        return self.weight * (means.var() + variances.var())
