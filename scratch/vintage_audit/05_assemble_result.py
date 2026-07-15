# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1 — Assemble the final result JSON from all probe results.
#   Produces the committed result file with per-vintage obs diagram cardinalities,
#   bottleneck vs cache, full recomputed p-value/d_perm table, and per-bank BHPS
#   reproduction verdicts. Includes the orphan-vintage sanity cross-check.
"""Assemble headline_vintage_materiality result JSON."""

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


def main() -> None:
    t_start = time.time()
    print("=" * 70)
    print("WT-1 Result assembly + sanity cross-check")
    print("=" * 70)

    # Load all probe results
    bhps_path = HERE / "01_bhps_vintage_probe_result.json"
    usoc_obs_path = HERE / "02_usoc_obs_diagram_result.json"
    usoc_w2_path = HERE / "03_usoc_w2_headline_result.json"

    missing = []
    for p in [bhps_path, usoc_obs_path, usoc_w2_path]:
        if not p.exists():
            missing.append(p.name)
    if missing:
        print(f"ERROR: Missing prerequisite results: {', '.join(missing)}")
        print("Run steps 01-03 first.")
        sys.exit(1)

    bhps_data = json.loads(bhps_path.read_text())
    usoc_obs_data = json.loads(usoc_obs_path.read_text())
    usoc_w2_data = json.loads(usoc_w2_path.read_text())

    # --- Sanity cross-check ---
    # The orphan-vintage p-values re-derived from committed data must match
    # the committed headline JSON exactly.
    print("\n--- Sanity cross-check: orphan-vintage committed values ---")
    committed = json.loads(al.USOC_FROZEN_HEADLINE.read_text())
    sanity_ok = True
    sanity_notes = []

    # The committed headline stores d_perm, mean_obs_null, mean_null_null.
    # If the Apr-8 W₂ stage reused these correctly, the orphan values in
    # committed_orphan_stats should match the committed headline exactly.
    if "committed_orphan_stats" in usoc_w2_data:
        for dim in ["h0", "h1"]:
            committed_dim = committed["result"][dim]
            reused = usoc_w2_data["committed_orphan_stats"][dim]
            for key in ["d_perm", "mean_obs_null", "mean_null_null", "w2_pvalue"]:
                cv = committed_dim.get(key)
                rv = reused.get(key)
                if cv is not None and rv is not None:
                    if abs(cv - rv) > 1e-12:
                        sanity_ok = False
                        sanity_notes.append(
                            f"MISMATCH {dim}.{key}: committed={cv}, reused={rv}"
                        )
                    else:
                        sanity_notes.append(f"  OK {dim}.{key} matches")
    else:
        sanity_notes.append("WARNING: committed_orphan_stats not in W2 result (escalated?)")
        sanity_ok = usoc_w2_data.get("escalated", False)

    for note in sanity_notes:
        print(f"  {note}")
    print(f"  Sanity check: {'PASS' if sanity_ok else 'FAIL'}")

    # --- Input provenance ---
    input_provenance = {
        "canonical_sequences": {
            "path": str(al.CANONICAL_SEQUENCES),
            "sha256": al.CANONICAL_SHA256,
        },
        "orphan_sequences": {
            "path": str(al.ORPHAN_SEQUENCES),
            "sha256": al.ORPHAN_SHA256,
        },
        "bhps_sequences": {
            "path": str(al.BHPS_SEQUENCES),
            "sha256": al.sha256_file(al.BHPS_SEQUENCES) if al.BHPS_SEQUENCES.exists() else "missing",
        },
        "usoc_frozen_cache": {
            "path": str(al.USOC_FROZEN_CACHE),
            "sha256": al.sha256_file(al.USOC_FROZEN_CACHE),
        },
        "committed_headline": {
            "path": str(al.USOC_FROZEN_HEADLINE),
            "sha256": al.sha256_file(al.USOC_FROZEN_HEADLINE),
        },
        "pvalue_denominator_cleanup": {
            "path": str(al.STAGE1_DIR / "pvalue_denominator_cleanup_2026-05-28.json"),
            "formula": al.PVALUE_FORMULA,
        },
    }

    # --- Assemble ---
    result = {
        "schema": "headline_vintage_materiality/v1",
        "generated": date.today().isoformat(),
        "audit_task": "WT-1",
        "seed": al.REF_SEED,
        "input_provenance": input_provenance,
        "usoc_obs_diagram_reconstruction": usoc_obs_data,
        "usoc_apr8_w2_headline": usoc_w2_data,
        "bhps_bank_vintage_probe": bhps_data,
        "sanity_crosscheck": {
            "orphan_vs_committed_match": sanity_ok,
            "notes": sanity_notes,
        },
    }

    # Write to the committed results path
    out_path = al.STAGE1_DIR / "headline_vintage_materiality_2026-07-12.json"
    out_path.write_text(json.dumps(al.convert_numpy(result), indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    # Also write to scratch for reference
    scratch_copy = HERE / "05_headline_vintage_materiality_result.json"
    scratch_copy.write_text(json.dumps(al.convert_numpy(result), indent=2), encoding="utf-8")
    print(f"Wrote {scratch_copy}")

    # Summary
    print(f"\n{'=' * 70}")
    print("RESULT SUMMARY")
    print(f"{'=' * 70}")

    if "apr8" in usoc_obs_data:
        apr8 = usoc_obs_data["apr8"]
        print(f"\nUSoc obs diagram vintage:")
        print(f"  Orphan reproduces cache: {usoc_obs_data['orphan']['reproduced']}")
        print(f"  Apr-8 reproduces cache:  {apr8['reproduced']}")
        print(f"  Apr-8 obs cardinality: H0={apr8['recon_h0_card']}, H1={apr8['recon_h1_card']}")
        print(f"  Cache obs cardinality: H0={apr8['cache_h0_card']}, H1={apr8['cache_h1_card']}")
        print(f"  Bottleneck H0={apr8['bottleneck_h0']:.3e}, H1={apr8['bottleneck_h1']:.3e}")

    if "comparison" in usoc_w2_data:
        print(f"\nUSoc headline comparison (orphan vs Apr-8):")
        for dim in ["h0", "h1"]:
            c = usoc_w2_data["comparison"][dim]
            print(f"  {dim.upper()}: d_perm orphan={c['d_perm_orphan']:.2f}, "
                  f"apr8={c['d_perm_apr8']:.2f} (delta={c['d_perm_delta']:+.2f}, "
                  f"{c['d_perm_pct_change']:+.1f}%)")
            print(f"       p-value orphan={c['p_value_orphan']:.6f}, "
                  f"apr8={c['p_value_apr8']:.6f} "
                  f"{'WARNING THRESHOLD CROSSED' if c['decision_threshold_crossed'] else 'same decision'}")

    print(f"\nBHPS bank vintage probe:")
    print(f"  Reproduced: {bhps_data['n_reproduced']}/{bhps_data['n_banks_checked']}")
    print(f"  Unresolved: {bhps_data['n_unresolved']}/{bhps_data['n_banks_checked']}")
    for bank in bhps_data["banks"]:
        print(f"  {bank['cache_file']}: {bank['verdict']}")

    print(f"\nSanity cross-check: {'PASS' if sanity_ok else 'FAIL'}")
    print(f"Total wall: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
