"""Validate Mapper graph against existing GMM regime structure.

Provides tools to compare the Mapper decomposition with the 7-regime
GMM clustering from Paper 1, identifying bridge nodes that span multiple
regimes and sub-regime structure that the GMM compresses away.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from sklearn.metrics import normalized_mutual_info_score

logger = logging.getLogger(__name__)


def validate_against_regimes(
    graph: dict,
    regime_labels: np.ndarray,
    n_regimes: int = 7,
) -> dict:
    """Compute overlap between Mapper nodes and GMM regime labels.

    Args:
        graph: KeplerMapper graph dict with 'nodes' key.
        regime_labels: (N,) integer regime labels from GMM clustering.
        n_regimes: Expected number of regimes.

    Returns:
        Dict with keys:
            - nmi: Normalized Mutual Information between Mapper node
              membership and regime labels.
            - node_purity: list of per-node purity values (fraction of
              dominant regime in each node).
            - bridge_nodes: list of node IDs spanning 2+ regimes with
              no single regime exceeding 70% of the node.
            - regime_fragmentation: dict mapping regime index to the
              number of distinct Mapper nodes that regime maps to.
            - per_node_regime_distribution: per-node regime frequency dicts.
            - purity: mean regime purity across all nodes.
            - n_bridge_nodes: count of bridge nodes.
    """
    nodes = graph.get("nodes", {})

    if not nodes:
        return {
            "nmi": 0.0,
            "node_purity": [],
            "bridge_nodes": [],
            "regime_fragmentation": {},
            "per_node_regime_distribution": {},
            "purity": 0.0,
            "n_bridge_nodes": 0,
        }

    # Build Mapper-based cluster labels for NMI.
    # Iterate in sorted order so first-assignment is deterministic.
    point_to_node: dict[int, str] = {}
    for node_id in sorted(nodes.keys()):
        for m in nodes[node_id]:
            if m not in point_to_node:
                point_to_node[m] = node_id

    # NMI: map node IDs to integers using deterministic ordering
    node_id_map = {nid: i for i, nid in enumerate(sorted(nodes.keys()))}
    covered_indices = sorted(point_to_node.keys())
    mapper_labels = np.array([node_id_map[point_to_node[i]] for i in covered_indices])
    regime_subset = regime_labels[covered_indices]

    nmi = float(normalized_mutual_info_score(regime_subset, mapper_labels))

    # Per-node regime distribution, purity, and bridge-node detection
    per_node_dist: dict[str, dict[int, int]] = {}
    purities: list[float] = []
    bridge_nodes: list[str] = []

    # Track which regimes map to which nodes for fragmentation
    regime_to_nodes: dict[int, set[str]] = {r: set() for r in range(n_regimes)}

    for node_id, members in nodes.items():
        member_regimes = regime_labels[members]
        counts = Counter(int(r) for r in member_regimes)
        total = len(members)
        per_node_dist[node_id] = dict(counts)

        # Record regime-to-node mapping
        for r in counts:
            if 0 <= r < n_regimes:
                regime_to_nodes[r].add(node_id)

        # Purity: fraction of dominant regime
        max_count = max(counts.values())
        purity = max_count / total
        purities.append(purity)

        # Bridge node: no single regime exceeds 70%
        if purity < 0.7 and len(counts) >= 2:
            bridge_nodes.append(node_id)

    mean_purity = float(np.mean(purities)) if purities else 0.0

    # Regime fragmentation: how many distinct Mapper nodes each regime maps to
    regime_fragmentation = {r: len(node_set) for r, node_set in regime_to_nodes.items()}

    logger.info(
        "Validation: NMI=%.3f, purity=%.3f, bridge_nodes=%d/%d",
        nmi,
        mean_purity,
        len(bridge_nodes),
        len(nodes),
    )

    return {
        "nmi": nmi,
        "node_purity": purities,
        "bridge_nodes": bridge_nodes,
        "regime_fragmentation": regime_fragmentation,
        "per_node_regime_distribution": per_node_dist,
        "purity": mean_purity,
        "n_bridge_nodes": len(bridge_nodes),
    }


def identify_subregime_structure(
    graph: dict,
    regime_labels: np.ndarray,
    outcome_values: np.ndarray,
    threshold_std: float = 1.0,
) -> dict:
    """Identify within-regime heterogeneity via Mapper.

    For each regime, finds Mapper nodes where the outcome differs
    significantly from the regime mean, revealing sub-regions that
    the GMM compresses away.

    Args:
        graph: KeplerMapper graph dict with 'nodes' key.
        regime_labels: (N,) integer regime labels.
        outcome_values: (N,) outcome values per trajectory.
        threshold_std: Number of regime standard deviations a node
            mean must differ from regime mean to be considered a
            sub-regime (default: 1.0).

    Returns:
        Dict with keys:
            - subregimes: list of dicts per detected sub-region,
              each with regime, node_id, node_mean, regime_mean, z_score.
            - summary: per-regime count of sub-regime nodes.
            - n_total: total number of sub-regime nodes found.
    """
    nodes = graph.get("nodes", {})

    # Compute per-regime statistics
    unique_regimes = sorted(set(int(r) for r in regime_labels))
    regime_stats: dict[int, dict] = {}
    for r in unique_regimes:
        mask = regime_labels == r
        vals = outcome_values[mask]
        regime_stats[r] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)) if len(vals) > 1 else 0.0,
            "n": int(mask.sum()),
        }

    subregimes = []
    summary: dict[int, int] = {r: 0 for r in unique_regimes}

    for node_id, members in nodes.items():
        member_regimes = regime_labels[members]
        # Only analyze nodes dominated by a single regime (purity > 50%)
        counts = Counter(int(r) for r in member_regimes)
        dominant_regime, dominant_count = counts.most_common(1)[0]
        if dominant_count / len(members) < 0.5:
            continue

        node_outcomes = outcome_values[members]
        node_mean = float(np.mean(node_outcomes))
        r_stats = regime_stats[dominant_regime]

        if r_stats["std"] > 0:
            z_score = abs(node_mean - r_stats["mean"]) / r_stats["std"]
        else:
            z_score = 0.0

        if z_score > threshold_std:
            subregimes.append(
                {
                    "regime": dominant_regime,
                    "node_id": node_id,
                    "node_mean": node_mean,
                    "regime_mean": r_stats["mean"],
                    "z_score": float(z_score),
                    "node_size": len(members),
                }
            )
            summary[dominant_regime] += 1

    logger.info(
        "Sub-regime analysis: %d sub-regime nodes found across %d regimes",
        len(subregimes),
        sum(1 for v in summary.values() if v > 0),
    )

    return {
        "subregimes": subregimes,
        "summary": summary,
        "n_total": len(subregimes),
    }


def compute_node_membership_labels(graph: dict, n_points: int) -> np.ndarray:
    """Convert Mapper graph to per-point cluster labels.

    Each point is assigned the integer label of its node.  When a point
    appears in multiple nodes it receives the label of the largest node
    (by member count).  Points that appear in no node receive label -1.

    Node labels are dense integers starting from 0, assigned in the
    order the nodes appear in ``graph["nodes"]``.

    Args:
        graph: KeplerMapper graph dict with 'nodes' key.
        n_points: Total number of data points in the dataset.

    Returns:
        (n_points,) integer array of cluster labels in [-1, n_nodes).
    """
    nodes = graph.get("nodes", {})
    labels = np.full(n_points, -1, dtype=np.int64)

    if not nodes:
        return labels

    # Map node IDs to dense integer labels
    node_id_to_label = {nid: idx for idx, nid in enumerate(nodes.keys())}

    # Sort nodes by size (descending) so that when we assign labels
    # the largest node wins for points in multiple nodes.
    sorted_nodes = sorted(nodes.items(), key=lambda x: len(x[1]), reverse=True)

    for node_id, members in sorted_nodes:
        lbl = node_id_to_label[node_id]
        for m in members:
            if 0 <= m < n_points:
                # Only assign if not yet assigned (largest-first ordering
                # ensures the largest node wins)
                if labels[m] == -1:
                    labels[m] = lbl

    n_assigned = int(np.sum(labels >= 0))
    logger.info(
        "Node membership labels: %d/%d points assigned (%d nodes)",
        n_assigned,
        n_points,
        len(nodes),
    )

    return labels
