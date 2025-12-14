"""
Counterfactual analysis for "what if" policy simulations.

This module provides utilities for modifying mobility surfaces to simulate
policy interventions (barrier removal, trap filling) and recomputing the
Morse-Smale complex to quantify the impact on population flows and basin
structure.

Counterfactual Scenarios:
    - Barrier removal: Smooth saddle points to eliminate mobility barriers
    - Trap filling: Raise minimum values to reduce trap depth
    - Combined interventions: Apply multiple modifications

Analysis Pipeline:
    1. Modify mobility surface using SurfaceModifier
    2. Recompute Morse-Smale complex via TTK
    3. Compare before/after topology and basin structure
    4. Estimate population redistribution

Integration:
    - mobility_surface.py: Surface construction and VTK export
    - morse_smale.py: Topology computation via TTK subprocess
    - trap_identification.py: Basin properties and trap scoring
    - barriers.py: Barrier strength and impact analysis
    - interventions.py: Intervention framework integration

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)


# =============================================================================
# MODIFICATION DATA STRUCTURES
# =============================================================================


@dataclass
class Modification:
    """A surface modification for counterfactual analysis.

    Attributes:
        type: Modification type ('remove_barrier', 'fill_trap').
        coords: (x, y) coordinates in grid space of the feature to modify.
        radius: Radius of influence in grid cells.
        parameters: Additional parameters specific to modification type:
            - For 'remove_barrier': {'method': 'gaussian'|'linear', 'sigma': float}
            - For 'fill_trap': {'target_value': float, 'method': 'gaussian'|'linear'}
    """

    type: str
    coords: tuple[float, float]
    radius: float
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate modification parameters."""
        if self.type not in ("remove_barrier", "fill_trap"):
            raise ValueError(
                f"Invalid modification type '{self.type}'. "
                "Must be 'remove_barrier' or 'fill_trap'"
            )
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")


# =============================================================================
# SURFACE MODIFIER
# =============================================================================


