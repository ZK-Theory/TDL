# SUPERSEDED pre-frozen results (BHPS stage1) — DO NOT CITE

Pointer to the authoritative manifest:
`../../trajectory_tda_integration/stage1/SUPERSEDED.md`.

Bug-era (per-call PCA re-fit) and pre-dedup files in this directory that must
**not** be cited in P01-A / P01-B:

| ❌ Do NOT cite | ✅ Canonical (cite this) |
|---|---|
| `bhps_length_matched_truncate_2026-05-25.json` (pre-frozen) | `bhps_length_matched_truncate_frozen_2026-05-30.json` (frozen + dedup; **Outcome A**) |
| `bhps_length_matched_truncate_frozen_2026-05-29.json` (frozen, no-dedup) | `bhps_length_matched_truncate_frozen_2026-05-30.json` |

The `*_probe-symmetric-dedup_*` and `*_probe-pinned-thresh_*` files are
robustness probes (Supplement §S6), not headline results — cite only as
robustness evidence, never as the headline cell.

See the main manifest for the full rationale, the retained-on-disk reason
(live inputs to the regenerable comparison/cleanup chain), and the deferral
of physical archiving to the paper repo-split.
