"""Tests for the KeplerMapper pipeline (Paper 2).

Uses small synthetic data to verify graph construction, node coloring,
parameter search, and regime validation logic.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("kmapper")

from trajectory_tda.mapper.mapper_pipeline import (
    _count_components,
    build_mapper_graph,
    mapper_graph_summary,
)
from trajectory_tda.mapper.node_coloring import (
    color_nodes_by_outcome,
    compute_escape_probability,
    compute_node_regime_distribution,
)
from trajectory_tda.mapper.parameter_search import mapper_parameter_search, parameter_grid_search
from trajectory_tda.mapper.validation import (
    compute_node_membership_labels,
    identify_subregime_structure,
    validate_against_regimes,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_embeddings():
    """Generate small synthetic embeddings with cluster structure for testing."""
    rng = np.random.RandomState(42)
    # Create 4 clusters so DBSCAN can find structure
    centers = rng.randn(4, 10) * 3
    points = []
    for c in centers:
        points.append(c + rng.randn(50, 10) * 0.5)
    return np.vstack(points)


@pytest.fixture()
def simple_graph(synthetic_embeddings):
    """Build a Mapper graph from synthetic embeddings."""
    graph, mapper_obj = build_mapper_graph(
        synthetic_embeddings,
        projection="pca_2d",
        n_cubes=5,
        overlap_frac=0.4,
        clusterer_params={"eps": 2.0, "min_samples": 3},
        verbose=0,
    )
    return graph


@pytest.fixture()
def regime_labels():
    """Synthetic regime labels for 200 points."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 5, size=200)


# ---------------------------------------------------------------------------
# Required tests from specification
# ---------------------------------------------------------------------------


