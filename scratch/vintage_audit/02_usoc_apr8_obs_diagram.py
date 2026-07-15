# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1 Goal step 1 — USoc materiality check, observed side.
#   Reconstruct the observed diagram from the Apr-8 canonical sequences and the
#   orphan sequences, compare each against the frozen cache obs diagram.
#   The orphan should reproduce (sanity/stop-condition check); the canonical should
#   NOT reproduce (confirming the vintage divergence). Saves the Apr-8 obs diagram
#   arrays for the W₂ stage.
"""USoc Apr-8 observed diagram reconstruction + vintage confirmation."""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _auditlib as al  # noqa: E402


def main() -> None:
    t_start = time.time()
    print("=" * 70)
    print("WT-1 USoc Apr-8 observed diagram reconstruction")
    print("=" * 70)

    # Verify inputs
    print("\n[input] Verifying sequence file hashes...")
    canonical_sha = al.verify_input(al.CANONICAL_SEQUENCES, al.CANONICAL_SHA256)
    print(f"  canonical: {canonical_sha} OK")
    orphan_sha = al.verify_input(al.ORPHAN_SEQUENCES, al.ORPHAN_SHA256)
    print(f"  orphan:    {orphan_sha} OK")

    # Load frozen cache obs diagram (the comparison target)
    print("\n[cache] Loading frozen USoc cache obs diagram...")
    cache = al.load_cache(al.USOC_FROZEN_CACHE)
    cache_h0 = al.finite_pairs(cache["obs_h0_diagram"])
    cache_h1 = al.finite_pairs(cache["obs_h1_diagram"])
    print(f"  cache obs finite: H0={cache_h0.shape[0]}, H1={cache_h1.shape[0]}")

    cache_sha = al.sha256_file(al.USOC_FROZEN_CACHE)
    print(f"  cache sha256: {cache_sha}")

    # --- Step A: Orphan reconstruction (sanity / stop-condition check) ---
    print("\n" + "-" * 50)
    print("[orphan] Reconstructing obs diagram from orphan sequences...")
    print("  (This SHOULD reproduce the cache — stop condition check)")
    t0 = time.time()
    orphan_recon = al.reconstruct_obs_diagram(
        al.ORPHAN_SEQUENCES, al.USOC_CHECKPOINT
    )
    orphan_comp = al.compare_diagrams(
        orphan_recon, cache["obs_h0_diagram"], cache["obs_h1_diagram"]
    )
    orphan_wall = round(time.time() - t0, 1)
    print(f"  orphan obs: H0={orphan_recon.h0_card}, H1={orphan_recon.h1_card} ({orphan_wall}s)")
    print(f"  bottleneck H0={orphan_comp['bottleneck_h0']:.3e}, H1={orphan_comp['bottleneck_h1']:.3e}")
    print(f"  cardinality match: H0={orphan_comp['cardinality_h0_match']}, H1={orphan_comp['cardinality_h1_match']}")
    print(f"  ORPHAN REPRODUCES: {orphan_comp['reproduced']}")

    if not orphan_comp["reproduced"]:
        print("\n*** STOP CONDITION: Orphan does NOT reproduce the cache. ***")
        print("    The reconstruction path itself has drifted. Escalate.")
        # Still write the result so the memo has evidence
        _write_result(
            orphan_recon, orphan_comp, orphan_wall,
            None, None, 0,
            cache_h0, cache_h1, cache_sha,
            round(time.time() - t_start, 1),
            stop_condition=True,
        )
        return

    # --- Step B: Apr-8 canonical reconstruction ---
    print("\n" + "-" * 50)
    print("[apr8] Reconstructing obs diagram from Apr-8 canonical sequences...")
    print("  (This should NOT reproduce the cache — confirming vintage divergence)")
    t0 = time.time()
    apr8_recon = al.reconstruct_obs_diagram(
        al.CANONICAL_SEQUENCES, al.USOC_CHECKPOINT
    )
    apr8_comp = al.compare_diagrams(
        apr8_recon, cache["obs_h0_diagram"], cache["obs_h1_diagram"]
    )
    apr8_wall = round(time.time() - t0, 1)
    print(f"  apr8 obs: H0={apr8_recon.h0_card}, H1={apr8_recon.h1_card} ({apr8_wall}s)")
    print(f"  bottleneck H0={apr8_comp['bottleneck_h0']:.3e}, H1={apr8_comp['bottleneck_h1']:.3e}")
    print(f"  cardinality match: H0={apr8_comp['cardinality_h0_match']}, H1={apr8_comp['cardinality_h1_match']}")
    print(f"  APR-8 REPRODUCES: {apr8_comp['reproduced']}")

    # Save Apr-8 obs diagram arrays for the W₂ stage
    np.savez_compressed(
        HERE / "apr8_obs_diagrams.npz",
        h0=apr8_recon.h0_finite,
        h1=apr8_recon.h1_finite,
    )
    print(f"\n  Saved Apr-8 obs diagrams to apr8_obs_diagrams.npz")
    print(f"    H0: {apr8_recon.h0_finite.shape}, H1: {apr8_recon.h1_finite.shape}")

    _write_result(
        orphan_recon, orphan_comp, orphan_wall,
        apr8_recon, apr8_comp, apr8_wall,
        cache_h0, cache_h1, cache_sha,
        round(time.time() - t_start, 1),
    )


def _write_result(
    orphan_recon, orphan_comp, orphan_wall,
    apr8_recon, apr8_comp, apr8_wall,
    cache_h0, cache_h1, cache_sha,
    total_wall,
    stop_condition=False,
):
    out = {
        "generated": date.today().isoformat(),
        "stage": "02_usoc_apr8_obs_diagram",
        "wall_s": total_wall,
        "stop_condition_triggered": stop_condition,
        "cache": {
            "path": str(al.USOC_FROZEN_CACHE),
            "sha256": cache_sha,
            "obs_h0_card": int(cache_h0.shape[0]),
            "obs_h1_card": int(cache_h1.shape[0]),
        },
        "orphan": {
            "seq_path": str(al.ORPHAN_SEQUENCES),
            "seq_sha256": orphan_recon.seq_sha256,
            "n_trajectories": orphan_recon.n_trajectories,
            "wall_s": orphan_wall,
            **al.convert_numpy(orphan_comp),
        },
    }
    if apr8_recon is not None:
        out["apr8"] = {
            "seq_path": str(al.CANONICAL_SEQUENCES),
            "seq_sha256": apr8_recon.seq_sha256,
            "n_trajectories": apr8_recon.n_trajectories,
            "wall_s": apr8_wall,
            **al.convert_numpy(apr8_comp),
        }

    out_path = HERE / "02_usoc_obs_diagram_result.json"
    out_path.write_text(json.dumps(al.convert_numpy(out), indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"Total wall: {total_wall}s")


if __name__ == "__main__":
    main()
