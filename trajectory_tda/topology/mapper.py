"""KeplerMapper wrapper for interior trajectory space exploration.

Paper 2: Apply Mapper to the existing PCA-20D embedding to produce a
navigable "map" of trajectory space. Colouring Mapper nodes by outcome
variables (escape probability, income endpoint, NS-SEC of origin)
establishes which regions of trajectory space are causally associated
with which outcomes — addressing the critique that topological features
are described but not connected to policy-relevant predictions.

Key contribution: sub-regime heterogeneity within the 7-GMM typology.
Mapper nodes can reveal within-regime variation (e.g., sub-regions of
"Low-Income Churn" with higher vs. lower escape likelihood) that the
GMM classification compresses away.

Reference:
    Singh, G., Mémoli, F., & Carlsson, G. (2007). Topological methods for
    the analysis of high dimensional data sets and 3D object recognition.
    SPBG 2007.

    KeplerMapper: https://kepler-mapper.scikit-tda.org/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


try:
    import kmapper as km

    HAS_KMAPPER = True
except ImportError:
    HAS_KMAPPER = False
    logger.info(
        "KeplerMapper not available. Install with: pip install kmapper. " "Required for Paper 2 Mapper analysis."
    )


@dataclass
class MapperConfig:
    """Configuration for the trajectory Mapper computation.

    Args:
        n_cubes: Number of cover intervals along the projection axis.
            Higher = more local; lower = more global. Typical range: 5–30.
        perc_overlap: Fractional overlap between adjacent cover intervals.
            Typical range: 0.2–0.7.
        clusterer: Sklearn-compatible clusterer for within-cover-element
            grouping. DBSCAN is standard; single-linkage also works well.
        projection: Projection function for the cover. Options:
            'pca_1': first PCA component (default — already computed).
            'pca_2': second PCA component.
            'income_density': income-weighted density kernel (requires
                scalar income labels to be passed to run()).
            A callable that takes the embedding and returns a 1D array
            is also accepted.
        min_intersection: Minimum number of shared points for two nodes
            to be connected by an edge.
    """

    n_cubes: int = 10
    perc_overlap: float = 0.5
    clusterer: object = None  # defaults to DBSCAN in run()
    projection: str | object = "pca_1"
    min_intersection: int = 1


@dataclass
class MapperGraph:
    """Result of a Mapper computation on the trajectory embedding.

    Attributes:
        nodes: Dict mapping node_id → list of point indices in that node.
        edges: List of (node_id_a, node_id_b) pairs.
        node_means: Dict mapping node_id → mean feature vector of members.
        node_outcome_means: Dict mapping node_id → dict of mean outcomes.
        n_points: Total number of input points.
        config: MapperConfig used to produce this graph.
    """

    nodes: dict[str, list[int]]
    edges: list[tuple[str, str]]
    node_means: dict[str, NDArray[np.float64]] = field(default_factory=dict)
    node_outcome_means: dict[str, dict[str, float]] = field(default_factory=dict)
    n_points: int = 0
    config: MapperConfig = field(default_factory=MapperConfig)


class TrajectoryMapper:
    """Compute the Mapper graph for the BHPS/USoc trajectory embedding.

    Takes the frozen PCA-20D embedding (27,280 points) and produces a
    simplicial graph summarising the interior density structure of
    trajectory space.

    Args:
        config: MapperConfig controlling cover and clustering.
    """

    def __init__(self, config: MapperConfig | None = None) -> None:
        if not HAS_KMAPPER:
            raise ImportError("kmapper is required. Install with: pip install kmapper")
        self.config = config or MapperConfig()

    def _get_projection(
        self,
        embedding: NDArray[np.float64],
        lens_labels: NDArray[np.float64] | None,
    ) -> NDArray[np.float64]:
        """Compute the 1D projection (lens) for the cover.

        Args:
            embedding: PCA-20D embedding, shape (n_points, 20).
            lens_labels: Optional scalar outcome labels (used for
                'income_density' projection).

        Returns:
            1D array of shape (n_points, 1) — the lens values.
        """
        proj = self.config.projection
        if proj == "pca_1":
            return embedding[:, [0]]
        if proj == "pca_2":
            return embedding[:, [1]]
        if proj == "income_density":
            if lens_labels is None:
                raise ValueError("lens_labels must be provided for 'income_density' projection")
            return lens_labels.reshape(-1, 1)
        if callable(proj):
            result = proj(embedding)
            return result.reshape(-1, 1)
        raise ValueError(f"Unknown projection: {proj!r}")

    def run(
        self,
        embedding: NDArray[np.float64],
        outcome_labels: dict[str, NDArray[np.float64]] | None = None,
        lens_labels: NDArray[np.float64] | None = None,
    ) -> MapperGraph:
        """Compute the Mapper graph.

        Args:
            embedding: PCA-embedded trajectories, shape (n_points, n_dims).
                Should use the frozen PCA loadings from the Paper 1 pipeline.
            outcome_labels: Optional dict of outcome_name → scalar array
                of shape (n_points,). Used to colour Mapper nodes by
                escape probability, income endpoint, NS-SEC origin, etc.
            lens_labels: Optional scalar labels for the 'income_density'
                projection. Not needed for 'pca_1' or 'pca_2'.

        Returns:
            MapperGraph with nodes, edges, and node-level outcome summaries.
        """
        from sklearn.cluster import DBSCAN

        mapper = km.KeplerMapper(verbose=0)
        lens = self._get_projection(embedding, lens_labels)
        clusterer = self.config.clusterer or DBSCAN(eps=0.5, min_samples=3)

        graph = mapper.map(
            lens,
            embedding,
            clusterer=clusterer,
            cover=km.Cover(
                n_cubes=self.config.n_cubes,
                perc_overlap=self.config.perc_overlap,
            ),
        )

        nodes = graph.get("nodes", {})
        edges_raw = graph.get("links", {})
        edges = [(src, dst) for src, dsts in edges_raw.items() for dst in dsts]

        node_means = {node_id: embedding[members].mean(axis=0) for node_id, members in nodes.items()}

        node_outcome_means: dict[str, dict[str, float]] = {}
        if outcome_labels:
            for node_id, members in nodes.items():
                node_outcome_means[node_id] = {
                    name: float(labels[members].mean()) for name, labels in outcome_labels.items()
                }

        logger.info(
            "Mapper complete: %d nodes, %d edges (n_cubes=%d, overlap=%.2f)",
            len(nodes),
            len(edges),
            self.config.n_cubes,
            self.config.perc_overlap,
        )

        return MapperGraph(
            nodes=nodes,
            edges=edges,
            node_means=node_means,
            node_outcome_means=node_outcome_means,
            n_points=len(embedding),
            config=self.config,
        )

    def to_html(
        self,
        graph: MapperGraph,
        embedding: NDArray[np.float64],
        colour_by: str = "escape_probability",
        output_path: str = "mapper_graph.html",
    ) -> str:
        """Export the Mapper graph to an interactive HTML file.

        Args:
            graph: MapperGraph from run().
            embedding: Original embedding (passed to visualiser for tooltips).
            colour_by: Key from graph.node_outcome_means to use for colouring.
            output_path: Path to write the HTML file.

        Returns:
            Path to the written HTML file.
        """
        mapper = km.KeplerMapper(verbose=0)

        # Rebuild raw kmapper dict format for visualisation
        raw_graph = {
            "nodes": graph.nodes,
            "links": {src: [dst for s, dst in graph.edges if s == src] for src in graph.nodes},
        }

        colour_values = None
        if colour_by in (graph.node_outcome_means.get(list(graph.nodes.keys())[0]) or {}):
            colour_values = np.array([graph.node_outcome_means.get(nid, {}).get(colour_by, 0.0) for nid in graph.nodes])

        mapper.visualize(
            raw_graph,
            path_html=output_path,
            title=f"Trajectory Space — coloured by {colour_by}",
            color_function=colour_values,
        )
        logger.info("Mapper graph written to %s", output_path)
        return output_path