class TestMapperSpecRequired:
    """The 8 tests required by the P02 specification."""

    def test_build_mapper_graph_basic(self, synthetic_embeddings):
        """Produces valid graph dict with nodes and links."""
        graph, mapper_obj = build_mapper_graph(
            synthetic_embeddings,
            n_cubes=5,
            overlap_frac=0.3,
            clusterer_params={"eps": 2.0, "min_samples": 3},
            verbose=0,
        )
        assert "nodes" in graph
        assert "links" in graph
        assert len(graph["nodes"]) > 0

    def test_build_mapper_graph_projections(self, synthetic_embeddings):
        """All projection types work and produce non-empty graphs."""
        for proj in ["pca_2d", "sum", "l2norm", "density"]:
            graph, _ = build_mapper_graph(
                synthetic_embeddings,
                projection=proj,
                n_cubes=5,
                overlap_frac=0.4,
                clusterer_params={"eps": 2.0, "min_samples": 3},
                verbose=0,
            )
            assert "nodes" in graph
            assert len(graph["nodes"]) > 0, f"No nodes for projection={proj}"

    def test_node_coloring_statistics(self, simple_graph):
        """Correct mean/std per node from color_nodes_by_outcome."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        rng = np.random.RandomState(42)
        values = rng.randn(n_total)

        result = color_nodes_by_outcome(simple_graph, values, outcome_name="test")

        assert len(result) == len(simple_graph["nodes"])
        for node_id, stats in result.items():
            members = simple_graph["nodes"][node_id]
            member_vals = values[members]

            assert stats["name"] == "test"
            assert stats["count"] == len(members)
            assert abs(stats["mean"] - float(np.mean(member_vals))) < 1e-10
            assert abs(stats["std"] - float(np.std(member_vals))) < 1e-10
            assert abs(stats["min"] - float(np.min(member_vals))) < 1e-10
            assert abs(stats["max"] - float(np.max(member_vals))) < 1e-10

    def test_regime_distribution(self, simple_graph):
        """Per-node regime fractions sum to 1."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        rng = np.random.RandomState(42)
        n_regimes = 5
        labels = rng.randint(0, n_regimes, size=n_total)

        result = compute_node_regime_distribution(simple_graph, labels, n_regimes=n_regimes)

        assert len(result) == len(simple_graph["nodes"])
        for node_id, info in result.items():
            dist = info["distribution"]
            assert len(dist) == n_regimes
            assert abs(sum(dist) - 1.0) < 1e-10, f"Distribution sums to {sum(dist)}, not 1.0"
            assert 0 <= info["dominant_regime"] < n_regimes
            assert info["count"] == len(simple_graph["nodes"][node_id])

    def test_parameter_search_runs(self, synthetic_embeddings):
        """Returns results for all parameter combinations."""
        n_cubes_range = [5, 8]
        overlap_range = [0.3, 0.5]
        expected_count = len(n_cubes_range) * len(overlap_range)

        result = mapper_parameter_search(
            synthetic_embeddings,
            n_cubes_range=n_cubes_range,
            overlap_range=overlap_range,
        )

        assert "results" in result
        assert "best_by_coverage" in result
        assert "best_by_components" in result
        assert len(result["results"]) == expected_count

        for entry in result["results"]:
            assert "n_cubes" in entry
            assert "overlap_frac" in entry
            assert "n_nodes" in entry
            assert "n_edges" in entry
            assert "n_components" in entry
            assert "mean_node_size" in entry
            assert "coverage" in entry

    def test_validate_against_regimes(self, simple_graph):
        """NMI in [0,1], purity in [0,1]."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        rng = np.random.RandomState(42)
        labels = rng.randint(0, 5, size=n_total)

        result = validate_against_regimes(simple_graph, labels, n_regimes=5)

        assert "nmi" in result
        assert 0 <= result["nmi"] <= 1.0
        assert "purity" in result
        assert 0 <= result["purity"] <= 1.0
        assert "node_purity" in result
        assert all(0 <= p <= 1 for p in result["node_purity"])
        assert "bridge_nodes" in result
        assert isinstance(result["bridge_nodes"], list)
        assert "regime_fragmentation" in result
        assert isinstance(result["regime_fragmentation"], dict)

    def test_node_membership_labels(self, simple_graph):
        """Correct shape, valid label range."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        labels = compute_node_membership_labels(simple_graph, n_total)

        assert labels.shape == (n_total,)
        assert labels.dtype == np.int64
        # All labels should be either -1 (unassigned) or in [0, n_nodes)
        n_nodes = len(simple_graph["nodes"])
        assert np.all((labels >= -1) & (labels < n_nodes))

    def test_mapper_graph_nonempty(self):
        """Graph is not empty for well-clustered data."""
        rng = np.random.RandomState(123)
        # Create tightly clustered data that DBSCAN will definitely cluster
        centers = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0]], dtype=np.float64)
        points = []
        for c in centers:
            points.append(c + rng.randn(40, 3) * 0.3)
        embeddings = np.vstack(points)

        graph, _ = build_mapper_graph(
            embeddings,
            projection="pca_2d",
            n_cubes=5,
            overlap_frac=0.4,
            clusterer_params={"eps": 1.5, "min_samples": 3},
            verbose=0,
        )

        assert len(graph["nodes"]) > 0
        summary = mapper_graph_summary(graph)
        assert summary["n_nodes"] > 0
        assert summary["n_covered"] > 0


# ---------------------------------------------------------------------------
# Additional tests (kept from original test suite for thoroughness)
# ---------------------------------------------------------------------------


