"""
3D Opportunity Terrain Visualization using PyVista.

This script creates a 3D terrain visualization where height represents
mobility values and color represents either mobility (continuous) or
basin membership (categorical). Critical points (minima, maxima, saddles)
can be annotated with glyphs.

Since ParaView Python bindings require a separate conda environment,
this implementation uses PyVista as a standalone alternative that can
run in the project's virtual environment.

Usage:
    python poverty_tda/viz/paraview_states/terrain_3d.py [options]

Options:
    --vti-path PATH       Path to VTK ImageData file (default: auto-generate sample)
    --critical-pts PATH   Path to critical points CSV (optional)
    --basins-csv PATH     Path to basin membership CSV (optional)
    --output-dir PATH     Output directory for renders (default: poverty_tda/viz/outputs/)
    --height-scale FLOAT  Vertical exaggeration factor (default: 0.0001)
    --color-mode MODE     Color mode: 'mobility' or 'basins' (default: mobility)
    --enable-shadows      Enable shadow rendering (slower but better depth)

Requirements:
    pip install pyvista matplotlib numpy pandas

License: Open Government Licence v3.0
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from matplotlib.colors import ListedColormap

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Default paths relative to project root
DEFAULT_OUTPUT_DIR = Path("poverty_tda/viz/outputs")
DEFAULT_VTI_PATH = Path("poverty_tda/data/processed/mobility_surface.vti")

# England/Wales bounding box (EPSG:27700)
ENGLAND_WALES_BOUNDS = {
    "x_min": 82672.0,
    "x_max": 655604.0,
    "y_min": 5337.0,
    "y_max": 657534.0,
}

# Visualization parameters
DEFAULT_HEIGHT_SCALE = 0.0001  # Vertical exaggeration (meters → visual units)
DEFAULT_WINDOW_SIZE = (1920, 1080)
DEFAULT_BACKGROUND_COLOR = "white"

# Basin color palette (categorical, high contrast)
BASIN_COLORS = [
    "#e41a1c",  # Red
    "#377eb8",  # Blue
    "#4daf4a",  # Green
    "#984ea3",  # Purple
    "#ff7f00",  # Orange
    "#ffff33",  # Yellow
    "#a65628",  # Brown
    "#f781bf",  # Pink
    "#999999",  # Gray
    "#66c2a5",  # Teal
    "#fc8d62",  # Salmon
    "#8da0cb",  # Lavender
]

# Critical point glyph parameters
GLYPH_COLORS = {
    "minimum": "#e41a1c",  # Red - poverty trap centers
    "maximum": "#4daf4a",  # Green - opportunity peaks
    "saddle": "#ff7f00",  # Orange - barriers
}

GLYPH_BASE_SCALE = 5000.0  # Base glyph size in meters
GLYPH_PERSISTENCE_FACTOR = 2.0  # Multiplier for persistence scaling


def load_mobility_surface(vti_path: Path) -> pv.ImageData:
    """
    Load mobility surface from VTK ImageData file.

    Args:
        vti_path: Path to .vti file containing mobility surface.

    Returns:
        PyVista ImageData mesh with mobility scalar field.

    Raises:
        FileNotFoundError: If VTI file doesn't exist.
        ValueError: If VTI file lacks mobility scalar field.
    """
    if not vti_path.exists():
        raise FileNotFoundError(f"VTI file not found: {vti_path}")

    logger.info(f"Loading mobility surface from: {vti_path}")
    mesh = pv.read(str(vti_path))

    # Check for scalar field
    if mesh.n_arrays == 0:
        raise ValueError(f"VTI file has no scalar fields: {vti_path}")

    scalar_name = mesh.array_names[0]  # Use first scalar field
    logger.info(
        f"Loaded {mesh.n_points} points, scalar field: '{scalar_name}', "
        f"range: [{mesh[scalar_name].min():.3f}, {mesh[scalar_name].max():.3f}]"
    )

    return mesh


def generate_sample_surface(
    resolution: int = 100,
    output_path: Path | None = None,
) -> pv.ImageData:
    """
    Generate a synthetic mobility surface for testing/demonstration.

    Creates a surface with multiple Gaussian peaks and valleys to
    simulate opportunity landscape, plus basin membership IDs.

    Args:
        resolution: Grid resolution (default 100 for fast rendering).
        output_path: Optional path to save generated surface as .vti.

    Returns:
        PyVista ImageData with synthetic mobility field and basin IDs.
    """
    logger.info(f"Generating synthetic {resolution}×{resolution} mobility surface")

    # Use simplified bounds for faster generation
    x = np.linspace(100000, 600000, resolution)
    y = np.linspace(50000, 600000, resolution)
    xx, yy = np.meshgrid(x, y)

    # Create multi-scale opportunity landscape
    # High opportunity peaks (urban centers)
    mobility = 0.3 * np.exp(-((xx - 300000) ** 2 + (yy - 400000) ** 2) / 1e11)
    mobility += 0.25 * np.exp(-((xx - 450000) ** 2 + (yy - 200000) ** 2) / 8e10)

    # Low opportunity valleys (poverty traps)
    mobility += 0.15 * np.exp(-((xx - 200000) ** 2 + (yy - 150000) ** 2) / 6e10)
    mobility -= 0.2 * np.exp(-((xx - 350000) ** 2 + (yy - 300000) ** 2) / 1.2e11)

    # Add noise for realism
    mobility += 0.05 * np.random.randn(*xx.shape)

    # Normalize to [0, 1] range
    mobility = (mobility - mobility.min()) / (mobility.max() - mobility.min())

    # Generate synthetic basin membership (Voronoi-style regions)
    # Place 5 basin centers (minima)
    basin_centers = [
        (200000, 150000),  # Basin 0 - SW low
        (350000, 300000),  # Basin 1 - Central low
        (300000, 400000),  # Basin 2 - NW high
        (450000, 200000),  # Basin 3 - SE high
        (500000, 500000),  # Basin 4 - NE mid
    ]

    # Assign each point to nearest basin center
    basins = np.zeros_like(mobility, dtype=np.int32)
    for i in range(resolution):
        for j in range(resolution):
            px, py = xx[i, j], yy[i, j]
            distances = [np.sqrt((px - cx) ** 2 + (py - cy) ** 2) for cx, cy in basin_centers]
            basins[i, j] = np.argmin(distances)

    # Create VTK ImageData
    spacing_x = (x.max() - x.min()) / (resolution - 1)
    spacing_y = (y.max() - y.min()) / (resolution - 1)

    mesh = pv.ImageData(
        dimensions=(resolution, resolution, 1),
        spacing=(spacing_x, spacing_y, 1.0),
        origin=(x.min(), y.min(), 0.0),
    )
    mesh.point_data["mobility"] = mobility.flatten(order="F")
    mesh.point_data["basin_id"] = basins.flatten(order="F")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.save(str(output_path))
        logger.info(f"Saved synthetic surface to: {output_path}")

    logger.info(
        f"Generated mobility range: [{mobility.min():.3f}, {mobility.max():.3f}], " f"basins: {len(basin_centers)}"
    )

    return mesh


def setup_plotter(
    window_size: tuple[int, int] = DEFAULT_WINDOW_SIZE,
    background_color: str = DEFAULT_BACKGROUND_COLOR,
    enable_shadows: bool = False,
) -> pv.Plotter:
    """
    Create and configure PyVista plotter for 3D terrain visualization.

    Args:
        window_size: (width, height) in pixels.
        background_color: Background color for rendering.
        enable_shadows: Enable shadow rendering (slower but better depth).

    Returns:
        Configured PyVista Plotter instance.
    """
    logger.info(f"Setting up plotter with size {window_size}")

    plotter = pv.Plotter(
        off_screen=True,  # Headless rendering for batch export
        window_size=window_size,
    )
    plotter.set_background(background_color)

    # Configure lighting for terrain depth perception
    # Key light: main illumination from above-left
    light_key = pv.Light(
        position=(-5e5, 5e5, 8e5),
        intensity=0.8,
        light_type="scene light",
    )
    plotter.add_light(light_key)

    # Fill light: softer illumination from right to reduce harsh shadows
    light_fill = pv.Light(
        position=(5e5, 3e5, 5e5),
        intensity=0.3,
        light_type="scene light",
    )
    plotter.add_light(light_fill)

    # Rim light: subtle backlighting for edge definition
    light_rim = pv.Light(
        position=(0, -5e5, 4e5),
        intensity=0.2,
        light_type="scene light",
    )
    plotter.add_light(light_rim)

    if enable_shadows:
        plotter.enable_shadows()
        logger.info("Shadow rendering enabled")

    return plotter


def create_terrain_mesh(
    surface: pv.ImageData,
    height_scale: float = DEFAULT_HEIGHT_SCALE,
    scalar_name: str | None = None,
) -> pv.PolyData:
    """
    Create 3D terrain mesh by warping surface by scalar values.

    Args:
        surface: Input ImageData with scalar field.
        height_scale: Vertical exaggeration multiplier.
        scalar_name: Name of scalar field to use for warping.
            If None, uses the first available scalar.

    Returns:
        Warped terrain as PolyData mesh.
    """
    if scalar_name is None:
        scalar_name = surface.array_names[0]

    logger.info(f"Creating terrain mesh with height_scale={height_scale}, " f"scalar='{scalar_name}'")

    # Convert to PolyData for warping
    terrain = surface.cast_to_unstructured_grid().extract_surface()

    # Warp by scalar (height = mobility × scale)
    terrain = terrain.warp_by_scalar(
        scalars=scalar_name,
        factor=height_scale,
        normal=(0, 0, 1),
    )

    logger.info(f"Terrain mesh created: {terrain.n_points} points, {terrain.n_cells} cells")

    return terrain


def create_basin_colormap(n_basins: int) -> list[str]:
    """
    Create a categorical colormap for basin visualization.

    Args:
        n_basins: Number of distinct basins.

    Returns:
        List of hex color codes.
    """
    if n_basins <= len(BASIN_COLORS):
        return BASIN_COLORS[:n_basins]

    # Generate additional colors if needed
    cmap = plt.cm.get_cmap("tab20", n_basins)
    return [plt.matplotlib.colors.rgb2hex(cmap(i)) for i in range(n_basins)]


def load_critical_points(csv_path: Path) -> dict:
    """
    Load critical points from CSV file.

    Expected CSV columns:
        - x, y, z: Coordinates
        - value: Scalar field value at critical point
        - point_type: 0=minimum, 1=saddle, 2=maximum
        - persistence: Optional persistence value

    Args:
        csv_path: Path to critical points CSV.

    Returns:
        Dictionary with keys: 'minima', 'maxima', 'saddles'
        Each containing list of dicts with point properties.

    Raises:
        FileNotFoundError: If CSV doesn't exist.
        ValueError: If CSV is malformed.
    """
    import pandas as pd

    if not csv_path.exists():
        raise FileNotFoundError(f"Critical points CSV not found: {csv_path}")

    logger.info(f"Loading critical points from: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = ["x", "y", "z", "value", "point_type"]

    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Critical points CSV must have columns {required_cols}, " f"got {df.columns.tolist()}")

    # Add default persistence if not present
    if "persistence" not in df.columns:
        df["persistence"] = 0.1  # Default value

    # Classify by type
    minima = df[df["point_type"] == 0].to_dict("records")
    saddles = df[df["point_type"] == 1].to_dict("records")
    maxima = df[df["point_type"] == 2].to_dict("records")

    logger.info(f"Loaded {len(minima)} minima, {len(maxima)} maxima, {len(saddles)} saddles")

    return {"minima": minima, "maxima": maxima, "saddles": saddles}


def generate_sample_critical_points(
    surface: pv.ImageData,
    height_scale: float = DEFAULT_HEIGHT_SCALE,
) -> dict:
    """
    Generate synthetic critical points from mobility surface.

    Identifies local minima and maxima using simple peak detection
    on the synthetic surface.

    Args:
        surface: Mobility surface mesh.
        height_scale: Vertical exaggeration (for z-coordinate calculation).

    Returns:
        Dictionary with keys: 'minima', 'maxima', 'saddles'
        Each containing list of dicts with point properties.
    """
    from scipy.ndimage import maximum_filter, minimum_filter

    logger.info("Generating synthetic critical points from surface")

    # Extract mobility field
    mobility = surface["mobility"].reshape(surface.dimensions[0], surface.dimensions[1])

    # Detect local minima and maxima
    min_filter = minimum_filter(mobility, size=5)
    max_filter = maximum_filter(mobility, size=5)

    is_minimum = (mobility == min_filter) & (mobility < 0.3)
    is_maximum = (mobility == max_filter) & (mobility > 0.7)

    minima_idx = np.argwhere(is_minimum)
    maxima_idx = np.argwhere(is_maximum)

    # Convert indices to coordinates
    origin = surface.origin
    spacing = surface.spacing

    minima = []
    for i, j in minima_idx[:10]:  # Limit to 10 strongest
        x = origin[0] + i * spacing[0]
        y = origin[1] + j * spacing[1]
        value = mobility[i, j]
        z = value * height_scale
        persistence = (1.0 - value) * 0.2  # Synthetic persistence

        minima.append(
            {
                "x": x,
                "y": y,
                "z": z,
                "value": value,
                "point_type": 0,
                "persistence": persistence,
            }
        )

    maxima = []
    for i, j in maxima_idx[:10]:  # Limit to 10 strongest
        x = origin[0] + i * spacing[0]
        y = origin[1] + j * spacing[1]
        value = mobility[i, j]
        z = value * height_scale
        persistence = value * 0.2  # Synthetic persistence

        maxima.append(
            {
                "x": x,
                "y": y,
                "z": z,
                "value": value,
                "point_type": 2,
                "persistence": persistence,
            }
        )

    # Generate synthetic saddle points (at basin boundaries)
    saddles = []
    if len(minima) >= 2 and len(maxima) >= 2:
        # Place saddles between min/max pairs
        for idx in range(min(3, len(minima), len(maxima))):
            min_pt = minima[idx]
            max_pt = maxima[idx]

            # Midpoint between minimum and maximum
            x = (min_pt["x"] + max_pt["x"]) / 2
            y = (min_pt["y"] + max_pt["y"]) / 2
            value = (min_pt["value"] + max_pt["value"]) / 2
            z = value * height_scale
            persistence = abs(max_pt["value"] - min_pt["value"]) * 0.15

            saddles.append(
                {
                    "x": x,
                    "y": y,
                    "z": z,
                    "value": value,
                    "point_type": 1,
                    "persistence": persistence,
                }
            )

    logger.info(f"Generated {len(minima)} minima, {len(maxima)} maxima, {len(saddles)} saddles")

    return {"minima": minima, "maxima": maxima, "saddles": saddles}


def add_critical_point_glyphs(
    plotter: pv.Plotter,
    critical_points: dict,
    label_major: bool = True,
    persistence_threshold: float = 0.05,
) -> None:
    """
    Add glyph markers for critical points to the plotter.

    Args:
        plotter: PyVista Plotter instance.
        critical_points: Dict with 'minima', 'maxima', 'saddles' lists.
        label_major: If True, add text labels for major critical points.
        persistence_threshold: Minimum persistence for text labeling.
    """
    logger.info("Adding critical point glyphs to terrain")

    # Add minima (red spheres)
    if critical_points["minima"]:
        for idx, pt in enumerate(critical_points["minima"]):
            pos = np.array([pt["x"], pt["y"], pt["z"]])
            radius = GLYPH_BASE_SCALE * (1.0 + pt["persistence"] * GLYPH_PERSISTENCE_FACTOR)

            sphere = pv.Sphere(radius=radius, center=pos)
            plotter.add_mesh(
                sphere,
                color=GLYPH_COLORS["minimum"],
                opacity=0.8,
                smooth_shading=True,
            )

            # Add label for major traps
            if label_major and pt["persistence"] > persistence_threshold:
                label_pos = pos + np.array([radius * 1.5, 0, radius * 0.5])
                plotter.add_point_labels(
                    [label_pos],
                    [f"Trap {idx + 1}\n({pt['value']:.2f})"],
                    font_size=12,
                    text_color=GLYPH_COLORS["minimum"],
                    point_size=1,
                    render_points_as_spheres=False,
                    always_visible=False,
                )

    # Add maxima (green cones)
    if critical_points["maxima"]:
        for idx, pt in enumerate(critical_points["maxima"]):
            pos = np.array([pt["x"], pt["y"], pt["z"]])
            height = GLYPH_BASE_SCALE * (1.0 + pt["persistence"] * GLYPH_PERSISTENCE_FACTOR)
            radius = height * 0.5

            # Create cone pointing upward
            cone = pv.Cone(
                center=pos + np.array([0, 0, height / 2]),
                direction=(0, 0, 1),
                height=height,
                radius=radius,
            )
            plotter.add_mesh(
                cone,
                color=GLYPH_COLORS["maximum"],
                opacity=0.8,
                smooth_shading=True,
            )

            # Add label for major peaks
            if label_major and pt["persistence"] > persistence_threshold:
                label_pos = pos + np.array([radius * 1.5, 0, height])
                plotter.add_point_labels(
                    [label_pos],
                    [f"Peak {idx + 1}\n({pt['value']:.2f})"],
                    font_size=12,
                    text_color=GLYPH_COLORS["maximum"],
                    point_size=1,
                    render_points_as_spheres=False,
                    always_visible=False,
                )

    # Add saddles (orange cubes)
    if critical_points["saddles"]:
        for idx, pt in enumerate(critical_points["saddles"]):
            pos = np.array([pt["x"], pt["y"], pt["z"]])
            size = GLYPH_BASE_SCALE * (1.0 + pt["persistence"] * GLYPH_PERSISTENCE_FACTOR)

            cube = pv.Cube(center=pos, x_length=size, y_length=size, z_length=size)
            plotter.add_mesh(
                cube,
                color=GLYPH_COLORS["saddle"],
                opacity=0.8,
                smooth_shading=True,
            )

            # Add label for major barriers
            if label_major and pt["persistence"] > persistence_threshold:
                label_pos = pos + np.array([size * 1.5, 0, size * 0.5])
                plotter.add_point_labels(
                    [label_pos],
                    [f"Barrier {idx + 1}\n({pt['value']:.2f})"],
                    font_size=12,
                    text_color=GLYPH_COLORS["saddle"],
                    point_size=1,
                    render_points_as_spheres=False,
                    always_visible=False,
                )

    n_total = len(critical_points["minima"]) + len(critical_points["maxima"]) + len(critical_points["saddles"])
    logger.info(f"Added {n_total} critical point glyphs")


def set_camera_view(
    plotter: pv.Plotter,
    view_type: str = "oblique",
    bounds: tuple[float, float, float, float, float, float] | None = None,
) -> None:
    """
    Set camera position for standard views of England/Wales terrain.

    Args:
        plotter: PyVista Plotter instance.
        view_type: Camera view type:
            - 'overview': Bird's eye view of full extent
            - 'oblique': 45-degree angled view showing depth
            - 'north_west': Regional zoom on North West England
        bounds: Mesh bounds (xmin, xmax, ymin, ymax, zmin, zmax).
            If None, uses default England/Wales bounds.
    """
    if bounds is None:
        xmin, xmax = ENGLAND_WALES_BOUNDS["x_min"], ENGLAND_WALES_BOUNDS["x_max"]
        ymin, ymax = ENGLAND_WALES_BOUNDS["y_min"], ENGLAND_WALES_BOUNDS["y_max"]
        zmin, zmax = 0, 0.1  # Approximate height range after scaling
    else:
        xmin, xmax, ymin, ymax, zmin, zmax = bounds

    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    cz = (zmin + zmax) / 2

    extent = max(xmax - xmin, ymax - ymin)

    if view_type == "overview":
        # Bird's eye view - directly above center
        camera_pos = (cx, cy, cz + extent * 1.2)
        focal_point = (cx, cy, cz)
        view_up = (0, 1, 0)

    elif view_type == "oblique":
        # 45-degree angled view showing depth
        camera_pos = (
            cx - extent * 0.8,
            cy - extent * 0.8,
            cz + extent * 0.6,
        )
        focal_point = (cx, cy, cz)
        view_up = (0, 0, 1)

    elif view_type == "north_west":
        # Zoom to North West region (Manchester/Liverpool area)
        cx_nw = 350000
        cy_nw = 400000
        extent_nw = 150000

        camera_pos = (
            cx_nw - extent_nw * 0.7,
            cy_nw - extent_nw * 0.7,
            cz + extent_nw * 0.5,
        )
        focal_point = (cx_nw, cy_nw, cz)
        view_up = (0, 0, 1)

    else:
        raise ValueError(f"Unknown view_type: {view_type}")

    logger.info(f"Setting camera view: {view_type}")
    plotter.camera_position = [camera_pos, focal_point, view_up]


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate 3D opportunity terrain visualization")
    parser.add_argument(
        "--vti-path",
        type=Path,
        default=None,
        help="Path to VTK ImageData file (if not provided, generates sample)",
    )
    parser.add_argument(
        "--basins-csv",
        type=Path,
        default=None,
        help="Path to basin membership CSV (optional)",
    )
    parser.add_argument(
        "--critical-pts",
        type=Path,
        default=None,
        help="Path to critical points CSV (optional, will generate if not provided)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for renders",
    )
    parser.add_argument(
        "--height-scale",
        type=float,
        default=DEFAULT_HEIGHT_SCALE,
        help="Vertical exaggeration factor",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=100,
        help="Resolution for sample surface generation",
    )
    parser.add_argument(
        "--color-mode",
        type=str,
        choices=["mobility", "basins", "both"],
        default="both",
        help="Color mode: mobility (continuous), basins (categorical), or both",
    )
    parser.add_argument(
        "--enable-shadows",
        action="store_true",
        help="Enable shadow rendering (slower)",
    )
    parser.add_argument(
        "--show-critical-pts",
        action="store_true",
        help="Show critical point glyphs and labels",
    )
    parser.add_argument(
        "--persistence-threshold",
        type=float,
        default=0.05,
        help="Minimum persistence for labeling critical points",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate surface
    if args.vti_path and args.vti_path.exists():
        surface = load_mobility_surface(args.vti_path)
    else:
        logger.info("No VTI file provided, generating sample surface")
        sample_path = args.output_dir / "sample_mobility_surface.vti"
        surface = generate_sample_surface(
            resolution=args.resolution,
            output_path=sample_path,
        )

    # Create terrain mesh
    terrain = create_terrain_mesh(surface, height_scale=args.height_scale)

    # Load or generate critical points
    critical_points = None
    if args.show_critical_pts:
        if args.critical_pts and args.critical_pts.exists():
            critical_points = load_critical_points(args.critical_pts)
        else:
            logger.info("No critical points CSV provided, generating from surface")
            critical_points = generate_sample_critical_points(surface, height_scale=args.height_scale)

    logger.info(f"Rendering terrain views with color_mode={args.color_mode}...")

    # Render multiple views
    views = ["overview", "oblique", "north_west"]

    for view_type in views:
        # Mobility coloring
        if args.color_mode in ["mobility", "both"]:
            plotter = setup_plotter(enable_shadows=args.enable_shadows)

            plotter.add_mesh(
                terrain,
                scalars="mobility",
                cmap="RdYlGn",
                show_scalar_bar=True,
                scalar_bar_args={
                    "title": "Mobility Proxy",
                    "vertical": True,
                    "position_x": 0.85,
                    "position_y": 0.15,
                    "width": 0.08,
                    "height": 0.7,
                    "title_font_size": 16,
                    "label_font_size": 12,
                },
                lighting=True,
                specular=0.5,
                specular_power=15,
            )

            # Add critical point glyphs if requested
            if critical_points:
                add_critical_point_glyphs(
                    plotter,
                    critical_points,
                    label_major=True,
                    persistence_threshold=args.persistence_threshold,
                )

            set_camera_view(plotter, view_type, bounds=terrain.bounds)

            suffix = "_with_cps" if critical_points else "_mobility"
            output_path = args.output_dir / f"terrain_{view_type}{suffix}.png"
            plotter.screenshot(str(output_path))
            logger.info(f"Saved render: {output_path}")
            plotter.close()

        # Basin coloring (if available)
        if args.color_mode in ["basins", "both"]:
            if "basin_id" in terrain.array_names:
                plotter = setup_plotter(enable_shadows=args.enable_shadows)

                basin_ids = terrain["basin_id"]
                n_basins = int(basin_ids.max()) + 1
                basin_colors = create_basin_colormap(n_basins)

                # Create custom colormap for categorical data
                basin_cmap = ListedColormap(basin_colors)

                plotter.add_mesh(
                    terrain,
                    scalars="basin_id",
                    cmap=basin_cmap,
                    show_scalar_bar=True,
                    scalar_bar_args={
                        "title": f"Basin ID (n={n_basins})",
                        "vertical": True,
                        "position_x": 0.85,
                        "position_y": 0.15,
                        "width": 0.08,
                        "height": 0.7,
                        "title_font_size": 16,
                        "label_font_size": 12,
                        "n_labels": min(n_basins, 10),
                    },
                    lighting=True,
                    specular=0.5,
                    specular_power=15,
                )

                # Add critical point glyphs if requested
                if critical_points:
                    add_critical_point_glyphs(
                        plotter,
                        critical_points,
                        label_major=True,
                        persistence_threshold=args.persistence_threshold,
                    )

                set_camera_view(plotter, view_type, bounds=terrain.bounds)

                suffix = "_with_cps" if critical_points else "_basins"
                output_path = args.output_dir / f"terrain_{view_type}{suffix}.png"
                plotter.screenshot(str(output_path))
                logger.info(f"Saved render: {output_path}")
                plotter.close()
            else:
                logger.warning(
                    f"Basin coloring requested but no basin_id field found in surface. "
                    f"Skipping basin renders for {view_type}."
                )

    logger.info(f"✓ Step 3 complete: Terrain with critical point annotations to {args.output_dir}")


if __name__ == "__main__":
    main()
