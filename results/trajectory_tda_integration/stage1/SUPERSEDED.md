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
  hold **DISCHARGED 2026-07-14** — the 2026-05-29 arm was re-derived under exact
  W₂ (WT-6 addendum, `[RESULT]` 2026-07-14). Cite
  `dedup_amendment_comparison_corrected_2026-07-14.json` for the **H1 W₂ cell and
  the decision_summary counts**; the committed `…_2026-06-01.json` remains the
  record for landscape-L², `dedup_provenance` and the probes. With both arms
  exact the flip disappears (`rejection_direction_changes` 1 → 0). **Outcome A is
  unchanged** (it rests on the exact-era 05-30 dedup arms). **But the committed
  `methodological_disclosure_draft` mechanism is misattributed** — the H1 W₂ flip
  is greedy→exact, not no-dedup→dedup; the dedup amendment must **not** be
  justified in the manuscript by the H1 W₂ flip (P01-A §S6 / §6.2 rewrite pending
  a User ruling — see `docs/plans/strategy/W2-Solver-Paper-Impact-and-Rewrite-Plan-2026-07-14.md`).

### Not covered by the WT-6 audit table — classified 2026-07-14 (Manager 13)

- **`04_nulls_wasserstein_w2_20260407.json`** (2026-04-07, deep greedy era; no
  cache exists ⇒ **SUSPECT-UNVERIFIABLE**). Feeds **P01-A Table 1**
  (`table1_effects_2026-05-22.*`, source label `L2000_legacy_2026-04-07`) and
  P01-B §4.2 Table 2's legacy label/cohort/order-shuffle rows. Its **H1 W₂
  numbers are unciteable without a production re-run** (ruling item 3 applies).
- **P01-A Table 1 H1 rows generally** — every source in
  `table1_effects_2026-05-22.md` is greedy era (`L5000_postaudit_2026-05-02`,
  `L2000_legacy_2026-04-07`, `L5000_markov2_postaudit_2026-05-02`,
  `stratified_markov1_L5000_2026-05-02`), all predating the earliest null cache
  (2026-05-24) ⇒ **SUSPECT-UNVERIFIABLE**, and all pre-frozen (also superseded on
  axis 1). Screen: every H1 `rho_hat` ≈ 1 (the greedy compression signature) and
  every H1 mean is 130–306 against an exact diagonal bound of ~20. Two cells
  **invert** under exact W₂ (BHPS `markov` H1 `p=0.978` non-reject vs the
  corrected exact headline `p=0.000999`; `stratified_markov1` H1 `p=1.0000`).
  **Updated 2026-07-16 (T1.38 Phase 2):** this blanket prohibition is lifted
  only for the fresh L=5000 exact-W2 H1 rows in
  `w2_gap_closure_table1_h1_2026-07-16.json`: order-shuffle, Markov-1,
  Markov-2, and stratified-Markov-1 for USoc and BHPS. Each has B=100,
  frozen loadings, the fail-loud Gudhi/POT solver, and a passed diagonal-bound
  screen; both Markov-1 directions agree with their corrected exact headlines.
  The historical greedy-era Table 1 files remain superseded. Label-shuffle and
  cohort-shuffle are permanently **INVALID-BY-CONSTRUCTION** because they are
  invariant to the set-valued statistic, and the L=2000 legacy rows remain
  unciteable.
- **`markov2_alpha_sweep_summary_2026-06-16.json`** — dated after the 2026-05-29/30
  boundary ⇒ **exact era, presumed IMMUNE**, but never explicitly gated. Feeds
  P01-B §4.2 Table 2's Markov-2 rows. Confirm by gate before citing as verified.
- **`post_audit/markov2_alpha_sweep_cell_{usoc,bhps}_alpha1_B1000_L5000_seed42_*.json`**
  (USoc 2026-06-15, BHPS 2026-06-08; committed under the H6 ruling, 2026-07-18
  `[DECISION]`) — split verdict by field family. **Landscape L² blocks
  (`result.h0/h1.landscape_*`): citable.** The landscape pipeline contains no
  optimal-transport solver, so these values are structurally immune to the greedy
  fallback; they are the sole source of P01-B Table 2's Markov-2 landscape values
  (USoc H₀ 0.2577→0.258, H₁ 0.002997→0.003; BHPS H₀/H₁ 0.000999→<0.001) and of the
  2026-07-17 recompute pre-registration's "certified landscape in hand" figures —
  resolving the audit's open conflict (footnote ‡ describes the W₂-only *summary*
  artifact; both statements are true of different artifacts). **W₂ fields:
  do-not-cite** — same solver-uncertifiable class as the summary (no solver-identity
  stamp; the fragile-window screen applies). Consequence: the pre-registered
  certified Markov-2 recompute is scoped to **W₂ only**.
- **`bhps_nonoverlap_reanalysis_2026-06-09`** H1 W2 — the retained L=5000
  remainder cache was re-derived under exact W2 by T1.38 on 2026-07-16
  (`w2_gap_closure_phase1_2026-07-16.json`). Its fresh greedy convention gate
  reproduces `arm_b.remainder_h1_w2_d_perm` exactly (-2.854533606986761); the
  exact re-derivation instead has `d_perm=+7.481197814190041`,
  `p=0.000999000999000999`. The claim that H1 rejection disappears after
  excluding spanning individuals is therefore **FALSIFIED** for this retained
  remainder object. Do not cite the greedy H1 value or rewrite P01-A §6.2 in
  task scope; the outcome has been escalated for Manager/User direction. The
  separate L=1882 arm and 20 subsample caches remain outside this cache-backed
  re-derivation.

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
