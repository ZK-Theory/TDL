# Code Review Triage — trajectory_tda directory, 2026-05-25

**Review source:** External static review of `trajectory_tda/` (run from worktree at `C:/Users/steph/.codex/worktrees/d07f/TDL/`), pasted into Manager chat 2026-05-25. Static review only; no code edits made by reviewer.

**Triage scope:** This document is Phase 1 triage (accuracy assessment from review text + first-principles math) + one Phase 2 confirmation (P0-3 and P1-5 null-layer code investigation). No code changes made in this session. Hard rule: no edits to `trajectory_tda/` until a fresh Manager session.

## CRITICAL — null-layer is structurally broken (P0-3 + P1-5 confirmed by code read)

### Finding

`trajectory_tda/topology/permutation_nulls.py`:

- **`_label_shuffle` (lines 53-64)** — performs `embeddings[rng.permutation(embeddings.shape[0])]`. PH on a row-permuted embedding matrix is **mathematically identical** to PH on the original — point-cloud topology is row-order invariant. The "label-shuffle null distribution" is therefore vacuous.
- **`_cohort_shuffle` (lines 67-92)** — within-cohort row permutation. Same PH-invariance problem at finer grain.
- **`_order_shuffle` / `_markov_shuffle` / `_stratified_markov_shuffle`** — structurally different: re-permute trajectory state sequences then call `ngram_embed(shuffled, **kwargs)`. Correctly regenerates input data BUT re-embeds — observed and null PH may live in different PCA coordinate frames (P1-5). Needs one more file read of `ngram_embed()` to confirm whether PCA is re-fit per call or uses frozen loadings.

### Why label-shuffle p-values aren't exactly 1.0

`_single_permutation` (lines 498-568) calls `maxmin_landmarks(X_perm, actual_lm, seed=seed)` with the per-permutation seed. Each null iteration therefore selects a different landmark subset. The "label-shuffle null distribution" is actually the distribution of **landmark-subsampling variance**, not a label-shuffle test. Observed p ≈ 0.5 (e.g., BHPS L=5000 label-shuffle H₀ p=0.512, H₁ p=0.558) is exactly the expected behaviour when comparing two random draws from the same underlying distribution.

### Impact on project record

**Invalidated p-values (label-shuffle and cohort-shuffle, all reports):**
- BHPS L=5000 "clean negative controls" (label-shuffle H₀ p=0.512 / H₁ p=0.558; cohort-shuffle H₀ p=0.554 / H₁ p=0.634) — these are landmark variance measurements, not negative-control evidence.
- BHPS L=2000 historical label-shuffle p=0.036 — also landmark variance; this never was a "BHPS asymmetry" finding.
- Any USoc label-shuffle / cohort-shuffle p-values in T1.1, T1.2a, or earlier runs.

**Invalidated vault entries and conventions:**
- The 2026-05-22 [DECISION] entry "L=5000 BHPS clean negative controls; CONVENTIONS rule replaced" must be reversed. The original CONVENTIONS rule ("NEVER treat BHPS shuffles as assumed negative controls") may have been correct in spirit — though for the wrong technical reason.
- Any prose draft section that cites label-shuffle / cohort-shuffle p-values as negative-control evidence (T2.1, T2.2 already merged) must be revised.

**Possibly intact (needs verification):**
- T1.2 headline Markov-1 W₂ rejections — depends on whether `ngram_embed()` produces deterministic coordinate frames or re-fits PCA per call. If the latter, even Markov-1 results are corrupted by coordinate-frame mismatch.
- T1.3 stratified Markov-1 — same condition.

## Full Phase 1 triage table

