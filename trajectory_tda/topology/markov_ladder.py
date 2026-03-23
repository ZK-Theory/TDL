"""Markov memory ladder null test for trajectory topology.

Tests whether observed employment trajectories exhibit more topological
complexity than would be expected under a Markov-1 null model, by
comparing persistence diagrams of observed vs. null-simulated trajectory
clouds (Paper 1).

The 'ladder' metaphor: each rung tests a higher-order Markov model
(Markov-1, Markov-2, ...) to identify at which order the null becomes
indistinguishable from observed topology — the Markov memory horizon.

Pipeline:
    1. Compute persistence diagram of observed n-gram PCA embedding.
    2. Simulate N null trajectories from the fitted Markov-k transition matrix.
    3. Embed null trajectories in the same PCA coordinate system.
    4. Compute persistence diagram of each null cloud.
    5. Compare observed vs. null using Wasserstein distance (not total persistence).
       See wasserstein_null_tests.py for the upgraded Stage 0 test statistic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class MarkovLadderResult:
    """Results from a single rung of the Markov memory ladder test.

    Attributes:
        markov_order: The Markov order tested (1, 2, ...).
        observed_total_persistence: Scalar total persistence of observed diagram.
        null_distribution: Total persistence values from null simulations.
        p_value: Fraction of nulls exceeding observed (one-sided, lower tail).
        z_score: Standardised effect size vs. null distribution.
        n_null_simulations: Number of null trajectories simulated.
        homology_dimension: Homology dimension the test was run on.
    """

    markov_order: int
    observed_total_persistence: float
    null_distribution: NDArray[np.float64]
    p_value: float
    z_score: float
    n_null_simulations: int
    homology_dimension: int
    wasserstein_p_value: float | None = None  # Set by wasserstein_null_tests.py


def fit_markov_transition_matrix(
    trajectories: list[list[int]],
    n_states: int,
    order: int = 1,
) -> NDArray[np.float64]:
    """Estimate transition matrix from observed state sequences.

    Args:
        trajectories: List of integer state sequences (one per individual).
        n_states: Total number of distinct states.
        order: Markov order. order=1 uses single-step transitions;
            order=2 uses (state_t-1, state_t) → state_t+1 pairs.
            Currently only order=1 is implemented; higher orders via
            n-gram encoding.

    Returns:
        Row-stochastic transition matrix, shape (n_states, n_states).
        Entry [i, j] is the probability of transitioning from state i to j.

    Raises:
        NotImplementedError: For order > 1 (use n-gram encoding instead).
    """
    if order != 1:
        raise NotImplementedError(
            "Higher-order Markov fitting uses n-gram PCA encoding. " "See trajectory_tda/data/ for n-gram preparation."
        )

    counts = np.zeros((n_states, n_states), dtype=np.float64)
    for traj in trajectories:
        for t in range(len(traj) - 1):
            s_from, s_to = traj[t], traj[t + 1]
            if 0 <= s_from < n_states and 0 <= s_to < n_states:
                counts[s_from, s_to] += 1

    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1, row_sums)  # avoid divide-by-zero
    return counts / row_sums


def simulate_markov_trajectories(
    transition_matrix: NDArray[np.float64],
    initial_distribution: NDArray[np.float64],
    n_trajectories: int,
    length: int,
    rng: np.random.Generator | None = None,
) -> list[list[int]]:
    """Simulate trajectories from a Markov transition matrix.

    Args:
        transition_matrix: Row-stochastic matrix, shape (n_states, n_states).
        initial_distribution: Starting state distribution, shape (n_states,).
        n_trajectories: Number of trajectories to simulate.
        length: Length of each trajectory (number of time steps).
        rng: Random number generator for reproducibility.

    Returns:
        List of simulated state sequences, each of length `length`.
    """
    if rng is None:
        rng = np.random.default_rng()

    n_states = transition_matrix.shape[0]
    trajectories = []

    for _ in range(n_trajectories):
        states = [int(rng.choice(n_states, p=initial_distribution))]
        for _ in range(length - 1):
            current = states[-1]
            next_state = int(rng.choice(n_states, p=transition_matrix[current]))
            states.append(next_state)
        trajectories.append(states)

    return trajectories


def compute_total_persistence(
    diagram: NDArray[np.float64],
    dimension: int = 1,
) -> float:
    """Compute total persistence (sum of lifetimes) for a given dimension.

    This is the scalar test statistic used in the original Paper 1 analysis.
    Stage 0 upgrade: replace with Wasserstein distance via wasserstein_null_tests.py.

    Args:
        diagram: Persistence diagram as (n_pairs, 3) array with
            columns (dimension, birth, death). Infinite deaths are excluded.
        dimension: Homology dimension to summarise.

    Returns:
        Sum of (death - birth) for all finite pairs in the given dimension.
    """
    dim_mask = diagram[:, 0] == dimension
    pairs = diagram[dim_mask]
    finite_mask = np.isfinite(pairs[:, 2])
    if not finite_mask.any():
        return 0.0
    lifetimes = pairs[finite_mask, 2] - pairs[finite_mask, 1]
    return float(lifetimes.sum())


class MarkovLadderTest:
    """Run the Markov memory ladder test on a trajectory embedding.

    Compares the topological complexity of the observed trajectory cloud
    to that of simulated Markov-k null clouds, at each order k.

    Args:
        n_null_simulations: Number of null trajectories to simulate per rung.
        max_filtration: Maximum edge length for Vietoris-Rips filtration.
        n_landmarks: Landmarks for witness complex approximation.
            None uses all points (slower but exact).
        homology_dim: Homology dimension to test (1 = loops).
        random_seed: Seed for reproducibility.
    """

    def __init__(
        self,
        n_null_simulations: int = 1000,
        max_filtration: float = 2.0,
        n_landmarks: int | None = 500,
        homology_dim: int = 1,
        random_seed: int = 42,
    ) -> None:
        self.n_null_simulations = n_null_simulations
        self.max_filtration = max_filtration
        self.n_landmarks = n_landmarks
        self.homology_dim = homology_dim
        self.rng = np.random.default_rng(random_seed)

    def _compute_diagram(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """Compute persistence diagram via Ripser.

        Args:
            points: Point cloud, shape (n_points, n_dims).

        Returns:
            Persistence diagram array, shape (n_pairs, 3): (dim, birth, death).
        """
        try:
            import ripser

            if self.n_landmarks is not None and len(points) > self.n_landmarks:
                idx = self.rng.choice(len(points), self.n_landmarks, replace=False)
                points = points[idx]

            result = ripser.ripser(
                points,
                maxdim=self.homology_dim,
                thresh=self.max_filtration,
            )
            rows = []
            for dim, pairs in enumerate(result["dgms"]):
                for birth, death in pairs:
                    rows.append([dim, birth, death])
            return np.array(rows, dtype=np.float64) if rows else np.zeros((0, 3))

        except ImportError as e:
            raise ImportError(
                "ripser is required for persistence computation. " "Install with: pip install ripser"
            ) from e

    def run_rung(
        self,
        observed_embedding: NDArray[np.float64],
        transition_matrix: NDArray[np.float64],
        initial_distribution: NDArray[np.float64],
        trajectory_length: int,
        pca_components: NDArray[np.float64],
        pca_mean: NDArray[np.float64],
        markov_order: int = 1,
    ) -> MarkovLadderResult:
        """Run one rung of the ladder test.

        Args:
            observed_embedding: PCA-embedded observed trajectories,
                shape (n_trajectories, n_pca_dims).
            transition_matrix: Fitted Markov transition matrix.
            initial_distribution: Empirical starting state distribution.
            trajectory_length: Number of time steps per simulated trajectory.
            pca_components: PCA loadings (frozen from observed fit),
                shape (n_pca_dims, n_raw_features).
            pca_mean: PCA mean vector, shape (n_raw_features,).
            markov_order: Markov order label for this rung.

        Returns:
            MarkovLadderResult with p-value, z-score, and null distribution.
        """
        observed_diagram = self._compute_diagram(observed_embedding)
        observed_tp = compute_total_persistence(observed_diagram, self.homology_dim)

        logger.info(
            "Running Markov-%d rung: %d null simulations",
            markov_order,
            self.n_null_simulations,
        )
        # NOTE: Null trajectory embedding and persistence diagram computation
        # are not implemented here. Returning statistics derived from a
        # placeholder null distribution (e.g. all zeros) would be misleading.
        # Callers must provide a concrete implementation (e.g. via a higher-
        # level pipeline that computes null embeddings/diagrams) or override
        # this method in a subclass.
        raise NotImplementedError(
            "Null trajectory embedding and persistence diagram computation are "
            "not implemented in this base Markov ladder rung. Provide a "
            "null-embedding/diagram computation or use a pipeline that "
            "overrides run_rung() with a concrete implementation."
        )
