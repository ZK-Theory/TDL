---
name: null-operation-invariance-audit
description: Use when a permutation/shuffle null is being designed or reviewed — to confirm the null operation actually perturbs the object the test statistic is computed on, rather than leaving it invariant.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - stochastic-null
  roles:
    - verifier
  runtime: agnostic
---

# Null-Operation Invariance Audit

Use this for the Stochastic / Null Model lane, focused on one decisive question: is
the test statistic invariant to the null operation? A permutation null that does
not change the quantity it permutes cannot reject anything — the null draws pile
onto the observed value.

## Core Check

0. **Static trace, before any compute.** Write the statistic as T(input-object).
   Does the null's perturbed variable appear in that construction at all? Is the
   construction invariant under the null operation's symmetry group — e.g. row
   order for a set-valued construction like Mapper or k-means-on-features? A "no"
   to either question is a silent identity operation, decidable without running a
   single draw: label permutations against label-blind statistics, and row
   permutations against set-invariant constructions, are the coarsest failure and
   the cheapest to catch.
1. Identify the test statistic and the object it is computed on (point cloud,
   persistence diagram, regression design matrix).
2. Identify where the shuffle is applied in the pipeline.
3. Confirm the shuffle is **upstream** of the statistic, so a non-identity
   permutation produces a different statistic value. The classic failure is
   shuffling rows that have already been embedded: the persistence diagram is a
   set, invariant to row order, so W2(observed, null) = 0 for every draw.
4. Verify a quick empirical witness: at least one non-identity permutation yields
   a statistic that differs from the observed when the tested association is real.
5. **Shape/alignment witness.** Compute the FULL statistic (not just its scalar
   summary) on the observed data AND on one null draw. Assert: (a) the per-element
   vectors have identical length/shape, (b) the reduction (trapz/sum/mean)
   executes without error on the null, (c) observed and null are evaluated on the
   *same fixed grid* — not each other's data-dependent grid (e.g. "active
   filtration steps," which can vary in count draw to draw when a helper filters
   or drops entries). A length/shape divergence is a red finding, not a runtime
   detail to fix later; it can make the battery crash or silently incomparable.
6. **Centering check.** If the statistic is a function of a sufficient statistic
   T(data), and the null model is a parametric fit obtained via T(data) itself
   (e.g. a Markov-k null whose MLE *is* the observed transition-count matrix),
   the observed statistic is by construction a plug-in of the null's own fitted
   parameters — expected p ≈ 0.5 regardless of any real signal. Non-degenerate
   null variance (step 4) is necessary but not sufficient. Require either a
   lower-order null rung, a statistic computed on a richer substrate than the
   null's sufficient statistic, or a two-sample design instead.

## Output Format

Verdict: **VALID NULL**, **INVARIANT NULL (cannot reject)**, or **DEGENERATE NULL
(centered on the statistic's own sufficient statistic — structurally
near-powerless)**, with the pipeline location, the object/substrate involved, and
(for DEGENERATE NULL) the sufficient statistic that ties observed to null.

## Pressure Scenarios

- Label/cohort shuffles permuted already-embedded rows; persistent homology was
  invariant to the null operation and the test was structurally unable to reject.
- A Mapper spike registered an employment-label permutation null against a
  construction built only from embedding + PCA filter (labels never entered it)
  and a spatial-permutation null against a plain z-scored point SET (Mapper on a
  set is row-order invariant) — both provably invariant before a single draw ran;
  caught by the static trace (step 0) and pinned with a unit test asserting the
  construction's row-permutation invariance.
- A persistent-Laplacian Fiedler-curve battery integrated `np.trapz(null_lambda1,
  observed_thresholds)` across observed (35 active steps) and null (34 active
  steps) grids — a shape mismatch the two-check audit (perturbation + variance)
  missed entirely; only computing the full statistic on one null draw first
  surfaced it (step 5).
- A Markov-1 null IFA battery returned p=0.241 with std(null IFA) > 0 (perturbation
  confirmed) — but the statistic factors through the same 9×9 transition-count
  matrix the Markov-1 null is fit from, so the test was structurally
  near-powerless by construction, not because the phenomenon was absent (step 6).

## Related Skills & Contracts

- Pairs with `representation-freeze-audit` (shuffle pre- vs post-embedding) and
  `statistical-design-audit` (exchangeability).
- Enforcing contract: `null-operation-changes-ph-input`.
