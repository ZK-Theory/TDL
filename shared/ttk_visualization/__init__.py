"""
TTK-based visualization utilities for topological data analysis.

This module provides TTK-enhanced visualization functions for both
financial and poverty TDA workflows, including persistence curve
generation, comparative analysis, and optional ParaView integration.

Architecture:
    - persistence_curves.py: Persistence curve generation via TTK subprocess
    - ttk_plots.py: TTK-enhanced plotting utilities
    - paraview_utils.py: ParaView state file helpers (optional)
    - scripts/: TTK subprocess scripts for isolated VTK environment

All TTK operations use subprocess isolation via shared.ttk_utils to avoid
VTK version conflicts (TTK VTK 9.3.x vs project VTK 9.5.2).

Examples:
    >>> from shared.ttk_visualization import create_persistence_curve
    >>> from shared.ttk_visualization import plot_persistence_comparison
    >>>
    >>> # Generate persistence curves for regime comparison
    >>> curves = create_persistence_curve([diagram_crisis, diagram_normal],
    ...                                    labels=['Crisis', 'Normal'])
    >>> # Plot comparison
    >>> plot_persistence_comparison(curves)

License: MIT
"""

from shared.ttk_visualization.persistence_curves import (
    create_persistence_curve,
    export_diagram_to_vtk,
)
from shared.ttk_visualization.ttk_plots import (
    plot_persistence_comparison,
    plot_persistence_curve,
)

__all__ = [
    "create_persistence_curve",
    "export_diagram_to_vtk",
    "plot_persistence_comparison",
    "plot_persistence_curve",
]
