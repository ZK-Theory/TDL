---
type: permanent-note-DRAFT
status: DRAFT — staged in the worktree for User review before any vault write
target: 02-Notes/Permanent/Markov-k-null-cannot-reject-statistics-of-the-order-k-sufficient-statistic.md
source: spike-05-c1-pl-postmortem-markov0 (2026-07-10); C1 T-C1-1 NEGATIVE (2026-07-07)
---

# A Markov-k null cannot reject a statistic of the order-k sufficient statistic

## The claim

If a test statistic T is a deterministic function of the order-k transition
counts, and the null simulates trajectories from the Markov-k model whose
maximum-likelihood parameters are estimated from those same counts, then the
expected null counts equal the observed counts up to sampling noise — the
observed statistic is a plug-in of the null's own fitted parameters and sits
near the centre of its null distribution **by construction**. Expected
p ≈ 0.5 regardless of what the data contain. The test can only detect
higher-order deviations that the statistic's substrate cannot express.

## The instance that motivated this note

C1 (T-C1-1, 2026-07-07, B = 1000, seed 42): the Integrated Fiedler Area of
the persistent-Laplacian curve on the BHPS 9-state employment transition
graph is a deterministic function of the 9x9 first-order count matrix; the
null was a Markov-1 parametric bootstrap fitted to the same trajectories.
Result: IFA p = 0.2408, observed at the 76th percentile of its null, 0/35
pointwise BH-FDR survivors — recorded as NEGATIVE. Post-mortem (Spike 5',
2026-07-10): the mean null count matrix deviates from the observed count
matrix by 2.85% relative Frobenius norm over 20 draws — pure sampling noise.
The design was near-powerless from the start; the NEGATIVE is a property of
the (statistic, null) pairing, not of the phenomenon.

## Perturbation ≠ non-centering

The dispatch's invariance audit verified that the null PERTURBS the object
(std(null IFA) = 9.3e-3 > 0) — necessary but not sufficient. A parametric
bootstrap both perturbs and CENTRES: variance without displacement. Every
null-model invariance audit must check both:

1. **Perturbation**: the rebuilt object differs across draws.
2. **Centering**: the null is not fitted through the statistic's own
   sufficient statistic. If T = f(S(data)) and the null is a parametric model
   fitted via S(data), the test degenerates into testing sampling noise
   against itself.

## Remedies (choose per design, pre-registered)

- A **lower-order null rung** (e.g. Markov-0 order-shuffle against an
  order-1-informed statistic) — the statistic's substrate can then express
  what the null destroys. Spike 5' Part 2 demonstrates this: against
  Markov-0, the same IFA statistic separates cleanly (observed below all 99
  draws) and is non-redundant with spectral gap and transition entropy.
- A **statistic on a richer substrate** than the null's sufficient statistic
  (e.g. per-wave time-resolved transition graphs vs a stationary Markov-1
  null).
- A **two-sample design** (compare groups/eras under the same construction),
  where neither side is fitted to the other.

## Cross-references

[[C1-persistent-laplacian-fiedler-markov1-null-negative]] ·
null-operation-invariance-audit skill (centering check) ·
spike-05-c1-pl-postmortem-markov0-result-2026-07-10 ·
Obs 47 in the skill-observation log (2026-07-09).
