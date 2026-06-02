# Common Statistical Issues — Identification and Remedy

Catalogue for the `statistical-design-audit` skill. Each entry gives how to spot
the issue and what to require. Specialised to TDL's permutation-null /
persistent-homology / UK-panel setting.

## 1. p-value denominator error

**Identify:** The denominator dividing the null-exceedance count is a diagnostic
cap, a fixed constant, or `total_pairs` when fewer draws were actually used.
p-values that cannot reach `1/(n+1)` for the stated B, or that do not move when r
changes, are red flags.

**Require:** `p = (r + 1) / (n + 1)` with `n = min(B, total_pairs)`. Output must
expose `pvalue_null_draws == n` per cell. Bind to `monte-carlo-permutation-p-value`.

## 2. Non-exchangeable permutation null

**Identify:** The shuffle permutes a quantity that the null should hold fixed, or
operates on an object downstream of where the association lives (e.g. permuting
rows that have already been embedded, so the persistence diagram is invariant to
the shuffle).

**Require:** The permutation breaks only the association under test and preserves
stratification/clustering. Apply the shuffle *before* embedding when the embedding
is the object compared. See `representation-freeze-audit` and
`null-operation-invariance-audit`.

## 3. Multiple comparisons without correction

**Identify:** Many tests reported, several p < 0.05, no mention of FDR/BH; or a
correction applied without stating the family.

**Require:** Benjamini-Hochberg FDR with the family defined explicitly (which
cells/dims/metrics are in it and why). Report both raw and adjusted p.

## 4. Pseudoreplication / ignored clustering

**Identify:** n defined as number of measurements rather than independent units;
repeated waves on the same individual treated as independent; SEs implausibly
small.

**Require:** Resampling/SE at the cluster (individual/household) level — cluster
bootstrap, cluster-robust SE, or a mixed model. Bind to `icc-cluster-bootstrap`
or `svyglm-cluster-robust-se`.

## 5. Circular analysis / double-dipping

**Identify:** Features, cells, or thresholds selected using the same data later
used to test them; "significant" cells chosen post hoc then reported as findings.

**Require:** Pre-register the selection rule, or use independent data for
selection vs testing; label post-hoc analyses as exploratory.

## 6. Estimand drift

**Identify:** The target quantity (ATE/ATT, escape probability, transition rate)
changes between runs while the task is framed as a routine rerun; eligibility
rules quietly shift.

**Require:** A written estimand, unchanged across reruns; a pre-reg amendment if
it must change. See `panel-estimand-audit`.

## 7. MICE non-convergence

**Identify:** Imputation diagnostics not reported; trace plots not inspected; too
few iterations.

**Require:** Convergence checked and reported; Rubin's rules for pooling. Bind to
`mice-convergence-rule` and `rubin-pooling`.

## 8. IPW instability

**Identify:** Extreme weights left untrimmed; effective sample size collapses;
weights not normalised.

**Require:** Normalised weights with a stated trimming rule. Bind to
`normalised-ipw-trimming`.

## 9. Manski bounds misuse

**Identify:** Bounds reported as point estimates; assumptions for tightening not
stated; bounds that exclude logically possible values.

**Require:** Explicit identifying assumptions, bounds reported as intervals, and
the conditioning set stated.
