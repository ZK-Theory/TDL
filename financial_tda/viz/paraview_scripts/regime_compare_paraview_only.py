"""
ParaView-only Script for Financial Regime Comparison Visualization.

This script uses ParaView's native Python API to create side-by-side visualizations
of pre-computed Rips complex data. Run this with pvpython after generating the
VTK files with the main regime_compare.py script.

Usage:
    pvpython regime_compare_paraview_only.py

Requirements:
    - ParaView 6.x with pvpython
    - Pre-computed VTK files from regime_compare.py

License: MIT
"""

from pathlib import Path

from paraview.simple import *

# Configuration - use absolute paths for ParaView
OUTPUT_DIR = Path("financial_tda/viz/outputs").resolve()
CRISIS_EDGES_PATH = OUTPUT_DIR / "crisis_rips_edges.vtp"
NORMAL_EDGES_PATH = OUTPUT_DIR / "normal_rips_edges.vtp"


def main():
    """Create side-by-side ParaView visualization."""
    print("=" * 60)
    print("ParaView Side-by-Side Rips Complex Visualization")
    print("=" * 60)

    # Check input files with absolute paths
    print(f"Looking for crisis edges: {CRISIS_EDGES_PATH}")
    print(f"Looking for normal edges: {NORMAL_EDGES_PATH}")

    if not CRISIS_EDGES_PATH.exists():
        print(f"ERROR: Crisis edge file not found: {CRISIS_EDGES_PATH}")
        print("\nRun 'python regime_compare.py' first to generate data.")
        return

    if not NORMAL_EDGES_PATH.exists():
        print(f"ERROR: Normal edge file not found: {NORMAL_EDGES_PATH}")
        print("\nRun 'python regime_compare.py' first to generate data.")
        return

    print("✓ Both VTK files found")

    # Create ParaView layout with two side-by-side views
    layout = CreateLayout("Horizontal Split View")

    # === LEFT VIEW: Crisis ===
    renderView1 = CreateView("RenderView")
    layout.AssignView(0, renderView1)
    renderView1.ViewSize = [960, 1080]
    renderView1.Background = [1.0, 1.0, 1.0]

    # Load crisis edges - use absolute path string with forward slashes
    crisis_path_str = str(CRISIS_EDGES_PATH).replace("\\", "/")
    print(f"Loading crisis edges from: {crisis_path_str}")
    crisis_reader = XMLPolyDataReader(FileName=crisis_path_str)
    crisis_reader.UpdatePipeline()

    crisis_display = Show(crisis_reader, renderView1)
    crisis_display.Representation = "Wireframe"
    crisis_display.AmbientColor = [0.7, 0.0, 0.0]
    crisis_display.DiffuseColor = [0.9, 0.0, 0.0]
    crisis_display.LineWidth = 3.0
    crisis_display.Opacity = 0.8

    # Add title annotation for crisis
    text1 = Text()
    text1.Text = "Crisis: Aug-Oct 2008\nLehman Brothers Collapse\n689 edges, threshold=0.0725"
    text1Display = Show(text1, renderView1)
    text1Display.FontSize = 16
    text1Display.Color = [0.6, 0.0, 0.0]
    text1Display.Bold = 1
    text1Display.WindowLocation = "Upper Center"

    # Camera setup for crisis view
    renderView1.ResetCamera()
    camera1 = GetActiveCamera()
    camera1.SetPosition(0.15, -0.3, 0.4)
    camera1.SetFocalPoint(0, 0, 0)
    camera1.SetViewUp(0, 0, 1)
    camera1.Azimuth(25)
    camera1.Elevation(15)
    renderView1.CameraParallelProjection = 0

    # === RIGHT VIEW: Normal ===
    renderView2 = CreateView("RenderView")
    layout.AssignView(1, renderView2)
    renderView2.ViewSize = [960, 1080]
    renderView2.Background = [1.0, 1.0, 1.0]

    # Load normal edges - use absolute path string with forward slashes
    normal_path_str = str(NORMAL_EDGES_PATH).replace("\\", "/")
    print(f"Loading normal edges from: {normal_path_str}")
    normal_reader = XMLPolyDataReader(FileName=normal_path_str)
    normal_reader.UpdatePipeline()

    normal_display = Show(normal_reader, renderView2)
    normal_display.Representation = "Wireframe"
    normal_display.AmbientColor = [0.0, 0.6, 0.0]
    normal_display.DiffuseColor = [0.0, 0.8, 0.0]
    normal_display.LineWidth = 3.0
    normal_display.Opacity = 0.8

    # Hide original reader, only show transformed version
    Hide(normal_reader, renderView2)

    # Add title annotation for normal
    text2 = Text()
    text2.Text = "Normal: Apr-Jun 2007\nPre-Crisis Market\n663 edges, threshold=0.0144"
    text2Display = Show(text2, renderView2)
    text2Display.FontSize = 16
    text2Display.Color = [0.0, 0.5, 0.0]
    text2Display.Bold = 1
    text2Display.WindowLocation = "Upper Center"

    # Camera setup for normal view - match crisis view
    renderView2.ResetCamera()
    camera2 = GetActiveCamera()
    camera2.SetPosition(0.15, -0.3, 0.4)
    camera2.SetFocalPoint(0, 0, 0)
    camera2.SetViewUp(0, 0, 1)
    camera2.Azimuth(25)
    camera2.Elevation(15)
    renderView2.CameraParallelProjection = 0

    # Render both views
    Render(renderView1)
    Render(renderView2)

    # Save screenshot of the layout (both views)
    output_path = OUTPUT_DIR / "regime_compare_side_by_side_paraview.png"
    SaveScreenshot(str(output_path), layout, ImageResolution=[1920, 1080])
    print(f"✓ Saved ParaView render: {output_path}")

    # Save ParaView state file for interactive exploration
    state_path = OUTPUT_DIR / "regime_compare_paraview.pvsm"
    SaveState(str(state_path))
    print(f"✓ Saved ParaView state file: {state_path}")
    print("\nTo explore interactively: Open ParaView → File → Load State → Select .pvsm file")

    print("=" * 60)
    print("ParaView visualization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
