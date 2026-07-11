---
type: permanent-note-DRAFT
status: APPROVED 2026-07-10 (Stephen) — promoted to the vault; this repo copy is the historical staging record
target: 02-Notes/Permanent/Markov-k-null-cannot-reject-statistics-of-the-order-k-sufficient-statistic.md (promoted 2026-07-10)
source: spike-05-c1-pl-postmortem-markov0 (2026-07-10); C1 T-C1-1 NEGATIVE (2026-07-07)
---

# A Markov-k null cannot reject a statistic of the order-k sufficient statistic

## The claim

If a test statistic T is a deterministic function of the order-k transition
counts, and the null simulates trajectories from the Markov-k model whose
maximum-likelihood parameters are estimated from those same counts, then the
expected null counts equal the observed counts up to sampling noise — the
observed statistic is a plug-in of the null's own fitted parameters and sits
near the centre of its null distribution **by construction**. Under the
assumptions of the centering argument — correctly specified Markov-k null,
exact sufficiency (T a function of the order-k counts alone), and enough
draws — the expected p-value is near 0.5 whatever the data contain. Finite
B, discrete statistics, boundary parameter estimates, and misspecification
can each displace the null centre, so p ≈ 0.5 is the idealised tendency of
the design, not a guarantee; the practical content is unchanged — the test
is near-powerless against anything the order-k counts can express, and can
only detect higher-order deviations that the statistic's substrate cannot
express.

## The instance that motivated this note

C1 (T-C1-1, 2026-07-07, B = 1000, seed 42): the Integrated Fiedler Area of
the persistent-Laplacian curve on the BHPS 9-state employment transition
graph is a deterministic function of the 9x9 first-order count matrix; the
null was a Markov-1 parametric bootstrap fitted to the same trajectories.
Result: IFA p = 0.2408, observed at the 76th percentile of its null, 0/35
pointwise BH-FDR survivors — recorded as NEGATIVE. Post-mortem (Spike 5',
2026-07-10): the mean null count matrix deviates from the observed count
matrix by 2.85% relative Frobenius norm over 20 draws — consistent with
sampling variation (20 draws bound that attribution only loosely; no formal
uncertainty interval was computed).
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
