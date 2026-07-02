# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Persistent-subprocess bridge to giotto-tda (Python 3.13 has no
#   giotto-tda wheel yet) as an alternative Rips-PH backend for permutation
#   batteries, motivated by ripser+loky's memory-bandwidth contention under
#   concurrency (measured 2026-07-01: ~6.4x per-task latency at n_jobs=12
#   vs solo, vs giotto-tda's ~1.3x at n_jobs=8 — see the T1.28 Task Log
#   pause note for the full verification record, including the sustained-
#   load sweep that found n_jobs=8 as the practical sweet spot on this
#   machine's 12 physical cores).
"""Client-side pool for the persistent giotto-tda Rips-PH worker.

``compute_rips_ph`` (poverty_tda.topology.multidim_ph) has no Python 3.13
wheel path for giotto-tda, so this bridges to it via subprocesses running
under an isolated Python 3.12 venv (``.venv-giotto312``, created by
``uv venv --python 3.12 .venv-giotto312 && uv pip install --python
.venv-giotto312/Scripts/python.exe giotto-tda``). Workers are persistent
(imported once, reused across many calls) to amortise the import cost;
``loky``/``joblib.Parallel`` cannot do this itself since a worker pool is
always pinned to its parent's interpreter.

Numerical equivalence to ripser was verified on real USoc and BHPS
production data, 2026-07-01: finite persistence pairs match bit-for-bit
(atol=1e-9) in both H0 and H1. See ``giotto_worker.py`` for the one (benign)
convention difference this bridge normalises.
"""

from __future__ import annotations

import pickle
import struct
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from poverty_tda.topology.multidim_ph import PHResult, _resolve_rips_threshold

_MODULE_DIR = Path(__file__).resolve().parent
_WORKER_SCRIPT = _MODULE_DIR / "giotto_worker.py"


def _find_giotto_python(worktree_root: Path) -> Path:
    """Locate the isolated giotto-tda venv's interpreter for this worktree.

    Raises:
        FileNotFoundError: If ``.venv-giotto312`` hasn't been created yet —
            see the module docstring for the setup command.
    """
    venv_dir = worktree_root / ".venv-giotto312"
    candidate = venv_dir / "Scripts" / "python.exe" if sys.platform == "win32" else venv_dir / "bin" / "python"
    if not candidate.exists():
        raise FileNotFoundError(
            f"giotto-tda venv not found at {candidate}. Create it with:\n"
            f"  uv venv --python 3.12 .venv-giotto312\n"
            f"  uv pip install --python {candidate} giotto-tda"
        )
    return candidate


class GiottoWorker:
    """One persistent giotto-tda subprocess. Not thread-safe on its own —
    ``GiottoPool`` serialises access via a per-worker lock."""

    def __init__(self, giotto_python: Path) -> None:
        self.proc = subprocess.Popen(
            [str(giotto_python), str(_WORKER_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.lock = threading.Lock()

    def compute(self, landmarks: NDArray[np.float64], threshold: float, max_dim: int) -> dict[str, NDArray[np.float64]]:
        req = pickle.dumps({"landmarks": landmarks, "threshold": threshold, "max_dim": max_dim})
        with self.lock:
            self.proc.stdin.write(struct.pack("<I", len(req)))
            self.proc.stdin.write(req)
            self.proc.stdin.flush()
            header = self.proc.stdout.read(4)
            if len(header) < 4:
                stderr = self.proc.stderr.read().decode(errors="replace")
                raise RuntimeError(f"giotto worker died; stderr:\n{stderr}")
            (n,) = struct.unpack("<I", header)
            buf = b""
            while len(buf) < n:
                chunk = self.proc.stdout.read(n - len(buf))
                if not chunk:
                    raise EOFError("giotto worker stdout closed mid-frame")
                buf += chunk
        resp = pickle.loads(buf)
        if resp["status"] != "ok":
            raise RuntimeError(f"giotto worker compute failed: {resp['error']}")
        return resp["result"]

    def close(self) -> None:
        """Escalating shutdown: closing stdin alone makes the worker's read
        loop see EOF and exit on its own in the common case; terminate()
        and finally kill() are fallbacks if it doesn't."""
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            pass
        self.proc.kill()
        self.proc.wait(timeout=10)


class GiottoPool:
    """Persistent pool of giotto-tda worker subprocesses.

    Sweet spot on this project's dev machine (12 physical cores) was
    empirically n_jobs=8 (2026-07-01 sustained-load sweep) — meaningfully
    better than both 4 and 12. Re-verify per-machine before assuming this
    transfers; it did not follow a smooth function of worker count.
    """

    def __init__(self, n_workers: int, worktree_root: Path) -> None:
        giotto_python = _find_giotto_python(worktree_root)
        self.workers = [GiottoWorker(giotto_python) for _ in range(n_workers)]
        self._executor = ThreadPoolExecutor(max_workers=n_workers)
        self._next = 0
        self._round_robin_lock = threading.Lock()

    def _pick_worker(self) -> GiottoWorker:
        with self._round_robin_lock:
            w = self.workers[self._next % len(self.workers)]
            self._next += 1
        return w

    def compute(
        self, landmarks: NDArray[np.float64], threshold: float, max_dim: int = 1
    ) -> dict[str, NDArray[np.float64]]:
        return self._pick_worker().compute(landmarks, threshold, max_dim)

    def close(self) -> None:
        self._executor.shutdown(wait=True)
        for w in self.workers:
            w.close()


def compute_rips_ph_giotto(
    X: NDArray[np.float64],
    pool: GiottoPool,
    max_dim: int = 1,
    thresh: float | None = None,
) -> PHResult:
    """Drop-in giotto-tda equivalent of ``compute_rips_ph`` for use with a
    live ``GiottoPool``. Resolves the auto-threshold identically to the
    ripser path (``_resolve_rips_threshold``, same seed=42 500-point
    subsample) so behaviour is deterministic-equivalent when ``thresh`` is
    left unset.

    Args:
        X: (n_points, n_dims) landmark point cloud.
        pool: A live ``GiottoPool`` to dispatch the computation to.
        max_dim: Maximum homology dimension.
        thresh: Explicit threshold; auto-resolved (matching ripser) if None.

    Returns:
        PHResult with ``dgms`` populated for dimensions 0..max_dim.
    """
    threshold, threshold_rule = _resolve_rips_threshold(X, thresh)
    result = pool.compute(X, threshold, max_dim)
    dgms = {dim: result[f"h{dim}"] for dim in range(max_dim + 1)}
    return PHResult(
        dgms=dgms,
        n_points=X.shape[0],
        n_dimensions=X.shape[1],
        ph_method="giotto-tda",
        do_cocycles=False,
        threshold_rule=threshold_rule,
        threshold_value=threshold,
    )
