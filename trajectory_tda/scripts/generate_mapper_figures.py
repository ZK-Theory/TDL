"""Generate publication figures for P02 Mapper paper.

Produces 7 figures for the v2 draft:
  Fig 1: Mapper graph (DBSCAN best) coloured by PC1 income gradient
  Fig 2: Mapper graph coloured by L2 norm (trajectory extremity)
  Fig 3: Mapper graph coloured by GMM regime label
  Fig 4: Sub-regime highlighting (PC1 |z|>1 nodes marked)
  Fig 5: Sensitivity panel — DBSCAN eps comparison (3 configs)
  Fig 6: DBSCAN vs Agglomerative comparison
  Fig 7: Lens function comparison (4 lenses, DBSCAN eps=0.5)

Usage:
    python -m trajectory_tda.scripts.generate_mapper_figures
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure

from trajectory_tda.mapper.mapper_pipeline import (
    build_mapper_graph,
    mapper_graph_summary,
)
from trajectory_tda.mapper.validation import identify_subregime_structure
from trajectory_tda.viz.constants import (
    DPI,
    FIGSIZE_FULL,
    PUBLICATION_RC,
    REGIME_LABELS,
)

logger = logging.getLogger(__name__)

plt.rcParams.update(PUBLICATION_RC)

# Output directories
RESULTS_DIR = Path("results/trajectory_tda_integration")
MAPPER_DIR = Path("results/trajectory_tda_mapper")
FIGURES_DIR = Path("papers/P02-Mapper/figures")

# Regime colour palette (qualitative, colourblind-safe)
REGIME_CMAP = ListedColormap(
    [
        "#e41a1c",  # R0 Mixed Churn — red
        "#377eb8",  # R1 Secure EH — blue
        "#ff7f00",  # R2 Inactive Low — orange
        "#984ea3",  # R3 Emp-Inactive Mix — purple
        "#4daf4a",  # R4 Employed Mid — green
        "#a65628",  # R5 High-Income Inactive — brown
        "#f781bf",  # R6 Low-Income Churn — pink
    ]
)


def _save_figure(fig: Figure, name: str) -> None:
    """Save figure in PDF and PNG."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.pdf", format="pdf")
    fig.savefig(FIGURES_DIR / f"{name}.png", format="png", dpi=DPI)
    plt.close(fig)
    logger.info("Saved %s.pdf + .png", name)


def _mapper_to_networkx(graph: dict) -> nx.Graph:
    """Convert KeplerMapper graph dict to a NetworkX graph."""
    G = nx.Graph()
    nodes = graph.get("nodes", {})
    links = graph.get("links", {})

    for node_id, members in nodes.items():
        G.add_node(node_id, size=len(members), members=members)

    for node_id, neighbours in links.items():
        for nbr in neighbours:
            if not G.has_edge(node_id, nbr):
                G.add_edge(node_id, nbr)

    return G


def _compute_node_colors(
    graph: dict,
    values: np.ndarray,
) -> tuple[list[str], list[float]]:
    """Compute per-node mean of a value array.

    Returns (node_ids, node_means) in graph node order.
    """
    nodes = graph.get("nodes", {})
    node_ids = []
    node_means = []
    for nid, members in nodes.items():
        node_ids.append(nid)
        node_means.append(float(np.mean(values[members])))
    return node_ids, node_means


def _layout_mapper_graph(
    G: nx.Graph,
    embeddings: np.ndarray,
    graph: dict,
) -> dict:
    """Position Mapper nodes at the mean PCA-2D position of their members."""
    pos = {}
    nodes = graph.get("nodes", {})
    for nid, members in nodes.items():
        if nid in G:
            mean_pos = np.mean(embeddings[members, :2], axis=0)
            pos[nid] = (float(mean_pos[0]), float(mean_pos[1]))
    return pos


def _draw_mapper_graph(
    ax,
    G: nx.Graph,
    pos: dict,
    node_colors: list[float],
    node_sizes: list[float],
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    alpha: float = 0.8,
    edge_alpha: float = 0.15,
) -> object:
    """Draw the Mapper graph on an axes, return the PathCollection for colorbar."""
    # Draw edges first
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=edge_alpha, edge_color="#cccccc", width=0.5)
    # Draw nodes
    sc = nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        alpha=alpha,
        linewidths=0.3,
        edgecolors="white",
    )
    ax.set_aspect("equal")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    return sc


