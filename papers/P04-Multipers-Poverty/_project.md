---
paper: P04
title: "Multi-Parameter Persistent Homology for Poverty Trap Detection in UK Employment Trajectories"
status: in-progress
target-journal: "Annals of Applied Statistics"
submitted: null
deadline: null
priority: medium
stage: 2
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, multipers, bifiltration, poverty-traps, multi-parameter-persistence]
current-draft: papers/P04-Multipers-Poverty/drafts/v4-2026-04.md
---

## Status

Target updated to *Annals of Applied Statistics* during the P01-P04 strategic
reorganisation. Draft v4 remains the current source draft, and authorship is now
fixed as single-author Stephen Dorman (The Open University, UK); endogeneity
checks and AoAS-specific reframing are still pending.

Active computation. v4 draft integrates Appendix B (Hilbert function + rank invariant) results and LaTeX pipeline.

### Pre-computation validation (2026-04-02)

- **P01 embedding stability:** VERIFIED. 16/16 tests pass including checkpoint consistency.
  - Embedding is fully deterministic (PCA uses full SVD — seed-independent)
  - Cached checkpoint (27,280 × 20, PCA, 49% variance) validated: shape, finiteness, metadata, fitted models
  - Fitted PCA transform on subsets matches row-slicing (landmark subsampling safe)
  - Income band extractable from state labels; distinguishes synthetic regimes
  - Tests: `tests/trajectory/test_p04_embedding_stability.py`
  - **Note:** sklearn version mismatch (joblib saved 1.8.0, loaded 1.3.2) — functional but should align before production runs

- **multipers library:** VALIDATED on synthetic bifiltrations. 13/13 tests pass.
  - Installed: multipers 2.3.4 (requires numpy <2.0 — project pins 1.26.4)
  - **multipers 2.5.0 requires numpy 2.x** — incompatible with current project constraint
  - `RipsLowerstar(points, function, threshold_radius)` is the correct API for Rips × income bifiltration
  - Signed measures compute for H0 and H1 on 2D and 20D point clouds
  - Circle (H1) detected; Gaussian blob (no H1 at tight radius) confirmed
  - Income permutation changes signed measure (validates null test design)
  - Landmark subsampling compatible
  - Tests: `tests/trajectory/test_multipers_validation.py`

### Exploratory computation (2026-04-02)

- **Development-scale bifiltration:** 2,000 maxmin landmarks from P01 checkpoint (27,280 × 20D)
  - Bifiltration: 215,958 simplices in ~3s; Rips radius 11.13 (10th percentile auto-tuned)
  - Income score: proportion-weighted mean of per-wave income bands (L=0, M=1, H=2); mean=1.02, median=1.00

- **Discretisation decision: QUANTILE grid** (primary), fixed as robustness check.
  - Quantile grid: H0 nearly balanced (low_frac=0.512); fixed grid biases toward high income (low_frac=0.454)
  - Resolution stability: quantile grid H1 low-fraction converges to ~0.33 by resolution 10 (range [0.329, 0.444]);
    fixed grid more volatile (range [0.263, 0.507])
  - Quartile-level H1 mass is robust across strategies: Q1≈20k, Q2≈35k, Q3≈79k, Q4≈77k
  - For AoAS: quantile as primary analysis; fixed grid in sensitivity appendix
  - Script: `trajectory_tda/scripts/p04_explore_discretisation.py`
  - Results: `results/p04_exploration/discretisation_exploration.json`
  - Figures: `figures/trajectory_tda/p04_exploration/`

- **Invariant decision: H1 signed measure with quartile decomposition** (primary).
  - H1 mass shows strong income gradient: Q3/Q4 carry ~4× the mass of Q1
  - Interpretation: topological cycles (diverse trajectory connectivity) concentrate among mid-to-high income individuals
  - Poverty trap signal: *absence* of H1 at low income — low-income trajectories form simpler, more linear structures
  - Euler surface (H0 − H1) adds no information: all negative, same gradient as H1
  - For AoAS: H1 signed measure heatmap as primary figure; quartile bar chart as secondary;
    Euler surface mentioned as robustness check
  - Signed measure heatmap is the most visually compelling visualisation — strong (ε, τ) gradient visible
  - **Key finding to test with permutation nulls:** H1 low-income fraction ~0.33 vs 0.50 expected under null

### Permutation null testing (2026-04-02)

- **999 income-label shuffle permutations** completed (24 min, 8-core i7 parallelised).
- **H1 low-income fraction:** observed = 0.329, null mean = 0.265, **p < 0.001** (two-sided).
- **Q1/Q3 mass ratio:** observed = 0.258, null mean = 0.161, **p < 0.001** (two-sided).
- **Direction:** Observed low-income fraction *higher* than null mean — real income labels moderate asymmetry.
  Low-income trajectories contribute more H1 complexity than random assignment predicts.
- **P01 baseline:** H1 density nearly identical across income subsets (0.95 low vs 0.88 high per point).
  Single-parameter PH cannot see the income stratification.
