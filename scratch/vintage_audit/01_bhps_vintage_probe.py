# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1 Goal step 2 — BHPS bank vintage check. For each BHPS frozen cache,
#   determine which on-disk sequence build reproduces the cached observed diagram
#   bit-for-bit (bottleneck ≈ 0 per dim, cardinality match). Uses the same probe
#   design as Spike Set B's 00_recon_measure / 00b_vintage_probe.
"""BHPS bank vintage probe — run first (cheap, ≤5 min per bank)."""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _auditlib as al  # noqa: E402


def probe_bank(
    cache_path: Path,
    candidate_seq_paths: list[tuple[str, Path]],
    checkpoint_dir: Path,
) -> dict:
    """Probe a single BHPS cache against candidate sequence files.

    Returns a verdict dict with reproduced/not-reproduced/unresolved per bank.
    """
    result: dict = {
        "cache_file": cache_path.name,
        "cache_sha256": al.sha256_file(cache_path),
        "cache_exists": cache_path.exists(),
    }

    if not cache_path.exists():
        result["verdict"] = "MISSING_CACHE"
        return result

    # Load cached obs diagram
    cache = al.load_cache(cache_path)
    cache_h0 = al.finite_pairs(cache["obs_h0_diagram"])
    cache_h1 = al.finite_pairs(cache["obs_h1_diagram"])
    result["cache_obs_h0_card"] = int(cache_h0.shape[0])
    result["cache_obs_h1_card"] = int(cache_h1.shape[0])
    result["candidates"] = []

    # Determine strategy based on cache filename
    strategy = None
    dedup_length_matched = False
    probe_pinned_thresh = "pinned-thresh" in cache_path.name

    if "length_matched_truncate" in cache_path.name:
        strategy = "truncate"
        dedup_length_matched = True
    elif "length_matched_first13" in cache_path.name:
        strategy = "first13"
        dedup_length_matched = True
    elif "nonoverlap" in cache_path.name:
        strategy = "non_overlap"
        dedup_length_matched = False

    for label, seq_path in candidate_seq_paths:
        if not seq_path.exists():
            result["candidates"].append({
                "label": label,
                "seq_path": str(seq_path),
                "exists": False,
            })
            continue

        print(f"  [{cache_path.name}] testing {label} (strategy={strategy}, dedup={dedup_length_matched}, pinned={probe_pinned_thresh}): {seq_path.name}...")
        t0 = time.time()
        try:
            recon = al.reconstruct_obs_diagram(
                seq_path, checkpoint_dir,
                strategy=strategy,
                dedup_length_matched=dedup_length_matched,
                probe_pinned_thresh=probe_pinned_thresh
            )
            comp = al.compare_diagrams(recon, cache["obs_h0_diagram"], cache["obs_h1_diagram"])
            wall = round(time.time() - t0, 1)
            result["candidates"].append({
                "label": label,
                "seq_path": str(seq_path),
                "seq_sha256": recon.seq_sha256,
                "exists": True,
                "wall_s": wall,
                **comp,
            })
            if comp["reproduced"]:
                print(f"    -> REPRODUCED (bottleneck H0={comp['bottleneck_h0']:.3e}, "
                      f"H1={comp['bottleneck_h1']:.3e}) in {wall}s")
        except Exception as exc:
            wall = round(time.time() - t0, 1)
            result["candidates"].append({
                "label": label,
                "seq_path": str(seq_path),
                "exists": True,
                "error": f"{type(exc).__name__}: {exc}",
                "wall_s": wall,
            })
            print(f"    -> ERROR: {exc}")

    # Determine verdict
    reproduced_by = [
        c for c in result["candidates"]
        if c.get("reproduced", False)
    ]
    if reproduced_by:
        result["verdict"] = "REPRODUCED"
        result["reproduced_by"] = reproduced_by[0]["label"]
        result["source_seq_path"] = reproduced_by[0]["seq_path"]
        result["source_seq_sha256"] = reproduced_by[0]["seq_sha256"]
    else:
        result["verdict"] = "UNRESOLVED"
        result["source_seq_path"] = None
        result["source_seq_sha256"] = None

    return result


def main() -> None:
    t_start = time.time()
    print("=" * 70)
    print("WT-1 BHPS bank vintage probe")
    print("=" * 70)

    # Build candidate list: canonical BHPS first, then USoc canonical, then orphan,
    # then any orphan/bak variants
    bhps_candidates: list[tuple[str, Path]] = [
        ("bhps_canonical", al.BHPS_SEQUENCES),
    ]

    # Check for orphan/bak variants in both checkpoint dirs
    for check_dir in [al.BHPS_CHECKPOINT, al.USOC_CHECKPOINT]:
        for p in sorted(check_dir.glob("*orphan*")):
            if "sequences" in p.name:
                bhps_candidates.append((f"orphan_{p.name}", p))
        for p in sorted(check_dir.glob("*.bak")):
            if "sequences" in p.name:
                bhps_candidates.append((f"bak_{p.name}", p))

    print(f"\nCandidate sequence files ({len(bhps_candidates)}):")
    for label, p in bhps_candidates:
        print(f"  {label}: {p.name} exists={p.exists()}")

    results = []
    for cache_path in al.BHPS_FROZEN_CACHES:
        print(f"\n--- Probing: {cache_path.name} ---")
        r = probe_bank(cache_path, bhps_candidates, al.BHPS_CHECKPOINT)
        results.append(r)
        print(f"  Verdict: {r['verdict']}")

    # Summary
    print("\n" + "=" * 70)
    print("BHPS bank vintage probe summary")
    print("=" * 70)
    n_reproduced = sum(1 for r in results if r["verdict"] == "REPRODUCED")
    n_unresolved = sum(1 for r in results if r["verdict"] == "UNRESOLVED")
    n_missing = sum(1 for r in results if r["verdict"] == "MISSING_CACHE")
    print(f"  REPRODUCED: {n_reproduced}/{len(results)}")
    print(f"  UNRESOLVED: {n_unresolved}/{len(results)}")
    print(f"  MISSING:    {n_missing}/{len(results)}")
    for r in results:
        print(f"  {r['cache_file']}: {r['verdict']}"
              + (f" (by {r.get('reproduced_by', '?')})" if r["verdict"] == "REPRODUCED" else ""))

    out = {
        "generated": date.today().isoformat(),
        "stage": "01_bhps_vintage_probe",
        "wall_s": round(time.time() - t_start, 1),
        "n_banks_checked": len(results),
        "n_reproduced": n_reproduced,
        "n_unresolved": n_unresolved,
        "banks": al.convert_numpy(results),
    }
    out_path = HERE / "01_bhps_vintage_probe_result.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"Total wall: {out['wall_s']}s")


if __name__ == "__main__":
    main()
