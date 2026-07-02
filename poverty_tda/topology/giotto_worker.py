# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Persistent giotto-tda Rips-PH worker, run under the isolated
#   Python 3.12 venv (.venv-giotto312) since giotto-tda has no Python 3.13
#   wheel yet. Invoked as a subprocess by GiottoPool (giotto_backend.py);
#   never imported directly by the main 3.13 environment.
"""Persistent giotto-tda Vietoris-Rips worker process.

Protocol: length-prefixed pickle frames over stdin/stdout. Each request is
``{"landmarks": ndarray, "threshold": float, "max_dim": int}``; each response
is ``{"status": "ok", "result": {"h0": ndarray, "h1": ndarray, ...}}`` or
``{"status": "error", "error": str}``. Essential (never-dying) classes are
remapped from giotto-tda's ``death == max_edge_length`` convention to
ripser's ``death == inf`` convention so callers can treat the output
identically regardless of backend. Loops until stdin closes.

Verified equivalent to ripser on finite persistence pairs (bit-for-bit,
atol=1e-9) on real USoc and BHPS production data, 2026-07-01 — see the T1.28
Task Log pause note for the verification record. The only observed
difference is that giotto-tda reports one fewer essential H0 class per
subgroup than ripser (both at birth=0) — irrelevant here since
``PHResult.h_features()`` (the only consumer) drops infinite/essential
classes before any statistic is computed.
"""

from __future__ import annotations

import pickle
import struct
import sys

import numpy as np
from gtda.homology import VietorisRipsPersistence
from numpy.typing import NDArray

_stdin = sys.stdin.buffer
_stdout = sys.stdout.buffer


def _read_frame() -> bytes | None:
    header = _stdin.read(4)
    if len(header) < 4:
        return None
    (n,) = struct.unpack("<I", header)
    buf = b""
    while len(buf) < n:
        chunk = _stdin.read(n - len(buf))
        if not chunk:
            raise EOFError("stdin closed mid-frame")
        buf += chunk
    return buf


def _write_frame(payload: bytes) -> None:
    _stdout.write(struct.pack("<I", len(payload)))
    _stdout.write(payload)
    _stdout.flush()


def compute(landmarks: NDArray[np.float64], threshold: float, max_dim: int) -> dict[str, NDArray[np.float64]]:
    """Compute Vietoris-Rips PH via giotto-tda, remapped to ripser's
    essential-class convention.

    Args:
        landmarks: (n_points, n_dims) landmark point cloud.
        threshold: Max edge length (matches ripser's ``thresh``).
        max_dim: Maximum homology dimension.

    Returns:
        Dict mapping ``h{dim}`` to an (n_features, 2) birth-death array,
        with essential classes at ``death == threshold`` remapped to
        ``death == inf``.
    """
    vr = VietorisRipsPersistence(
        metric="euclidean",
        homology_dimensions=tuple(range(max_dim + 1)),
        max_edge_length=threshold,
        n_jobs=1,
    )
    diagrams = vr.fit_transform(landmarks[None, :, :])
    dgm = diagrams[0]
    out: dict[str, NDArray[np.float64]] = {}
    for dim in range(max_dim + 1):
        d = dgm[dgm[:, 2] == dim][:, :2].astype(np.float64)
        at_thresh = np.isclose(d[:, 1], threshold, atol=1e-9)
        d[at_thresh, 1] = np.inf
        out[f"h{dim}"] = d
    return out


def main() -> None:
    while True:
        frame = _read_frame()
        if frame is None:
            break
        req = pickle.loads(frame)
        try:
            result = compute(req["landmarks"], float(req["threshold"]), int(req["max_dim"]))
            resp = {"status": "ok", "result": result}
        except Exception as exc:  # noqa: BLE001 - reported to parent, not crashed on
            resp = {"status": "error", "error": repr(exc)}
        _write_frame(pickle.dumps(resp))


if __name__ == "__main__":
    main()
