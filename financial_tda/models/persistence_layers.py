"""
Learnable persistence diagram vectorization layers.

This module implements Perslay-style neural network layers for learning
directly on persistence diagrams. Based on Carrière et al. (2020) architecture
with DeepSet-based permutation-invariant transformations.

The Perslay architecture vectorizes persistence diagrams via:
    Perslay(D) = ρ(perm_op(φ(p) · w(p) for p in D))

Where:
    - D: persistence diagram (set of (birth, death) points)
    - w: optional weight function (learnable importance scores)
    - φ: transformation function (maps points to vectors)
    - perm_op: permutation-invariant aggregation (sum/mean/max)
    - ρ: optional postprocessing MLP

References:
    Carrière, M., Chazal, F., Ike, Y., Lacombe, T., Royer, M., & Umeda, Y. (2020).
    PersLay: A Neural Network Layer for Persistence Diagrams and New Graph
    Topological Signatures. AISTATS 2020.

    Zaheer, M., et al. (2017). Deep Sets. NeurIPS 2017.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import torch
import torch.nn as nn
from torch import Tensor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type aliases
AggregationType = Literal["sum", "mean", "max"]


def pad_diagrams(
    diagrams_list: list[Tensor],
    max_points: int | None = None,
) -> tuple[Tensor, Tensor]:
    """
    Pad variable-length persistence diagrams to uniform batch size.

    Converts list of persistence diagrams with varying numbers of points
    to a padded tensor with boolean mask for valid points.

    Args:
        diagrams_list: List of persistence diagram tensors, each with shape
            (n_points, 2) where columns are [birth, death].
        max_points: Maximum number of points to pad to. If None, uses the
            maximum number of points across all diagrams in the batch.

    Returns:
        Tuple of (padded_diagrams, mask):
            - padded_diagrams: Tensor of shape (batch_size, max_points, 2)
            - mask: Boolean tensor of shape (batch_size, max_points) where
              True indicates valid points, False indicates padding.

    Raises:
        ValueError: If diagrams_list is empty or contains invalid tensors.

    Examples:
        >>> import torch
        >>> diag1 = torch.tensor([[0.1, 0.5], [0.2, 0.8]])  # 2 points
        >>> diag2 = torch.tensor([[0.1, 0.3]])  # 1 point
        >>> padded, mask = pad_diagrams([diag1, diag2])
        >>> print(padded.shape)  # (2, 2, 2)
        >>> print(mask)  # [[True, True], [True, False]]
    """
    if not diagrams_list:
        raise ValueError("diagrams_list cannot be empty")

    batch_size = len(diagrams_list)

    # Validate input tensors
    for i, diag in enumerate(diagrams_list):
        if not isinstance(diag, Tensor):
            raise ValueError(f"Diagram {i} must be a torch.Tensor")
        if diag.ndim != 2 or diag.shape[1] != 2:
            raise ValueError(
                f"Diagram {i} must have shape (n_points, 2), got {diag.shape}"
            )

    # Determine max_points
    if max_points is None:
        max_points = max(d.shape[0] for d in diagrams_list)

    if max_points == 0:
        raise ValueError("All diagrams are empty")

    # Create padded tensor and mask
    device = diagrams_list[0].device
    dtype = diagrams_list[0].dtype

    padded = torch.zeros(batch_size, max_points, 2, dtype=dtype, device=device)
    mask = torch.zeros(batch_size, max_points, dtype=torch.bool, device=device)

    for i, diag in enumerate(diagrams_list):
        n_points = diag.shape[0]
        if n_points > 0:
            padded[i, :n_points] = diag
            mask[i, :n_points] = True

    logger.debug(
        "Padded %d diagrams to max_points=%d (device=%s)",
        batch_size,
        max_points,
        device,
    )

    return padded, mask


class DeepSetPhi(nn.Module):
    """
    DeepSet-based transformation function for persistence diagrams.

    Applies the same MLP independently to each point in the persistence diagram,
    implementing a permutation-equivariant transformation φ(p). This is the core
    component of the DeepSet architecture (Zaheer et al., 2017).

    The MLP transforms each (birth, death) pair to a higher-dimensional embedding,
    enabling the network to learn complex features from topological structure.

    Args:
        input_dim: Dimension of input points (2 for birth-death pairs).
        hidden_dims: List of hidden layer dimensions for the MLP.
            Default [64, 32] creates a two-layer network.
        output_dim: Dimension of output embedding per point. Default 16.
        activation: Activation function to use between layers. Default 'relu'.
        dropout: Dropout probability for regularization. Default 0.0 (no dropout).

    Attributes:
        output_dim: Dimension of the output embedding (for downstream layers).

    Examples:
        >>> phi = DeepSetPhi(input_dim=2, hidden_dims=[64, 32], output_dim=16)
        >>> diagrams = torch.randn(8, 50, 2)  # batch=8, max_points=50
        >>> mask = torch.ones(8, 50, dtype=torch.bool)
        >>> features = phi(diagrams, mask)  # (8, 50, 16)
    """

    def __init__(
        self,
        input_dim: int = 2,
        hidden_dims: list[int] | None = None,
        output_dim: int = 16,
        activation: str = "relu",
        dropout: float = 0.0,
    ):
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [64, 32]

        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.output_dim = output_dim

        # Build MLP layers
        layers = []
        dims = [input_dim] + hidden_dims + [output_dim]

        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))

            # Add activation and dropout except for final layer
            if i < len(dims) - 2:
                if activation == "relu":
                    layers.append(nn.ReLU())
                elif activation == "tanh":
                    layers.append(nn.Tanh())
                elif activation == "elu":
                    layers.append(nn.ELU())
                else:
                    raise ValueError(f"Unknown activation: {activation}")

                if dropout > 0:
                    layers.append(nn.Dropout(dropout))

        self.mlp = nn.Sequential(*layers)

        logger.debug(
            "Initialized DeepSetPhi: %d -> %s -> %d (activation=%s, dropout=%.2f)",
            input_dim,
            hidden_dims,
            output_dim,
            activation,
            dropout,
        )

    def forward(self, diagrams: Tensor, mask: Tensor) -> Tensor:
        """
        Apply MLP transformation to each point in persistence diagrams.

        Args:
            diagrams: Padded persistence diagrams of shape
                (batch_size, max_points, input_dim).
            mask: Boolean mask of shape (batch_size, max_points) indicating
                valid points (True) vs padding (False).

        Returns:
            Transformed features of shape (batch_size, max_points, output_dim).
            Masked (padded) positions will have zero features.
        """
        # Apply MLP to all points (including padding)
        features = self.mlp(diagrams)  # (batch, max_points, output_dim)

        # Zero out features for padded points
        features = features * mask.unsqueeze(-1).float()

        return features


class PowerWeight(nn.Module):
    """
    Learnable power-law weight function for persistence diagrams.

    Assigns importance weights to persistence diagram points based on their
    persistence (lifetime): w(p) = c · persistence^α

    Where:
        - persistence = death - birth
        - c: learnable coefficient parameter
        - α: fixed power parameter

    Points with longer persistence (more prominent topological features)
    receive higher weights. The learnable coefficient allows the network
    to adjust the importance of persistence.

    Args:
        power: Fixed power parameter α. Default 1.0 (linear weighting).
        init_coeff: Initial value for learnable coefficient c. Default 1.0.

    Examples:
        >>> weight = PowerWeight(power=1.0, init_coeff=1.0)
        >>> diagrams = torch.tensor([[[0.1, 0.5], [0.2, 0.9]]])  # (1, 2, 2)
        >>> weights = weight(diagrams)  # (1, 2)
        >>> print(weights)  # [[0.4, 0.7]] (approximately, scaled by coefficient)
    """

    def __init__(self, power: float = 1.0, init_coeff: float = 1.0):
        super().__init__()

        self.power = power
        self.coefficient = nn.Parameter(torch.tensor(init_coeff))

        logger.debug(
            "Initialized PowerWeight: power=%.2f, init_coeff=%.2f",
            power,
            init_coeff,
        )

    def forward(self, diagrams: Tensor) -> Tensor:
        """
        Compute power-law weights for persistence diagram points.

        Args:
            diagrams: Persistence diagrams of shape (batch_size, max_points, 2)
                where last dimension is [birth, death].

        Returns:
            Weights of shape (batch_size, max_points).
        """
        # Compute persistence: death - birth
        persistence = diagrams[..., 1] - diagrams[..., 0]

        # Avoid negative persistence (numerical issues)
        persistence = torch.clamp(persistence, min=0.0)

        # Compute weights: c * persistence^power
        weights = self.coefficient * (persistence**self.power)

        return weights


class Perslay(nn.Module):
    """
    Perslay layer for learning on persistence diagrams.

    Implements the Perslay architecture (Carrière et al., 2020):
        Perslay(D) = ρ(perm_op(φ(p) · w(p) for p in D))

    This layer vectorizes variable-length persistence diagrams into fixed-size
    embeddings using learnable transformations and permutation-invariant
    aggregation.

    Args:
        phi: Transformation function module (e.g., DeepSetPhi) that maps
            each point to a feature vector.
        weight: Optional weight function module (e.g., PowerWeight) for
            learnable importance weighting. If None, all points weighted equally.
        perm_op: Permutation-invariant aggregation operation. Options:
            - "sum": Sum over all points (default)
            - "mean": Mean over valid (non-padded) points
            - "max": Element-wise max over all points
        rho: Optional postprocessing module (e.g., nn.Linear) applied after
            aggregation. If None, uses identity (no postprocessing).

    Attributes:
        output_dim: Dimension of the output embedding (from phi.output_dim).

    Examples:
        >>> phi = DeepSetPhi(input_dim=2, output_dim=16)
        >>> weight = PowerWeight(power=1.0)
        >>> perslay = Perslay(phi=phi, weight=weight, perm_op="mean")
        >>> # Process batch of diagrams with variable lengths
        >>> diag1 = torch.randn(50, 2)  # 50 points
        >>> diag2 = torch.randn(30, 2)  # 30 points
        >>> embeddings = perslay([diag1, diag2])  # (2, 16)
    """

    def __init__(
        self,
        phi: nn.Module,
        weight: nn.Module | None = None,
        perm_op: AggregationType = "sum",
        rho: nn.Module | None = None,
    ):
        super().__init__()

        if not hasattr(phi, "output_dim"):
            raise ValueError("phi module must have output_dim attribute")

        if perm_op not in {"sum", "mean", "max"}:
            raise ValueError(f"Invalid perm_op: {perm_op}. Use 'sum', 'mean', or 'max'")

        self.phi = phi
        self.weight = weight
        self.perm_op = perm_op
        self.rho = rho if rho is not None else nn.Identity()

        self.output_dim = phi.output_dim

        logger.debug(
            "Initialized Perslay: output_dim=%d, perm_op=%s, weight=%s, rho=%s",
            self.output_dim,
            perm_op,
            weight is not None,
            not isinstance(self.rho, nn.Identity),
        )

    def forward(self, diagrams_list: list[Tensor]) -> Tensor:
        """
        Vectorize persistence diagrams to fixed-size embeddings.

        Args:
            diagrams_list: List of persistence diagram tensors, each with shape
                (n_points, 2) where columns are [birth, death]. Diagrams can
                have different numbers of points.

        Returns:
            Embeddings of shape (batch_size, output_dim).

        Raises:
            ValueError: If diagrams_list is empty or contains invalid diagrams.
        """
        # Pad diagrams and create mask
        diagrams, mask = pad_diagrams(diagrams_list)  # (batch, max_points, 2)

        # Apply transformation φ to each point
        features = self.phi(diagrams, mask)  # (batch, max_points, output_dim)

        # Apply optional weight function w
        if self.weight is not None:
            weights = self.weight(diagrams)  # (batch, max_points)
            # Broadcast weights and apply
            features = features * weights.unsqueeze(-1)

        # Zero out padded positions (redundant with phi masking, but ensures
        # correctness)
        features = features * mask.unsqueeze(-1).float()

        # Permutation-invariant aggregation
        if self.perm_op == "sum":
            aggregated = features.sum(dim=1)  # (batch, output_dim)

        elif self.perm_op == "mean":
            # Mean over valid points only
            num_valid = mask.sum(dim=1, keepdim=True).float()  # (batch, 1)
            # Avoid division by zero for empty diagrams
            num_valid = torch.clamp(num_valid, min=1.0)
            aggregated = features.sum(dim=1) / num_valid  # (batch, output_dim)

        elif self.perm_op == "max":
            # Set padded positions to -inf before max
            features_masked = features.clone()
            features_masked[~mask] = float("-inf")
            aggregated = features_masked.max(dim=1)[0]  # (batch, output_dim)
            # Handle case where all points are padding (max returns -inf)
            aggregated = torch.where(
                torch.isinf(aggregated),
                torch.zeros_like(aggregated),
                aggregated,
            )

        else:
            raise RuntimeError(f"Unexpected perm_op: {self.perm_op}")

        # Apply optional postprocessing ρ
        output = self.rho(aggregated)

        return output


def create_perslay(
    input_dim: int = 2,
    hidden_dims: list[int] | None = None,
    output_dim: int = 16,
    use_weight: bool = False,
    weight_power: float = 1.0,
    perm_op: AggregationType = "mean",
    use_postprocessing: bool = False,
    postprocessing_dim: int | None = None,
    activation: str = "relu",
    dropout: float = 0.0,
) -> Perslay:
    """
    Factory function to create a Perslay layer with common configurations.

    This convenience function simplifies creation of Perslay layers with
    standard architectures for persistence diagram learning.

    Args:
        input_dim: Dimension of input points (2 for birth-death pairs).
        hidden_dims: Hidden layer dimensions for DeepSetPhi MLP.
            Default [64, 32].
        output_dim: Dimension of Perslay output embedding. Default 16.
        use_weight: Whether to use PowerWeight for learnable importance.
            Default False.
        weight_power: Power parameter for PowerWeight. Default 1.0.
        perm_op: Aggregation operation ('sum', 'mean', 'max'). Default 'mean'.
        use_postprocessing: Whether to add linear postprocessing layer ρ.
            Default False.
        postprocessing_dim: Output dimension of postprocessing layer.
            If None, uses output_dim (no dimension change). Only used if
            use_postprocessing=True.
        activation: Activation function for DeepSetPhi. Default 'relu'.
        dropout: Dropout probability for DeepSetPhi. Default 0.0.

    Returns:
        Configured Perslay layer ready for training.

    Examples:
        >>> # Simple Perslay with mean aggregation
        >>> perslay = create_perslay(output_dim=32, perm_op="mean")
        >>>
        >>> # Perslay with learnable weights and postprocessing
        >>> perslay = create_perslay(
        ...     output_dim=64,
        ...     use_weight=True,
        ...     weight_power=2.0,
        ...     use_postprocessing=True,
        ...     postprocessing_dim=32
        ... )
    """
    if hidden_dims is None:
        hidden_dims = [64, 32]

    # Create transformation function φ
    phi = DeepSetPhi(
        input_dim=input_dim,
        hidden_dims=hidden_dims,
        output_dim=output_dim,
        activation=activation,
        dropout=dropout,
    )

    # Create optional weight function w
    weight = PowerWeight(power=weight_power) if use_weight else None

    # Create optional postprocessing ρ
    rho = None
    if use_postprocessing:
        if postprocessing_dim is None:
            postprocessing_dim = output_dim
        rho = nn.Linear(output_dim, postprocessing_dim)

    # Create Perslay layer
    perslay_layer = Perslay(phi=phi, weight=weight, perm_op=perm_op, rho=rho)

    logger.info(
        "Created Perslay layer: output_dim=%d, use_weight=%s, perm_op=%s",
        output_dim,
        use_weight,
        perm_op,
    )

    return perslay_layer
