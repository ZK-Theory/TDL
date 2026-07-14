# SUPERSEDED pre-frozen results — DO NOT CITE in P01-A / P01-B

**Status:** authoritative supersession manifest for the Stage-1 headline battery.
**Created:** 2026-06-21 (Manager 11), ahead of the Stage-2 writing phase.
**Updated:** 2026-07-14 (Manager 13) — solver-artifact supersession of the H1 W₂
statistics and the sequence-vintage note (sections below).
**Scope:** `results/trajectory_tda_integration/stage1/` and
`results/trajectory_tda_bhps/stage1/`.

## Solver-artifact supersession — H1 W₂ statistics (2026-07-14 `[DECISION]`)

The W₂ solver silently degraded to a greedy persistence-rank matching whenever
POT was absent from the venv (era ≤ 2026-05-29; fail-loud fix + full audit:
WT-6, PR #94, `w2_fallback_audit_2026-07-14.json`). **H0 and landscape-L²
values are unaffected** (immunity verified, not assumed). For **H1 W₂**
inference the canonical citable values move:

| Object (H1 W₂ only) | ❌ Superseded — do NOT cite | ✅ Canonical (cite this) |
|---|---|---|
| USoc headline H1 W₂ | H1 W₂ block of `usoc_headline_frozen_2026-05-28.json` (greedy: obs-null 233.68, d_perm +22.09) | `headline_vintage_materiality_corrected_2026-07-14.json` (exact: obs-null 12.68, d_perm +31.16, p floor) |
| BHPS headline H1 W₂ | H1 W₂ block of `bhps_headline_frozen_2026-05-28.json` (greedy: d_perm +2.06, p 0.019) | `…/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json` (exact: d_perm +19.26, p floor; lands with PR #94) |

The frozen 2026-05-28 files remain canonical for **H0 W₂ and landscape-L²**.
Additional constraints from the audit:

- `lm_sensitivity_L2500/L8000` (all four): H1 W₂ numbers are
  **SUSPECT-UNVERIFIABLE** (no cached diagrams) — unciteable in manuscripts
  without a production re-run. Their design-choice role (L=5000 selection,
  internally greedy-consistent) stands.
- `dedup_amendment_comparison_*` "rejection direction preserved / 0 changes":
  **do not rely** pending exact re-derivation of the 2026-05-29 arm (its arms
  straddle the solver boundary).

## Sequence-vintage note (2026-07-14 `[DECISION]`, ruling (a))

The frozen 2026-05-28 USoc headline and its null banks were computed on the
**May-2 orphan** sequence file, not the canonical Apr-8 build (established
bit-for-bit by Spike Set B, 2026-07-10, superseding the B9 2026-06-22
mtime-based "Apr-8-rooted" assertion). Exact-W₂ re-derivation on the canonical
Apr-8 sequences (WT-1c, `headline_vintage_materiality_corrected_2026-07-14.json`)
moves d_perm by ≤ 0.11 (H1) / 0.23 (H0) and flips no conclusion — the vintage
is **immaterial** and the headline stands with this note carried into any
citing prose. BHPS banks: 6/8 reproduce bit-for-bit from canonical BHPS
(per-bank verdicts in the 2026-07-12 memo/result JSON). Per-cache source
vintages: `cache/*.provenance.json` sidecar manifests.

## Why this file exists

The 2026-05-24/25 Stage-1 headline JSONs were computed under the **per-call
PCA re-fit bug** identified in the 2026-05-25 `[NEGATIVE]` null-layer audit
(the null embedding was re-fitted on each permutation instead of using frozen
observed loadings). That bug was fixed by **T1.36** (frozen-loadings threading,
merged `753420a`) and the headline battery was re-run under frozen loadings by
**T1.37** (merged `97f5026`). The corrected reruns flipped **21 of 50 battery
cells** — most consequentially BHPS H1 W2 (p=0.99 → 0.019) — as quantified in
`frozen_vs_provisional_comparison_2026-05-29.json`.

**The files listed under "superseded" below carry bug-era p-values and must
not be cited in the manuscripts, tables, figures, or supplements.** Cite the
canonical frozen file instead.

## Canonical citable files (use these)

| Object | ❌ Superseded — do NOT cite | ✅ Canonical (cite this) |
|---|---|---|
| USoc headline | `usoc_headline_2026-05-24.json` | `usoc_headline_frozen_2026-05-28.json` |
| BHPS headline | `bhps_headline_2026-05-24.json` | `bhps_headline_frozen_2026-05-28.json` |
| USoc LM sensitivity L=2500 | `lm_sensitivity_L2500_2026-05-24.json` | `lm_sensitivity_L2500_frozen_2026-05-28.json` |
| USoc LM sensitivity L=8000 | `lm_sensitivity_L8000_2026-05-25.json` | `lm_sensitivity_L8000_frozen_2026-05-28.json` |
| BHPS length-matched truncate | `bhps_length_matched_truncate_2026-05-25.json` (pre-frozen) **and** `…_frozen_2026-05-29.json` (frozen, no-dedup) | `…/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_frozen_2026-05-30.json` (frozen + external-indexing dedup; **Outcome A**) |
| BHPS length-matched first13 | — | `…/trajectory_tda_bhps/stage1/bhps_length_matched_first13_frozen_2026-05-30.json` |
| Stratified Markov-1 battery | `stratified_markov1_battery_2026-05-13.json` (B=100, pre-frozen, pairwise-between-subgroup) | `…/stratified_markov/stratified_markov1_W2_L5000_frozen_2026-05-29.json` |

Note the length-matched truncate cell has **two** superseded versions: the
pre-frozen 2026-05-25 file *and* the 2026-05-29 frozen file (which predates the
external-indexing dedup). The dedup correction (2026-05-30) is what locks
Outcome A — see the 2026-05-31 `[DECISION]` and Supplement §S6
(`papers/P01-A-JRSSA/drafts/sections/supplement-S6-length-matched-dedup.md`).

## Why the superseded files are retained on disk (not deleted/moved)

They are **live inputs to the regenerable provenance chain** and are kept as
historical record per the no-overwrite rule. Moving or deleting them would
break:

- `trajectory_tda/scripts/stage1/build_frozen_vs_provisional_comparison.py`
- `trajectory_tda/scripts/stage1/build_pvalue_denominator_cleanup.py`
- `tests/trajectory_tda/test_stage1_comparison_contracts.py`
- the recorded input paths inside `frozen_vs_provisional_comparison_2026-05-29.json`
  and `pvalue_denominator_cleanup_2026-05-28.json` (no-overwrite-locked).

Physical archiving (move into an `archive/` subtree with atomic path updates
to the scripts/tests above) is **deferred to the paper repo-split**, the
natural point at which these paths are rewritten anyway, and at which the
provisional files are simply excluded from the reproducibility package rather
than shipped.

## Provenance anchors

- 2026-05-25 `[NEGATIVE]` — per-call PCA re-fit bug (vault Computational-Log).
- T1.36 frozen-loadings fix — merge `753420a`.
- T1.37 frozen reruns + comparison — merge `97f5026`; `frozen_vs_provisional_comparison_2026-05-29.json`.
- 2026-05-29 (later) `[DECISION]` — T1.2h asymmetry lock superseded.
- 2026-05-31 `[DECISION]` — Pre-reg #5 redo Outcome A locked.
