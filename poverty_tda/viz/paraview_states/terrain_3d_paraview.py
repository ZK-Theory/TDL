"""
ParaView Python Script for 3D Opportunity Terrain Visualization.

This script uses ParaView's native Python API (pvpython) to create
3D terrain visualizations with proper ParaView state file generation.

Usage with pvpython (ParaView's Python interpreter):
    pvpython poverty_tda/viz/paraview_states/terrain_3d_paraview.py [options]

Usage with regular Python (will fall back to PyVista):
    python poverty_tda/viz/paraview_states/terrain_3d_paraview.py [options]

Note: For ParaView state file (.pvsm) generation, use pvpython.

Requirements for pvpython:
    ParaView 5.x or 6.x with Python bindings

Requirements for Python fallback:
    pip install pyvista matplotlib numpy pandas scipy

License: Open Government Licence v3.0
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Try to import ParaView modules
try:
    from paraview.simple import *

    HAS_PARAVIEW = True
    logger.info("ParaView Python modules loaded successfully")
except ImportError:
    HAS_PARAVIEW = False
    logger.warning("ParaView Python modules not available, falling back to PyVista")

    # Fall back to PyVista
    try:
        import pyvista as pv
        from scipy.ndimage import maximum_filter, minimum_filter

        HAS_PYVISTA = True
    except ImportError:
        logger.error("Neither ParaView nor PyVista available. Please install one.")
        sys.exit(1)

# Default paths
DEFAULT_OUTPUT_DIR = Path("poverty_tda/viz/outputs")
DEFAULT_HEIGHT_SCALE = 0.0001


def create_paraview_terrain(
    vti_path: Path,
    output_dir: Path,
    height_scale: float = DEFAULT_HEIGHT_SCALE,
    show_critical_pts: bool = False,
    critical_pts_csv: Path | None = None,
) -> None:
    """
    Create 3D terrain visualization using ParaView Python API.

    Args:
        vti_path: Path to VTK ImageData file (.vti)
        output_dir: Output directory for renders and state file
        height_scale: Vertical exaggeration factor
        show_critical_pts: Whether to add critical point glyphs
        critical_pts_csv: Path to critical points CSV
    """
    logger.info("Creating ParaView terrain visualization")

    # Read the VTI file
    mobility_surface = XMLImageDataReader(FileName=str(vti_path))
    mobility_surface.UpdatePipeline()

    logger.info(f"Loaded VTI file: {vti_path}")

    # Create a render view
    renderView = CreateView("RenderView")
    renderView.ViewSize = [1920, 1080]
    renderView.Background = [1.0, 1.0, 1.0]  # White background

    # Warp by scalar to create 3D terrain
    warpByScalar = WarpByScalar(Input=mobility_surface)
    warpByScalar.Scalars = ["POINTS", "mobility"]
    warpByScalar.ScaleFactor = height_scale

    # Display the warped surface
    terrain_display = Show(warpByScalar, renderView)
    terrain_display.Representation = "Surface"
    terrain_display.ColorArrayName = ["POINTS", "mobility"]

    # Set up color map (RdYlGn)
    mobility_LUT = GetColorTransferFunction("mobility")
    mobility_LUT.ApplyPreset("RdYlGn", True)

    # Add color bar
    mobility_LUTColorBar = GetScalarBar(mobility_LUT, renderView)
    mobility_LUTColorBar.Title = "Mobility Proxy"
    mobility_LUTColorBar.ComponentTitle = ""
    mobility_LUTColorBar.Position = [0.85, 0.15]
    mobility_LUTColorBar.ScalarBarLength = 0.7
    terrain_display.SetScalarBarVisibility(renderView, True)

    # Configure lighting
    renderView.UseLight = True

    # Add key light
    key_light = CreateLight()
    key_light.Coords = "Ambient"
    key_light.Intensity = 0.8
    renderView.AdditionalLights = [key_light]

    # Reset camera to fit data
    renderView.ResetCamera()

    # Create multiple camera views
    views = {
        "overview": {"description": "Bird's eye view"},
        "oblique": {"description": "Oblique 45-degree view"},
        "north_west": {"description": "North West regional zoom"},
    }

    for view_name in views.keys():
        logger.info(f"Rendering {view_name} view")

        # Set camera position based on view type
        if view_name == "overview":
            # Bird's eye - directly above
            camera = GetActiveCamera()
            camera.SetPosition(350000, 400000, 200000)
            camera.SetFocalPoint(350000, 400000, 0)
            camera.SetViewUp(0, 1, 0)

        elif view_name == "oblique":
            # Oblique view - 45 degrees
            camera = GetActiveCamera()
            camera.SetPosition(100000, 100000, 150000)
            camera.SetFocalPoint(350000, 400000, 0)
            camera.SetViewUp(0, 0, 1)

        elif view_name == "north_west":
            # Regional zoom
            camera = GetActiveCamera()
            camera.SetPosition(250000, 300000, 100000)
            camera.SetFocalPoint(350000, 400000, 0)
            camera.SetViewUp(0, 0, 1)

        # Render and save
        Render()
        output_path = output_dir / f"terrain_{view_name}_paraview.png"
        SaveScreenshot(str(output_path), renderView, ImageResolution=[1920, 1080])
        logger.info(f"Saved: {output_path}")

    # Save ParaView state file
    state_path = output_dir / "terrain_paraview_state.pvsm"
    SaveState(str(state_path))
    logger.info(f"Saved ParaView state file: {state_path}")

    logger.info("ParaView terrain visualization complete")


def create_pyvista_terrain(
    vti_path: Path,
    output_dir: Path,
    height_scale: float = DEFAULT_HEIGHT_SCALE,
    show_critical_pts: bool = False,
) -> None:
    """
    Create 3D terrain using PyVista (fallback when ParaView not available).

    This uses the terrain_3d.py script functionality.
    """
    logger.info("Using PyVista fallback (import terrain_3d.py functionality)")

    # Import the existing PyVista script
    import importlib.util

    spec = importlib.util.spec_from_file_location("terrain_3d", "poverty_tda/viz/paraview_states/terrain_3d.py")
    terrain_3d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(terrain_3d)

    # Use the existing implementation
    surface = terrain_3d.load_mobility_surface(vti_path)
    terrain = terrain_3d.create_terrain_mesh(surface, height_scale=height_scale)

    views = ["overview", "oblique", "north_west"]

    for view_type in views:
        plotter = terrain_3d.setup_plotter()

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
            },
        )

        terrain_3d.set_camera_view(plotter, view_type, bounds=terrain.bounds)

        output_path = output_dir / f"terrain_{view_type}_pyvista_fallback.png"
        plotter.screenshot(str(output_path))
        logger.info(f"Saved: {output_path}")
        plotter.close()


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate 3D terrain with ParaView or PyVista fallback")
    parser.add_argument(
        "--vti-path",
        type=Path,
        required=True,
        help="Path to VTK ImageData file (.vti)",
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
        "--show-critical-pts",
        action="store_true",
        help="Show critical point glyphs (PyVista only)",
    )
    parser.add_argument(
        "--critical-pts",
        type=Path,
        default=None,
        help="Path to critical points CSV",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Check if VTI file exists
    if not args.vti_path.exists():
        logger.error(f"VTI file not found: {args.vti_path}")
        sys.exit(1)

    # Use ParaView if available, otherwise fall back to PyVista
    if HAS_PARAVIEW:
        logger.info("Using ParaView Python API")
        create_paraview_terrain(
            args.vti_path,
            args.output_dir,
            height_scale=args.height_scale,
            show_critical_pts=args.show_critical_pts,
            critical_pts_csv=args.critical_pts,
        )
    elif HAS_PYVISTA:
        logger.info("Using PyVista fallback")
        create_pyvista_terrain(
            args.vti_path,
            args.output_dir,
            height_scale=args.height_scale,
            show_critical_pts=args.show_critical_pts,
        )
    else:
        logger.error("Neither ParaView nor PyVista available")
        sys.exit(1)


if __name__ == "__main__":
    main()