class TestMapperPipeline:
    """Tests for core Mapper graph construction."""

    def test_graph_summary(self, simple_graph):
        """Summary stats are computed correctly."""
        summary = mapper_graph_summary(simple_graph)
        assert summary["n_nodes"] > 0
        assert summary["n_covered"] > 0
        assert 0 <= summary["coverage"] <= 1
        assert summary["n_connected_components"] >= 1
        assert summary["mean_node_size"] > 0
        assert summary["min_node_size"] <= summary["max_node_size"]

    def test_callable_projection(self, synthetic_embeddings):
        """Callable projection works correctly."""

        def custom_lens(x):
            return x[:, :1]

        graph, _ = build_mapper_graph(
            synthetic_embeddings,
            projection=custom_lens,
            n_cubes=5,
            overlap_frac=0.4,
            clusterer_params={"eps": 2.0, "min_samples": 3},
            verbose=0,
        )
        assert len(graph["nodes"]) > 0

    def test_invalid_projection_raises(self, synthetic_embeddings):
        """Invalid projection name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown projection"):
            build_mapper_graph(synthetic_embeddings, projection="invalid", verbose=0)

    def test_agglomerative_clusterer(self, synthetic_embeddings):
        """Agglomerative clustering produces a valid graph."""
        graph, _ = build_mapper_graph(
            synthetic_embeddings,
            clusterer="agglomerative",
            clusterer_params={"threshold": 2.0},
            n_cubes=5,
            overlap_frac=0.4,
            verbose=0,
        )
        assert len(graph["nodes"]) > 0

    def test_count_components_empty(self):
        """Empty graph has 0 components."""
        assert _count_components({"nodes": {}, "links": {}}) == 0

    def test_count_components_disconnected(self):
        """Two disconnected nodes yield 2 components."""
        graph = {
            "nodes": {"a": [0, 1], "b": [2, 3]},
            "links": {},
        }
        assert _count_components(graph) == 2

    def test_count_components_connected(self):
        """Two connected nodes yield 1 component."""
        graph = {
            "nodes": {"a": [0, 1], "b": [2, 3]},
            "links": {"a": ["b"], "b": ["a"]},
        }
        assert _count_components(graph) == 1


class TestNodeColoring:
    """Tests for node coloring functions."""

    def test_all_points_covered(self, simple_graph):
        """Every data point in a node gets its value included."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        values = np.arange(n_total, dtype=np.float64)
        result = color_nodes_by_outcome(simple_graph, values)
        for node_id, stats in result.items():
            members = simple_graph["nodes"][node_id]
            assert stats["count"] == len(members)

    def test_escape_probability(self):
        """Escape probability computed correctly."""
        labels = np.array([0, 1, 2, 3, 0, 1])
        escape = compute_escape_probability(labels, disadvantaged_regimes=[0, 1])
        expected = np.array([0, 0, 1, 1, 0, 0], dtype=np.float64)
        np.testing.assert_array_equal(escape, expected)


class TestParameterSearch:
    """Tests for parameter grid search."""

    def test_grid_search_runs(self, synthetic_embeddings):
        """Legacy parameter_grid_search completes without error."""
        result = parameter_grid_search(
            synthetic_embeddings,
            n_cubes_range=[5, 8],
            overlap_range=[0.3, 0.5],
            projections=["pca_2d"],
        )
        assert "results" in result
        assert "best" in result
        assert result["n_evaluated"] == 4  # 1 proj * 2 cubes * 2 overlaps
        assert len(result["results"]) == 4

    def test_grid_search_results_have_summaries(self, synthetic_embeddings):
        """Each grid search result has a summary dict."""
        result = parameter_grid_search(
            synthetic_embeddings,
            n_cubes_range=[5],
            overlap_range=[0.3],
            projections=["pca_2d"],
        )
        for r in result["results"]:
            assert "params" in r
            assert r["summary"] is not None
            assert "n_nodes" in r["summary"]


class TestValidation:
    """Tests for regime validation."""

    def test_bridge_nodes_identified(self, simple_graph):
        """Bridge nodes spanning multiple regimes are found."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        labels = np.zeros(n_total, dtype=np.int64)
        labels[::2] = 0
        labels[1::2] = 1

        result = validate_against_regimes(simple_graph, labels, n_regimes=2)
        assert result["n_bridge_nodes"] >= 0
        assert isinstance(result["per_node_regime_distribution"], dict)

    def test_empty_graph(self):
        """Empty graph produces zero metrics."""
        graph = {"nodes": {}, "links": {}}
        labels = np.array([0, 1, 2])
        result = validate_against_regimes(graph, labels)
        assert result["nmi"] == 0.0
        assert result["purity"] == 0.0
        assert result["node_purity"] == []
        assert result["regime_fragmentation"] == {}

    def test_subregime_structure(self, simple_graph, regime_labels):
        """Sub-regime identification runs without error."""
        n_total = max(max(m) for m in simple_graph["nodes"].values()) + 1
        outcomes = np.random.RandomState(42).randn(n_total)
        if len(regime_labels) < n_total:
            regime_labels = np.resize(regime_labels, n_total)

        result = identify_subregime_structure(simple_graph, regime_labels, outcomes)
        assert "subregimes" in result
        assert "summary" in result
        assert "n_total" in result
        assert isinstance(result["subregimes"], list)

    def test_membership_labels_unassigned(self):
        """Points not in any node get label -1."""
        graph = {"nodes": {"a": [0, 1, 2]}, "links": {}}
        labels = compute_node_membership_labels(graph, n_points=5)
        assert labels.shape == (5,)
        assert labels[0] == 0
        assert labels[1] == 0
        assert labels[2] == 0
        assert labels[3] == -1
        assert labels[4] == -1
