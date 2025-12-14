"""
Tests for intervention targeting framework.

Tests cover:
- Intervention type definitions
- Intervention dataclass validation
- Impact model estimation methods
- Intervention prioritizer and cost-benefit analysis
"""

import numpy as np
import pandas as pd
import pytest

from poverty_tda.analysis.interventions import (
    ImpactModel,
    Intervention,
    InterventionPrioritizer,
    InterventionType,
    SimulationResult,
    generate_intervention_report,
    simulate_intervention,
)

# =============================================================================
# INTERVENTION TYPE AND DATACLASS TESTS
# =============================================================================


def test_intervention_type_enum():
    """Test InterventionType enum has expected values."""
    assert InterventionType.EDUCATION.value == "education"
    assert InterventionType.TRANSPORT.value == "transport"
    assert InterventionType.EMPLOYMENT.value == "employment"
    assert InterventionType.HOUSING.value == "housing"


def test_intervention_creation_valid():
    """Test creating valid Intervention instance."""
    intervention = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=["E01000001", "E01000002"],
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
        description="School quality improvement",
        baseline_mobility=0.3,
        affected_population=5000,
    )

    assert intervention.intervention_id == 1
    assert intervention.type == InterventionType.EDUCATION
    assert len(intervention.target_lsoas) == 2
    assert intervention.estimated_effect == 0.05
    assert intervention.cost_estimate == 10.0
    assert intervention.implementation_time == 24
    assert intervention.affected_population == 5000


def test_intervention_validation_negative_cost():
    """Test Intervention rejects negative cost."""
    with pytest.raises(ValueError, match="Cost must be positive"):
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=["E01000001"],
            estimated_effect=0.05,
            cost_estimate=-10.0,
            implementation_time=24,
        )


def test_intervention_validation_negative_time():
    """Test Intervention rejects negative implementation time."""
    with pytest.raises(ValueError, match="Implementation time must be positive"):
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=["E01000001"],
            estimated_effect=0.05,
            cost_estimate=10.0,
            implementation_time=-5,
        )


def test_intervention_validation_empty_lsoas():
    """Test Intervention requires at least one target LSOA."""
    with pytest.raises(ValueError, match="Must specify at least one target LSOA"):
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=[],
            estimated_effect=0.05,
            cost_estimate=10.0,
            implementation_time=24,
        )


# =============================================================================
# IMPACT MODEL TESTS
# =============================================================================


def test_impact_model_initialization():
    """Test ImpactModel initializes with expected coefficients."""
    model = ImpactModel()

    assert model.education_ks4_coefficient > 0
    assert model.transport_barrier_coefficient > 0
    assert model.employment_job_coefficient > 0


def test_estimate_education_impact_positive():
    """Test education impact estimation with valid inputs."""
    model = ImpactModel()
    baseline_mobility = 0.3
    ks4_improvement_pct = 10.0

    impact = model.estimate_education_impact(baseline_mobility, ks4_improvement_pct)

    # +10% KS4 → +0.02 mobility (10 × 0.002)
    assert impact == pytest.approx(0.02, abs=1e-6)


def test_estimate_education_impact_zero():
    """Test education impact is zero when no improvement."""
    model = ImpactModel()
    impact = model.estimate_education_impact(0.3, 0.0)
    assert impact == pytest.approx(0.0, abs=1e-9)


def test_estimate_education_impact_invalid_ks4():
    """Test education impact rejects invalid KS4 values."""
    model = ImpactModel()

    with pytest.raises(ValueError, match="KS4 improvement must be in"):
        model.estimate_education_impact(0.3, -5.0)

    with pytest.raises(ValueError, match="KS4 improvement must be in"):
        model.estimate_education_impact(0.3, 150.0)


def test_estimate_transport_impact_positive():
    """Test transport impact estimation with valid inputs."""
    model = ImpactModel()
    barrier_height = 0.2
    barrier_reduction_pct = 50.0

    impact = model.estimate_transport_impact(barrier_height, barrier_reduction_pct)

    # 0.2 × 0.5 × 0.5 = 0.05
    assert impact == pytest.approx(0.05, abs=1e-6)


