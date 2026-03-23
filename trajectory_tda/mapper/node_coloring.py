"""Color Mapper nodes by outcome variables.

Provides functions to compute per-node statistics for various trajectory
outcome measures, enabling visual analysis of the Mapper graph structure
in relation to socio-economic outcomes.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def color_nodes_by_outcome(
    graph: dict,
    outcome_values: np.ndarray,
    outcome_name: str = "outcome",
) -> dict:
    """Compute per-node statistics for an outcome variable.

    Args:
        graph: KeplerMapper graph dict with 'nodes' key.
        outcome_values: (N,) outcome values per trajectory.
        outcome_name: Name of the outcome variable for labelling.

    Returns:
        Dict mapping node_id to {name, mean, std, count, min, max, members}.
    """
    nodes = graph.get("nodes", {})
    result = {}

    for node_id, members in nodes.items():
        member_values = outcome_values[members]
        result[node_id] = {
            "name": outcome_name,
            "mean": float(np.mean(member_values)),
            "std": float(np.std(member_values)),
            "count": len(members),
            "min": float(np.min(member_values)),
            "max": float(np.max(member_values)),
            "members": members,
        }

    logger.info(
        "Colored %d nodes by '%s' (global mean=%.3f)",
        len(result),
        outcome_name,
        float(np.mean(outcome_values)),
    )
    return result


def compute_node_regime_distribution(
    graph: dict,
    regime_labels: np.ndarray,
    n_regimes: int = 7,
) -> dict:
    """Compute per-node regime composition.

    For each Mapper node, determines the fraction of member trajectories
    belonging to each regime, producing a distribution vector that sums
    to 1.

    Args:
        graph: KeplerMapper graph dict with 'nodes' key.
        regime_labels: (N,) integer regime label per trajectory.
        n_regimes: Total number of regimes (determines distribution length).

    Returns:
        Dict mapping node_id to a dict with:
            - distribution: list of floats (fraction in each regime, length n_regimes)
            - dominant_regime: int (regime with highest fraction)
            - count: int (number of member trajectories)
    """
    nodes = graph.get("nodes", {})
    result = {}

    for node_id, members in nodes.items():
        member_regimes = regime_labels[members]
        counts = np.zeros(n_regimes, dtype=np.float64)
        for r in member_regimes:
            r_int = int(r)
            if 0 <= r_int < n_regimes:
                counts[r_int] += 1

        total = counts.sum()
        distribution = (counts / total).tolist() if total > 0 else [0.0] * n_regimes

        result[node_id] = {
            "distribution": distribution,
            "dominant_regime": int(np.argmax(counts)),
            "count": len(members),
        }

    logger.info("Computed regime distributions for %d nodes (k=%d)", len(result), n_regimes)
    return result


def compute_escape_probability(
    regime_labels: np.ndarray,
    disadvantaged_regimes: list[int],
) -> np.ndarray:
    """Compute binary escape indicator per trajectory.

    A trajectory 'escapes' if its regime label is NOT in the set of
    disadvantaged regimes (i.e., it ended up in a more favourable
    trajectory cluster).

    Args:
        regime_labels: (N,) integer regime labels from GMM clustering.
        disadvantaged_regimes: List of regime indices considered
            disadvantaged (e.g., high-unemployment or low-income clusters).

    Returns:
        (N,) binary array where 1 = escaped, 0 = disadvantaged.
    """
    disadvantaged_set = set(disadvantaged_regimes)
    escape = np.array(
        [0 if int(label) in disadvantaged_set else 1 for label in regime_labels],
        dtype=np.float64,
    )
    logger.info(
        "Escape probability: %.1f%% escaped (%d / %d)",
        100 * escape.mean(),
        int(escape.sum()),
        len(escape),
    )
    return escape


def _compute_employment_rate(trajectories: list[list[str]]) -> np.ndarray:
    """Compute fraction of periods spent in employment for each trajectory.

    Args:
        trajectories: List of N state-sequence lists (each state is e.g. 'EH').

    Returns:
        (N,) array of employment rates in [0, 1].
    """
    rates = np.zeros(len(trajectories), dtype=np.float64)
    for i, traj in enumerate(trajectories):
        if not traj:
            continue
        employed = sum(1 for s in traj if s.startswith("E"))
        rates[i] = employed / len(traj)
    return rates


def _compute_final_income_proxy(trajectories: list[list[str]]) -> np.ndarray:
    """Compute ordinal income proxy from final state in each trajectory.

    Maps state suffix to ordinal: L=0, M=1, H=2.

    Args:
        trajectories: List of N state-sequence lists.

    Returns:
        (N,) array of ordinal income levels {0, 1, 2}.
    """
    income_map = {"L": 0, "M": 1, "H": 2}
    incomes = np.zeros(len(trajectories), dtype=np.float64)
    for i, traj in enumerate(trajectories):
        if traj:
            final_state = traj[-1]
            suffix = final_state[-1] if final_state else "L"
            incomes[i] = income_map.get(suffix, 0)
    return incomes


def compute_all_colorings(
    graph: dict,
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    metadata: dict,
) -> dict:
    """Compute all standard colorings for Mapper nodes.

    Computes: escape probability, employment rate, final income proxy,
    and regime label.

    Args:
        graph: KeplerMapper graph dict.
        embeddings: (N, D) embedding array (unused but kept for API
            consistency and future density-based colorings).
        trajectories: List of N state-sequence lists.
        metadata: Dict with 'analysis' key containing regime info.

    Returns:
        Dict mapping coloring name to the color_nodes_by_outcome result.
    """
    analysis = metadata.get("analysis", {})
    gmm_labels = np.array(analysis.get("gmm_labels", []), dtype=np.int64)
    regimes = analysis.get("regimes", {})
    k_optimal = regimes.get("k_optimal", 7)

    # Identify disadvantaged regimes: those with dominant state starting
    # with 'U' (unemployed) or 'I' (inactive)
    profiles = regimes.get("profiles", {})
    disadvantaged = []
    for regime_id, profile in profiles.items():
        dominant = profile.get("dominant_state", "")
        if dominant.startswith(("U", "I")):
            disadvantaged.append(int(regime_id))
    logger.info("Disadvantaged regimes: %s (k=%d)", disadvantaged, k_optimal)

    colorings = {}

    # 1. Escape probability
    if len(gmm_labels) > 0:
        escape = compute_escape_probability(gmm_labels, disadvantaged)
        colorings["escape_probability"] = color_nodes_by_outcome(graph, escape, outcome_name="escape_probability")

    # 2. Employment rate
    emp_rate = _compute_employment_rate(trajectories)
    colorings["employment_rate"] = color_nodes_by_outcome(graph, emp_rate, outcome_name="employment_rate")

    # 3. Final income proxy
    income = _compute_final_income_proxy(trajectories)
    colorings["final_income"] = color_nodes_by_outcome(graph, income, outcome_name="final_income")

    # 4. Regime label (as float for aggregation)
    if len(gmm_labels) > 0:
        colorings["regime_label"] = color_nodes_by_outcome(
            graph, gmm_labels.astype(np.float64), outcome_name="regime_label"
        )

    logger.info("Computed %d colorings", len(colorings))
    return colorings
