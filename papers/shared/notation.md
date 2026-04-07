# Shared Notation Standard for P01-A, P01-B, and P04

Created during Phase 0 of the P01-P04 strategic reorganisation.

## Purpose

This note reconciles notation across the archived source papers and fixes the
minimum shared language needed before draft assembly. It standardises symbols
where possible and records where harmonisation is blocked by a computation
audit.

## Default Conventions

| Symbol | Meaning | Default use |
| --- | --- | --- |
| $X \subset \mathbb{R}^d$ | Embedded trajectory point cloud | Use for the full embedded sample |
| $X_t$ | Time- or cohort-indexed subset of the embedding | Use in annual or era-specific analyses |
| $K_\varepsilon(X)$ | Vietoris-Rips complex at scale $\varepsilon$ | Use for single-parameter PH |
| $K_{\varepsilon,\tau}(X, a)$ | Bi-filtration at scale $\varepsilon$ and income threshold $\tau$ | Use for P04 |
| $D_q(X)$ | Persistence diagram in homology degree $q$ | Use across all papers |
| $b_i, d_i$ | Birth and death coordinates of a persistence pair | Use when referring to individual bars/points |
| $\lambda_q$ | Persistence landscape in homology degree $q$ | Use when reporting landscape $L^2$ distances |
| $W_p(D, D')$ | $p$-Wasserstein distance between diagrams $D$ and $D'$ | Always write the order $p$ explicitly |

Unless a paper has a strong reason to do otherwise, the ground metric for
Wasserstein computation is Euclidean on the birth-death plane.

## Paper-Specific Context

| Concept | P01-A | P01-B | P04 |
| --- | --- | --- | --- |
| Primary topological object | $K_\varepsilon(X)$ | $K_\varepsilon(X)$ and null-generated analogues | $K_{\varepsilon,\tau}(X, a)$ |
| Persistence diagram | $D_q(X)$ | $D_q^{\mathrm{obs}}$, $D_q^{\mathrm{null}}$ | $D_q(\varepsilon, \tau)$ or signed-measure summaries derived from the bifiltration |
| Statistical comparison | Null tests on scalar and diagram-level summaries | Formal testing language is primary | Income-stratified comparison across the second filtration parameter |

## Wasserstein Order Audit

This is the blocking notation issue for Phase 0.

### Verified code and manuscript state on 2026-04-07

- `papers/P01-VR-PH-Core/latex/body.tex` currently writes the diagram-level
  statistic as $W_1(D_{\mathrm{obs}}, D_{\mathrm{null}})$.
- `trajectory_tda/topology/vectorisation.py` defines the reusable trajectory
  Wasserstein distance with `p: int = 2` and calls
  `gudhi.wasserstein.wasserstein_distance(..., order=p, internal_p=2)`.
- `trajectory_tda/validation/wasserstein_null_tests.py` likewise defaults to
  `order: int = 2`.
- `papers/P03-Zigzag/latex/body.tex` explicitly describes the annual distance
  matrix as a 2-Wasserstein analysis.
- `trajectory_tda/analysis/annual_wasserstein.py` computes the annual distance
  matrix with `order: float = 2.0` by default.
- A deterministic replay of the P01 integration order-shuffle null under the
  current W2 code path does not reproduce the stored JSON exactly
  (`H_0`: 12.6766 vs 11.2172; `H_1`: 139.8963 vs 139.6884), so exact
  code-environment provenance remains imperfect.
- The same replay under an explicit W1 monkeypatch is orders of magnitude away
  from the stored values (`H_0`: 498.64 vs 11.22; `H_1`: 7026.36 vs 139.69),
  ruling out W1 as the source of the stored trajectory null-battery results.

### Phase 0 conclusion

P03 is internally aligned on $W_2$. For P01, the order question is now resolved
even though the exact code-environment replay is not: the stored trajectory
null-battery Wasserstein values should be treated as W2-era outputs, and the
current $W_1$ manuscript wording should be treated as stale prose rather than as
the authoritative computation record.

### Drafting rule for the reorganisation

For P01-B, state that the audited trajectory null-battery results are reported
as W2 results and note that exact replay drift persists across code/environment
revisions. If the legacy P01 results are recomputed under the current pipeline,
record those as a new result rather than silently replacing the archived values.

## Drafting Rules

- Use $W_p$ in general statements and specialise to $W_1$ or $W_2$ only when
  the computation is fixed and verified.
- Use persistence landscape $L^2$ distance as the complementary metric whenever
  cross-diagram comparisons are reported.
- In P01-B, reserve sociological interpretation for the application section and
  keep the framework notation dataset-agnostic.
- In P04, reserve $\tau$ for the income threshold parameter so it does not clash
  with filtration radius $\varepsilon$.