def test_estimate_transport_impact_zero_reduction():
    """Test transport impact is zero with no barrier reduction."""
    model = ImpactModel()
    impact = model.estimate_transport_impact(0.2, 0.0)
    assert impact == pytest.approx(0.0, abs=1e-9)


def test_estimate_transport_impact_invalid_reduction():
    """Test transport impact rejects invalid reduction values."""
    model = ImpactModel()

    with pytest.raises(ValueError, match="Barrier reduction must be in"):
        model.estimate_transport_impact(0.2, -10.0)

    with pytest.raises(ValueError, match="Barrier reduction must be in"):
        model.estimate_transport_impact(0.2, 150.0)


def test_estimate_employment_impact_positive():
    """Test employment impact estimation with valid inputs."""
    model = ImpactModel()
    baseline_mobility = 0.3
    job_creation_count = 1000

    impact = model.estimate_employment_impact(baseline_mobility, job_creation_count)

    # 1000 × 0.00001 = 0.01
    assert impact == pytest.approx(0.01, abs=1e-6)


def test_estimate_employment_impact_zero_jobs():
    """Test employment impact is zero with no jobs created."""
    model = ImpactModel()
    impact = model.estimate_employment_impact(0.3, 0)
    assert impact == pytest.approx(0.0, abs=1e-9)


def test_estimate_employment_impact_invalid_jobs():
    """Test employment impact rejects negative job count."""
    model = ImpactModel()

    with pytest.raises(ValueError, match="Job creation count must be non-negative"):
        model.estimate_employment_impact(0.3, -100)


def test_estimate_housing_impact_positive():
    """Test housing impact estimation with valid inputs."""
    model = ImpactModel()
    baseline_mobility = 0.3
    housing_units = 500
    affordability_improvement = 0.2

    impact = model.estimate_housing_impact(
        baseline_mobility, housing_units, affordability_improvement
    )

    # 500 × 0.2 × 0.00005 = 0.005
    assert impact == pytest.approx(0.005, abs=1e-6)


def test_estimate_housing_impact_zero():
    """Test housing impact is zero with no units."""
    model = ImpactModel()
    impact = model.estimate_housing_impact(0.3, 0, 0.2)
    assert impact == pytest.approx(0.0, abs=1e-9)


def test_estimate_housing_impact_invalid_units():
    """Test housing impact rejects negative housing units."""
    model = ImpactModel()

    with pytest.raises(ValueError, match="Housing units must be non-negative"):
        model.estimate_housing_impact(0.3, -100, 0.2)


def test_estimate_housing_impact_invalid_affordability():
    """Test housing impact rejects invalid affordability values."""
    model = ImpactModel()

    with pytest.raises(ValueError, match="Affordability improvement must be in"):
        model.estimate_housing_impact(0.3, 500, -0.1)

    with pytest.raises(ValueError, match="Affordability improvement must be in"):
        model.estimate_housing_impact(0.3, 500, 1.5)


# =============================================================================
# INTERVENTION PRIORITIZER TESTS
# =============================================================================


@pytest.fixture
def sample_gateway_data():
    """Create sample gateway LSOA data for testing."""
    return pd.DataFrame(
        {
            "lsoa_code": ["E01000001", "E01000002", "E01000003", "E01000004"],
            "population": [1000, 2000, 1500, 800],
            "barrier_crossed_id": [1, 1, 2, 2],
            "destination_basin_id": [10, 10, 20, 20],
            "flow_convergence": [1, 3, 2, 1],
        }
    )


@pytest.fixture
def sample_trap_data():
    """Create sample trap score data for testing."""
    return pd.DataFrame(
        {
            "basin_id": [10, 20],
            "total_score": [0.8, 0.5],
            "population_estimate": [50000, 30000],
        }
    )


@pytest.fixture
def sample_barrier_data():
    """Create sample barrier data for testing."""
    return pd.DataFrame(
        {
            "barrier_id": [1, 2],
            "persistence": [0.6, 0.4],
            "barrier_height": [0.2, 0.15],
        }
    )


