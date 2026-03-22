"""Utilities for combinatorial complex neural networks (CCNNs).

Provides the data structures and helper functions for representing
multi-level social data as cell complexes for use with TopoModelX:

    0-cells: individuals
    1-cells: households (boundary = pair of individuals)
    2-cells: neighbourhoods (e.g., LSOA/MSOA)
    3-cells: local authorities

TopoModelX (Hajij et al. 2023) provides the CCNN message-passing
implementations. This module handles data preparation.

References:
    Hajij, M., et al. (2023). Combinatorial Complexes: Bridging the gap
    between Cell Complexes and Hypergraphs. NeurIPS 2023 TDL Workshop.

    https://github.com/pyt-team/TopoModelX
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

try:
    import topomodelx  # noqa: F401

    HAS_TOPOMODELX = True
except ImportError:
    HAS_TOPOMODELX = False
    logger.info(
        "TopoModelX not available. Install with: pip install topomodelx. "
        "Combinatorial complex neural networks require this dependency."
    )


@dataclass
class SocialCellComplex:
    """Multi-level social data represented as a combinatorial complex.

    Designed for the UK household/neighbourhood/LA structure in Paper 9.
    Each level is optional; start with 0-cells and 1-cells, then extend.

    Attributes:
        individual_features: Node features for 0-cells (individuals).
            Shape (n_individuals, individual_feature_dim).
        household_features: Features for 1-cells (households).
            Shape (n_households, household_feature_dim). Optional.
        neighbourhood_features: Features for 2-cells (LSOAs/MSOAs).
            Shape (n_neighbourhoods, neighbourhood_feature_dim). Optional.
        la_features: Features for 3-cells (Local Authorities).
            Shape (n_las, la_feature_dim). Optional.
        individual_to_household: Membership map from individuals to households.
            Shape (n_individuals,) with household index per individual.
        individual_to_neighbourhood: Membership map to neighbourhoods.
            Shape (n_individuals,) with neighbourhood index. Optional.
        neighbourhood_to_la: Membership map from neighbourhoods to LAs.
            Shape (n_neighbourhoods,) with LA index. Optional.
    """

    individual_features: NDArray[np.float32]
    household_features: NDArray[np.float32] | None = None
    neighbourhood_features: NDArray[np.float32] | None = None
    la_features: NDArray[np.float32] | None = None
    individual_to_household: NDArray[np.int64] | None = None
    individual_to_neighbourhood: NDArray[np.int64] | None = None
    neighbourhood_to_la: NDArray[np.int64] | None = None
    _metadata: dict = field(default_factory=dict)

    @property
    def n_individuals(self) -> int:
        return len(self.individual_features)

    @property
    def n_households(self) -> int:
        return len(self.household_features) if self.household_features is not None else 0

    @property
    def n_levels(self) -> int:
        """Number of complex levels with data."""
        levels = 1  # always have individuals
        if self.household_features is not None:
            levels += 1
        if self.neighbourhood_features is not None:
            levels += 1
        if self.la_features is not None:
            levels += 1
        return levels

    def validate(self) -> None:
        """Check dimensional consistency of membership maps.

        Raises:
            ValueError: If any membership array has wrong shape.
        """
        if self.individual_to_household is not None and len(self.individual_to_household) != self.n_individuals:
            raise ValueError(
                f"individual_to_household length {len(self.individual_to_household)} "
                f"does not match n_individuals {self.n_individuals}"
            )
        if self.individual_to_neighbourhood is not None and len(self.individual_to_neighbourhood) != self.n_individuals:
            raise ValueError(
                f"individual_to_neighbourhood length {len(self.individual_to_neighbourhood)} "
                f"does not match n_individuals {self.n_individuals}"
            )
        if (
            self.neighbourhood_to_la is not None
            and self.neighbourhood_features is not None
            and len(self.neighbourhood_to_la) != len(self.neighbourhood_features)
        ):
            raise ValueError("neighbourhood_to_la length does not match n_neighbourhoods")


def build_incidence_matrix(
    membership: NDArray[np.int64],
    n_lower: int,
    n_upper: int,
) -> NDArray[np.float32]:
    """Build an incidence matrix B from a membership array.

    Entry B[i, j] = 1 if lower-level cell i belongs to upper-level cell j.

    Used to construct the boundary matrices required by TopoModelX CCNN
    message-passing between adjacent complex levels.

    Args:
        membership: Array of shape (n_lower,) where entry i is the
            upper-level index that lower-cell i belongs to.
        n_lower: Number of lower-level cells (rows).
        n_upper: Number of upper-level cells (columns).

    Returns:
        Dense incidence matrix, shape (n_lower, n_upper), dtype float32.
    """
    B = np.zeros((n_lower, n_upper), dtype=np.float32)
    for lower_idx, upper_idx in enumerate(membership):
        if 0 <= upper_idx < n_upper:
            B[lower_idx, upper_idx] = 1.0
    return B


def complex_to_topomodelx(
    complex: SocialCellComplex,
) -> dict:
    """Convert a SocialCellComplex to TopoModelX input format.

    Returns a dict of tensors suitable for passing to a TopoModelX CCNN.
    Requires TopoModelX to be installed.

    Args:
        complex: A validated SocialCellComplex.

    Returns:
        Dict with keys 'x_0', 'x_1', 'x_2', 'x_3' (cell features at each
        level, as available) and 'B_1', 'B_2', 'B_3' (incidence matrices
        between adjacent levels, as available).

    Raises:
        ImportError: If TopoModelX is not installed.
    """
    if not HAS_TOPOMODELX:
        raise ImportError("TopoModelX is required. Install with: pip install topomodelx")

    import torch

    complex.validate()
    result: dict = {}

    result["x_0"] = torch.tensor(complex.individual_features, dtype=torch.float32)

    if complex.household_features is not None:
        result["x_1"] = torch.tensor(complex.household_features, dtype=torch.float32)
        if complex.individual_to_household is not None:
            B1 = build_incidence_matrix(
                complex.individual_to_household,
                complex.n_individuals,
                complex.n_households,
            )
            result["B_1"] = torch.tensor(B1, dtype=torch.float32)

    if complex.neighbourhood_features is not None:
        result["x_2"] = torch.tensor(complex.neighbourhood_features, dtype=torch.float32)
        if complex.individual_to_neighbourhood is not None and complex.household_features is not None:
            # Neighbourhood incidence: household → neighbourhood
            # Derive from individual memberships
            n_hh = complex.n_households
            n_neigh = len(complex.neighbourhood_features)
            hh_to_neigh = np.full(n_hh, -1, dtype=np.int64)
            individual_to_household = (
                complex.individual_to_household
                if complex.individual_to_household is not None
                else []
            )
            for ind, hh in enumerate(individual_to_household):
                neigh = complex.individual_to_neighbourhood[ind]
                hh_to_neigh[hh] = neigh
            B2 = build_incidence_matrix(hh_to_neigh, n_hh, n_neigh)
            result["B_2"] = torch.tensor(B2, dtype=torch.float32)

    if complex.la_features is not None and complex.neighbourhood_to_la is not None:
        result["x_3"] = torch.tensor(complex.la_features, dtype=torch.float32)

        if complex.neighbourhood_features is None:
            raise ValueError(
                "Cannot construct B_3: 'neighbourhood_features' must be provided when "
                "'neighbourhood_to_la' is set."
            )

        n_neigh = len(complex.neighbourhood_features)
        n_la = len(complex.la_features)

        # Optional consistency check between features and mapping
        if len(complex.neighbourhood_to_la) != n_neigh:
            raise ValueError(
                "Length mismatch between 'neighbourhood_features' "
                f"({n_neigh}) and 'neighbourhood_to_la' "
                f"({len(complex.neighbourhood_to_la)})."
            )
        B3 = build_incidence_matrix(complex.neighbourhood_to_la, n_neigh, n_la)
        result["B_3"] = torch.tensor(B3, dtype=torch.float32)

    return result
