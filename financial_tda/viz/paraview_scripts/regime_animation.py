"""
Filtration Sweep Animation for Financial Regime Comparison.

This script creates an animation showing how the Rips complex evolves
as the filtration parameter increases, for both crisis and normal regimes.

Usage:
    python regime_animation.py --output-dir outputs --n-frames 60

Requirements:
    - Pre-generated VTK files from regime_compare.py
    - pyvista, numpy, imageio (for GIF creation)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

try:
    import pyvista as pv
except ImportError:
    print("ERROR: PyVista required. Install with: pip install pyvista")
    exit(1)

try:
    import imageio
except ImportError:
    print("ERROR: imageio required for GIF creation. Install with: pip install imageio")
    exit(1)

from scipy.spatial.distance import pdist

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("financial_tda/viz/outputs")


def load_embedding(vtp_path: Path) -> NDArray[np.floating]:
    """Load point cloud from VTP file."""
    mesh = pv.read(str(vtp_path))
    return np.array(mesh.points)


def compute_rips_edges_at_threshold(points: NDArray[np.floating], threshold: float) -> NDArray[np.integer]:
    """Compute Rips complex edges at given threshold."""
    from scipy.spatial.distance import squareform

    distance_matrix = squareform(pdist(points))
    edge_pairs = np.argwhere(
        (distance_matrix <= threshold) & (distance_matrix > 0) & (np.triu(np.ones_like(distance_matrix), k=1) > 0)
    )
    return edge_pairs


def create_frame(
    crisis_points: NDArray[np.floating],
    normal_points: NDArray[np.floating],
    threshold: float,
    frame_idx: int,
    total_frames: int,
) -> pv.Plotter:
    """
    Create a single animation frame at given filtration threshold.

    Args:
        crisis_points: Crisis embedding points
        normal_points: Normal embedding points
        threshold: Current filtration threshold
        frame_idx: Current frame number
        total_frames: Total number of frames

    Returns:
        PyVista plotter with the frame rendered
    """
    plotter = pv.Plotter(shape=(1, 2), window_size=[1920, 1080], off_screen=True)

    # Compute edges at current threshold
    crisis_edges = compute_rips_edges_at_threshold(crisis_points, threshold)
    normal_edges = compute_rips_edges_at_threshold(normal_points, threshold)

    # Create meshes
    crisis_mesh = create_rips_mesh(crisis_points, crisis_edges)
    normal_mesh = create_rips_mesh(normal_points, normal_edges)

    # LEFT: Crisis
    plotter.subplot(0, 0)
    title = f"Crisis: Aug-Oct 2008\nThreshold: {threshold:.4f}\n{len(crisis_edges)} edges"
    plotter.add_text(title, position="upper_edge", font_size=12, color="darkred")

    if len(crisis_edges) > 0:
        plotter.add_mesh(
            crisis_mesh,
            color="darkred",
            line_width=2,
            opacity=0.7,
            show_scalar_bar=False,
        )

    plotter.add_mesh(
        pv.PolyData(crisis_points),
        color="red",
        point_size=8,
        render_points_as_spheres=True,
    )
    plotter.camera_position = "iso"
    plotter.background_color = "white"

    # RIGHT: Normal
    plotter.subplot(0, 1)
    title = f"Normal: Apr-Jun 2007\nThreshold: {threshold:.4f}\n{len(normal_edges)} edges"
    plotter.add_text(title, position="upper_edge", font_size=12, color="darkgreen")

    if len(normal_edges) > 0:
        plotter.add_mesh(
            normal_mesh,
            color="darkgreen",
            line_width=2,
            opacity=0.7,
            show_scalar_bar=False,
        )

    plotter.add_mesh(
        pv.PolyData(normal_points),
        color="green",
        point_size=8,
        render_points_as_spheres=True,
    )
    plotter.camera_position = "iso"
    plotter.background_color = "white"

    # Link cameras
    plotter.link_views()

    # Progress indicator
    progress = f"Frame {frame_idx + 1}/{total_frames}"
    plotter.add_text(
        progress,
        position="lower_right",
        font_size=10,
        color="black",
    )

    return plotter


def create_rips_mesh(points: NDArray[np.floating], edges: NDArray[np.integer]) -> pv.PolyData:
    """Create PyVista mesh from points and edges."""
    if len(edges) == 0:
        return pv.PolyData()

    lines = []
    for i, j in edges:
        lines.extend([2, i, j])
    lines = np.array(lines)

    return pv.PolyData(points, lines=lines)


def create_filtration_animation(
    crisis_embedding_path: Path,
    normal_embedding_path: Path,
    output_dir: Path,
    n_frames: int = 60,
    fps: int = 10,
) -> None:
    """
    Create filtration sweep animation.

    Args:
        crisis_embedding_path: Path to crisis VTP file
        normal_embedding_path: Path to normal VTP file
        output_dir: Output directory for frames and GIF
        n_frames: Number of animation frames
        fps: Frames per second for output GIF
    """
    logger.info("=" * 60)
    logger.info("Filtration Sweep Animation")
    logger.info("=" * 60)

    # Load embeddings
    crisis_points = load_embedding(crisis_embedding_path)
    normal_points = load_embedding(normal_embedding_path)

    logger.info(f"Loaded crisis embedding: {crisis_points.shape}")
    logger.info(f"Loaded normal embedding: {normal_points.shape}")

    # Compute distance ranges
    crisis_distances = pdist(crisis_points)
    normal_distances = pdist(normal_points)

    min_threshold = 0.0
    max_threshold = max(
        np.percentile(crisis_distances, 75),
        np.percentile(normal_distances, 75),
    )

    logger.info(f"Threshold range: {min_threshold:.4f} to {max_threshold:.4f}")
    logger.info(f"Generating {n_frames} frames...")

    # Create frames directory
    frames_dir = output_dir / "animation_frames"
    frames_dir.mkdir(exist_ok=True)

    # Generate frames
    frame_paths = []
    thresholds = np.linspace(min_threshold, max_threshold, n_frames)

    for i, threshold in enumerate(thresholds):
        plotter = create_frame(crisis_points, normal_points, threshold, i, n_frames)

        frame_path = frames_dir / f"frame_{i:04d}.png"
        plotter.screenshot(str(frame_path))
        plotter.close()

        frame_paths.append(frame_path)

        if (i + 1) % 10 == 0:
            logger.info(f"Generated {i + 1}/{n_frames} frames")

    logger.info(f"All frames saved to {frames_dir}")

    # Create GIF
    logger.info("Creating animated GIF...")
    images = [imageio.imread(str(p)) for p in frame_paths]

    gif_path = output_dir / "filtration_animation.gif"
    imageio.mimsave(str(gif_path), images, fps=fps, loop=0)
    logger.info(f"Saved animation: {gif_path}")

    # Create MP4 if ffmpeg available
    try:
        mp4_path = output_dir / "filtration_animation.mp4"
        imageio.mimsave(str(mp4_path), images, fps=fps, codec="libx264")
        logger.info(f"Saved MP4: {mp4_path}")
    except Exception as e:
        logger.warning(f"Could not create MP4 (ffmpeg required): {e}")

    logger.info("=" * 60)
    logger.info("Animation complete!")
    logger.info("=" * 60)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Create filtration sweep animation for regime comparison")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "--n-frames",
        type=int,
        default=60,
        help="Number of animation frames (default: 60)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frames per second (default: 10)",
    )

    args = parser.parse_args()

    # Check for input files
    crisis_path = args.output_dir / "crisis_embedding.vtp"
    normal_path = args.output_dir / "normal_embedding.vtp"

    if not crisis_path.exists() or not normal_path.exists():
        logger.error("Input VTP files not found. Run regime_compare.py first.")
        return

    create_filtration_animation(
        crisis_embedding_path=crisis_path,
        normal_embedding_path=normal_path,
        output_dir=args.output_dir,
        n_frames=args.n_frames,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
