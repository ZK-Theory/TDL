"""
ParaView/PyVista Script for Financial Regime Comparison Visualization.

This script creates side-by-side visualizations comparing the topological structure
of financial market regimes using Rips complex evolution and persistence diagrams.

Compares:
    - Crisis Period: 2008 Global Financial Crisis (Sep 2008)
    - Normal Period: Pre-crisis normal market (Jun 2007)

Visualizations:
    1. Side-by-side Rips complex with edges at fixed filtration value
    2. Persistence diagram overlay (crisis vs normal, color-coded)
    3. Optional filtration sweep animation

Usage with PyVista (fallback):
    python financial_tda/viz/paraview_scripts/regime_compare.py

Usage with ParaView pvpython:
    pvpython financial_tda/viz/paraview_scripts/regime_compare.py

Requirements:
    pip install pyvista numpy pandas yfinance gudhi giotto-tda matplotlib

License: MIT
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

# Try to import ParaView modules
try:
    from paraview.simple import *

    HAS_PARAVIEW = True
    logger = logging.getLogger(__name__)
    logger.info("ParaView Python modules loaded successfully")
except ImportError:
    HAS_PARAVIEW = False
    logger = logging.getLogger(__name__)
    logger.warning("ParaView Python modules not available, falling back to PyVista")

    # Fall back to PyVista
    try:
        import pyvista as pv

        HAS_PYVISTA = True
    except ImportError:
        logger.error("Neither ParaView nor PyVista available. Please install one.")
        sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from financial_tda.topology.embedding import optimal_tau, takens_embedding
from financial_tda.topology.filtration import (
    compute_persistence_statistics,
    compute_persistence_vr,
    get_persistence_pairs,
)

# Default paths and parameters
DEFAULT_OUTPUT_DIR = Path("financial_tda/viz/outputs")
CRISIS_PERIOD = ("2008-08-01", "2008-10-31")  # Aug-Oct 2008 - Lehman collapse period
NORMAL_PERIOD = ("2007-04-01", "2007-06-30")  # Apr-Jun 2007 - Pre-crisis
DEFAULT_SYMBOL = "^GSPC"  # S&P 500 index
DEFAULT_DELAY = 5  # Default Takens delay if not auto-computed


def fetch_market_data(symbol: str, start_date: str, end_date: str) -> NDArray[np.floating]:
    """
    Fetch market data for a specified period.

    Args:
        symbol: Ticker symbol (e.g., "^GSPC" for S&P 500)
        start_date: Start date in "YYYY-MM-DD" format
        end_date: End date in "YYYY-MM-DD" format

    Returns:
        1D array of log returns
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Install with: pip install yfinance")
        sys.exit(1)

    logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")

    # Download data
    df = yf.download(symbol, start=start_date, end=end_date, progress=False)

    if df.empty:
        raise ValueError(f"No data returned for {symbol} in specified period")

    # Compute log returns
    prices = df["Close"].values.flatten()  # Ensure 1D array
    log_returns = np.diff(np.log(prices))

    logger.info(f"Retrieved {len(log_returns)} log returns")

    return log_returns