| # | Item | Math/code accuracy | Blast radius | Confidence | Verdict |
|---|---|---|---|---|---|
| P0-1 | Zigzag `max_dim=1` ⇒ no H1 deaths (`zigzag.py:322`) | Accurate by VR math | LOW if zigzag dormant in P01-A | High | Investigate Phase 2 — confirm dormancy |
| P0-2 | Zigzag year-shuffle null passes `metadata=None` (`zigzag_null_tests.py:123`) | Plausible per reviewer specificity | Same as P0-1 | Med | Investigate Phase 2 alongside P0-1 |
| **P0-3** | **Label/cohort permutation tests are topologically invariant (`permutation_nulls.py:54`, `:68`)** | **CONFIRMED 2026-05-25 by Manager code read** | **CRITICAL** — invalidates all negative-control evidence | **High** | **CRITICAL — full triage above; vault [NEGATIVE] + paper revision required** |
| P0-4 | BHPS wave-IDs used as `pidp` (`employment_status.py:60`, `income_band.py:38`) | Plausible — not verified by T0.9/T0.10/T0.11 | HIGH — trajectory integrity at ingest | Med | Investigate Phase 2 |
| P1-1 | Cycle "reps" use global centroid (`cycle_detection.py:91`) | Accurate from first principles | LOW if no loop-specific prose | High | Defer to repo cleanup |
| P1-2 | W₂ empty-vs-non-empty returns 0.0 (`wasserstein_null_tests.py:79`) | Accurate | LOW under normal sample sizes | High | Defer to fix; verify not in T1.2 hot path |
| P1-3 | Missing `(r+1)/(B+1)` correction in multiple modules | Accurate | Mixed — T2.2 fixed paper prose; new T0.12 pipeline records correct formula; legacy modules still buggy | High | Defer; confirm live paths |
| **P1-5** | **Null embeddings re-fit scaler/PCA/UMAP per null (`permutation_nulls.py:96`, `:117`)** | **PARTIALLY CONFIRMED — `_order_shuffle` calls `ngram_embed(shuffled, **kwargs)`; whether this re-fits depends on `ngram_embed()` internals (next investigation)** | **HIGH — compounds P0-3 for Markov-1 nulls** | **High on math** | **CRITICAL — next Phase 2 step (read `ngram_embed()`)** |
| P1-4 | Markov matrices not row-stochastic for zero-transition states | Accurate concern; T0.4 only fixed Markov-2 | MED — Markov-1 is headline null | Med | Investigate Phase 2 |
| P1-6 | Trajectory builder forward-fills (not NN), drops on long gap, miscounts `n_imputed` | Plausible | MED — Stage 4 Option A | Med | Investigate Phase 2 |
| P1-7 | `annual_partition.py` repeats whole-career embeddings per year | Plausible | LOW for P01-A if dormant; was central to P03 Zigzag (archived) | Med | Defer — confirm dormancy |
| P1-8 | "Firth" fallback is L1 regularised (`age_stratified.py:425`) | Accurate per reviewer quote (L1 ≠ Firth) | HIGH — affects T1.19 → T1.20 ORs if used | High on math | Investigate Phase 2 — confirm T1.19 rerun used this path or R `logistf` |
| P2-1 | TF-IDF can yield negative IDF (`ngram_embed.py:97`) | Accurate | LOW; subtle | High | Defer |
| P2-2 | Mapper `min_intersection` unused; `income_density` lens returns labels not density | Plausible | LOW | Med | Defer |
| P2-3 | NMI(Mapper, regime) forces overlap to arbitrary partition (`validation.py:18`) | Accurate | LOW-MED | High | Defer with prose flag |
| P2-4 | R scripts hard-code paths + runtime `install.packages` | Accurate; T1.32 Group D partial cleanup; reviewer flagging remainder | LOW — reproducibility | High | Defer to repo cleanup batch |
| P2-5 | T1.24 stability SE on different metric (`t1_24_stability_se_wilson_ci.R`) | Plausible — Table 2 SE/CI might be for wrong statistic | MED — affects published Table 2 | Med | Investigate Phase 2 |

## Outstanding Phase 2 investigation queue (for next Manager session)

In priority order:

1. **`ngram_embed()` internals** — confirm whether PCA basis is re-fit per call. If yes, P1-5 is fully confirmed and the Markov-1 / stratified-Markov-1 nulls also suffer coordinate-frame mismatch (would corrupt T1.2/T1.3 headlines even after the label/cohort bug is fixed).
2. **P0-4** — read `employment_status.py:60` and `income_band.py:38` to verify the wave-ID-as-`pidp` fallback. Cross-check against the T0.10 "10,992 spanning individuals" count.
3. **P1-8** — read `age_stratified.py:425` context; determine which path T1.19 rerun actually used (Python `fit_regularized` vs R `logistf`).
4. **P0-1 / P0-2** — quick grep for zigzag invocations in current Stage 1 scripts to confirm dormancy.
5. **P2-5** — read `t1_24_stability_se_wilson_ci.R` to confirm the metric mismatch.

