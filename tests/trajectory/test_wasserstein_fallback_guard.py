# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Guard the exact-vs-greedy Wasserstein convention. The W2 solver in
#   trajectory_tda.topology.vectorisation must fail loud when POT (`ot`) is
#   unavailable rather than silently degrading to greedy persistence-rank
#   matching, which is NOT optimal transport and inflated the frozen USoc H1
#   headline ~18x (WT-1c / WT-6 defect, 2026-07-14).

from __future__ import annotations

import sys

import numpy as np
import pytest

from poverty_tda.topology.multidim_ph import PHResult
from trajectory_tda.topology.vectorisation import (
    _import_exact_wasserstein_solver,
    wasserstein_distance,
)


def _ph(dgm: list[list[float]]) -> PHResult:
    """Wrap an H1 (birth, death) diagram as a PHResult (mirrors the battery)."""
    return PHResult(dgms={1: np.asarray(dgm, dtype=np.float64)})


# Two H1 diagrams whose points are scattered in birth, so greedy rank-matching
# (which ignores birth location) is badly suboptimal vs exact optimal transport.
# This reproduces the qualitative structure of the frozen USoc H1 defect.
_DGM_A = [[0.5, 3.0], [4.0, 4.6], [8.0, 8.5], [12.0, 12.4]]
_DGM_B = [[8.2, 8.7], [0.4, 2.9], [11.8, 12.3], [3.9, 4.4]]


def test_pot_present_returns_exact() -> None:
    """With POT importable, the exact optimal-transport value is returned."""
    solver = _import_exact_wasserstein_solver()
    assert solver is not None, "POT must be installed in the test venv (core dep since 2026-06-16)."

    got = wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2)

    # Reference: gudhi exact EMD directly on the same diagrams (W2 is order-
    # invariant, so the raw arrays are a valid reference for the function path).
    ref = float(solver(np.asarray(_DGM_A), np.asarray(_DGM_B), order=2, internal_p=2))
    assert got == pytest.approx(ref, rel=1e-12, abs=1e-12)


def test_pot_absent_raises_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """With POT hidden, the default call RAISES rather than degrading silently."""
    monkeypatch.setitem(sys.modules, "gudhi.wasserstein", None)
    assert _import_exact_wasserstein_solver() is None

    with pytest.raises(RuntimeError, match="greedy"):
        wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2)


def test_pot_absent_greedy_requires_explicit_optin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Greedy is reachable ONLY via explicit opt-in, and it differs from exact."""
    exact = wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2)

    monkeypatch.setitem(sys.modules, "gudhi.wasserstein", None)
    greedy = wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2, allow_greedy_fallback=True)

    assert np.isfinite(greedy)
    # Greedy rank-matching is suboptimal on birth-scattered H1 points, so it
    # over-estimates the distance relative to exact optimal transport.
    assert greedy > exact


def test_greedy_optin_ignored_when_pot_present() -> None:
    """allow_greedy_fallback has no effect when POT is available: exact wins."""
    exact = wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2)
    with_flag = wasserstein_distance(_ph(_DGM_A), _ph(_DGM_B), dim=1, p=2, allow_greedy_fallback=True)
    assert with_flag == pytest.approx(exact, rel=1e-12, abs=1e-12)