def _build_graph_for_config(
    embeddings: np.ndarray,
    projection: str = "pca_2d",
    n_cubes: int = 30,
    overlap_frac: float = 0.5,
    clusterer: str = "dbscan",
    clusterer_params: dict | None = None,
) -> tuple[dict, nx.Graph, dict, list[float]]:
    """Build Mapper graph + networkx + layout + node sizes."""
    graph, _ = build_mapper_graph(
        embeddings,
        projection=projection,
        n_cubes=n_cubes,
        overlap_frac=overlap_frac,
        clusterer=clusterer,
        clusterer_params=clusterer_params or {},
        verbose=0,
    )
    G = _mapper_to_networkx(graph)
    pos = _layout_mapper_graph(G, embeddings, graph)

    # Node sizes: scale by member count
    nodes = graph.get("nodes", {})
    sizes = []
    for nid in G.nodes():
        s = len(nodes.get(nid, []))
        sizes.append(max(3, min(s * 0.3, 100)))  # clamp
    return graph, G, pos, sizes


def fig1_pc1_gradient(embeddings, gmm_labels):
    """Figure 1: Mapper graph coloured by PC1 income gradient."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    node_ids, node_means = _compute_node_colors(graph, embeddings[:, 0])

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_means,
        sizes,
        cmap="RdYlBu_r",
        vmin=np.percentile(node_means, 2),
        vmax=np.percentile(node_means, 98),
    )
    fig.colorbar(sc, ax=ax, shrink=0.8, label="Mean PC1 (income gradient)")
    ax.set_title("Mapper Graph — PC1 Income Gradient (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig1_mapper_pc1")


def fig2_l2_norm(embeddings, gmm_labels):
    """Figure 2: Mapper graph coloured by L2 norm."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    l2 = np.linalg.norm(embeddings, axis=1)
    node_ids, node_means = _compute_node_colors(graph, l2)

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_means,
        sizes,
        cmap="magma",
        vmin=np.percentile(node_means, 2),
        vmax=np.percentile(node_means, 98),
    )
    fig.colorbar(sc, ax=ax, shrink=0.8, label="Mean L2 norm (trajectory extremity)")
    ax.set_title("Mapper Graph — L2 Norm (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig2_mapper_l2")


def fig3_regime_labels(embeddings, gmm_labels):
    """Figure 3: Mapper graph coloured by dominant GMM regime."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    nodes = graph.get("nodes", {})

    # Dominant regime per node
    from collections import Counter

    node_regimes = []
    for nid in G.nodes():
        members = nodes[nid]
        counts = Counter(int(r) for r in gmm_labels[members])
        node_regimes.append(counts.most_common(1)[0][0])

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_regimes,
        sizes,
        cmap=REGIME_CMAP,
        vmin=-0.5,
        vmax=6.5,
    )
    # Discrete colorbar
    cb = fig.colorbar(sc, ax=ax, shrink=0.8, ticks=range(7))
    cb.ax.set_yticklabels([REGIME_LABELS.get(i, f"R{i}") for i in range(7)])
    cb.set_label("Dominant GMM Regime")
    ax.set_title("Mapper Graph — GMM Regimes (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig3_mapper_regimes")


def fig4_subregime_highlight(embeddings, gmm_labels):
    """Figure 4: Sub-regime nodes highlighted on the Mapper graph."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    pc1 = embeddings[:, 0]

    # Identify sub-regime nodes
    subregime = identify_subregime_structure(graph, gmm_labels, pc1)
    subregime_node_ids = {s["node_id"] for s in subregime["subregimes"]}

    # Colour: sub-regime nodes red, others grey
    node_colors = []
    node_alphas = []
    for nid in G.nodes():
        if nid in subregime_node_ids:
            node_colors.append("#e41a1c")
            node_alphas.append(0.9)
        else:
            node_colors.append("#b0b0b0")
            node_alphas.append(0.4)

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.1, edge_color="#cccccc", width=0.5)
    nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=sizes,
        alpha=0.7,
        linewidths=0.3,
        edgecolors="white",
    )
    ax.set_aspect("equal")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    n_sub = len(subregime_node_ids)
    n_total = len(G.nodes())
    ax.set_title(f"Sub-Regime Nodes (|z| > 1.0 on PC1): {n_sub}/{n_total} nodes highlighted")
    # Legend
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#e41a1c",
            markersize=8,
            label=f"Sub-regime ({n_sub})",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#b0b0b0",
            markersize=8,
            label=f"Normal ({n_total - n_sub})",
        ),
    ]
    ax.legend(handles=legend_elements, loc="upper right", framealpha=0.9)
    _save_figure(fig, "fig4_subregime_highlight")