def prepare_regime_data(
    crisis_period: tuple[str, str] = CRISIS_PERIOD,
    normal_period: tuple[str, str] = NORMAL_PERIOD,
    symbol: str = DEFAULT_SYMBOL,
    delay: int | None = None,
    dimension: int = 3,
) -> tuple[NDArray[np.floating], NDArray[np.floating], dict]:
    """
    Prepare Takens embeddings for crisis and normal market periods.

    Args:
        crisis_period: Tuple of (start_date, end_date) for crisis
        normal_period: Tuple of (start_date, end_date) for normal period
        symbol: Market ticker symbol
        delay: Takens delay parameter (if None, computed via optimal_tau)
        dimension: Takens embedding dimension

    Returns:
        Tuple of (crisis_embedding, normal_embedding, metadata_dict)
    """
    logger.info("=" * 60)
    logger.info("REGIME DATA PREPARATION")
    logger.info("=" * 60)

    # Fetch crisis data
    crisis_returns = fetch_market_data(symbol, crisis_period[0], crisis_period[1])

    # Fetch normal data
    normal_returns = fetch_market_data(symbol, normal_period[0], normal_period[1])

    # Compute optimal delay if not provided
    if delay is None:
        # Check if we have enough data for optimal_tau (requires 50+ samples)
        if len(crisis_returns) >= 50:
            delay = optimal_tau(crisis_returns, max_lag=20)
            logger.info(f"Computed optimal delay: {delay}")
        else:
            delay = DEFAULT_DELAY
            logger.info(f"Time series too short for optimal_tau, using default delay: {delay}")

    # Create Takens embeddings
    logger.info(f"Creating Takens embeddings (delay={delay}, dimension={dimension})")

    crisis_embedding = takens_embedding(crisis_returns, delay=delay, dimension=dimension)
    normal_embedding = takens_embedding(normal_returns, delay=delay, dimension=dimension)

    logger.info(f"Crisis embedding shape: {crisis_embedding.shape}")
    logger.info(f"Normal embedding shape: {normal_embedding.shape}")

    # Prepare metadata
    metadata = {
        "symbol": symbol,
        "crisis_period": crisis_period,
        "normal_period": normal_period,
        "delay": delay,
        "dimension": dimension,
        "crisis_n_points": crisis_embedding.shape[0],
        "normal_n_points": normal_embedding.shape[0],
    }

    return crisis_embedding, normal_embedding, metadata


def export_point_cloud_vtk(
    point_cloud: NDArray[np.floating],
    output_path: Path,
    scalar_name: str = "time_index",
) -> None:
    """
    Export point cloud as VTK PolyData file (.vtp).

    Args:
        point_cloud: 2D array of shape (n_points, 3) for 3D embedding
        output_path: Path to output .vtp file
        scalar_name: Name for scalar field (time ordering)
    """
    try:
        import pyvista as pv
    except ImportError:
        logger.error("PyVista required for VTK export. Install with: pip install pyvista")
        sys.exit(1)

    # Create PyVista PolyData
    mesh = pv.PolyData(point_cloud)

    # Add time index as scalar (for potential coloring by trajectory order)
    mesh[scalar_name] = np.arange(len(point_cloud))

    # Save to VTK format
    mesh.save(str(output_path))
    logger.info(f"Exported point cloud to {output_path}")


def compute_rips_edges(
    point_cloud: NDArray[np.floating],
    filtration_value: float,
) -> NDArray[np.integer]:
    """
    Compute Rips complex edges at a fixed filtration value.

    Args:
        point_cloud: 2D array of shape (n_points, n_dims)
        filtration_value: Distance threshold for edge creation

    Returns:
        2D array of shape (n_edges, 2) with edge indices
    """
    from scipy.spatial.distance import pdist, squareform

    # Compute pairwise distances
    distances = pdist(point_cloud)
    distance_matrix = squareform(distances)

    # Find edges: pairs (i, j) where i < j and distance <= threshold
    edge_pairs = np.argwhere(
        (distance_matrix <= filtration_value)
        & (distance_matrix > 0)
        & (np.triu(np.ones_like(distance_matrix), k=1) > 0)
    )

    logger.info(f"Computed {len(edge_pairs)} edges at filtration value {filtration_value:.4f}")

    return edge_pairs


