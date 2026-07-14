# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Cheap classification pass over every committed W2 result file whose
#   values could have passed through the greedy fallback. For each file x dim:
#   (a) greedy convention gate — replicate the greedy fallback on the cached
#       diagrams and require bit-for-bit reproduction of the committed value
#       before classifying ARTIFACT-CONFIRMED (never classify on era alone when
#       diagrams exist); (b) diagonal-bound screen — an exact W2 cannot exceed
#       the project-everything-to-diagonal bound, so a committed value above it
#       is mathematically impossible as exact W2.
#   Greedy is O(n log n) per pair (no EMD), so this whole pass is cheap; the
#   expensive exact re-derivation is handled separately by 01_recompute_block.py.

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import audit_lib as al
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

BHPS_STAGE1 = al.PROJ_ROOT / "results/trajectory_tda_bhps/stage1"
PANEL = al.PROJ_ROOT / "results/panel_methodology"

# Gate tolerance: the greedy replica accumulates in the same sequential order as
# the original loop, so agreement should be at float64 round-off.
GATE_TOL = 1e-6

# (label, result_json, explicit_cache_or_None)
TARGETS: list[tuple[str, Path, str | None]] = [
    ("usoc_headline_frozen_2026-05-28", al.STAGE1_DIR / "usoc_headline_frozen_2026-05-28.json", None),
    ("usoc_headline_2026-05-24", al.STAGE1_DIR / "usoc_headline_2026-05-24.json", None),
    ("bhps_headline_frozen_2026-05-28", BHPS_STAGE1 / "bhps_headline_frozen_2026-05-28.json", None),
    ("bhps_headline_2026-05-24", al.STAGE1_DIR / "bhps_headline_2026-05-24.json", None),
    ("bhps_length_matched_truncate_2026-05-25", BHPS_STAGE1 / "bhps_length_matched_truncate_2026-05-25.json", None),
    (
        "bhps_length_matched_truncate_frozen_2026-05-29",
        BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_2026-05-29.json",
        None,
    ),
    (
        "bhps_length_matched_truncate_frozen_2026-05-30",
        BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_2026-05-30.json",
        None,
    ),
    (
        "bhps_length_matched_first13_frozen_2026-05-30",
        BHPS_STAGE1 / "bhps_length_matched_first13_frozen_2026-05-30.json",
        None,
    ),
    (
        "bhps_length_matched_truncate_frozen_probe-pinned-thresh_2026-05-31",
        BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_probe-pinned-thresh_2026-05-31.json",
        None,
    ),
    (
        "bhps_length_matched_truncate_frozen_probe-symmetric-dedup_2026-05-30",
        BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_probe-symmetric-dedup_2026-05-30.json",
        None,
    ),
]


def resolve_cache(payload: dict[str, Any], explicit: str | None) -> Path | None:
    """Read the cache path the run itself recorded (run_params.null_diagram_cache)."""
    if explicit:
        return al.CACHE_DIR / explicit
    rp = payload.get("run_params", {})
    raw = rp.get("null_diagram_cache") or rp.get("cache")
    if not raw:
        return None
    return al.CACHE_DIR / Path(str(raw).replace("\\", "/")).name


def iter_cells(payload: dict[str, Any]):
    """Yield (dim, cell_dict) for h0/h1 cells that carry W2 means."""
    res = payload.get("result", {})
    for dim in (0, 1):
        cell = res.get(f"h{dim}")
        if isinstance(cell, dict) and "mean_obs_null" in cell:
            yield dim, cell


