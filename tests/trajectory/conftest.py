"""Shared test fixtures for trajectory TDA tests.

Provides synthetic trajectory generators with known topological structure
so that all tests can run without UKDS data access.
"""

from __future__ import annotations

import numpy as np
import pytest

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]

# ──────────────────────────────────────────────────────────────────────
# Synthetic trajectory generators
# ──────────────────────────────────────────────────────────────────────


def make_synthetic_trajectories(
    n: int = 100,
    t: int = 15,
    n_states: int = 9,
    seed: int = 42,
) -> list[list[str]]:
    """Generate random trajectories with uniform state transitions.

    Useful as a null baseline — no structure expected.
    """
    rng = np.random.RandomState(seed)
    states = STATES[:n_states]
    return [[states[rng.randint(n_states)] for _ in range(t)] for _ in range(n)]


def make_clustered_trajectories(
    n: int = 200,
    k: int = 3,
    t: int = 15,
    seed: int = 42,
) -> tuple[list[list[str]], list[int]]:
    """Generate trajectories with k well-separated regimes.

    Regime 0: mostly EH (stable secure)
    Regime 1: mostly EL/EM (working poor)
    Regime 2: mostly UL/IL (workless low-income)

    Returns:
        (trajectories, labels) — labels indicate ground-truth regime.
    """
    rng = np.random.RandomState(seed)

    # Regime-specific state distributions (probabilities over 9 states)
    regime_probs = {
        0: [0.02, 0.08, 0.70, 0.01, 0.01, 0.05, 0.01, 0.02, 0.10],  # EH-dom
        1: [0.40, 0.35, 0.05, 0.05, 0.05, 0.01, 0.04, 0.04, 0.01],  # EL/EM
        2: [0.05, 0.02, 0.01, 0.30, 0.05, 0.01, 0.40, 0.10, 0.06],  # UL/IL
    }

    trajectories = []
    labels = []
    per_k = n // k

    for regime in range(k):
        probs = regime_probs.get(regime, [1 / 9] * 9)
        for _ in range(per_k if regime < k - 1 else n - per_k * (k - 1)):
            traj = [STATES[rng.choice(9, p=probs)] for _ in range(t)]
            trajectories.append(traj)
            labels.append(regime)

    return trajectories, labels


def make_cyclic_trajectories(
    n: int = 50,
    cycle: list[str] | None = None,
    noise: float = 0.1,
    t: int = 20,
    seed: int = 42,
) -> list[list[str]]:
    """Generate trajectories that traverse a known cycle.

    Default cycle: EL → UL → IL → IM → EM → EL (poverty churn).
    With probability `noise`, a random state is inserted instead.
    """
    rng = np.random.RandomState(seed)
    if cycle is None:
        cycle = ["EL", "UL", "IL", "IM", "EM", "EL"]

    trajectories = []
    for _ in range(n):
        traj = []
        cycle_len = len(cycle)
        # Start at a random point in the cycle
        start = rng.randint(cycle_len)
        for step in range(t):
            if rng.random() < noise:
                traj.append(STATES[rng.randint(len(STATES))])
            else:
                traj.append(cycle[(start + step) % cycle_len])
        trajectories.append(traj)
    return trajectories


def make_churn_regimes(
    n: int = 200,
    t: int = 20,
    seed: int = 42,
) -> tuple[list[list[str]], list[int]]:
    """Generate Markov-driven trajectories with distinct regime dynamics.

    Regime 0 (stable): High self-transition prob in EH.
    Regime 1 (churn): Frequent transitions between EL/UL/IL.

    Returns:
        (trajectories, labels)
    """
    rng = np.random.RandomState(seed)

    # State index mapping
    s2i = {s: i for i, s in enumerate(STATES)}

    # Transition matrices (9×9)
    # Regime 0: stable employed-high
    tm_stable = np.full((9, 9), 0.01)
    eh = s2i["EH"]
    tm_stable[eh, eh] = 0.90
    tm_stable[eh, s2i["EM"]] = 0.05
    for i in range(9):
        tm_stable[i] /= tm_stable[i].sum()

    # Regime 1: churn between EL/UL/IL
    tm_churn = np.full((9, 9), 0.02)
    churn_states = [s2i["EL"], s2i["UL"], s2i["IL"]]
    for s in churn_states:
        for t_s in churn_states:
            tm_churn[s, t_s] = 0.25
    for i in range(9):
        tm_churn[i] /= tm_churn[i].sum()

    trajectories = []
    labels = []
    per_regime = n // 2

    for regime, (tm, start_state) in enumerate([(tm_stable, eh), (tm_churn, s2i["EL"])]):
        count = per_regime if regime == 0 else n - per_regime
        for _ in range(count):
            traj = [STATES[start_state]]
            current = start_state
            for _ in range(t - 1):
                current = rng.choice(9, p=tm[current])
                traj.append(STATES[current])
            trajectories.append(traj)
            labels.append(regime)

    return trajectories, labels


# ──────────────────────────────────────────────────────────────────────
# Pytest fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def random_trajectories():
    """100 random 15-year trajectories."""
    return make_synthetic_trajectories(n=100, t=15)


@pytest.fixture
def clustered_trajectories():
    """200 trajectories in 3 well-separated regimes."""
    return make_clustered_trajectories(n=200, k=3)


@pytest.fixture
def cyclic_trajectories():
    """50 trajectories traversing EL→UL→IL→IM→EM→EL cycle."""
    return make_cyclic_trajectories(n=50)


@pytest.fixture
def churn_trajectories():
    """200 Markov trajectories: half stable (EH), half churning (EL/UL/IL)."""
    return make_churn_regimes(n=200)