def create_rips_lines_mesh(
    point_cloud: NDArray[np.floating],
    edge_indices: NDArray[np.integer],
) -> "pv.PolyData":
    """
    Create PyVista mesh for Rips complex edges.

    Args:
        point_cloud: 2D array of shape (n_points, 3) for 3D embedding
        edge_indices: 2D array of shape (n_edges, 2) with edge vertex indices

    Returns:
        PyVista PolyData mesh with lines representing edges
    """
    try:
        import pyvista as pv
    except ImportError:
        logger.error("PyVista required. Install with: pip install pyvista")
        sys.exit(1)

    # Create lines from edge indices
    lines = []
    for i, j in edge_indices:
        lines.extend([2, i, j])  # Format: [n_points, point_i, point_j]

    lines = np.array(lines)

    # Create PolyData mesh
    mesh = pv.PolyData(point_cloud, lines=lines)

    logger.info(f"Created Rips mesh with {len(edge_indices)} edges")

    return mesh


def visualize_side_by_side_rips(
    crisis_embedding: NDArray[np.floating],
    normal_embedding: NDArray[np.floating],
    output_dir: Path,
    filtration_percentile: float = 50,
) -> None:
    """
    Create side-by-side visualization of Rips complex for crisis vs normal periods.

    Args:
        crisis_embedding: Crisis period point cloud (n_points, 3)
        normal_embedding: Normal period point cloud (n_points, 3)
        output_dir: Output directory for renders
        filtration_percentile: Percentile of pairwise distances to use as threshold
    """
    try:
        import pyvista as pv
    except ImportError:
        logger.error("PyVista required. Install with: pip install pyvista")
        sys.exit(1)

    from scipy.spatial.distance import pdist

    logger.info("=" * 60)
    logger.info("Step 2: Side-by-Side Rips Complex Visualization")
    logger.info("=" * 60)

    # Compute filtration thresholds
    crisis_distances = pdist(crisis_embedding)
    normal_distances = pdist(normal_embedding)

    crisis_threshold = float(np.percentile(crisis_distances, filtration_percentile))
    normal_threshold = float(np.percentile(normal_distances, filtration_percentile))

    logger.info(f"Crisis filtration threshold: {crisis_threshold:.4f}")
    logger.info(f"Normal filtration threshold: {normal_threshold:.4f}")

    # Compute Rips edges
    crisis_edges = compute_rips_edges(crisis_embedding, crisis_threshold)
    normal_edges = compute_rips_edges(normal_embedding, normal_threshold)

    # Create meshes
    crisis_rips_mesh = create_rips_lines_mesh(crisis_embedding, crisis_edges)
    normal_rips_mesh = create_rips_lines_mesh(normal_embedding, normal_edges)

    # Save edge meshes for ParaView use
    crisis_edges_path = output_dir / "crisis_rips_edges.vtp"
    normal_edges_path = output_dir / "normal_rips_edges.vtp"
    crisis_rips_mesh.save(str(crisis_edges_path))
    normal_rips_mesh.save(str(normal_edges_path))
    logger.info(f"Saved edge meshes for ParaView: {crisis_edges_path}, {normal_edges_path}")

    # Create point meshes (glyphs)
    crisis_points = pv.PolyData(crisis_embedding)
    normal_points = pv.PolyData(normal_embedding)

    # Create side-by-side plotter
    plotter = pv.Plotter(shape=(1, 2), window_size=[1920, 1080], off_screen=True)

    # --- LEFT VIEW: Crisis Period ---
    plotter.subplot(0, 0)
    plotter.add_text(
        "Crisis: Aug-Oct 2008\nLehman Brothers Collapse",
        position="upper_edge",
        font_size=14,
        color="darkred",
        font="arial",
    )

    # Add edges (colored by index as proxy for persistence/birth time)
    edge_scalars = np.arange(len(crisis_edges))
    crisis_rips_mesh["edge_index"] = edge_scalars
    plotter.add_mesh(
        crisis_rips_mesh,
        scalars="edge_index",
        cmap="Reds",
        line_width=2,
        opacity=0.7,
        show_scalar_bar=False,
    )

    # Add point glyphs
    plotter.add_mesh(
        crisis_points,
        color="darkred",
        point_size=10,
        render_points_as_spheres=True,
    )

    plotter.camera_position = "iso"
    plotter.add_axes()
    plotter.background_color = "white"

    # --- RIGHT VIEW: Normal Period ---
    plotter.subplot(0, 1)
    plotter.add_text(
        "Normal: Apr-Jun 2007\nPre-Crisis Market",
        position="upper_edge",
        font_size=14,
        color="darkgreen",
        font="arial",
    )

    # Add edges
    edge_scalars = np.arange(len(normal_edges))
    normal_rips_mesh["edge_index"] = edge_scalars
    plotter.add_mesh(
        normal_rips_mesh,
        scalars="edge_index",
        cmap="Greens",
        line_width=2,
        opacity=0.7,
        show_scalar_bar=False,
    )

    # Add point glyphs
    plotter.add_mesh(
        normal_points,
        color="darkgreen",
        point_size=10,
        render_points_as_spheres=True,
    )

    plotter.camera_position = "iso"
    plotter.add_axes()
    plotter.background_color = "white"

    # Link cameras for synchronized viewing
    plotter.link_views()

    # Render before screenshot
    plotter.render()

    # Save screenshot
    output_path = output_dir / "regime_compare_side_by_side.png"
    plotter.screenshot(str(output_path), return_img=False)
    logger.info(f"Saved side-by-side render: {output_path}")

    plotter.close()

    logger.info("Step 2 Complete: Side-by-side Rips visualization rendered")


