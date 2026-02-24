"""Tests for trajectory_builder: merging, gap handling, filtering."""

from __future__ import annotations

import pandas as pd

from trajectory_tda.data.trajectory_builder import (
    STATES,
    _find_longest_consecutive_run,
    _interpolate_gaps,
    build_trajectories,
)


class TestInterpolateGaps:
    """Test gap interpolation logic."""

    def test_no_gaps(self):
        years = [2000, 2001, 2002, 2003]
        states = ["EH", "EH", "EM", "EH"]
        result = _interpolate_gaps(years, states, max_gap=2)
        assert result is not None
        filled_years, filled_states = result
        assert filled_years == years
        assert filled_states == states

    def test_one_year_gap(self):
        years = [2000, 2002, 2003]
        states = ["EH", "EM", "EH"]
        result = _interpolate_gaps(years, states, max_gap=2)
        assert result is not None
        filled_years, filled_states = result
        assert 2001 in filled_years
        assert len(filled_years) == 4
        # Gap filled with NN (previous state)
        idx_2001 = filled_years.index(2001)
        assert filled_states[idx_2001] == "EH"

    def test_two_year_gap(self):
        years = [2000, 2003]
        states = ["EL", "EM"]
        result = _interpolate_gaps(years, states, max_gap=2)
        assert result is not None
        filled_years, filled_states = result
        assert len(filled_years) == 4  # 2000, 2001, 2002, 2003

    def test_gap_too_large(self):
        years = [2000, 2004]
        states = ["EH", "EM"]
        result = _interpolate_gaps(years, states, max_gap=2)
        assert result is None  # Gap of 3 exceeds max_gap=2

    def test_single_year(self):
        result = _interpolate_gaps([2000], ["EH"], max_gap=2)
        assert result is not None
        assert result == ([2000], ["EH"])


class TestFindLongestRun:
    """Test consecutive run detection."""

    def test_all_consecutive(self):
        years = [2000, 2001, 2002, 2003, 2004]
        states = ["EH"] * 5
        result = _find_longest_consecutive_run(years, states, min_years=3)
        assert result is not None
        assert len(result[0]) == 5

    def test_two_runs(self):
        years = [2000, 2001, 2002, 2005, 2006, 2007, 2008]
        states = ["EH", "EM", "EL", "UL", "IL", "IM", "EH"]
        result = _find_longest_consecutive_run(years, states, min_years=3)
        assert result is not None
        # Longest run is 4 years (2005-2008)
        assert len(result[0]) == 4

    def test_too_short(self):
        years = [2000, 2002, 2004]
        states = ["EH", "EM", "EL"]
        result = _find_longest_consecutive_run(years, states, min_years=3)
        assert result is None


class TestBuildTrajectories:
    """Test trajectory construction from DataFrames."""

    def test_basic_merge(self):
        emp_df = pd.DataFrame(
            {
                "pidp": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "year": list(range(2000, 2010)),
                "emp_status": ["E"] * 8 + ["U", "E"],
            }
        )
        inc_df = pd.DataFrame(
            {
                "pidp": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "year": list(range(2000, 2010)),
                "income_band": ["H"] * 7 + ["M", "L", "M"],
            }
        )

        trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df, min_years=10)

        assert len(trajectories) == 1
        assert len(trajectories[0]) == 10
        assert all(s in STATES for s in trajectories[0])
        assert metadata.iloc[0]["n_years"] == 10

    def test_filter_short(self):
        emp_df = pd.DataFrame(
            {
                "pidp": [1, 1, 1],
                "year": [2000, 2001, 2002],
                "emp_status": ["E", "E", "U"],
            }
        )
        inc_df = pd.DataFrame(
            {
                "pidp": [1, 1, 1],
                "year": [2000, 2001, 2002],
                "income_band": ["H", "H", "L"],
            }
        )

        trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df, min_years=5)

        assert len(trajectories) == 0

    def test_multiple_persons(self):
        emp_df = pd.DataFrame(
            {
                "pidp": [1] * 12 + [2] * 12,
                "year": list(range(2000, 2012)) * 2,
                "emp_status": ["E"] * 12 + ["I"] * 12,
            }
        )
        inc_df = pd.DataFrame(
            {
                "pidp": [1] * 12 + [2] * 12,
                "year": list(range(2000, 2012)) * 2,
                "income_band": ["H"] * 12 + ["L"] * 12,
            }
        )

        trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df, min_years=10)

        assert len(trajectories) == 2
        assert metadata.iloc[0]["dominant_state"] == "EH"
        assert metadata.iloc[1]["dominant_state"] == "IL"

    def test_all_nine_states(self):
        """Verify all 9 states are valid."""
        for state in STATES:
            emp = state[0]  # E, U, or I
            inc = state[1]  # L, M, or H
            assert emp in {"E", "U", "I"}
            assert inc in {"L", "M", "H"}

    def test_empty_input(self):
        emp_df = pd.DataFrame(columns=["pidp", "year", "emp_status"])
        inc_df = pd.DataFrame(columns=["pidp", "year", "income_band"])

        trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df, min_years=10)
        assert len(trajectories) == 0