def fig5_eps_comparison(embeddings, gmm_labels):
    """Figure 5: Panel comparing DBSCAN eps = {0.2, 0.3, 0.5}."""
    eps_values = [0.2, 0.3, 0.5]
    fig, axes = plt.subplots(1, 3, figsize=(FIGSIZE_FULL[0], FIGSIZE_FULL[1] * 0.85))

    for ax, eps in zip(axes, eps_values):
        graph, G, pos, sizes = _build_graph_for_config(embeddings, clusterer_params={"eps": eps, "min_samples": 5})
        node_ids, node_means = _compute_node_colors(graph, embeddings[:, 0])
        summary = mapper_graph_summary(graph, n_points=len(embeddings))

        sc = _draw_mapper_graph(
            ax,
            G,
            pos,
            node_means,
            sizes,
            cmap="RdYlBu_r",
            vmin=-4,
            vmax=5,
        )
        ax.set_title(
            f"eps={eps}\n{summary['n_nodes']} nodes, {summary['coverage']:.0%} coverage",
            fontsize=9,
        )
        if eps != eps_values[0]:
            ax.set_ylabel("")

    fig.colorbar(sc, ax=axes, shrink=0.8, label="Mean PC1", location="right")
    fig.suptitle("DBSCAN eps Sensitivity (PCA-2D, n_cubes=30, overlap=0.5)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 0.92, 0.93])
    _save_figure(fig, "fig5_eps_sensitivity")


def fig6_dbscan_vs_agglom(embeddings, gmm_labels):
    """Figure 6: DBSCAN (eps=0.5) vs Agglomerative (t=1.5) side by side."""
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_FULL)

    # DBSCAN
    graph_db, G_db, pos_db, sizes_db = _build_graph_for_config(embeddings)
    _, means_db = _compute_node_colors(graph_db, embeddings[:, 0])
    s_db = mapper_graph_summary(graph_db, n_points=len(embeddings))

    sc = _draw_mapper_graph(
        axes[0],
        G_db,
        pos_db,
        means_db,
        sizes_db,
        cmap="RdYlBu_r",
        vmin=-4,
        vmax=5,
    )
    axes[0].set_title(
        f"DBSCAN (eps=0.5)\n{s_db['n_nodes']} nodes, {s_db['coverage']:.0%} coverage, 0 bridge",
        fontsize=9,
    )

    # Agglomerative — sample for visualization (full graph is 37k nodes)
    graph_ag, _ = build_mapper_graph(
        embeddings,
        projection="pca_2d",
        n_cubes=30,
        overlap_frac=0.5,
        clusterer="agglomerative",
        clusterer_params={"threshold": 1.5},
        verbose=0,
    )
    s_ag = mapper_graph_summary(graph_ag, n_points=len(embeddings))

    # For agglomerative with 37k nodes, subsample the largest components
    # to keep the figure readable
    G_ag = _mapper_to_networkx(graph_ag)
    pos_ag = _layout_mapper_graph(G_ag, embeddings, graph_ag)

    # Sample top 1500 nodes by size for visibility
    nodes_ag = graph_ag.get("nodes", {})
    node_sizes_full = [(nid, len(m)) for nid, m in nodes_ag.items()]
    node_sizes_full.sort(key=lambda x: x[1], reverse=True)
    top_nodes = {nid for nid, _ in node_sizes_full[:1500]}
    G_sub = G_ag.subgraph([n for n in G_ag.nodes() if n in top_nodes])
    pos_sub = {n: pos_ag[n] for n in G_sub.nodes() if n in pos_ag}

    _, means_ag = _compute_node_colors(graph_ag, embeddings[:, 0])
    # Remap means to subgraph node order
    node_id_list = list(graph_ag["nodes"].keys())
    mean_map = dict(zip(node_id_list, means_ag))
    means_sub = [mean_map.get(n, 0) for n in G_sub.nodes()]
    sizes_sub = [max(2, min(len(nodes_ag.get(n, [])) * 0.15, 50)) for n in G_sub.nodes()]

    from trajectory_tda.mapper.validation import validate_against_regimes

    val_ag = validate_against_regimes(graph_ag, gmm_labels)

    _draw_mapper_graph(
        axes[1],
        G_sub,
        pos_sub,
        means_sub,
        sizes_sub,
        cmap="RdYlBu_r",
        vmin=-4,
        vmax=5,
        edge_alpha=0.05,
    )
    axes[1].set_title(
        f"Agglomerative (t=1.5)\n"
        f"{s_ag['n_nodes']:,} nodes, {s_ag['coverage']:.0%} coverage, "
        f"{val_ag['n_bridge_nodes']} bridge (top 1500 shown)",
        fontsize=9,
    )

    fig.colorbar(sc, ax=axes, shrink=0.8, label="Mean PC1", location="right")
    fig.suptitle("DBSCAN vs Agglomerative Clustering", fontsize=11)
    fig.tight_layout(rect=[0, 0, 0.92, 0.93])
    _save_figure(fig, "fig6_dbscan_vs_agglom")


