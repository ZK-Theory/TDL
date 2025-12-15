"""
ParaView state file generation utilities.

This module provides helper functions for creating ParaView state files (.pvsm)
for interactive exploration of TTK results. These are optional and require
ParaView with TTK installed.

Note: ParaView state files are difficult to generate programmatically due to
XML complexity. This module provides basic templates and utilities.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_paraview_state_template(
    data_files: list[str | Path],
    output_path: str | Path,
    title: str = "TTK Visualization",
) -> Path:
    """
    Create a basic ParaView state file template for TTK visualization.

    Args:
        data_files: List of VTK files to load in ParaView.
        output_path: Path to save the .pvsm state file.
        title: Title for the ParaView session.

    Returns:
        Path to created state file.

    Examples:
        >>> files = ["crisis_diagram.vti", "normal_diagram.vti"]
        >>> state_path = create_paraview_state_template(files, "comparison.pvsm")

    Notes:
        This creates a minimal state file. Users should open in ParaView
        and customize visualization, then save updated state.
    """
    output_path = Path(output_path)

    # Basic ParaView state file XML template
    # This is a simplified template - full state files are complex
    xml_content = f"""<?xml version="1.0"?>
<ParaView version="5.13.0">
  <ServerManagerState>
    <!-- {title} -->
    <!-- Data files: {", ".join(str(f) for f in data_files)} -->
    
    <!-- NOTE: This is a minimal template. -->
    <!-- Open in ParaView, add TTK filters, and save updated state. -->
    
  </ServerManagerState>
</ParaView>
"""

    output_path.write_text(xml_content)

    logger.info(f"Created ParaView state template at {output_path}")
    logger.info("Open in ParaView, add TTK filters, then save updated state")

    return output_path


def suggest_paraview_workflow() -> str:
    """
    Return suggested ParaView workflow for TTK visualization.

    Returns:
        Multi-line string with ParaView workflow instructions.

    Examples:
        >>> print(suggest_paraview_workflow())
    """
    workflow = """
    SUGGESTED PARAVIEW WORKFLOW FOR TTK VISUALIZATION
    ================================================
    
    For Persistence Diagrams:
    1. File → Open → Select .vti or .vtp file with diagram data
    2. Filters → TTK - Scalar Data → TTK PersistenceDiagram
    3. Configure persistence threshold
    4. Apply → View persistence diagram
    5. File → Save State → Save as .pvsm
    
    For Morse-Smale Complex:
    1. File → Open → Select .vti file with scalar field
    2. Filters → TTK - Scalar Data → TTK TopologicalSimplification (optional)
    3. Filters → TTK - Scalar Data → TTK MorseSmaleComplex
    4. Configure persistence threshold
    5. Apply → View critical points and separatrices
    6. File → Save State → Save as .pvsm
    
    For Persistence Curves:
    1. Load multiple persistence diagrams
    2. Use TTK - Statistics → TTK PersistenceCurve
    3. Compare multiple datasets
    4. Save state for reuse
    
    Saving State Files:
    - File → Save State
    - Select "Python State File" (.py) for programmable access
    - OR "ParaView State File" (.pvsm) for XML format
    
    Note: State files contain absolute paths - update paths when moving files.
    """

    return workflow
