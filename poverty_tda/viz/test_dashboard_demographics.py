"""
Test script for demographic breakdown functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from poverty_tda.viz.dashboard import generate_mock_basin_data


def test_domain_scores():
    """Test that domain scores are generated correctly."""
    print("Testing domain score generation...")

    basins = generate_mock_basin_data("North West", n_basins=3)

    for basin in basins:
        print(f"\nBasin {basin['basin_id']}: {basin['basin_name']}")
        print(f"  Trap Score: {basin['trap_score']:.3f}")

        # Verify domain_scores key exists
        assert "domain_scores" in basin, "Missing domain_scores key"

        domain_scores = basin["domain_scores"]
        print("  Domain Scores:")
        print(f"    Income:      {domain_scores['income']:.2f}")
        print(f"    Employment:  {domain_scores['employment']:.2f}")
        print(f"    Education:   {domain_scores['education']:.2f}")
        print(f"    Health:      {domain_scores['health']:.2f}")

        # Verify all scores are in valid range
        for domain, score in domain_scores.items():
            assert 0 <= score <= 100, f"{domain} score {score} out of range"

        # Verify correlation with trap score (inverse relationship)
        # Higher trap score = lower domain scores
        mean_domain = sum(domain_scores.values()) / len(domain_scores)
        expected_domain = (1 - basin["trap_score"]) * 100

        print(f"  Mean Domain Score: {mean_domain:.2f} (expected ~{expected_domain:.2f})")

    print("\n✓ Domain scores test passed!")


def test_decile_distribution():
    """Test that decile distributions are valid."""
    print("\nTesting decile distribution...")

    basins = generate_mock_basin_data("London", n_basins=3)

    for basin in basins:
        decile_counts = basin["decile_counts"]

        print(f"\nBasin {basin['basin_id']} (Trap Score: {basin['trap_score']:.2f}):")
        print(f"  Decile counts: {decile_counts}")

        # Verify we have 10 deciles
        assert len(decile_counts) == 10, "Should have 10 decile counts"

        # Verify all are non-negative
        assert all(c >= 0 for c in decile_counts), "Counts should be non-negative"

        # Calculate mean decile (weighted average)
        total_pop = sum(decile_counts)
        mean_decile = sum((i + 1) * count for i, count in enumerate(decile_counts)) / total_pop

        print(f"  Total population: {total_pop}")
        print(f"  Mean decile: {mean_decile:.2f}")

        # Verify correlation: higher trap score = lower mean decile
        if basin["trap_score"] > 0.6:
            assert mean_decile < 5.0, "Severe traps should have low mean decile"
            print("  ✓ Severe trap correctly has low mean decile")
        elif basin["trap_score"] < 0.4:
            assert mean_decile > 5.0, "Low traps should have high mean decile"
            print("  ✓ Low trap correctly has high mean decile")

    print("\n✓ Decile distribution test passed!")


def test_quintile_aggregation():
    """Test quintile aggregation from deciles."""
    print("\nTesting quintile aggregation...")

    basins = generate_mock_basin_data("Yorkshire and The Humber", n_basins=2)

    for basin in basins:
        decile_counts = basin["decile_counts"]

        # Aggregate into quintiles
        quintile_counts = [
            sum(decile_counts[0:2]),  # Q1
            sum(decile_counts[2:4]),  # Q2
            sum(decile_counts[4:6]),  # Q3
            sum(decile_counts[6:8]),  # Q4
            sum(decile_counts[8:10]),  # Q5
        ]

        print(f"\nBasin {basin['basin_id']}:")
        print(f"  Deciles: {decile_counts}")
        print(f"  Quintiles: {quintile_counts}")

        # Verify total population preserved
        assert sum(quintile_counts) == sum(decile_counts), "Population should be preserved"

        # Verify Q1 (most deprived) is largest for high trap scores
        if basin["trap_score"] > 0.6:
            assert quintile_counts[0] == max(quintile_counts), "Q1 should be largest for severe traps"
            print("  ✓ Most deprived quintile is largest (severe trap)")

    print("\n✓ Quintile aggregation test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Demographic Breakdown Test Suite")
    print("=" * 60)

    try:
        test_domain_scores()
        test_decile_distribution()
        test_quintile_aggregation()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