def fig7_lens_comparison(embeddings, gmm_labels):
    """Figure 7: Four lens functions compared (DBSCAN eps=0.5)."""
    import json
    import pathlib

    from trajectory_tda.mapper.validation import validate_against_regimes

    lenses = ["pca_2d", "l2norm", "sum", "density"]
    lens_labels = ["PCA-2D", "L2 Norm", "Sum", "KDE Density"]

    # Load NMI from pre-computed sweep results to avoid re-running slow KDE lens
    _sweep_path = pathlib.Path("results/trajectory_tda_mapper/sensitivity/sweep_results.json")
    _nmi_lookup: dict = {}
    if _sweep_path.exists():
        _sweep = json.loads(_sweep_path.read_text())
        for _r in _sweep.get("results", []):
            _cfg = _r.get("config", {})
            if _cfg.get("clusterer") == "dbscan" and abs(_cfg.get("clusterer_params", {}).get("eps", 0) - 0.5) < 0.01:
                _nmi_lookup[_cfg["projection"]] = _r["validation"]["nmi"]

    fig, axes = plt.subplots(2, 2, figsize=(FIGSIZE_FULL[0], FIGSIZE_FULL[0] * 0.75))
    axes = axes.ravel()

    last_sc = None
    for ax, proj, label in zip(axes, lenses, lens_labels):
        graph, G, pos, sizes = _build_graph_for_config(
            embeddings,
            projection=proj,
        )
        _, node_means = _compute_node_colors(graph, embeddings[:, 0])
        summary = mapper_graph_summary(graph, n_points=len(embeddings))

        # Use pre-computed NMI if available; otherwise compute (skip for density)
        if proj in _nmi_lookup:
            nmi_str = f"{_nmi_lookup[proj]:.3f}"
        elif proj != "density":
            val = validate_against_regimes(graph, gmm_labels)
            nmi_str = f"{val['nmi']:.3f}" if val.get("nmi") is not None else "?"
        else:
            nmi_str = "?"

        sc = _draw_mapper_graph(
            ax,
            G,
            pos,
            node_means,
            sizes,
            cmap="RdYlBu_r",
            vmin=-4,
            vmax=5,
        )
        ax.set_title(
            f"{label}\n{summary['n_nodes']} nodes, NMI={nmi_str}",
            fontsize=9,
        )
        last_sc = sc

    fig.colorbar(last_sc, ax=axes, shrink=0.6, label="Mean PC1", location="right")
    fig.suptitle("Lens Function Comparison (DBSCAN, eps=0.5, n_cubes=30)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 0.92, 0.95])
    _save_figure(fig, "fig7_lens_comparison")


def fig8_employment_rate(embeddings, gmm_labels, outcomes):
    """Figure 8: Mapper graph coloured by employment rate."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    _, node_means = _compute_node_colors(graph, outcomes["employment_rate"])

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_means,
        sizes,
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
    )
    fig.colorbar(sc, ax=ax, shrink=0.8, label="Mean Employment Rate")
    ax.set_title("Mapper Graph — Employment Rate (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig8_employment_rate")


def fig9_churning_rate(embeddings, gmm_labels, outcomes):
    """Figure 9: Mapper graph coloured by churning rate."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    _, node_means = _compute_node_colors(graph, outcomes["churning_rate"])

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_means,
        sizes,
        cmap="YlOrRd",
        vmin=0,
        vmax=np.percentile(outcomes["churning_rate"], 98),
    )
    fig.colorbar(sc, ax=ax, shrink=0.8, label="Mean Churning Rate")
    ax.set_title("Mapper Graph — Churning Rate (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig9_churning_rate")