def visualize_side_by_side_rips_paraview(
    crisis_embedding: NDArray[np.floating],
    normal_embedding: NDArray[np.floating],
    output_dir: Path,
    filtration_percentile: float = 50,
) -> None:
    """
    Create side-by-side visualization using ParaView native API.

    Args:
        crisis_embedding: Crisis period point cloud (n_points, 3)
        normal_embedding: Normal period point cloud (n_points, 3)
        output_dir: Output directory for renders and state file
        filtration_percentile: Percentile of pairwise distances for threshold
    """
    if not HAS_PARAVIEW:
        logger.error("ParaView Python modules not available. Run with pvpython.")
        return

    from scipy.spatial.distance import pdist

    logger.info("=" * 60)
    logger.info("Step 2 (ParaView): Side-by-Side Rips Complex Visualization")
    logger.info("=" * 60)

    # Compute filtration thresholds
    crisis_distances = pdist(crisis_embedding)
    normal_distances = pdist(normal_embedding)

    crisis_threshold = float(np.percentile(crisis_distances, filtration_percentile))
    normal_threshold = float(np.percentile(normal_distances, filtration_percentile))

    logger.info(f"Crisis filtration threshold: {crisis_threshold:.4f}")
    logger.info(f"Normal filtration threshold: {normal_threshold:.4f}")

    # Compute Rips edges
    crisis_edges = compute_rips_edges(crisis_embedding, crisis_threshold)
    normal_edges = compute_rips_edges(normal_embedding, normal_threshold)

    # Save edges and points as VTK PolyData for ParaView
    crisis_edges_path = output_dir / "crisis_rips_edges.vtp"
    normal_edges_path = output_dir / "normal_rips_edges.vtp"

    _save_edges_vtk(crisis_embedding, crisis_edges, crisis_edges_path)
    _save_edges_vtk(normal_embedding, normal_edges, normal_edges_path)

    # Create ParaView layout with two views
    layout = CreateLayout("Horizontal Split View")

    # === LEFT VIEW: Crisis ===
    renderView1 = CreateView("RenderView")
    layout.AssignView(0, renderView1)
    renderView1.ViewSize = [960, 1080]
    renderView1.Background = [1.0, 1.0, 1.0]

    # Load crisis edges
    crisis_reader = XMLPolyDataReader(FileName=str(crisis_edges_path))
    crisis_display = Show(crisis_reader, renderView1)
    crisis_display.Representation = "Wireframe"
    crisis_display.AmbientColor = [0.5, 0.0, 0.0]
    crisis_display.DiffuseColor = [0.8, 0.0, 0.0]
    crisis_display.LineWidth = 2.0

    # Add title
    text1 = Text()
    text1.Text = "Crisis: Aug-Oct 2008\nLehman Brothers Collapse"
    text1Display = Show(text1, renderView1)
    text1Display.FontSize = 14
    text1Display.Color = [0.5, 0.0, 0.0]
    text1Display.WindowLocation = "UpperCenter"

    # Camera and lighting
    renderView1.ResetCamera()
    renderView1.CameraPosition = [1, 1, 1]
    renderView1.CameraViewUp = [0, 0, 1]

    # === RIGHT VIEW: Normal ===
    renderView2 = CreateView("RenderView")
    layout.AssignView(1, renderView2)
    renderView2.ViewSize = [960, 1080]
    renderView2.Background = [1.0, 1.0, 1.0]

    # Load normal edges
    normal_reader = XMLPolyDataReader(FileName=str(normal_edges_path))
    normal_display = Show(normal_reader, renderView2)
    normal_display.Representation = "Wireframe"
    normal_display.AmbientColor = [0.0, 0.5, 0.0]
    normal_display.DiffuseColor = [0.0, 0.6, 0.0]
    normal_display.LineWidth = 2.0

    # Add title
    text2 = Text()
    text2.Text = "Normal: Apr-Jun 2007\nPre-Crisis Market"
    text2Display = Show(text2, renderView2)
    text2Display.FontSize = 14
    text2Display.Color = [0.0, 0.5, 0.0]
    text2Display.WindowLocation = "UpperCenter"

    # Camera and lighting (match left view)
    renderView2.ResetCamera()
    renderView2.CameraPosition = [1, 1, 1]
    renderView2.CameraViewUp = [0, 0, 1]

    # Save screenshot
    output_path = output_dir / "regime_compare_side_by_side_paraview.png"
    SaveScreenshot(str(output_path), layout, ImageResolution=[1920, 1080])
    logger.info(f"Saved ParaView render: {output_path}")

    # Save ParaView state file
    state_path = output_dir / "regime_compare_paraview.pvsm"
    SaveState(str(state_path))
    logger.info(f"Saved ParaView state file: {state_path}")

    logger.info("Step 2 (ParaView) Complete: ParaView visualization rendered")