- **GMM regime overlay:** R6 (n=99, mean_income=0.47, 88.9% low-income) = poverty trap cluster.
  R5 (n=16, mean_income=1.55, 6.2% low-income) = high-income cluster.
- **v3 framing correction:** Topological simplicity at low income IS the poverty trap signal.
  H1 cycles concentrate at high income (73.7% at Q3/Q4). Poverty traps = constrained pathways.
- Module: `trajectory_tda/topology/multipers_bifiltration.py`
- Runner: `trajectory_tda/scripts/p04_run_nulls.py`
- Results: `results/p04_multipers/p04_results.json`
- Figures: `figures/trajectory_tda/p04/`

### Legacy v1 draft

Archived to `archive/morse-smale-imd/`. Pre-programme Morse-Smale/TTK paper on IMD geographic data — IMD 7D lacks dimensionality for meaningful higher-order topology. May be revisited for a standalone poverty_tda paper outside the 10-paper programme.

## Key Contribution

Single-parameter VR persistent homology (P01) captures global topological structure of UK employment trajectory space but cannot distinguish features at specific income levels. Bi-filtration on pairwise distance × income threshold reveals **income-stratified topological structure**: H1 cycles concentrate overwhelmingly at mid-to-high income (Q3/Q4 carry ~74% of mass), with low-income trajectory space being topologically simpler (Q1 carries ~10%). This **topological simplicity** at low income formalises a poverty trap: constrained career pathways produce fewer loops and less cyclical connectivity. Permutation null testing (999 income-label shuffles, $p < 0.001$) confirms the finding is not a geometric artefact, and that real income labels increase low-income H1 mass by ~24% relative to random assignment.

## Research Questions

1. Does the bifiltration (distance × income) reveal topological features absent from single-parameter PH?
2. Do income-stratified persistence features at low thresholds correspond to known poverty trap regimes (from P01's GMM typology)?
3. Is the multi-parameter topological signal robust to permutation of income labels?
4. Does the rank invariant distinguish liberal welfare-state trajectory spaces from other structures — a preview of P05's cross-national question?

## Computational Requirements

- **Local (i7/32GB/RTX 3080):** Feasible for development on 2,000–5,000 landmarks with moderate income discretisation (~10–20 thresholds)
- **Cloud (A100, 4–8 GPU-hrs):** Full-scale bifiltration (8,000+ landmarks × fine income discretisation, 50+ thresholds)
- `multipers` PyTorch-autodiff components can use RTX 3080 (10GB VRAM) locally

## Dependencies

- **P01 complete** — embedding pipeline (n-gram PCA) + baseline single-parameter PH results
- `multipers` library installed and validated against known bifiltration examples
- Mean trajectory income computed per individual (already available from BHPS/USoc data pipeline)

## Computational Milestones

1. Install and validate `multipers` library on toy bifiltration examples
2. Construct bifiltration input: P01 embedding + per-person mean income as second parameter
3. Compute multi-parameter PH on landmark subsets (2,000 points) — local
4. Develop income-stratified topology visualisations (Hilbert function heatmaps, rank invariant)
5. Run permutation null tests (income label shuffles)
6. Scale to 5,000 landmarks — local stress test
7. Full-scale computation (8,000+ landmarks) — cloud if local times are prohibitive
8. Write results sections with comparison to P01 single-parameter baseline

## Open Items

- [ ] Run the income-proxy endogeneity regression of the income proxy on PC1-PC20
  and report $R^2$
- [ ] Reframe the draft and submission materials for AoAS (IMS class,
  separate supplement, reproducibility statement)

- [x] Verify P01 embedding pipeline produces stable output for P04 consumption
- [x] Install `multipers` and run tutorial / validation on synthetic bifiltration
- [x] Archive legacy Morse-Smale draft
- [x] Decide income discretisation strategy (uniform quantiles vs fixed thresholds)
- [x] Determine which `multipers` invariant is most interpretable for social science audience
- [x] Run development-scale bifiltration (2,000 landmarks) on real data
- [x] Create `trajectory_tda/topology/multipers_bifiltration.py` module
- [x] Extract per-person mean income from BHPS/USoc and align with P01 embedding rows
- [x] Implement income-label permutation null tests (999 perms, p < 0.001)
- [x] P01 single-parameter baseline comparison (H1 density indistinguishable across income subsets)
- [x] GMM regime overlay (R6 = poverty trap cluster, 88.9% low-income)
- [x] Write v3 draft with corrected framing (topological simplicity as poverty trap signal)
- [x] Compute Hilbert function heatmaps (Appendix B.1) — 10×10 and 20×20, resolution-stable
- [x] Compute rank invariant (Appendix B.2) — 100% persistence to infinity, no income-confined features
- [x] Write v4 draft integrating Appendix B results
- [x] LaTeX pipeline (main.tex + body.tex, 23 pages, 7 figures)
- [ ] Scale to 5,000 landmarks
- [ ] Run `/humanizer` before submission
