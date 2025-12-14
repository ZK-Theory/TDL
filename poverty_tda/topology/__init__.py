"""
Topological analysis of mobility landscapes.

This module provides tools for constructing and analyzing topological
features of mobility and deprivation surfaces.

Main Pipeline:
    analyze_mobility_topology: Complete LSOA → surface → Morse-Smale pipeline

Surface Construction:
    build_mobility_surface: Interpolate LSOA data to regular grid + VTK export
    create_mobility_grid: Create interpolation grid from LSOA boundaries
    interpolate_surface: Scipy-based surface interpolation
    export_mobility_vtk: Export surface to VTK format

Morse-Smale Analysis:
    compute_morse_smale: Extract critical points and separatrices
    simplify_topology: Remove low-persistence features
    compute_persistence_pairs: Extract persistence diagram
    suggest_persistence_threshold: Auto-select simplification threshold

Data Classes:
    CriticalPoint: Local min/max/saddle in the scalar field
    Separatrix: Gradient path connecting critical points
    MorseSmaleResult: Complete Morse-Smale complex result
    PersistencePair: Birth-death pair for topological features
"""

from poverty_tda.topology.mobility_surface import (
    analyze_mobility_topology,
    build_mobility_surface,
    create_mobility_grid,
    export_mobility_vtk,
    get_mobility_barriers,
    get_opportunity_hotspots,
    interpolate_chunked,
    interpolate_surface,
)
from poverty_tda.topology.morse_smale import (
    CriticalPoint,
    MorseSmaleResult,
    PersistencePair,
    Separatrix,
    check_ttk_available,
    check_ttk_environment,
    compute_morse_smale,
    compute_persistence_pairs,
    get_persistence_diagram,
    get_ttk_python_path,
    load_vtk_data,
    simplify_topology,
    suggest_persistence_threshold,
    validate_scalar_field,
)

__all__ = [
    # Main pipeline
    "analyze_mobility_topology",
    # mobility_surface exports
    "build_mobility_surface",
    "create_mobility_grid",
    "export_mobility_vtk",
    "get_mobility_barriers",
    "get_opportunity_hotspots",
    "interpolate_chunked",
    "interpolate_surface",
    # morse_smale exports
    "CriticalPoint",
    "MorseSmaleResult",
    "PersistencePair",
    "Separatrix",
    "check_ttk_available",
    "check_ttk_environment",
    "compute_morse_smale",
    "compute_persistence_pairs",
    "get_persistence_diagram",
    "get_ttk_python_path",
    "load_vtk_data",
    "simplify_topology",
    "suggest_persistence_threshold",
    "validate_scalar_field",
]