def classify_file(label: str, path: Path, explicit: str | None) -> dict[str, Any]:
    rec: dict[str, Any] = {"label": label, "result_file": str(path), "cells": []}
    if not path.exists():
        rec["status"] = "MISSING_RESULT_FILE"
        return rec
    rec["result_sha256"] = al.sha256_file(path)
    payload = al.load_result_json(path)
    cache_path = resolve_cache(payload, explicit)
    rec["declared_cache"] = str(cache_path) if cache_path else None

    if cache_path is None or not cache_path.exists():
        rec["status"] = "NO_CACHE"
        for dim, cell in iter_cells(payload):
            rec["cells"].append(
                {
                    "dim": f"h{dim}",
                    "committed": {k: cell.get(k) for k in ("mean_obs_null", "mean_null_null", "d_perm", "w2_pvalue")},
                    "classification": "IMMUNE" if dim == 0 else "SUSPECT-UNVERIFIABLE",
                    "basis": "H0: births all 0 => greedy rank-matching is optimal 1-D transport (greedy==exact)"
                    if dim == 0
                    else "greedy era, H1, no cached diagrams to verify or re-derive",
                }
            )
        return rec

    rec["cache_sha256"] = al.sha256_file(cache_path)
    cache = al.load_cache(cache_path)
    n_perm = len(cache["h1_diagrams"])
    rec["B"] = n_perm
    pair_indices = al.reproduce_pair_indices(n_perm, max(al.DEFAULT_N_NULL_PAIRS, n_perm), 42)
    rec["status"] = "CACHED"

    for dim, cell in iter_cells(payload):
        obs = cache[f"obs_h{dim}_diagram"]
        nulls = cache[f"h{dim}_diagrams"]
        t0 = time.time()
        g_obs = al.obs_null_distances(obs, nulls, "greedy")
        g_nn = al.null_null_distances(nulls, pair_indices, "greedy")
        g = al.headline_stats_from_distances(g_obs, g_nn)

        bounds = np.array([al.diagonal_bound(obs, nd) for nd in nulls])
        committed_obs = float(cell["mean_obs_null"])
        gate_diff = abs(committed_obs - g["mean_obs_null"])
        gate_pass = gate_diff < GATE_TOL
        impossible = committed_obs > float(bounds.mean())

        if dim == 0:
            classification = "IMMUNE"
            basis = "H0: births all 0 => greedy rank-matching is optimal 1-D transport (greedy==exact)"
        elif gate_pass and impossible:
            classification = "ARTIFACT-CONFIRMED"
            basis = "greedy reproduces committed bit-for-bit AND committed exceeds the diagonal bound"
        elif gate_pass:
            classification = "ARTIFACT-CONFIRMED (gate only)"
            basis = "greedy reproduces committed bit-for-bit; diagonal screen did not flag impossibility"
        elif impossible:
            classification = "UNRESOLVED (screen-only)"
            basis = "committed exceeds the diagonal bound (impossible as exact) but greedy gate did not reproduce it"
        else:
            classification = "UNRESOLVED"
            basis = "greedy gate did not reproduce the committed value; convention ambiguous"

        rec["cells"].append(
            {
                "dim": f"h{dim}",
                "committed": {
                    k: cell.get(k) for k in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
                },
                "greedy_regate": {
                    k: g[k] for k in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
                },
                "gate_absdiff_mean_obs_null": gate_diff,
                "gate_reproduces_committed": bool(gate_pass),
                "diagonal_bound_mean": float(bounds.mean()),
                "diagonal_bound_max": float(bounds.max()),
                "committed_exceeds_diagonal_bound": bool(impossible),
                "classification": classification,
                "basis": basis,
                "wall_s": round(time.time() - t0, 1),
            }
        )
        print(
            f"  [{label}] h{dim}: {classification} gate_diff={gate_diff:.2e} "
            f"committed={committed_obs:.4f} bound={bounds.mean():.4f} ({time.time() - t0:.0f}s)",
            flush=True,
        )
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="classification_raw.json")
    ap.add_argument("--only", default=None, help="substring filter on label")
    args = ap.parse_args()

    records = []
    for label, path, explicit in TARGETS:
        if args.only and args.only not in label:
            continue
        print(f"\n=== {label} ===", flush=True)
        rec = classify_file(label, path, explicit)
        print(f"  status={rec.get('status')}", flush=True)
        records.append(rec)
        Path(args.out).write_text(json.dumps(al.convert_numpy(records), indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
