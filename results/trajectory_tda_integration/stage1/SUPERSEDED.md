# SUPERSEDED pre-frozen results — DO NOT CITE in P01-A / P01-B

**Status:** authoritative supersession manifest for the Stage-1 headline battery.
**Created:** 2026-06-21 (Manager 11), ahead of the Stage-2 writing phase.
**Scope:** `results/trajectory_tda_integration/stage1/` and
`results/trajectory_tda_bhps/stage1/`.

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
