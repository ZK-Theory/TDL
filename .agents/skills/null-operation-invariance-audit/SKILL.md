---
name: null-operation-invariance-audit
description: Use when a permutation/shuffle null is being designed or reviewed — to confirm the null operation actually perturbs the object the test statistic is computed on, rather than leaving it invariant.
---

# Null-Operation Invariance Audit

Use this for the Stochastic / Null Model lane, focused on one decisive question: is
the test statistic invariant to the null operation? A permutation null that does
not change the quantity it permutes cannot reject anything — the null draws pile
onto the observed value.

## Core Check

1. Identify the test statistic and the object it is computed on (point cloud,
   persistence diagram, regression design matrix).
2. Identify where the shuffle is applied in the pipeline.
3. Confirm the shuffle is **upstream** of the statistic, so a non-identity
   permutation produces a different statistic value. The classic failure is
   shuffling rows that have already been embedded: the persistence diagram is a
   set, invariant to row order, so W2(observed, null) = 0 for every draw.
4. Verify a quick empirical witness: at least one non-identity permutation yields
   a statistic that differs from the observed when the tested association is real.

## Output Format

Verdict: **VALID NULL** or **INVARIANT NULL (cannot reject)**, with the pipeline
location of the shuffle and the object it acts on.

## Pressure Scenario

Label/cohort shuffles permuted already-embedded rows; persistent homology was
invariant to the null operation and the test was structurally unable to reject.

## Related Skills & Contracts

- Pairs with `representation-freeze-audit` (shuffle pre- vs post-embedding) and
  `statistical-design-audit` (exchangeability).
- Enforcing contract: `null-operation-changes-ph-input`.