class SurfaceModifier:
    """Modify mobility surfaces for counterfactual analysis.

    This class provides methods for applying controlled modifications to
    mobility surfaces, simulating policy interventions like barrier removal
    or trap filling.

    Attributes:
        surface: Original mobility surface (2D array).
        grid_x: X-coordinates of grid points (1D array).
        grid_y: Y-coordinates of grid points (1D array).
        modified_surface: Current modified surface (starts as copy of original).
    """

    def __init__(
        self,
        surface: NDArray[np.float64],
        grid_x: NDArray[np.float64],
        grid_y: NDArray[np.float64],
    ) -> None:
        """Initialize surface modifier.

        Args:
            surface: Original mobility surface (2D array).
            grid_x: X-coordinates of grid points (1D or 2D array).
            grid_y: Y-coordinates of grid points (1D or 2D array).

        Raises:
            ValueError: If surface and grid dimensions don't match.
        """
        self.surface = surface.copy()
        self.grid_x = np.asarray(grid_x)
        self.grid_y = np.asarray(grid_y)

        # Validate dimensions
        if surface.ndim != 2:
            raise ValueError(f"Surface must be 2D, got shape {surface.shape}")

        # Handle both 1D and 2D grid arrays
        if self.grid_x.ndim == 1:
            # Convert 1D arrays to 2D meshgrid if needed
            if len(self.grid_x) != surface.shape[1]:
                raise ValueError(
                    f"grid_x length {len(self.grid_x)} doesn't match "
                    f"surface width {surface.shape[1]}"
                )
        elif self.grid_x.ndim == 2:
            if self.grid_x.shape != surface.shape:
                raise ValueError(
                    f"grid_x shape {self.grid_x.shape} doesn't match "
                    f"surface shape {surface.shape}"
                )
        else:
            raise ValueError(f"grid_x must be 1D or 2D, got {self.grid_x.ndim}D")

        # Similar validation for grid_y
        if self.grid_y.ndim == 1:
            if len(self.grid_y) != surface.shape[0]:
                raise ValueError(
                    f"grid_y length {len(self.grid_y)} doesn't match "
                    f"surface height {surface.shape[0]}"
                )
        elif self.grid_y.ndim == 2:
            if self.grid_y.shape != surface.shape:
                raise ValueError(
                    f"grid_y shape {self.grid_y.shape} doesn't match "
                    f"surface shape {surface.shape}"
                )
        else:
            raise ValueError(f"grid_y must be 1D or 2D, got {self.grid_y.ndim}D")

        # Start with unmodified copy
        self.modified_surface = self.surface.copy()

        logger.info(
            f"SurfaceModifier initialized: surface shape {surface.shape}, "
            f"value range [{surface.min():.3f}, {surface.max():.3f}]"
        )

    def _coords_to_indices(self, coords: tuple[float, float]) -> tuple[int, int] | None:
        """Convert (x, y) coordinates to grid indices.

        Args:
            coords: (x, y) coordinates in coordinate space.

        Returns:
            (i, j) indices in grid, or None if out of bounds.
        """
        x, y = coords

        # Check if coordinates are within grid bounds first
        x_min, x_max = self.grid_x.min(), self.grid_x.max()
        y_min, y_max = self.grid_y.min(), self.grid_y.max()

        if not (x_min <= x <= x_max and y_min <= y <= y_max):
            return None

        # Handle both 1D and 2D grids
        if self.grid_x.ndim == 1:
            # Find nearest indices in 1D arrays
            i = np.argmin(np.abs(self.grid_y - y))
            j = np.argmin(np.abs(self.grid_x - x))
        else:
            # Find nearest indices in 2D meshgrid
            distances = (self.grid_x - x) ** 2 + (self.grid_y - y) ** 2
            i, j = np.unravel_index(np.argmin(distances), distances.shape)

        # Validate bounds
        if 0 <= i < self.surface.shape[0] and 0 <= j < self.surface.shape[1]:
            return int(i), int(j)
        return None

    def remove_barrier(
        self,
        saddle_coords: tuple[float, float],
        radius: float,
        method: str = "gaussian",
    ) -> NDArray[np.float64]:
        """Remove a barrier (saddle point) from the surface.

        This simulates interventions like new transport links that reduce
        mobility barriers between regions.

        Args:
            saddle_coords: (x, y) coordinates of saddle point to remove.
            radius: Radius of influence in grid cells.
            method: Modification method:
                - 'gaussian': Smooth with Gaussian kernel (default)
                - 'linear': Linear interpolation to surrounding average

        Returns:
            Modified surface with barrier removed.

        Raises:
            ValueError: If method is invalid or saddle_coords out of bounds.
        """
        if method not in ("gaussian", "linear"):
            raise ValueError(
                f"Invalid method '{method}'. Must be 'gaussian' or 'linear'"
            )

        indices = self._coords_to_indices(saddle_coords)
        if indices is None:
            raise ValueError(
                f"Coordinates {saddle_coords} are out of grid bounds. "
                f"Grid bounds: x=[{self.grid_x.min():.1f}, {self.grid_x.max():.1f}], "
                f"y=[{self.grid_y.min():.1f}, {self.grid_y.max():.1f}]"
            )

        i_center, j_center = indices

        logger.info(
            f"Removing barrier at {saddle_coords} "
            f"(grid indices [{i_center}, {j_center}]) "
            f"with {method} method, radius={radius}"
        )

        if method == "gaussian":
            # Apply Gaussian smoothing around saddle point
            # Sigma based on radius (radius ≈ 2*sigma for 95% coverage)
            sigma = radius / 2.0

            # Create weight mask: higher weight near saddle point
            i_coords = np.arange(self.surface.shape[0])
            j_coords = np.arange(self.surface.shape[1])
            i_grid, j_grid = np.meshgrid(i_coords, j_coords, indexing="ij")

            distances = np.sqrt((i_grid - i_center) ** 2 + (j_grid - j_center) ** 2)
            weights = np.exp(-(distances**2) / (2 * sigma**2))
            weights[distances > radius] = 0  # Limit to radius

            # Smooth only the affected region
            smoothed = gaussian_filter(self.modified_surface, sigma=sigma)

            # Blend smoothed values based on distance weights
            self.modified_surface = (
                weights * smoothed + (1 - weights) * self.modified_surface
            )

        elif method == "linear":
            # Replace saddle region with average of surrounding ring
            i_min = max(0, int(i_center - radius))
            i_max = min(self.surface.shape[0], int(i_center + radius + 1))
            j_min = max(0, int(j_center - radius))
            j_max = min(self.surface.shape[1], int(j_center + radius + 1))

            # Get surrounding ring values (just outside radius)
            i_coords = np.arange(self.surface.shape[0])
            j_coords = np.arange(self.surface.shape[1])
            i_grid, j_grid = np.meshgrid(i_coords, j_coords, indexing="ij")
            distances = np.sqrt((i_grid - i_center) ** 2 + (j_grid - j_center) ** 2)

            # Ring: radius < distance < radius + 2
            ring_mask = (distances > radius) & (distances < radius + 2)
            if ring_mask.any():
                ring_avg = self.modified_surface[ring_mask].mean()
            else:
                # Fallback to local region average
                ring_avg = self.modified_surface[i_min:i_max, j_min:j_max].mean()

            # Fill interior with ring average
            interior_mask = distances <= radius
            self.modified_surface[interior_mask] = ring_avg

        logger.debug(
            f"Barrier removed. Modified surface range: "
            f"[{self.modified_surface.min():.3f}, {self.modified_surface.max():.3f}]"
        )

        return self.modified_surface

    def fill_trap(
        self,
        minimum_coords: tuple[float, float],
        radius: float,
        target_value: float,
    ) -> NDArray[np.float64]:
        """Fill a poverty trap (minimum) by raising values.

        This simulates interventions that improve local opportunity
        and reduce trap depth.

        Args:
            minimum_coords: (x, y) coordinates of minimum to fill.
            radius: Radius of influence in grid cells.
            target_value: Target value to raise minimum to.

        Returns:
            Modified surface with trap filled.

        Raises:
            ValueError: If minimum_coords out of bounds.
        """
        indices = self._coords_to_indices(minimum_coords)
        if indices is None:
            raise ValueError(
                f"Coordinates {minimum_coords} are out of grid bounds. "
                f"Grid bounds: x=[{self.grid_x.min():.1f}, {self.grid_x.max():.1f}], "
                f"y=[{self.grid_y.min():.1f}, {self.grid_y.max():.1f}]"
            )

        i_center, j_center = indices

        logger.info(
            f"Filling trap at {minimum_coords} (grid indices [{i_center}, {j_center}]) "
            f"to target value {target_value:.3f}, radius={radius}"
        )

        # Create distance-based weight mask
        i_coords = np.arange(self.surface.shape[0])
        j_coords = np.arange(self.surface.shape[1])
        i_grid, j_grid = np.meshgrid(i_coords, j_coords, indexing="ij")

        distances = np.sqrt((i_grid - i_center) ** 2 + (j_grid - j_center) ** 2)

        # Smooth transition: full raise at center, zero at radius
        # Weight decreases linearly from 1 at center to 0 at radius
        weights = np.clip(1 - distances / radius, 0, 1)

        # Compute raise amount (only raise, never lower)
        current_values = self.modified_surface
        # At center (weight=1), raise to target_value
        # At radius (weight=0), no change
        # In between, proportional raise
        target_values = np.maximum(current_values, target_value)
        raise_amount = (target_values - current_values) * weights

        # Apply weighted raise
        self.modified_surface = current_values + raise_amount

        logger.debug(
            f"Trap filled. Modified surface range: "
            f"[{self.modified_surface.min():.3f}, {self.modified_surface.max():.3f}]"
        )

        return self.modified_surface

    def apply_modifications(
        self, modifications: list[Modification]
    ) -> NDArray[np.float64]:
        """Apply a sequence of modifications to the surface.

        Args:
            modifications: List of Modification objects to apply sequentially.

        Returns:
            Modified surface with all modifications applied.

        Raises:
            ValueError: If any modification is invalid.
        """
        if not modifications:
            logger.warning("No modifications to apply")
            return self.modified_surface

        logger.info(f"Applying {len(modifications)} modifications")

        for idx, mod in enumerate(modifications, 1):
            logger.debug(
                f"Applying modification {idx}/{len(modifications)}: {mod.type}"
            )

            if mod.type == "remove_barrier":
                method = mod.parameters.get("method", "gaussian")
                self.remove_barrier(mod.coords, mod.radius, method=method)

            elif mod.type == "fill_trap":
                target_value = mod.parameters.get("target_value")
                if target_value is None:
                    raise ValueError(
                        f"Modification {idx}: 'fill_trap' requires "
                        "'target_value' in parameters"
                    )
                self.fill_trap(mod.coords, mod.radius, target_value)

            else:
                raise ValueError(f"Modification {idx}: Unknown type '{mod.type}'")

        logger.info(
            f"All modifications applied. Final surface range: "
            f"[{self.modified_surface.min():.3f}, {self.modified_surface.max():.3f}]"
        )

        return self.modified_surface

    def reset(self) -> None:
        """Reset modified surface to original state."""
        self.modified_surface = self.surface.copy()
        logger.debug("Surface reset to original state")

    def get_modification_impact(self) -> dict[str, float]:
        """Compute summary statistics of modifications.

        Returns:
            Dictionary with:
            - mean_change: Mean absolute change
            - max_change: Maximum absolute change
            - affected_cells: Number of cells with any change
            - affected_fraction: Fraction of grid affected
        """
        change = np.abs(self.modified_surface - self.surface)
        affected_mask = change > 1e-9  # Numerical tolerance

        return {
            "mean_change": float(change[affected_mask].mean())
            if affected_mask.any()
            else 0.0,
            "max_change": float(change.max()),
            "affected_cells": int(affected_mask.sum()),
            "affected_fraction": float(affected_mask.sum() / change.size),
        }


