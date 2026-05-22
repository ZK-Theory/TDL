# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Smoke-test numerical equivalence between the legacy monolithic
#   trajectory_tda/scripts/run_stage1_battery.py and the new phase-split
#   trajectory_tda/scripts/stage1/run_usoc_headline.py, at L=200, B=10, seed=42.
#   Locks the refactor so it cannot diverge from the legacy reference.
"""Smoke test — legacy vs phase-split numerical equivalence at L=200, B=10.

Asserts that W2 p-value, t_ratio, d_perm, and landscape L2 p-value match to
``1e-10`` between:

    * trajectory_tda/scripts/run_stage1_battery.py   (legacy monolith, USoc only)
    * trajectory_tda/scripts/stage1/run_usoc_headline.py  (phase-split)

Both scripts read the USoc checkpoint at the ``PROJ_ROOT`` results path
(``01_trajectories_sequences.json`` is gitignored — see CLAUDE.md
"Two-path output rule").

The test is marked ``slow`` and ``integration`` — opt in via
``-m "slow and integration"`` or ``--run-slow``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest


PROJ_ROOT = Path("C:/Users/steph/TDL")
USOC_CHECKPOINT_DIR = PROJ_ROOT / "results/trajectory_tda_integration"

TOL = 1e-10
L = 200
B = 10
SEED = 42


pytestmark = [pytest.mark.slow, pytest.mark.integration]


def _have_usoc_data() -> bool:
    return (USOC_CHECKPOINT_DIR / "embeddings.npy").exists() and (
        USOC_CHECKPOINT_DIR / "01_trajectories_sequences.json"
    ).exists()


def _run_legacy(cwd: Path, output_path: Path) -> dict:
    """Invoke the legacy monolith on USoc only, headline only."""
    cmd = [
        sys.executable,
        "-m",
        "trajectory_tda.scripts.run_stage1_battery",
        "--usoc-dir",
        str(USOC_CHECKPOINT_DIR),
        "--landmarks",
        str(L),
        "--n-perms",
        str(B),
        "--seed",
        str(SEED),
        "--skip-bhps",
        "--skip-sensitivity",
        "--output",
        str(output_path),
        "--n-jobs",
        "1",
    ]
    subprocess.run(cmd, cwd=str(cwd), check=True)
    with open(output_path) as f:
        return json.load(f)


def _run_phase_usoc(cwd: Path, today: str) -> dict:
    """Invoke the phase-split USoc headline script in --smoke mode."""
    cmd = [
        sys.executable,
        "-m",
        "trajectory_tda.scripts.stage1.run_usoc_headline",
        "--usoc-dir",
        str(USOC_CHECKPOINT_DIR),
        "--L",
        str(L),
        "--B",
        str(B),
        "--seed",
        str(SEED),
        "--n-jobs",
        "1",
        "--smoke",
    ]
    subprocess.run(cmd, cwd=str(cwd), check=True)
    out = cwd / f"results/trajectory_tda_integration/stage1/usoc_headline_smoke_{today}.json"
    with open(out) as f:
        return json.load(f)


def _compare_cells(legacy_cell: dict, phase_cell: dict, dim_key: str) -> None:
    """Compare the four critical numerical fields at 1e-10."""
    fields = ("w2_pvalue", "t_ratio", "d_perm", "landscape_l2_pvalue")
    for field in fields:
        lv = legacy_cell.get(field)
        pv = phase_cell.get(field)
        assert lv is not None, f"legacy[{dim_key}].{field} missing"
        assert pv is not None, f"phase[{dim_key}].{field} missing"
        # NaN check: if either is NaN, both must be NaN
        if lv != lv or pv != pv:
            assert lv != lv and pv != pv, f"{dim_key}.{field}: legacy={lv}, phase={pv} (NaN mismatch)"
            continue
        assert abs(lv - pv) <= TOL, f"{dim_key}.{field} mismatch: legacy={lv}, phase={pv}, |diff|={abs(lv - pv)}"


@pytest.fixture(autouse=True)
def _clean_partial_dir(tmp_path_factory):
    """Each test gets a clean .partial/ slate to avoid stale files."""
    cwd = Path.cwd()
    partial = cwd / "results/trajectory_tda_integration/stage1/.partial"
    if partial.exists():
        for p in partial.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
    yield


@pytest.mark.skipif(
    not _have_usoc_data(),
    reason="USoc checkpoint missing at PROJ_ROOT; regenerate via "
    "trajectory_tda/scripts/bhps_pipeline.py before running this smoke test.",
)
def test_phase_split_matches_legacy_usoc_headline_at_small_B(tmp_path: Path) -> None:
    """USoc headline cell from phase-split equals legacy cell at L=200, B=10, seed=42."""
    cwd = Path(os.environ.get("PYTEST_CWD", Path.cwd()))
    today = date.today().isoformat()

    legacy_output = tmp_path / f"matched_w2_battery_legacy_{today}.json"
    legacy_payload = _run_legacy(cwd, legacy_output)
    phase_payload = _run_phase_usoc(cwd, today)

    legacy_usoc = legacy_payload["usoc"]
    phase_usoc = phase_payload["result"]

    assert set(legacy_usoc.keys()) >= {"h0", "h1"}, f"unexpected legacy keys: {legacy_usoc.keys()}"
    assert set(phase_usoc.keys()) >= {"h0", "h1"}, f"unexpected phase keys: {phase_usoc.keys()}"

    _compare_cells(legacy_usoc["h0"], phase_usoc["h0"], "h0")
    _compare_cells(legacy_usoc["h1"], phase_usoc["h1"], "h1")


@pytest.mark.skipif(
    not _have_usoc_data(),
    reason="USoc checkpoint missing at PROJ_ROOT.",
)
def test_phase_split_writes_cache_with_expected_schema(tmp_path: Path) -> None:
    """Verify the null-diagram cache .npz has the documented schema."""
    import numpy as np

    cwd = Path(os.environ.get("PYTEST_CWD", Path.cwd()))
    today = date.today().isoformat()
    _run_phase_usoc(cwd, today)

    cache_dir = PROJ_ROOT / "results/trajectory_tda_integration/stage1/cache"
    expected = cache_dir / f"null_diagrams_usoc_B{B}_L{L}_seed{SEED}_smoke_{today}.npz"
    assert expected.exists(), f"Cache not written at expected path: {expected}"

    with np.load(expected, allow_pickle=True) as data:
        for key in ("h0_diagrams", "h1_diagrams", "obs_h0_diagram", "obs_h1_diagram", "metadata"):
            assert key in data, f"cache missing key: {key}"
        h0 = data["h0_diagrams"]
        h1 = data["h1_diagrams"]
        assert h0.shape == (B,), f"h0_diagrams shape={h0.shape}, expected ({B},)"
        assert h1.shape == (B,), f"h1_diagrams shape={h1.shape}, expected ({B},)"
        # Each entry should be a (n_i, 2) array
        for arr in h0:
            arr2 = np.array(arr, dtype=np.float64).reshape(-1, 2)
            assert arr2.ndim == 2 and arr2.shape[1] == 2

    # Clean up the smoke cache to avoid polluting PROJ_ROOT
    expected.unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_partials_session(request):
    """Remove the .partial/ tree at session end (test artefacts only)."""
    yield
    cwd = Path.cwd()
    partial = cwd / "results/trajectory_tda_integration/stage1/.partial"
    if partial.exists():
        shutil.rmtree(partial, ignore_errors=True)