def _save_edges_vtk(
    points: NDArray[np.floating],
    edges: NDArray[np.integer],
    output_path: Path,
) -> None:
    """
    Save points and edges as VTK PolyData file.

    Args:
        points: Point coordinates (n_points, 3)
        edges: Edge indices (n_edges, 2)
        output_path: Output .vtp file path
    """
    try:
        import pyvista as pv
    except ImportError:
        logger.error("PyVista required for VTK export")
        sys.exit(1)

    # Create lines
    lines = []
    for i, j in edges:
        lines.extend([2, i, j])
    lines = np.array(lines)

    # Create PolyData
    mesh = pv.PolyData(points, lines=lines)
    mesh.save(str(output_path))


def visualize_persistence_overlay(
    crisis_embedding: NDArray[np.floating],
    normal_embedding: NDArray[np.floating],
    output_dir: Path,
    persistence_threshold: float = 0.01,
) -> None:
    """
    Create persistence diagram overlay comparing crisis vs normal regimes.

    Args:
        crisis_embedding: Crisis period point cloud (n_points, 3)
        normal_embedding: Normal period point cloud (n_points, 3)
        output_dir: Output directory for renders
        persistence_threshold: Threshold for significant features
    """
    logger.info("=" * 60)
    logger.info("Step 3: Persistence Diagram Overlay")
    logger.info("=" * 60)

    # Compute persistence diagrams
    logger.info("Computing persistence diagrams...")
    crisis_diagram = compute_persistence_vr(crisis_embedding, homology_dimensions=(0, 1, 2))
    normal_diagram = compute_persistence_vr(normal_embedding, homology_dimensions=(0, 1, 2))

    logger.info(f"Crisis: {len(crisis_diagram)} features")
    logger.info(f"Normal: {len(normal_diagram)} features")

    # Compute statistics
    crisis_stats = {}
    normal_stats = {}
    for dim in [0, 1, 2]:
        crisis_stats[dim] = compute_persistence_statistics(crisis_diagram, dimension=dim)
        normal_stats[dim] = compute_persistence_statistics(normal_diagram, dimension=dim)

    logger.info("Topological summary statistics:")
    for dim in [0, 1, 2]:
        logger.info(
            f"  H{dim} - Crisis: {crisis_stats[dim]['n_features']} features, "
            f"total persistence: {crisis_stats[dim]['total_persistence']:.4f}"
        )
        logger.info(
            f"  H{dim} - Normal: {normal_stats[dim]['n_features']} features, "
            f"total persistence: {normal_stats[dim]['total_persistence']:.4f}"
        )

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(12, 10))

    # Define colors and markers for different dimensions
    colors_crisis = {0: "#8B0000", 1: "#DC143C", 2: "#FF6347"}  # Dark to light red
    colors_normal = {0: "#006400", 1: "#228B22", 2: "#32CD32"}  # Dark to light green
    markers = {0: "o", 1: "s", 2: "^"}  # Circle, square, triangle
    labels = {0: "H₀ (Components)", 1: "H₁ (Loops)", 2: "H₂ (Voids)"}

    # Plot crisis persistence diagrams
    for dim in [0, 1, 2]:
        pairs = get_persistence_pairs(crisis_diagram, dimension=dim)
        if len(pairs) > 0:
            # Filter out infinite persistence
            finite_mask = np.isfinite(pairs[:, 1])
            pairs = pairs[finite_mask]

            if len(pairs) > 0:
                ax.scatter(
                    pairs[:, 0],
                    pairs[:, 1],
                    c=colors_crisis[dim],
                    marker=markers[dim],
                    s=100,
                    alpha=0.6,
                    edgecolors="darkred",
                    linewidth=1.5,
                    label=f"Crisis {labels[dim]}",
                )

    # Plot normal persistence diagrams
    for dim in [0, 1, 2]:
        pairs = get_persistence_pairs(normal_diagram, dimension=dim)
        if len(pairs) > 0:
            # Filter out infinite persistence
            finite_mask = np.isfinite(pairs[:, 1])
            pairs = pairs[finite_mask]

            if len(pairs) > 0:
                ax.scatter(
                    pairs[:, 0],
                    pairs[:, 1],
                    c=colors_normal[dim],
                    marker=markers[dim],
                    s=100,
                    alpha=0.6,
                    edgecolors="darkgreen",
                    linewidth=1.5,
                    label=f"Normal {labels[dim]}",
                )

    # Add diagonal reference line (death = birth)
    all_births = np.concatenate([crisis_diagram[:, 0], normal_diagram[:, 0]])
    all_deaths = np.concatenate([crisis_diagram[:, 1], normal_diagram[:, 1]])
    finite_deaths = all_deaths[np.isfinite(all_deaths)]

    if len(finite_deaths) > 0:
        max_val = max(all_births.max(), finite_deaths.max())
        min_val = min(all_births.min(), finite_deaths.min())

        ax.plot(
            [min_val, max_val],
            [min_val, max_val],
            "k--",
            linewidth=2,
            alpha=0.5,
            label="Death = Birth",
        )

    # Formatting
    ax.set_xlabel("Birth", fontsize=14, fontweight="bold")
    ax.set_ylabel("Death", fontsize=14, fontweight="bold")
    ax.set_title(
        "Persistence Diagram: Crisis vs Normal Market Regimes",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="lower right", fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="box")

    # Add statistics text box
    stats_text = "Topological Summary:\n"
    stats_text += "─" * 35 + "\n"
    for dim in [0, 1, 2]:
        stats_text += f"H{dim} - Crisis: {crisis_stats[dim]['n_features']} features\n"
        stats_text += f"     Total pers: {crisis_stats[dim]['total_persistence']:.4f}\n"
        stats_text += f"H{dim} - Normal: {normal_stats[dim]['n_features']} features\n"
        stats_text += f"     Total pers: {normal_stats[dim]['total_persistence']:.4f}\n"

        # Count significant features
        crisis_pairs = get_persistence_pairs(crisis_diagram, dimension=dim)
        normal_pairs = get_persistence_pairs(normal_diagram, dimension=dim)

        if len(crisis_pairs) > 0:
            crisis_pers = crisis_pairs[:, 1] - crisis_pairs[:, 0]
            crisis_pers = crisis_pers[np.isfinite(crisis_pers)]
            crisis_sig = np.sum(crisis_pers > persistence_threshold)
            stats_text += f"     Significant (>{persistence_threshold:.3f}): {crisis_sig}\n"

        if len(normal_pairs) > 0:
            normal_pers = normal_pairs[:, 1] - normal_pairs[:, 0]
            normal_pers = normal_pers[np.isfinite(normal_pers)]
            normal_sig = np.sum(normal_pers > persistence_threshold)
            stats_text += f"     Significant (>{persistence_threshold:.3f}): {normal_sig}\n"

        stats_text += "\n"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        family="monospace",
    )

    plt.tight_layout()

    # Save figure
    output_path = output_dir / "persistence_overlay.png"
    plt.savefig(str(output_path), dpi=300, bbox_inches="tight")
    logger.info(f"Saved persistence overlay: {output_path}")
    plt.close()

    logger.info("Step 3 Complete: Persistence diagram overlay rendered")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Financial Regime Comparison ParaView Visualization")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for renders and VTK files",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=DEFAULT_SYMBOL,
        help="Market ticker symbol (default: ^GSPC)",
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=3,
        help="Takens embedding dimension (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=DEFAULT_DELAY,
        help="Takens delay parameter (default: 5)",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Financial Regime Comparison Visualization")
    logger.info(f"Output directory: {args.output_dir}")

    # Step 1: Prepare regime data
    crisis_embedding, normal_embedding, metadata = prepare_regime_data(
        symbol=args.symbol,
        delay=args.delay,
        dimension=args.dimension,
    )

    # Export point clouds as VTK files for ParaView/PyVista
    crisis_vtp_path = args.output_dir / "crisis_embedding.vtp"
    normal_vtp_path = args.output_dir / "normal_embedding.vtp"

    export_point_cloud_vtk(crisis_embedding, crisis_vtp_path)
    export_point_cloud_vtk(normal_embedding, normal_vtp_path)

    logger.info("=" * 60)
    logger.info("Step 1 Complete: Regime data prepared and exported")
    logger.info("=" * 60)
    logger.info(f"Crisis embedding: {crisis_vtp_path}")
    logger.info(f"Normal embedding: {normal_vtp_path}")
    logger.info(f"Metadata: {metadata}")

    # Save metadata for later steps
    metadata_path = args.output_dir / "regime_metadata.json"
    import json

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to {metadata_path}")

    # Step 2: Side-by-side Rips complex visualization
    if HAS_PARAVIEW:
        # Use ParaView native API (only when running with pvpython)
        visualize_side_by_side_rips_paraview(
            crisis_embedding=crisis_embedding,
            normal_embedding=normal_embedding,
            output_dir=args.output_dir,
            filtration_percentile=50,
        )
    else:
        # Fallback to PyVista
        visualize_side_by_side_rips(
            crisis_embedding=crisis_embedding,
            normal_embedding=normal_embedding,
            output_dir=args.output_dir,
            filtration_percentile=50,
        )

    # Step 3: Persistence diagram overlay
    visualize_persistence_overlay(
        crisis_embedding=crisis_embedding,
        normal_embedding=normal_embedding,
        output_dir=args.output_dir,
        persistence_threshold=0.01,
    )


if __name__ == "__main__":
    main()