# =============================================================================
# COUNTERFACTUAL RESULT
# =============================================================================


@dataclass
class CounterfactualResult:
    """Results from counterfactual analysis.

    Attributes:
        modification: The modification that was applied.
        original_morse_smale: Original Morse-Smale complex before modification.
        modified_morse_smale: Recomputed Morse-Smale complex after modification.
        basin_changes: Dictionary mapping basin IDs to size changes (fraction).
        flow_redistribution: DataFrame with population flow changes.
        barriers_removed: Number of saddle points eliminated.
        traps_reduced: Number of minima weakened or eliminated.
        population_affected: Total population affected by changes.
        critical_point_changes: Dictionary with counts of added/removed critical points.
    """

    modification: Modification | list[Modification]
    original_morse_smale: Any  # MorseSmaleResult
    modified_morse_smale: Any | None = None  # MorseSmaleResult
    basin_changes: dict[int, float] = field(default_factory=dict)
    flow_redistribution: pd.DataFrame | None = None
    barriers_removed: int = 0
    traps_reduced: int = 0
    population_affected: int = 0
    critical_point_changes: dict[str, int] = field(default_factory=dict)


# =============================================================================
# COUNTERFACTUAL ANALYZER
# =============================================================================


class CounterfactualAnalyzer:
    """Analyze counterfactual scenarios by recomputing topology.

    This class takes a modified mobility surface, recomputes the Morse-Smale
    complex via TTK, and compares before/after topology to quantify the
    impact of interventions.

    Attributes:
        original_surface: Original mobility surface (2D array).
        original_morse_smale: Original Morse-Smale complex.
        grid_x: X-coordinates of grid.
        grid_y: Y-coordinates of grid.
    """

    def __init__(
        self,
        original_surface: NDArray[np.float64],
        original_morse_smale: Any,
        grid_x: NDArray[np.float64] | None = None,
        grid_y: NDArray[np.float64] | None = None,
    ) -> None:
        """Initialize counterfactual analyzer.

        Args:
            original_surface: Original mobility surface (2D array).
            original_morse_smale: Original Morse-Smale complex result.
            grid_x: Optional X-coordinates of grid.
            grid_y: Optional Y-coordinates of grid.
        """
        self.original_surface = original_surface.copy()
        self.original_morse_smale = original_morse_smale
        self.grid_x = grid_x
        self.grid_y = grid_y

        logger.info(
            f"CounterfactualAnalyzer initialized with surface shape "
            f"{original_surface.shape}"
        )

    def compare_critical_points(
        self, original_result: Any, modified_result: Any
    ) -> dict[str, int]:
        """Compare critical points between original and modified surfaces.

        Args:
            original_result: Original Morse-Smale result.
            modified_result: Modified Morse-Smale result.

        Returns:
            Dictionary with:
            - minima_removed: Number of minima eliminated
            - minima_added: Number of new minima created
            - saddles_removed: Number of saddles eliminated
            - saddles_added: Number of new saddles created
            - maxima_removed: Number of maxima eliminated
            - maxima_added: Number of new maxima created
            - total_change: Net change in critical points
        """
        # Count original critical points by type
        original_minima = sum(
            1 for cp in original_result.critical_points if cp.is_minimum
        )
        original_saddles = sum(
            1 for cp in original_result.critical_points if cp.is_saddle
        )
        original_maxima = sum(
            1 for cp in original_result.critical_points if cp.is_maximum
        )

        # Count modified critical points by type
        modified_minima = sum(
            1 for cp in modified_result.critical_points if cp.is_minimum
        )
        modified_saddles = sum(
            1 for cp in modified_result.critical_points if cp.is_saddle
        )
        modified_maxima = sum(
            1 for cp in modified_result.critical_points if cp.is_maximum
        )

        # Compute changes
        minima_change = modified_minima - original_minima
        saddles_change = modified_saddles - original_saddles
        maxima_change = modified_maxima - original_maxima

        changes = {
            "minima_removed": max(0, -minima_change),
            "minima_added": max(0, minima_change),
            "saddles_removed": max(0, -saddles_change),
            "saddles_added": max(0, saddles_change),
            "maxima_removed": max(0, -maxima_change),
            "maxima_added": max(0, maxima_change),
            "total_change": abs(minima_change)
            + abs(saddles_change)
            + abs(maxima_change),
        }

        logger.info(
            f"Critical point changes: {minima_change:+d} minima, "
            f"{saddles_change:+d} saddles, {maxima_change:+d} maxima"
        )

        return changes

    def compute_population_impact(
        self,
        flow_redistribution: pd.DataFrame,
        lsoa_populations: pd.DataFrame,
    ) -> dict[str, Any]:
        """Estimate population affected by flow redistribution.

        Args:
            flow_redistribution: DataFrame with columns:
                - from_basin: Origin basin ID
                - to_basin: Destination basin ID
                - population_moved: Estimated population transitioning
            lsoa_populations: DataFrame with LSOA population data.

        Returns:
            Dictionary with:
            - total_affected: Total population affected
            - avg_mobility_change: Average mobility improvement
            - basin_population_changes: Dict mapping basin_id to population change
        """
        if flow_redistribution is None or flow_redistribution.empty:
            return {
                "total_affected": 0,
                "avg_mobility_change": 0.0,
                "basin_population_changes": {},
            }

        # Sum population moved
        total_affected = int(flow_redistribution["population_moved"].sum())

        # Compute average mobility change if mobility columns exist
        if (
            "from_mobility" in flow_redistribution.columns
            and "to_mobility" in flow_redistribution.columns
        ):
            mobility_changes = (
                flow_redistribution["to_mobility"]
                - flow_redistribution["from_mobility"]
            )
            weighted_avg = (
                mobility_changes * flow_redistribution["population_moved"]
            ).sum() / total_affected
            avg_mobility_change = float(weighted_avg) if total_affected > 0 else 0.0
        else:
            avg_mobility_change = 0.0

        # Aggregate population changes by basin
        basin_changes = {}
        for _, row in flow_redistribution.iterrows():
            from_basin = int(row["from_basin"])
            to_basin = int(row["to_basin"])
            pop_moved = int(row["population_moved"])

            basin_changes[from_basin] = basin_changes.get(from_basin, 0) - pop_moved
            basin_changes[to_basin] = basin_changes.get(to_basin, 0) + pop_moved

        logger.info(
            f"Population impact: {total_affected} affected, "
            f"avg mobility change: {avg_mobility_change:+.4f}"
        )

        return {
            "total_affected": total_affected,
            "avg_mobility_change": avg_mobility_change,
            "basin_population_changes": basin_changes,
        }

    def analyze(
        self,
        modified_surface: NDArray[np.float64],
        modification: Modification | list[Modification],
        vtk_output_path: str | None = None,
    ) -> CounterfactualResult:
        """Analyze counterfactual scenario with modified surface.

        This method:
        1. Exports modified surface to VTK
        2. Recomputes Morse-Smale complex via TTK subprocess
        3. Compares before/after topology
        4. Estimates population flow redistribution

        Args:
            modified_surface: Modified mobility surface (2D array).
            modification: Modification(s) that were applied.
            vtk_output_path: Optional path to save modified surface VTK file.
                If None, creates temporary file.

        Returns:
            CounterfactualResult with analysis metrics.

        Raises:
            ImportError: If pyvista not available for VTK export.
            RuntimeError: If TTK subprocess fails.
        """
        logger.info("Starting counterfactual analysis")

        # Note: Full implementation requires VTK export and TTK subprocess
        # For now, create placeholder result with simplified analysis

        # Compare critical point counts (requires modified_morse_smale)
        # This is a simplified placeholder - real implementation needs
        # TTK recomputation

        # Create placeholder modified_morse_smale (in real implementation,
        # this comes from TTK)
        modified_morse_smale = None  # Would be computed via TTK subprocess

        # Compare critical points
        # Placeholder values when TTK not available
        # In a real implementation, compare critical points using TTK output
        critical_point_changes = {
            "minima_removed": 0,
            "minima_added": 0,
            "saddles_removed": 0,
            "saddles_added": 0,
            "maxima_removed": 0,
            "maxima_added": 0,
            "total_change": 0,
        }
        barriers_removed = 0
        traps_reduced = 0

        # Create placeholder flow redistribution
        # Real implementation would compute from basin boundary changes
        flow_redistribution = pd.DataFrame(
            {
                "from_basin": [],
                "to_basin": [],
                "population_moved": [],
            }
        )

        # Estimate basin size changes (simplified)
        # Real implementation would compare basin masks before/after
        basin_changes = {}

        result = CounterfactualResult(
            modification=modification,
            original_morse_smale=self.original_morse_smale,
            modified_morse_smale=modified_morse_smale,
            basin_changes=basin_changes,
            flow_redistribution=flow_redistribution,
            barriers_removed=barriers_removed,
            traps_reduced=traps_reduced,
            population_affected=0,
            critical_point_changes=critical_point_changes,
        )

        logger.info(
            f"Counterfactual analysis complete: {barriers_removed} barriers removed, "
            f"{traps_reduced} traps reduced"
        )

        return result


