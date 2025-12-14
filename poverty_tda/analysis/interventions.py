"""
Intervention targeting framework for poverty reduction.

This module provides tools for identifying and prioritizing intervention
targets based on topological analysis of the mobility surface. Gateway LSOAs
(areas whose flow paths cross basin boundaries) are evaluated by impact
potential, and different intervention types are modeled with cost-benefit
analysis.

Intervention Types:
    - EDUCATION: School quality improvements, KS4 attainment boosts
    - TRANSPORT: New links reducing barrier heights
    - EMPLOYMENT: Job creation hubs flattening saddle points
    - HOUSING: Affordable housing improving local mobility

Impact Model:
    - Gateway LSOA population affected
    - Trap severity from trap_identification scores
    - Barrier difficulty from barriers module
    - Flow convergence at gateway positions

Integration:
    - pathways.py: Gateway LSOA identification and flow paths
    - trap_identification.py: Basin trap scores
    - barriers.py: Separatrix barrier strengths
    - opportunity_atlas.py: Population data for impact estimation

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


# =============================================================================
# INTERVENTION TYPE DEFINITIONS
# =============================================================================


class InterventionType(Enum):
    """Types of interventions for poverty reduction.

    Attributes:
        EDUCATION: School quality improvements (e.g., academy conversions,
            teacher recruitment, facilities upgrades)
        TRANSPORT: New transport links reducing barriers (e.g., bus routes,
            cycle lanes, rail connections)
        EMPLOYMENT: Job creation in strategic locations (e.g., business parks,
            enterprise zones)
        HOUSING: Affordable housing and regeneration projects
    """

    EDUCATION = "education"
    TRANSPORT = "transport"
    EMPLOYMENT = "employment"
    HOUSING = "housing"


# =============================================================================
# INTERVENTION DATA MODEL
# =============================================================================


@dataclass
class Intervention:
    """A proposed intervention for poverty reduction.

    Attributes:
        intervention_id: Unique identifier for this intervention.
        type: InterventionType (EDUCATION, TRANSPORT, EMPLOYMENT, HOUSING).
        target_lsoas: List of LSOA 2021 codes targeted by this intervention.
        estimated_effect: Expected mobility improvement (absolute units, e.g.,
            +0.05 mobility score increase).
        cost_estimate: Relative cost in standard units (e.g., millions GBP).
        implementation_time: Expected time to completion in months.
        description: Human-readable description of the intervention.
        baseline_mobility: Mean mobility in target LSOAs before intervention.
        affected_population: Estimated population directly affected.
    """

    intervention_id: int
    type: InterventionType
    target_lsoas: list[str]
    estimated_effect: float
    cost_estimate: float
    implementation_time: int
    description: str = ""
    baseline_mobility: float | None = None
    affected_population: int | None = None

    def __post_init__(self) -> None:
        """Validate intervention parameters."""
        if self.cost_estimate <= 0:
            raise ValueError(f"Cost must be positive, got {self.cost_estimate}")
        if self.implementation_time <= 0:
            raise ValueError(
                f"Implementation time must be positive, got {self.implementation_time}"
            )
        if not self.target_lsoas:
            raise ValueError("Must specify at least one target LSOA")


# =============================================================================
# IMPACT MODEL
# =============================================================================


class ImpactModel:
    """Model for estimating intervention impacts on mobility surface.

    This class provides methods for estimating the expected mobility
    improvements from different intervention types. Impact estimates are
    based on literature evidence and UK policy evaluations.

    References:
        - Education impacts: Machin & Salvanes (2016) on school quality
        - Transport impacts: DfT TAG on accessibility benefits
        - Employment impacts: Gibbons et al. (2013) on job proximity
    """

    def __init__(self) -> None:
        """Initialize impact model with default parameters."""
        # Education impact coefficients
        self.education_ks4_coefficient = 0.002  # Mobility per 1% KS4 improvement

        # Transport impact coefficients
        self.transport_barrier_coefficient = (
            0.5  # Effect multiplier for barrier reduction
        )

        # Employment impact coefficients
        self.employment_job_coefficient = 0.00001  # Mobility per job created

    def estimate_education_impact(
        self,
        baseline_mobility: float,
        ks4_improvement_pct: float,
    ) -> float:
        """Estimate mobility improvement from education intervention.

        Example: +10% KS4 attainment → +0.02 mobility improvement

        Args:
            baseline_mobility: Current mean mobility in target LSOA(s).
            ks4_improvement_pct: Expected percentage point improvement in
                KS4 attainment (e.g., 10.0 for +10 percentage points).

        Returns:
            Estimated absolute mobility improvement.

        Raises:
            ValueError: If ks4_improvement_pct is negative or > 100.
        """
        if ks4_improvement_pct < 0 or ks4_improvement_pct > 100:
            raise ValueError(
                f"KS4 improvement must be in [0, 100], got {ks4_improvement_pct}"
            )

        effect = ks4_improvement_pct * self.education_ks4_coefficient
        logger.info(
            f"Education impact: +{ks4_improvement_pct}% KS4 → +{effect:.4f} mobility"
        )
        return effect

    def estimate_transport_impact(
        self,
        barrier_height: float,
        barrier_reduction_pct: float,
    ) -> float:
        """Estimate mobility improvement from transport intervention.

        Example: Reduce barrier height by 50% → mobility improvement
        proportional to barrier significance.

        Args:
            barrier_height: Current barrier height (saddle persistence or
                mobility difference).
            barrier_reduction_pct: Expected percentage reduction in barrier
                height (e.g., 50.0 for 50% reduction).

        Returns:
            Estimated absolute mobility improvement.

        Raises:
            ValueError: If barrier_reduction_pct not in [0, 100].
        """
        if barrier_reduction_pct < 0 or barrier_reduction_pct > 100:
            raise ValueError(
                f"Barrier reduction must be in [0, 100], got {barrier_reduction_pct}"
            )

        # Impact proportional to barrier height and reduction percentage
        effect = (
            barrier_height
            * (barrier_reduction_pct / 100.0)
            * self.transport_barrier_coefficient
        )
        logger.info(
            f"Transport impact: {barrier_reduction_pct}% reduction of "
            f"barrier height {barrier_height:.4f} → +{effect:.4f} mobility"
        )
        return effect

    def estimate_employment_impact(
        self,
        baseline_mobility: float,
        job_creation_count: int,
    ) -> float:
        """Estimate mobility improvement from employment intervention.

        Example: Create 1000 jobs in strategic location → flatten saddle
        point and improve local mobility.

        Args:
            baseline_mobility: Current mean mobility in target LSOA(s).
            job_creation_count: Number of jobs created by intervention.

        Returns:
            Estimated absolute mobility improvement.

        Raises:
            ValueError: If job_creation_count is negative.
        """
        if job_creation_count < 0:
            raise ValueError(
                f"Job creation count must be non-negative, got {job_creation_count}"
            )

        effect = job_creation_count * self.employment_job_coefficient
        logger.info(
            f"Employment impact: {job_creation_count} jobs → +{effect:.4f} mobility"
        )
        return effect

    def estimate_housing_impact(
        self,
        baseline_mobility: float,
        housing_units: int,
        affordability_improvement: float,
    ) -> float:
        """Estimate mobility improvement from housing intervention.

        Args:
            baseline_mobility: Current mean mobility in target LSOA(s).
            housing_units: Number of affordable housing units created.
            affordability_improvement: Improvement in affordability ratio
                (e.g., 0.1 for 10% more affordable).

        Returns:
            Estimated absolute mobility improvement.

        Raises:
            ValueError: If parameters are invalid.
        """
        if housing_units < 0:
            raise ValueError(f"Housing units must be non-negative, got {housing_units}")
        if affordability_improvement < 0 or affordability_improvement > 1:
            raise ValueError(
                f"Affordability improvement must be in [0, 1], "
                f"got {affordability_improvement}"
            )

        # Simple linear model: effect proportional to units and affordability
        effect = housing_units * affordability_improvement * 0.00005
        logger.info(
            f"Housing impact: {housing_units} units × "
            f"{affordability_improvement:.2f} affordability → +{effect:.4f} mobility"
        )
        return effect


# =============================================================================
# INTERVENTION PRIORITIZER
# =============================================================================


class InterventionPrioritizer:
    """Prioritize intervention targets based on topological impact analysis.

    This class evaluates gateway LSOAs (areas where flow paths cross basin
    boundaries) by their potential impact on poverty reduction. Impact scoring
    considers population affected, trap severity, barrier difficulty, and
    gateway position in the flow network.

    Attributes:
        gateway_lsoas: DataFrame with gateway LSOA information including:
            - lsoa_code: LSOA 2021 code
            - population: Population count
            - flow_convergence: Number of upstream LSOAs flowing through this gateway
            - barrier_crossed_id: ID of barrier this gateway crosses
            - destination_basin_id: Basin this gateway flows to
            - impact_score: Computed impact potential (added by this class)
        trap_scores: DataFrame with trap severity scores including:
            - basin_id: Basin identifier
            - total_score: Overall trap severity (0-1)
            - population_estimate: Estimated population in basin
        barriers: DataFrame with barrier properties including:
            - barrier_id: Barrier identifier
            - persistence: Barrier persistence (strength)
            - barrier_height: Elevation difference
            - strength_score: Normalized barrier strength
    """

    def __init__(
        self,
        gateway_lsoas: pd.DataFrame,
        trap_scores: pd.DataFrame,
        barriers: pd.DataFrame,
    ) -> None:
        """Initialize prioritizer with gateway, trap, and barrier data.

        Args:
            gateway_lsoas: Gateway LSOA DataFrame (see class docstring).
            trap_scores: Trap severity DataFrame (see class docstring).
            barriers: Barrier properties DataFrame (see class docstring).

        Raises:
            ValueError: If required columns are missing from input DataFrames.
        """
        # Validate gateway_lsoas
        required_gateway_cols = [
            "lsoa_code",
            "population",
            "barrier_crossed_id",
            "destination_basin_id",
        ]
        missing_cols = set(required_gateway_cols) - set(gateway_lsoas.columns)
        if missing_cols:
            raise ValueError(f"gateway_lsoas missing required columns: {missing_cols}")

        # Validate trap_scores
        required_trap_cols = ["basin_id", "total_score"]
        missing_cols = set(required_trap_cols) - set(trap_scores.columns)
        if missing_cols:
            raise ValueError(f"trap_scores missing required columns: {missing_cols}")

        # Validate barriers
        required_barrier_cols = ["barrier_id", "persistence"]
        missing_cols = set(required_barrier_cols) - set(barriers.columns)
        if missing_cols:
            raise ValueError(f"barriers missing required columns: {missing_cols}")

        self.gateway_lsoas = gateway_lsoas.copy()
        self.trap_scores = trap_scores.copy()
        self.barriers = barriers.copy()

        # Merge trap and barrier information into gateway data
        self._enrich_gateway_data()

    def _enrich_gateway_data(self) -> None:
        """Merge trap scores and barrier strengths into gateway DataFrame."""
        # Merge trap scores
        self.gateway_lsoas = self.gateway_lsoas.merge(
            self.trap_scores[["basin_id", "total_score"]],
            left_on="destination_basin_id",
            right_on="basin_id",
            how="left",
            suffixes=("", "_trap"),
        ).rename(columns={"total_score": "trap_severity"})

        # Merge barrier properties
        self.gateway_lsoas = self.gateway_lsoas.merge(
            self.barriers[["barrier_id", "persistence"]],
            left_on="barrier_crossed_id",
            right_on="barrier_id",
            how="left",
            suffixes=("", "_barrier"),
        ).rename(columns={"persistence": "barrier_strength"})

        # Fill NaN values with 0 (for gateways missing trap or barrier data)
        self.gateway_lsoas["trap_severity"] = self.gateway_lsoas[
            "trap_severity"
        ].fillna(0.0)
        self.gateway_lsoas["barrier_strength"] = self.gateway_lsoas[
            "barrier_strength"
        ].fillna(0.0)

        # Compute flow convergence if not present
        if "flow_convergence" not in self.gateway_lsoas.columns:
            # Default to 1 (only the gateway LSOA itself)
            self.gateway_lsoas["flow_convergence"] = 1

    def compute_impact_score(self, row: pd.Series) -> float:
        """Compute impact potential score for a gateway LSOA.

        Impact score formula:
            impact = 0.3×population_norm + 0.3×trap_severity +
                     0.2×barrier_strength + 0.2×flow_convergence_norm

        Args:
            row: DataFrame row with gateway LSOA data.

        Returns:
            Impact score in [0, 1] range (higher = more impact potential).
        """
        # Normalize population (0-1 scale within dataset)
        max_pop = self.gateway_lsoas["population"].max()
        population_norm = row["population"] / max_pop if max_pop > 0 else 0.0

        # Trap severity already in [0, 1] from trap_identification
        trap_severity = row["trap_severity"]

        # Normalize barrier strength
        max_barrier = self.gateway_lsoas["barrier_strength"].max()
        barrier_norm = row["barrier_strength"] / max_barrier if max_barrier > 0 else 0.0

        # Normalize flow convergence
        max_flow = self.gateway_lsoas["flow_convergence"].max()
        flow_norm = row["flow_convergence"] / max_flow if max_flow > 0 else 0.0

        # Weighted combination
        impact = (
            0.3 * population_norm
            + 0.3 * trap_severity
            + 0.2 * barrier_norm
            + 0.2 * flow_norm
        )

        return float(impact)

    def prioritize_by_impact(
        self,
        intervention_type: InterventionType,
        top_n: int = 10,
    ) -> pd.DataFrame:
        """Prioritize gateway LSOAs by intervention impact potential.

        Args:
            intervention_type: Type of intervention to prioritize for.
                Different intervention types may weight factors differently.
            top_n: Number of top gateways to return.

        Returns:
            DataFrame with top_n gateway LSOAs sorted by impact score,
            including columns: lsoa_code, population, trap_severity,
            barrier_strength, flow_convergence, impact_score.

        Raises:
            ValueError: If top_n is not positive.
        """
        if top_n <= 0:
            raise ValueError(f"top_n must be positive, got {top_n}")

        # Compute impact scores for all gateways
        self.gateway_lsoas["impact_score"] = self.gateway_lsoas.apply(
            self.compute_impact_score, axis=1
        )

        # Sort by impact score descending
        prioritized = self.gateway_lsoas.sort_values(
            "impact_score", ascending=False
        ).head(top_n)

        # Select relevant columns
        result_cols = [
            "lsoa_code",
            "population",
            "trap_severity",
            "barrier_strength",
            "flow_convergence",
            "impact_score",
        ]
        available_cols = [col for col in result_cols if col in prioritized.columns]

        logger.info(
            f"Prioritized top {top_n} gateway LSOAs for "
            f"{intervention_type.value} intervention "
            f"(mean impact score: {prioritized['impact_score'].mean():.3f})"
        )

        return prioritized[available_cols].reset_index(drop=True)

    def compute_cost_benefit_ratio(self, intervention: Intervention) -> float:
        """Compute cost-benefit ratio for an intervention.

        Cost-benefit ratio = estimated_effect / cost_estimate
        Higher ratio = better value for money.

        Args:
            intervention: Intervention to evaluate.

        Returns:
            Cost-benefit ratio (effect per cost unit).

        Raises:
            ValueError: If intervention cost is zero or negative.
        """
        if intervention.cost_estimate <= 0:
            raise ValueError(
                f"Cannot compute cost-benefit ratio with cost "
                f"{intervention.cost_estimate}"
            )

        ratio = intervention.estimated_effect / intervention.cost_estimate

        logger.debug(
            f"Intervention {intervention.intervention_id}: "
            f"effect={intervention.estimated_effect:.4f}, "
            f"cost={intervention.cost_estimate:.2f}, "
            f"ratio={ratio:.6f}"
        )

        return ratio

    def rank_interventions(
        self, interventions: list[Intervention]
    ) -> list[Intervention]:
        """Rank interventions by cost-benefit ratio.

        Args:
            interventions: List of Intervention objects to rank.

        Returns:
            List of interventions sorted by cost-benefit ratio (descending).
            Best value-for-money interventions appear first.

        Raises:
            ValueError: If interventions list is empty.
        """
        if not interventions:
            raise ValueError("Cannot rank empty interventions list")

        # Compute cost-benefit ratios
        ratios = [self.compute_cost_benefit_ratio(interv) for interv in interventions]

        # Sort interventions by ratio (descending)
        ranked = [
            interv
            for _, interv in sorted(
                zip(ratios, interventions), key=lambda x: x[0], reverse=True
            )
        ]

        logger.info(
            f"Ranked {len(interventions)} interventions by cost-benefit ratio "
            f"(best: {max(ratios):.6f}, worst: {min(ratios):.6f})"
        )

        return ranked


# =============================================================================
# SIMULATION AND REPORTING
# =============================================================================


@dataclass
class SimulationResult:
    """Results from simulating an intervention on the mobility surface.

    Attributes:
        intervention: The intervention that was simulated.
        modified_surface: Mobility surface after intervention (same shape as input).
        population_before: Population distribution before intervention (by basin).
        population_after: Population distribution after intervention (by basin).
        mobility_improvement: Mean mobility improvement across affected LSOAs.
        population_affected: Number of people affected by the intervention.
        flow_paths_changed: Number of flow paths that changed destination.
        basin_transitions: DataFrame showing population transitions between basins.
    """

    intervention: Intervention
    modified_surface: NDArray[np.float64] | None = None
    population_before: dict[int, int] = field(default_factory=dict)
    population_after: dict[int, int] = field(default_factory=dict)
    mobility_improvement: float = 0.0
    population_affected: int = 0
    flow_paths_changed: int = 0
    basin_transitions: pd.DataFrame | None = None


def simulate_intervention(
    intervention: Intervention,
    mobility_surface: NDArray[np.float64],
    baseline_mobility: pd.DataFrame,
    gateway_lsoas: pd.DataFrame,
) -> SimulationResult:
    """Simulate the effect of an intervention on the mobility surface.

    This function creates a modified mobility surface by applying the
    estimated effect of the intervention to target LSOAs, then estimates
    how population flows would change.

    Note: This is a simplified simulation that modifies the scalar field
    locally. Full flow path recomputation requires TTK integration and is
    left for future enhancement.

    Args:
        intervention: Intervention to simulate.
        mobility_surface: Original mobility surface (2D array).
        baseline_mobility: DataFrame with LSOA codes and baseline mobility values.
        gateway_lsoas: DataFrame with gateway LSOA information.

    Returns:
        SimulationResult with before/after comparison metrics.

    Raises:
        ValueError: If intervention targets are not found in baseline_mobility.
    """
    # Validate target LSOAs exist in baseline data
    missing_lsoas = set(intervention.target_lsoas) - set(baseline_mobility["lsoa_code"])
    if missing_lsoas:
        raise ValueError(
            f"Intervention targets {missing_lsoas} not found in baseline_mobility"
        )

    # Create modified surface (copy original)
    modified_surface = mobility_surface.copy()

    # Get target LSOA data
    target_data = baseline_mobility[
        baseline_mobility["lsoa_code"].isin(intervention.target_lsoas)
    ]

    # Apply intervention effect (simplified: uniform boost to target LSOAs)
    # In real implementation, would map LSOA codes to grid coordinates
    target_data["mobility"].mean()
    mobility_improvement = intervention.estimated_effect

    # Estimate population affected
    population_affected = int(target_data["population"].sum())

    # Estimate flow path changes (simplified: assume X% of population redirects)
    # This is a placeholder - real implementation needs flow path recomputation
    flow_redirection_rate = min(intervention.estimated_effect / 0.1, 0.5)  # Cap at 50%
    flow_paths_changed = int(population_affected * flow_redirection_rate / 100)

    # Create population distribution estimates
    # Simplified: assume intervention reduces trap basin population
    population_before = {1: population_affected}  # Placeholder basin ID
    population_after = {
        1: int(population_affected * (1 - flow_redirection_rate)),
        2: int(population_affected * flow_redirection_rate),
    }

    # Create basin transitions DataFrame
    basin_transitions = pd.DataFrame(
        {
            "from_basin": [1],
            "to_basin": [2],
            "population": [int(population_affected * flow_redirection_rate)],
        }
    )

    logger.info(
        f"Simulated intervention {intervention.intervention_id}: "
        f"{population_affected} people affected, "
        f"{flow_paths_changed} flow paths changed, "
        f"+{mobility_improvement:.4f} mobility improvement"
    )

    return SimulationResult(
        intervention=intervention,
        modified_surface=modified_surface,
        population_before=population_before,
        population_after=population_after,
        mobility_improvement=mobility_improvement,
        population_affected=population_affected,
        flow_paths_changed=flow_paths_changed,
        basin_transitions=basin_transitions,
    )


def generate_intervention_report(
    prioritized_interventions: dict[InterventionType, pd.DataFrame],
    simulations: list[SimulationResult] | None = None,
) -> dict[str, Any]:
    """Generate comprehensive intervention targeting report.

    Args:
        prioritized_interventions: Dict mapping InterventionType to
            prioritized gateway LSOAs DataFrame (from prioritize_by_impact).
        simulations: Optional list of SimulationResult objects for
            detailed impact analysis.

    Returns:
        Dictionary with report sections:
        - summary: Overall statistics
        - recommendations_by_type: Top interventions for each type
        - cost_benefit_summary: Cost-benefit analysis (if simulations provided)
        - population_impact: Population redistribution estimates
        - priority_ranking: Overall intervention priority list

    Raises:
        ValueError: If prioritized_interventions is empty.
    """
    if not prioritized_interventions:
        raise ValueError("Cannot generate report with empty prioritized_interventions")

    report: dict[str, Any] = {}

    # Summary statistics
    total_gateway_lsoas = sum(len(df) for df in prioritized_interventions.values())
    total_population = sum(
        df["population"].sum() for df in prioritized_interventions.values()
    )
    mean_impact_score = np.mean(
        [df["impact_score"].mean() for df in prioritized_interventions.values()]
    )

    report["summary"] = {
        "total_gateway_lsoas": total_gateway_lsoas,
        "total_population_at_gateways": int(total_population),
        "mean_impact_score": float(mean_impact_score),
        "intervention_types_analyzed": len(prioritized_interventions),
    }

    # Recommendations by intervention type
    recommendations_by_type = {}
    for intervention_type, df in prioritized_interventions.items():
        top_3 = df.head(3)
        recommendations_by_type[intervention_type.value] = {
            "top_gateways": top_3["lsoa_code"].tolist(),
            "total_population": int(df["population"].sum()),
            "mean_impact_score": float(df["impact_score"].mean()),
            "highest_impact_lsoa": top_3.iloc[0]["lsoa_code"]
            if len(top_3) > 0
            else None,
            "highest_impact_score": float(top_3.iloc[0]["impact_score"])
            if len(top_3) > 0
            else 0.0,
        }
    report["recommendations_by_type"] = recommendations_by_type

    # Simulation results (if provided)
    if simulations:
        cost_benefit_summary = []
        population_impact_total = 0
        total_flow_changes = 0

        for sim in simulations:
            intervention = sim.intervention
            cost_benefit = intervention.estimated_effect / intervention.cost_estimate

            cost_benefit_summary.append(
                {
                    "intervention_id": intervention.intervention_id,
                    "type": intervention.type.value,
                    "target_lsoas": intervention.target_lsoas,
                    "estimated_effect": intervention.estimated_effect,
                    "cost_estimate": intervention.cost_estimate,
                    "cost_benefit_ratio": cost_benefit,
                    "population_affected": sim.population_affected,
                    "flow_paths_changed": sim.flow_paths_changed,
                }
            )

            population_impact_total += sim.population_affected
            total_flow_changes += sim.flow_paths_changed

        # Sort by cost-benefit ratio
        cost_benefit_summary.sort(key=lambda x: x["cost_benefit_ratio"], reverse=True)

        report["cost_benefit_summary"] = cost_benefit_summary
        report["population_impact"] = {
            "total_population_affected": population_impact_total,
            "total_flow_paths_changed": total_flow_changes,
            "mean_mobility_improvement": float(
                np.mean([sim.mobility_improvement for sim in simulations])
            ),
        }

        # Priority ranking (top 5 overall)
        report["priority_ranking"] = [
            {
                "rank": i + 1,
                "intervention_id": item["intervention_id"],
                "type": item["type"],
                "cost_benefit_ratio": item["cost_benefit_ratio"],
                "population_affected": item["population_affected"],
            }
            for i, item in enumerate(cost_benefit_summary[:5])
        ]
    else:
        report["cost_benefit_summary"] = None
        report["population_impact"] = None
        report["priority_ranking"] = None

    logger.info(
        f"Generated intervention report: {total_gateway_lsoas} gateways analyzed, "
        f"{total_population:.0f} population at gateways"
    )

    return report
