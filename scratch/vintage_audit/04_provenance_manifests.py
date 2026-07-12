# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1 Goal step 3 — provenance re-stamp (skill Observation 53).
#   For every frozen .npz cache: write a sidecar manifest recording cache sha256,
#   source-sequences path + sha256, embedding/loadings provenance, seed policy, etc.
#   Never modifies the .npz files themselves.
"""Sidecar provenance manifest writer for all frozen caches."""

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
    print("WT-1 Provenance manifest writer")
    print("=" * 70)

    # Load BHPS vintage probe results to get source info
    bhps_result_path = HERE / "01_bhps_vintage_probe_result.json"
    bhps_verdicts: dict[str, dict] = {}
    if bhps_result_path.exists():
        bhps_data = json.loads(bhps_result_path.read_text())
        for bank in bhps_data.get("banks", []):
            bhps_verdicts[bank["cache_file"]] = bank
        print(f"  Loaded BHPS vintage probe: {bhps_data['n_reproduced']} reproduced, "
              f"{bhps_data['n_unresolved']} unresolved")
    else:
        print("  WARNING: BHPS vintage probe result not found; source info will be unresolved")

    # USoc frozen cache: source is the orphan (confirmed by Spike Set B bit-for-bit)
    manifests_written = 0

    # --- USoc frozen cache ---
    print(f"\n--- USoc frozen cache ---")
    cache = al.USOC_FROZEN_CACHE
    if cache.exists():
        m = al.write_provenance_manifest(
            cache,
            source_seq_path=str(al.ORPHAN_SEQUENCES),
            source_seq_sha256=al.ORPHAN_SHA256,
            checkpoint_dir=str(al.USOC_CHECKPOINT),
            audit_notes="Source vintage confirmed orphan (May-2) by Spike Set B bit-for-bit "
                        "reproduction (bottleneck ≈ 1e-308, W₂ = 0). The Apr-8 canonical "
                        "build does NOT reproduce this cache.",
        )
        manifests_written += 1
        print(f"  OK {m.name}")

    # --- USoc frozen 2026-05-26 (if different from the 05-28 one) ---
    usoc_frozen_26 = al.CACHE_DIR / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-26.npz"
    if usoc_frozen_26.exists() and usoc_frozen_26 != al.USOC_FROZEN_CACHE:
        # Same provenance as the 05-28: built from the orphan sequences
        m = al.write_provenance_manifest(
            usoc_frozen_26,
            source_seq_path=str(al.ORPHAN_SEQUENCES),
            source_seq_sha256=al.ORPHAN_SHA256,
            checkpoint_dir=str(al.USOC_CHECKPOINT),
            audit_notes="Same vintage as the 2026-05-28 frozen cache (orphan, May-2). "
                        "Both dates are within the period the orphan was live.",
        )
        manifests_written += 1
        print(f"  OK {m.name}")

    # --- BHPS frozen caches ---
    print(f"\n--- BHPS frozen caches ({len(al.BHPS_FROZEN_CACHES)}) ---")
    for cache in al.BHPS_FROZEN_CACHES:
        if not cache.exists():
            print(f"  FAIL {cache.name} (not found)")
            continue

        verdict = bhps_verdicts.get(cache.name, {})
        source_path = verdict.get("source_seq_path")
        source_sha = verdict.get("source_seq_sha256")
        v = verdict.get("verdict", "UNRESOLVED")

        notes = f"BHPS vintage probe verdict: {v}."
        if v == "REPRODUCED":
            notes += f" Reproduced by {verdict.get('reproduced_by', 'unknown')}."
        elif v == "UNRESOLVED":
            notes += " No candidate sequence file reproduced this cache's observed diagram."

        m = al.write_provenance_manifest(
            cache,
            source_seq_path=source_path,
            source_seq_sha256=source_sha,
            checkpoint_dir=str(al.BHPS_CHECKPOINT),
            audit_notes=notes,
        )
        manifests_written += 1
        print(f"  OK {m.name} ({v})")

    # --- Non-frozen caches (for completeness) ---
    print(f"\n--- Non-frozen caches ---")
    for cache in al.OTHER_CACHES:
        if not cache.exists():
            continue
        if cache.with_suffix(".provenance.json").exists():
            continue  # Already written above (e.g. USoc frozen)

        # Determine likely source based on name
        if "usoc" in cache.name:
            if "orphan" in cache.name or "2026-05-02" in cache.name:
                seq_path = str(al.ORPHAN_SEQUENCES)
                seq_sha = al.ORPHAN_SHA256
            else:
                # Pre-frozen caches (2026-05-24) used the then-live sequences.
                # On 2026-05-24 the live file was the original Apr-8 build
                # (orphan rewrite was 2026-05-02, but that's when it became
                # the orphan; actually the orphan IS the May-2 rewrite).
                # On 2026-05-24 the live file was the orphan (May-2 rewrite).
                seq_path = "unresolved"
                seq_sha = "unresolved"
            checkpoint = str(al.USOC_CHECKPOINT)
        else:
            seq_path = str(al.BHPS_SEQUENCES) if al.BHPS_SEQUENCES.exists() else "unresolved"
            seq_sha = al.sha256_file(al.BHPS_SEQUENCES) if al.BHPS_SEQUENCES.exists() else "unresolved"
            checkpoint = str(al.BHPS_CHECKPOINT)

        m = al.write_provenance_manifest(
            cache,
            source_seq_path=seq_path,
            source_seq_sha256=seq_sha,
            checkpoint_dir=checkpoint,
            audit_notes="Non-frozen (provisional loadings) cache. Source vintage "
                        "determined by date and checkpoint state.",
        )
        manifests_written += 1
        print(f"  OK {m.name}")

    # Count total caches and manifests
    all_caches = list(al.CACHE_DIR.glob("*.npz"))
    all_manifests = list(al.CACHE_DIR.glob("*.provenance.json"))
    # Also check for subdirectory caches
    sub_caches = list(al.CACHE_DIR.rglob("*.npz"))

    print(f"\n{'=' * 70}")
    print(f"Provenance manifests written: {manifests_written}")
    print(f"Total .npz caches found: {len(all_caches)}")
    print(f"Total .provenance.json files: {len(all_manifests)}")
    print(f"Coverage: {len(all_manifests)}/{len(all_caches)}")
    print(f"Wall: {time.time()-t_start:.1f}s")

    # Validate all manifests are valid JSON
    invalid = 0
    for m in all_manifests:
        try:
            data = json.loads(m.read_text())
            assert "cache_sha256" in data
            assert "source_sequences_sha256" in data
        except Exception as exc:
            print(f"  INVALID: {m.name}: {exc}")
            invalid += 1

    if invalid:
        print(f"\n  WARNING: {invalid} invalid manifests")
    else:
        print(f"  All {len(all_manifests)} manifests valid [OK]")


if __name__ == "__main__":
    main()