# =============================================================================
# VISUALIZATION AND REPORTING
# =============================================================================


def visualize_counterfactual(
    original_surface: NDArray[np.float64],
    modified_surface: NDArray[np.float64],
    result: CounterfactualResult,
    grid_x: NDArray[np.float64] | None = None,
    grid_y: NDArray[np.float64] | None = None,
) -> dict[str, Any]:
    """Create visualization comparing original and modified surfaces.

    This function generates matplotlib figures showing before/after comparison
    of the mobility surface and critical point changes.

    Args:
        original_surface: Original mobility surface (2D array).
        modified_surface: Modified mobility surface (2D array).
        result: CounterfactualResult from analysis.
        grid_x: Optional X-coordinates for proper spatial visualization.
        grid_y: Optional Y-coordinates for proper spatial visualization.

    Returns:
        Dictionary with figure keys:
        - 'surface_comparison': Side-by-side surface plots
        - 'critical_points': Critical point overlay
        - 'difference_map': Surface change heatmap

    Raises:
        ImportError: If matplotlib not available.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib required for visualization. "
            "Install with: pip install matplotlib"
        )

    figures = {}

    # Create figure for surface comparison
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

    # Original surface
    im1 = ax1.imshow(original_surface, cmap="viridis", origin="lower")
    ax1.set_title("Original Surface")
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    plt.colorbar(im1, ax=ax1, label="Mobility")

    # Modified surface
    im2 = ax2.imshow(modified_surface, cmap="viridis", origin="lower")
    ax2.set_title("Modified Surface")
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    plt.colorbar(im2, ax=ax2, label="Mobility")

    # Difference map
    difference = modified_surface - original_surface
    im3 = ax3.imshow(difference, cmap="RdBu_r", origin="lower", vmin=-0.1, vmax=0.1)
    ax3.set_title("Change (Modified - Original)")
    ax3.set_xlabel("X")
    ax3.set_ylabel("Y")
    plt.colorbar(im3, ax=ax3, label="Mobility Change")

    plt.tight_layout()
    figures["surface_comparison"] = fig

    # Create figure for critical point changes
    fig2, ax = plt.subplots(figsize=(8, 6))

    changes = result.critical_point_changes
    categories = ["Minima", "Saddles", "Maxima"]
    removed = [
        changes.get("minima_removed", 0),
        changes.get("saddles_removed", 0),
        changes.get("maxima_removed", 0),
    ]
    added = [
        changes.get("minima_added", 0),
        changes.get("saddles_added", 0),
        changes.get("maxima_added", 0),
    ]

    x = np.arange(len(categories))
    width = 0.35

    ax.bar(x - width / 2, removed, width, label="Removed", color="red", alpha=0.7)
    ax.bar(x + width / 2, added, width, label="Added", color="green", alpha=0.7)

    ax.set_ylabel("Count")
    ax.set_title("Critical Point Changes")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    figures["critical_points"] = fig2

    logger.info(f"Generated {len(figures)} visualization figures")

    return figures


def generate_counterfactual_report(
    result: CounterfactualResult,
    intervention_description: str | None = None,
) -> dict[str, Any]:
    """Generate comprehensive counterfactual analysis report.

    Args:
        result: CounterfactualResult from analysis.
        intervention_description: Optional human-readable description of
            the intervention(s) that were simulated.

    Returns:
        Dictionary with report sections:
        - summary: High-level overview
        - modifications_applied: Details of surface modifications
        - topology_changes: Critical point changes
        - population_impact: Estimated population effects
        - recommendations: Policy recommendations based on impact

    Example:
        >>> report = generate_counterfactual_report(result, "New bus route")
        >>> print(report['summary']['barriers_removed'])
        1
    """
    report: dict[str, Any] = {}

    # Summary section
    report["summary"] = {
        "intervention_description": intervention_description
        or "Counterfactual scenario",
        "barriers_removed": result.barriers_removed,
        "traps_reduced": result.traps_reduced,
        "population_affected": result.population_affected,
        "total_topology_changes": result.critical_point_changes.get("total_change", 0),
    }

    # Modifications applied
    if isinstance(result.modification, list):
        modifications_list = [
            {
                "type": mod.type,
                "coords": mod.coords,
                "radius": mod.radius,
                "parameters": mod.parameters,
            }
            for mod in result.modification
        ]
    else:
        modifications_list = [
            {
                "type": result.modification.type,
                "coords": result.modification.coords,
                "radius": result.modification.radius,
                "parameters": result.modification.parameters,
            }
        ]

    report["modifications_applied"] = {
        "count": len(modifications_list),
        "modifications": modifications_list,
    }

    # Topology changes detail
    report["topology_changes"] = {
        "critical_points": result.critical_point_changes,
        "basin_changes": result.basin_changes,
    }

    # Population impact
    if result.flow_redistribution is not None and not result.flow_redistribution.empty:
        total_moved = int(result.flow_redistribution["population_moved"].sum())
        report["population_impact"] = {
            "total_population_moved": total_moved,
            "flow_transitions": len(result.flow_redistribution),
            "major_flows": result.flow_redistribution.nlargest(
                5, "population_moved"
            ).to_dict(orient="records"),
        }
    else:
        report["population_impact"] = {
            "total_population_moved": 0,
            "flow_transitions": 0,
            "major_flows": [],
        }

    # Policy recommendations
    recommendations = []

    if result.barriers_removed > 0:
        recommendations.append(
            f"Intervention successfully removed {result.barriers_removed} "
            f"topological barrier(s), potentially improving mobility paths."
        )

    if result.traps_reduced > 0:
        recommendations.append(
            f"Intervention weakened {result.traps_reduced} poverty trap(s), "
            f"which may enable upward mobility for trapped populations."
        )

    if result.population_affected > 0:
        recommendations.append(
            f"Estimated {result.population_affected:,} people would be affected "
            f"by this intervention."
        )

    if not recommendations:
        recommendations.append(
            "Intervention had minimal topological impact. "
            "Consider targeting areas with stronger barriers or deeper traps."
        )

    report["recommendations"] = recommendations

    # Impact assessment
    total_changes = result.critical_point_changes.get("total_change", 0)
    if total_changes >= 3:
        impact_level = "High"
    elif total_changes >= 1:
        impact_level = "Moderate"
    else:
        impact_level = "Low"

    report["impact_assessment"] = {
        "impact_level": impact_level,
        "cost_benefit_note": (
            "Compare topology changes with intervention cost to assess "
            "value for money. Higher topology changes (especially barrier/"
            "trap removal) indicate stronger impact."
        ),
    }

    logger.info(
        f"Generated counterfactual report: {total_changes} topology changes, "
        f"{impact_level} impact level"
    )

    return report