## What to do next (recommendations for incoming Manager)

### Immediate (before any other work)

1. **Hold all dispatch of T1.33, T1.34, T1.35.** The pre-reg amendments and pre-regs filed earlier today assume the null-layer apparatus works. T1.33's "constrained-shuffle permutation null" needs methodological review before dispatch.
2. **File a vault `[NEGATIVE]` entry** documenting the P0-3 confirmation against `04-Methods/Computational-Log`. Reference this triage file. Cite the specific p-values that are now invalidated.
3. **Reverse the 2026-05-22 [DECISION] entry on CONVENTIONS** — the "L=5000 BHPS clean negative controls" finding does not survive the null-layer audit. Either revert CONVENTIONS to the original "NEVER treat BHPS shuffles as assumed negative controls" rule, or restate it with the technical reason corrected.
4. **Surface to User immediately as a project-direction decision point.** This is bigger than a normal bug — it changes what claims P01-A can defend. The User should drive the response strategy.

### Methodological re-design required

The label-shuffle / cohort-shuffle nulls need to be re-implemented to **actually test their stated hypotheses**:

- **Correct label-shuffle:** shuffle the state/regime labels at the person-year level *before* embedding, then re-build trajectories from the shuffled labels, then re-embed. This breaks trajectory structure under the null and is a real test of "do the topology features depend on label sequence?"
- **Correct cohort-shuffle:** shuffle birth-cohort assignments across individuals, then if the embedding pipeline conditions on cohort (it may not), recompute it. If the embedding doesn't condition on cohort, cohort-shuffle is moot for embedding-level PH and should be tested at a different stage (e.g., regression).

A proper re-implementation requires coordination between the TDA Agent (null-layer code) and the Reproducibility Agent (coordinate-frame consistency for embeddings).

### Paper sections requiring revision

- §4.3 negative-control discussion in P01-A v2 (T2.1 already merged, content already on `main` in `papers/P01-A-JRSSA/drafts/v2-2026-05.md` or equivalent) — must remove or re-frame any claim relying on label-shuffle/cohort-shuffle p-values.
- §6.2 BHPS rewrite (T2.8 pending) — the "L=5000 clean negative controls" framing planned for §6.2 is gone.
- T2.3 §3 intrinsic-d paragraph (merged today 2026-05-24 at commit `4cdab52`) — not directly affected; intrinsic-dimensionality is a separate computation.

### Stage 1 results requiring re-derivation

If P1-5 is confirmed for `ngram_embed()`, the following also need re-run:

- T1.2 USoc + BHPS headlines (currently in batch — T1.2a/b/c/d done, e/f/g/h pending)
- T1.3 stratified Markov-1 outcomes
- T1.6 BHPS H4 negative-control diagnostics (depends on label-shuffle as a baseline)
- T1.8 Markov-2 α sweep
- Any other null-test result in `results/trajectory_tda_integration/post_audit/` or `results/trajectory_tda_bhps/post_audit/`

### What is probably NOT affected

- T0.9 jbstat verification, T0.10 income verification, T0.11 FOO clustering — these are data-side verifications, separate from the null-layer code.
- T1.4 intrinsic dimensionality — separate computation on the static 20-D embedding.
- T1.12 BIC curve — GMM, separate from null tests.
- T1.13–T1.20 panel-statistics work — regression-side, separate from PH nulls (though T1.19 is flagged separately for P1-8 Firth/L1 issue).

## Vault status

No `[NEGATIVE]` entry has been filed yet for the null-layer finding. The User asked for triage only ("determine if the feedback is accurate and needs action initially rather than diving in to change anything"). Vault filing is a User-decision point because of the project-direction implications.

## Handoff payload

This file is the triage artefact. Incoming Manager should:
1. Read this file first.
2. Read the Tracker working note from 2026-05-25 referring to the code review.
3. Read the Phase 2 investigation queue above and decide priority with the User.
4. Do NOT dispatch T1.33/T1.34/T1.35 until null-layer status is resolved.
5. The T1.2b-h batch is still running on `run/stage1-headline-batch` — results from T1.2e/f/g/h may still arrive and need to be archived as **provisional pending null-layer audit**, not treated as final.