def test_prioritizer_initialization_valid(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test InterventionPrioritizer initializes with valid data."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    assert len(prioritizer.gateway_lsoas) == 4
    assert "trap_severity" in prioritizer.gateway_lsoas.columns
    assert "barrier_strength" in prioritizer.gateway_lsoas.columns


def test_prioritizer_initialization_missing_gateway_columns(
    sample_trap_data, sample_barrier_data
):
    """Test prioritizer rejects gateway data with missing columns."""
    bad_gateway_data = pd.DataFrame(
        {
            "lsoa_code": ["E01000001"],
            "population": [1000],
            # Missing barrier_crossed_id and destination_basin_id
        }
    )

    with pytest.raises(ValueError, match="gateway_lsoas missing required columns"):
        InterventionPrioritizer(
            gateway_lsoas=bad_gateway_data,
            trap_scores=sample_trap_data,
            barriers=sample_barrier_data,
        )


def test_prioritizer_initialization_missing_trap_columns(
    sample_gateway_data, sample_barrier_data
):
    """Test prioritizer rejects trap data with missing columns."""
    bad_trap_data = pd.DataFrame(
        {
            "basin_id": [10, 20],
            # Missing total_score
        }
    )

    with pytest.raises(ValueError, match="trap_scores missing required columns"):
        InterventionPrioritizer(
            gateway_lsoas=sample_gateway_data,
            trap_scores=bad_trap_data,
            barriers=sample_barrier_data,
        )


def test_prioritizer_initialization_missing_barrier_columns(
    sample_gateway_data, sample_trap_data
):
    """Test prioritizer rejects barrier data with missing columns."""
    bad_barrier_data = pd.DataFrame(
        {
            "barrier_id": [1, 2],
            # Missing persistence
        }
    )

    with pytest.raises(ValueError, match="barriers missing required columns"):
        InterventionPrioritizer(
            gateway_lsoas=sample_gateway_data,
            trap_scores=sample_trap_data,
            barriers=bad_barrier_data,
        )


def test_prioritizer_enriches_gateway_data(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test prioritizer merges trap and barrier data into gateways."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    # Check E01000001: destination_basin_id=10 → trap_severity=0.8
    row1 = prioritizer.gateway_lsoas[
        prioritizer.gateway_lsoas["lsoa_code"] == "E01000001"
    ].iloc[0]
    assert row1["trap_severity"] == pytest.approx(0.8, abs=1e-6)

    # Check E01000001: barrier_crossed_id=1 → barrier_strength=0.6
    assert row1["barrier_strength"] == pytest.approx(0.6, abs=1e-6)


def test_compute_impact_score(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test impact score computation logic."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    # Get first row (E01000001)
    row = prioritizer.gateway_lsoas.iloc[0]
    impact = prioritizer.compute_impact_score(row)

    # Impact should be in [0, 1]
    assert 0.0 <= impact <= 1.0

    # Impact formula: 0.3×pop_norm + 0.3×trap + 0.2×barrier_norm
    # + 0.2×flow_norm
    # E01000001: pop=1000 (max=2000→0.5), trap=0.8,
    # barrier=0.6 (max=0.6→1.0), flow=1 (max=3→0.333)
    expected = 0.3 * 0.5 + 0.3 * 0.8 + 0.2 * 1.0 + 0.2 * (1 / 3)
    assert impact == pytest.approx(expected, abs=1e-6)


def test_prioritize_by_impact_returns_top_n(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test prioritize_by_impact returns correct number of results."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    result = prioritizer.prioritize_by_impact(InterventionType.EDUCATION, top_n=2)

    assert len(result) == 2
    assert "lsoa_code" in result.columns
    assert "impact_score" in result.columns


def test_prioritize_by_impact_sorted_descending(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test prioritize_by_impact returns results sorted by impact score."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    result = prioritizer.prioritize_by_impact(InterventionType.EDUCATION, top_n=4)

    # Check impact scores are descending
    impact_scores = result["impact_score"].values
    assert all(
        impact_scores[i] >= impact_scores[i + 1] for i in range(len(impact_scores) - 1)
    )


def test_prioritize_by_impact_invalid_top_n(
    sample_gateway_data, sample_trap_data, sample_barrier_data
):
    """Test prioritize_by_impact rejects invalid top_n values."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=sample_gateway_data,
        trap_scores=sample_trap_data,
        barriers=sample_barrier_data,
    )

    with pytest.raises(ValueError, match="top_n must be positive"):
        prioritizer.prioritize_by_impact(InterventionType.EDUCATION, top_n=0)

    with pytest.raises(ValueError, match="top_n must be positive"):
        prioritizer.prioritize_by_impact(InterventionType.EDUCATION, top_n=-5)


def test_compute_cost_benefit_ratio_positive():
    """Test cost-benefit ratio computation with valid intervention."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=pd.DataFrame(
            {
                "lsoa_code": ["E01000001"],
                "population": [1000],
                "barrier_crossed_id": [1],
                "destination_basin_id": [10],
            }
        ),
        trap_scores=pd.DataFrame({"basin_id": [10], "total_score": [0.8]}),
        barriers=pd.DataFrame({"barrier_id": [1], "persistence": [0.6]}),
    )

    intervention = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=["E01000001"],
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
    )

    ratio = prioritizer.compute_cost_benefit_ratio(intervention)

    # 0.05 / 10.0 = 0.005
    assert ratio == pytest.approx(0.005, abs=1e-9)


def test_compute_cost_benefit_ratio_zero_cost():
    """Test that Intervention dataclass rejects zero cost at creation."""
    # Zero cost is already rejected by Intervention.__post_init__
    # This test validates the dataclass validation happens before
    # cost-benefit computation
    with pytest.raises(ValueError, match="Cost must be positive"):
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=["E01000001"],
            estimated_effect=0.05,
            cost_estimate=0.0,  # Invalid - caught by dataclass validation
            implementation_time=24,
        )


def test_rank_interventions_by_cost_benefit():
    """Test intervention ranking by cost-benefit ratio."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=pd.DataFrame(
            {
                "lsoa_code": ["E01000001"],
                "population": [1000],
                "barrier_crossed_id": [1],
                "destination_basin_id": [10],
            }
        ),
        trap_scores=pd.DataFrame({"basin_id": [10], "total_score": [0.8]}),
        barriers=pd.DataFrame({"barrier_id": [1], "persistence": [0.6]}),
    )

    interventions = [
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=["E01000001"],
            estimated_effect=0.05,
            cost_estimate=10.0,  # ratio = 0.005
            implementation_time=24,
        ),
        Intervention(
            intervention_id=2,
            type=InterventionType.TRANSPORT,
            target_lsoas=["E01000001"],
            estimated_effect=0.08,
            cost_estimate=20.0,  # ratio = 0.004
            implementation_time=36,
        ),
        Intervention(
            intervention_id=3,
            type=InterventionType.EMPLOYMENT,
            target_lsoas=["E01000001"],
            estimated_effect=0.03,
            cost_estimate=5.0,  # ratio = 0.006 (best)
            implementation_time=12,
        ),
    ]

    ranked = prioritizer.rank_interventions(interventions)

    # Should be sorted by ratio descending: [3, 1, 2]
    assert ranked[0].intervention_id == 3
    assert ranked[1].intervention_id == 1
    assert ranked[2].intervention_id == 2


def test_rank_interventions_empty_list():
    """Test rank_interventions rejects empty list."""
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=pd.DataFrame(
            {
                "lsoa_code": ["E01000001"],
                "population": [1000],
                "barrier_crossed_id": [1],
                "destination_basin_id": [10],
            }
        ),
        trap_scores=pd.DataFrame({"basin_id": [10], "total_score": [0.8]}),
        barriers=pd.DataFrame({"barrier_id": [1], "persistence": [0.6]}),
    )

    with pytest.raises(ValueError, match="Cannot rank empty interventions list"):
        prioritizer.rank_interventions([])


# =============================================================================
# SIMULATION AND REPORTING TESTS
# =============================================================================


def test_simulate_intervention_basic():
    """Test basic intervention simulation."""
    intervention = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=["E01000001", "E01000002"],
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
    )

    # Mock mobility surface (10x10 grid)
    mobility_surface = np.random.rand(10, 10) * 0.5 + 0.3

    # Mock baseline mobility data
    baseline_mobility = pd.DataFrame(
        {
            "lsoa_code": ["E01000001", "E01000002", "E01000003"],
            "mobility": [0.3, 0.35, 0.4],
            "population": [1000, 1500, 2000],
        }
    )

    # Mock gateway data
    gateway_lsoas = pd.DataFrame(
        {
            "lsoa_code": ["E01000001", "E01000002"],
            "population": [1000, 1500],
            "barrier_crossed_id": [1, 1],
            "destination_basin_id": [10, 10],
        }
    )

    result = simulate_intervention(
        intervention, mobility_surface, baseline_mobility, gateway_lsoas
    )

    assert isinstance(result, SimulationResult)
    assert result.intervention == intervention
    assert result.modified_surface is not None
    assert result.population_affected > 0
    assert result.mobility_improvement == intervention.estimated_effect


def test_simulate_intervention_missing_lsoas():
    """Test simulation rejects interventions with missing LSOA targets."""
    intervention = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=["E01000999"],  # Not in baseline_mobility
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
    )

    mobility_surface = np.random.rand(10, 10)
    baseline_mobility = pd.DataFrame(
        {
            "lsoa_code": ["E01000001", "E01000002"],
            "mobility": [0.3, 0.35],
            "population": [1000, 1500],
        }
    )
    gateway_lsoas = pd.DataFrame(
        {
            "lsoa_code": ["E01000001"],
            "population": [1000],
            "barrier_crossed_id": [1],
            "destination_basin_id": [10],
        }
    )

    with pytest.raises(ValueError, match="not found in baseline_mobility"):
        simulate_intervention(
            intervention, mobility_surface, baseline_mobility, gateway_lsoas
        )


def test_generate_intervention_report_basic():
    """Test basic intervention report generation."""
    # Create prioritized interventions by type
    prioritized_interventions = {
        InterventionType.EDUCATION: pd.DataFrame(
            {
                "lsoa_code": ["E01000001", "E01000002"],
                "population": [1000, 1500],
                "trap_severity": [0.8, 0.7],
                "barrier_strength": [0.6, 0.5],
                "flow_convergence": [3, 2],
                "impact_score": [0.75, 0.65],
            }
        ),
        InterventionType.TRANSPORT: pd.DataFrame(
            {
                "lsoa_code": ["E01000003"],
                "population": [2000],
                "trap_severity": [0.9],
                "barrier_strength": [0.7],
                "flow_convergence": [4],
                "impact_score": [0.85],
            }
        ),
    }

    report = generate_intervention_report(prioritized_interventions)

    assert "summary" in report
    assert "recommendations_by_type" in report
    assert report["summary"]["total_gateway_lsoas"] == 3
    assert report["summary"]["total_population_at_gateways"] == 4500
    assert report["summary"]["intervention_types_analyzed"] == 2

    # Check recommendations by type
    assert "education" in report["recommendations_by_type"]
    assert "transport" in report["recommendations_by_type"]
    assert report["recommendations_by_type"]["education"]["total_population"] == 2500
    assert report["recommendations_by_type"]["transport"]["total_population"] == 2000


def test_generate_intervention_report_with_simulations():
    """Test report generation with simulation results."""
    prioritized_interventions = {
        InterventionType.EDUCATION: pd.DataFrame(
            {
                "lsoa_code": ["E01000001"],
                "population": [1000],
                "trap_severity": [0.8],
                "barrier_strength": [0.6],
                "flow_convergence": [3],
                "impact_score": [0.75],
            }
        ),
    }

    # Create mock simulations
    intervention1 = Intervention(
        intervention_id=1,
        type=InterventionType.EDUCATION,
        target_lsoas=["E01000001"],
        estimated_effect=0.05,
        cost_estimate=10.0,
        implementation_time=24,
    )
    intervention2 = Intervention(
        intervention_id=2,
        type=InterventionType.TRANSPORT,
        target_lsoas=["E01000002"],
        estimated_effect=0.03,
        cost_estimate=5.0,
        implementation_time=12,
    )

    simulations = [
        SimulationResult(
            intervention=intervention1,
            mobility_improvement=0.05,
            population_affected=1000,
            flow_paths_changed=50,
        ),
        SimulationResult(
            intervention=intervention2,
            mobility_improvement=0.03,
            population_affected=1500,
            flow_paths_changed=30,
        ),
    ]

    report = generate_intervention_report(prioritized_interventions, simulations)

    assert report["cost_benefit_summary"] is not None
    assert len(report["cost_benefit_summary"]) == 2
    assert report["population_impact"] is not None
    assert report["population_impact"]["total_population_affected"] == 2500
    assert report["priority_ranking"] is not None
    assert len(report["priority_ranking"]) == 2

    # Check cost-benefit sorting (intervention 2 should rank first:
    # 0.03/5 = 0.006 > 0.05/10 = 0.005)
    assert report["cost_benefit_summary"][0]["intervention_id"] == 2


def test_generate_intervention_report_empty_interventions():
    """Test report generation rejects empty interventions."""
    with pytest.raises(ValueError, match="Cannot generate report with empty"):
        generate_intervention_report({})


# =============================================================================
# INTEGRATION TEST
# =============================================================================


def test_full_intervention_workflow():
    """Integration test: full workflow from gateway prioritization to reporting."""
    # Step 1: Create sample data
    gateway_lsoas = pd.DataFrame(
        {
            "lsoa_code": ["E01000001", "E01000002", "E01000003"],
            "population": [1000, 2000, 1500],
            "barrier_crossed_id": [1, 1, 2],
            "destination_basin_id": [10, 10, 20],
            "flow_convergence": [1, 3, 2],
        }
    )

    trap_scores = pd.DataFrame(
        {
            "basin_id": [10, 20],
            "total_score": [0.8, 0.6],
        }
    )

    barriers = pd.DataFrame(
        {
            "barrier_id": [1, 2],
            "persistence": [0.7, 0.5],
        }
    )

    # Step 2: Initialize prioritizer
    prioritizer = InterventionPrioritizer(
        gateway_lsoas=gateway_lsoas,
        trap_scores=trap_scores,
        barriers=barriers,
    )

    # Step 3: Prioritize gateways for different intervention types
    prioritized = {
        InterventionType.EDUCATION: prioritizer.prioritize_by_impact(
            InterventionType.EDUCATION, top_n=2
        ),
        InterventionType.TRANSPORT: prioritizer.prioritize_by_impact(
            InterventionType.TRANSPORT, top_n=2
        ),
    }

    # Step 4: Create interventions based on top gateways
    impact_model = ImpactModel()
    interventions = []

    top_education_lsoa = prioritized[InterventionType.EDUCATION].iloc[0]["lsoa_code"]
    education_effect = impact_model.estimate_education_impact(0.3, 10.0)
    interventions.append(
        Intervention(
            intervention_id=1,
            type=InterventionType.EDUCATION,
            target_lsoas=[top_education_lsoa],
            estimated_effect=education_effect,
            cost_estimate=10.0,
            implementation_time=24,
        )
    )

    top_transport_lsoa = prioritized[InterventionType.TRANSPORT].iloc[0]["lsoa_code"]
    transport_effect = impact_model.estimate_transport_impact(0.2, 50.0)
    interventions.append(
        Intervention(
            intervention_id=2,
            type=InterventionType.TRANSPORT,
            target_lsoas=[top_transport_lsoa],
            estimated_effect=transport_effect,
            cost_estimate=15.0,
            implementation_time=36,
        )
    )

    # Step 5: Rank interventions by cost-benefit
    ranked = prioritizer.rank_interventions(interventions)

    # Validate ranking logic
    assert len(ranked) == 2
    ratios = [prioritizer.compute_cost_benefit_ratio(interv) for interv in ranked]
    assert ratios[0] >= ratios[1]  # Should be sorted descending

    # Step 6: Generate report
    report = generate_intervention_report(prioritized)

    assert report["summary"]["total_gateway_lsoas"] == 4  # 2 per type
    assert "education" in report["recommendations_by_type"]
    assert "transport" in report["recommendations_by_type"]

    # Validate prioritization logic
    assert report["recommendations_by_type"]["education"]["highest_impact_score"] > 0.0
    assert report["recommendations_by_type"]["transport"]["highest_impact_score"] > 0.0