def fig10_final_income(embeddings, gmm_labels, outcomes):
    """Figure 10: Mapper graph coloured by final income band."""
    graph, G, pos, sizes = _build_graph_for_config(embeddings)
    _, node_means = _compute_node_colors(graph, outcomes["final_income_band"].astype(np.float64))

    fig, ax = plt.subplots(figsize=FIGSIZE_FULL)
    sc = _draw_mapper_graph(
        ax,
        G,
        pos,
        node_means,
        sizes,
        cmap="RdYlGn",
        vmin=0,
        vmax=2,
    )
    cb = fig.colorbar(sc, ax=ax, shrink=0.8, ticks=[0, 1, 2])
    cb.ax.set_yticklabels(["Low", "Mid", "High"])
    cb.set_label("Mean Final Income Band")
    ax.set_title("Mapper Graph — Final Income Band (DBSCAN, eps=0.5)")
    _save_figure(fig, "fig10_final_income")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Loading data...")
    embeddings = np.load(RESULTS_DIR / "embeddings.npy")
    with open(RESULTS_DIR / "05_analysis.json") as f:
        analysis = json.load(f)
    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)
    logger.info(
        "Loaded %d embeddings, %d regimes",
        len(embeddings),
        analysis["regimes"]["k_optimal"],
    )

    logger.info("Generating Figure 1: PC1 gradient...")
    fig1_pc1_gradient(embeddings, gmm_labels)

    logger.info("Generating Figure 2: L2 norm...")
    fig2_l2_norm(embeddings, gmm_labels)

    logger.info("Generating Figure 3: Regime labels...")
    fig3_regime_labels(embeddings, gmm_labels)

    logger.info("Generating Figure 4: Sub-regime highlight...")
    fig4_subregime_highlight(embeddings, gmm_labels)

    logger.info("Generating Figure 5: Eps sensitivity...")
    fig5_eps_comparison(embeddings, gmm_labels)

    logger.info("Generating Figure 6: DBSCAN vs Agglomerative...")
    fig6_dbscan_vs_agglom(embeddings, gmm_labels)

    logger.info("Generating Figure 7: Lens comparison...")
    fig7_lens_comparison(embeddings, gmm_labels)

    # Load trajectory outcomes if available
    outcomes_path = RESULTS_DIR / "trajectory_outcomes.npz"
    if outcomes_path.exists():
        outcomes = dict(np.load(outcomes_path))
        logger.info("Loaded trajectory outcomes (%d variables)", len(outcomes))

        logger.info("Generating Figure 8: Employment rate...")
        fig8_employment_rate(embeddings, gmm_labels, outcomes)

        logger.info("Generating Figure 9: Churning rate...")
        fig9_churning_rate(embeddings, gmm_labels, outcomes)

        logger.info("Generating Figure 10: Final income band...")
        fig10_final_income(embeddings, gmm_labels, outcomes)
    else:
        logger.warning(
            "No trajectory_outcomes.npz found — skipping Figs 8–10. Run reconstruct_trajectory_outcomes first."
        )

    logger.info("All figures saved to %s", FIGURES_DIR)


if __name__ == "__main__":
    main()
