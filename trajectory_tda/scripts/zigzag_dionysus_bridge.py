"""Dionysus zigzag persistence bridge — runs inside WSL.

Called by :func:`trajectory_tda.topology.zigzag.run_gudhi_zigzag` via::

    wsl --exec /tmp/miniforge3/bin/python zigzag_dionysus_bridge.py \\
        /mnt/c/.../filtration.npz \\
        /mnt/c/.../barcode.json

Input ``filtration.npz`` (numpy .npz archive):
    simplex_vertices : int32 array of shape (N_simplices, max_dim + 2)
        Row i encodes simplex i as a list of vertex indices, padded with
        -1.  A vertex is [v, -1, -1], an edge [u, v, -1], etc.
    times : float64 array of shape (N_simplices, 2)
        Row i is ``[z_enter, z_exit]`` in the zigzag level parameterisation:
        - ``z_enter`` — first level at which the simplex is present.
        - ``z_exit``  — first level at which it is *absent* (exclusive).
        Dionysus interprets this as: appears at ``z_enter``, disappears at
        ``z_exit``.

Output ``barcode.json``:
    ``{"0": [[birth, death], ...], "1": [[birth, death], ...]}``

    Bars are in zigzag level coordinates.  Infinite deaths are encoded as
    ``1e308`` (JSON-safe substitute for ``Infinity``).

Dependencies (installed in WSL miniforge3 env):
    dionysus >= 2.1.8, numpy >= 1.20, scipy (unused, kept for compatibility)
"""

from __future__ import annotations

import json
import sys

import dionysus as d
import numpy as np

_INF_PROXY = 1e308  # JSON-safe stand-in for float('inf')


def _load_filtration(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load simplex_vertices and times arrays from .npz file."""
    data = np.load(path, allow_pickle=False)
    return data["simplex_vertices"], data["times"]


def _build_filtration(
    simplex_vertices: np.ndarray,
    times: np.ndarray,
) -> tuple[d.Filtration, list[list[float]]]:
    """Construct a sorted dionysus Filtration and parallel times list.

    Filtration weight for each simplex is set to its entry time
    (``times[i, 0]``). Sorting by weight ensures the boundary-before-fill
    invariant holds when the entry times are non-decreasing by dimension:
    every vertex enters no later than any edge it spans, and every edge
    enters no later than any triangle it bounds.

    Returns:
        flt     : dionysus.Filtration (sorted by weight)
        tlist   : list[list[float]] parallel with ``flt`` after sorting,
                  each element is ``[z_enter, z_exit]``.
    """
    # Build a lookup: canonical simplex tuple → (z_enter, z_exit)
    times_dict: dict[tuple[int, ...], tuple[float, float]] = {}
    for i in range(len(simplex_vertices)):
        verts = tuple(int(v) for v in simplex_vertices[i] if v >= 0)
        times_dict[verts] = (float(times[i, 0]), float(times[i, 1]))

    flt = d.Filtration()
    for i in range(len(simplex_vertices)):
        verts = [int(v) for v in simplex_vertices[i] if v >= 0]
        weight = float(times[i, 0])
        flt.append(d.Simplex(verts, weight))

    flt.sort()  # sort by weight; stable for equal weights (lower dim first)

    tlist: list[list[float]] = []
    for s in flt:
        key = tuple(sorted(s))
        z_enter, z_exit = times_dict[key]
        tlist.append([z_enter, z_exit])

    return flt, tlist


def _extract_barcodes(dgms: list) -> dict[str, list[list[float]]]:
    """Convert dionysus diagrams to a JSON-serialisable dict.

    Infinite deaths are replaced with ``_INF_PROXY``.
    """
    result: dict[str, list[list[float]]] = {}
    for dim, dgm in enumerate(dgms):
        bars: list[list[float]] = []
        for pt in dgm:
            birth = float(pt.birth)
            death = float(pt.death) if not (pt.death != pt.death) else _INF_PROXY
            # Replace actual infinity (isinf) and NaN
            if death != death or abs(death) > 1e200:
                death = _INF_PROXY
            bars.append([birth, death])
        result[str(dim)] = bars
    return result


def main() -> None:
    """Entry point: read filtration, run zigzag, write barcode."""
    if len(sys.argv) != 3:
        print(
            f"Usage: python {sys.argv[0]} <filtration.npz> <barcode.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    print(f"[bridge] Loading filtration: {input_path}", file=sys.stderr)
    simplex_vertices, times = _load_filtration(input_path)
    print(
        f"[bridge] {len(simplex_vertices)} simplices loaded",
        file=sys.stderr,
    )

    print("[bridge] Building dionysus Filtration...", file=sys.stderr)
    flt, tlist = _build_filtration(simplex_vertices, times)
    print(f"[bridge] Filtration size: {len(flt)}", file=sys.stderr)

    print("[bridge] Running zigzag_homology_persistence...", file=sys.stderr)
    _, dgms, _ = d.zigzag_homology_persistence(flt, tlist, progress=False)
    print(f"[bridge] {len(dgms)} diagram dimensions produced", file=sys.stderr)

    barcodes = _extract_barcodes(dgms)
    for dim_str, bars in barcodes.items():
        print(
            f"[bridge] H{dim_str}: {len(bars)} bars",
            file=sys.stderr,
        )

    with open(output_path, "w") as f:
        json.dump(barcodes, f)
    print(f"[bridge] Barcode written: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
