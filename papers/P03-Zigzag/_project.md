---
paper: P03
title: "Topological Business Cycles? Zigzag Persistence, Survey Design, and Labour Market Fragmentation in the UK, 1991–2022"
status: archived
target-journal: "Sociological Methods & Research"
submitted: null
deadline: 2026-12-01
priority: medium
stage: 1
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, zigzag, business-cycle, time-series-topology]
---

## Status

Archived on 2026-04-07. Content absorbed into `papers/P01-B-JRSSB/`. The v2
draft, figures, and LaTeX sources remain as the historical source record for the
survey-design diagnostic toolkit and zigzag motivation now feeding the JRSS-B
paper.

Zigzag computation complete; paper v2 drafted and humanized; LaTeX package builds
cleanly to 29 pages. Key finding: dominant post-2008 topological discontinuity is a
BHPS→USoc survey-design artefact, not a GFC signature. Genuine secular flexibilisation
trend identified within BHPS era (1991–2008). All figures produced. Peer review prep next.

## Target

Primary: *Sociological Methods & Research*
Fallback: *Journal of Computational Social Science*

## Key Contribution

Tracks how UK trajectory-space topology changes across annual cohort snapshots (1991–2023), capturing topological signatures of recession (1993, 2008), austerity (2010–2015), and pandemic (2020). Tests whether H₀ increases (fragmentation) during recessions and H₁ appears during recovery.

## Open Items

- [x] Archive standalone submission plan — superseded by P01-B (JRSS-B)

- [x] Zigzag computation complete (4-stage pipeline, 150 landmarks, 32 years)
- [x] Annual snapshot data pipeline verified (1991–2022, `results/trajectory_tda_zigzag/`)
- [x] Review P03 agent output from run/p03-zigzag
- [x] Data-driven ε selection via per-year β₀ knee analysis
- [x] 2D sensitivity grid (ε × L) — 11 × 4 = 44 cells
- [x] Era-specific robustness runs (BHPS-only, USoc-only) — completed with sub-sampling
- [x] Post-2008 deep dive (Betti curves, entropy, spanning-individual decomposition)
- [x] Wasserstein distance matrix between 32 annual diagrams
- [x] Year-shuffle null model (label permutation + pool-draw)
- [x] Macroeconomic correlation analysis (GDP, unemployment, Gini)
- [x] First draft (`papers/P03-Zigzag/drafts/v1-2026-03.md`) — naïve framing, pre-decomposition
- [x] Second draft (`papers/P03-Zigzag/drafts/v2-2026-03.md`) — corrected narrative: survey design + flexibilisation
- [x] Humanizer pass before submission — completed March 2026
- [x] Figure production (6 figures) — `papers/P03-Zigzag/figures/fig{1-6}_*.pdf`
- [x] LaTeX conversion — `papers/P03-Zigzag/latex/` (29 pages, builds clean with pdflatex+bibtex)

## Current Results Summary

### Per-year β₀ knee analysis

Computed β₀(ε) from 32 independent per-year VR diagrams (300 landmarks each).
The knee (max curvature in β₀ descent) identifies the natural clustering scale:

- **Median knee ε = 0.54** (Q25=0.46, Q75=0.63)
- BHPS era (1991–2008): median knee ε = 0.50
- USoc era (2009–2022): median knee ε = 0.65
- Maximum H₀ death across years: median 0.88, max 0.99
- Minimum CV of H₀ across landmark counts: ε = 0.49 (CV = 0.090)

Results: `results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json`

### 2D sensitivity grid (ε × L)

Full grid of H₀ zigzag bars across 11 ε × 4 landmark counts:

```
ε\L       75    100    150    200
0.34     632    829   1134   1357  ← far below knee (noise)
0.44     483    626    732    783
0.49     416    490    528    519  ← minimum CV across L
0.54     329    357    310    275  ← per-year knee
0.59     246    219    161    131
0.64     149    124     81     63
0.70      68     51     35     26  ← (original H1 run)
0.74      47     33     24     22
0.80      25     19     17     16
0.90      11      9      8      8
1.00       5      4      4      4  ← (original main run)
```

**Key patterns:**
- Below knee: H₀ increases with L (noise-dominated)
- At knee (ε ≈ 0.49–0.54): H₀ nearly constant across L (maximally resolution-stable)
- Above knee: H₀ decreases with L (signal-dominated)
- The crossover from noise→signal regimes confirms the per-year knee

### Stable features at ε = 1.0 (identical at L=100, 150, 200)

1. **Full-span component** (1991→2022.5, 31.5 yr) — main connectivity
2. **USoc-era component** (2008.5→2022.5, 14.0 yr) — GFC/survey transition
3. **Early-BHPS component** (1991→2003, 12.0 yr) — pre-2000s cluster
4. **ERM-era fragment** (1991→1996.5, 5.5 yr) — early 90s recession

### 2008 boundary is the dominant topological feature

At every (ε, L) in the grid, features cluster around 2008±1.
This coincides with both the GFC and the BHPS→USoc survey transition.
Paper must carefully adjudicate between these two explanations.

- **Critical concern (resolved):** Original 75 vs 150 landmark discrepancy (68 vs 4 H₀) was ε effect (0.7 vs 1.0), not landmark sensitivity. The 2D grid shows clean monotonic decline with ε at all L.

### Era-specific robustness (BHPS-only vs USoc-only)

Ran zigzag separately on each survey era to adjudicate whether the full-panel 2008.5 feature is GFC or survey-transition artefact. Mini-grid: 5 ε × 2 L for BHPS (10 cells), 4 ε × 2 L for USoc (8 cells).

**Era-specific zigzag results at ε=1.0, L=150:**

```
                           H₀ bars  All full-span?
BHPS-only (1991-2008):     3        Yes (all 1991→2008.5)
USoc-only (2009-2022):     4        Yes (all 2009→2022.5)
Full panel (1991-2022):    4        No  (deaths at 1996.5, 2003, 2008.5)
```

**Key finding: No within-era merger events.** All era-specific bars are full-span — clusters never merge within their era. The full-panel's temporal features (bars dying at 1996.5, 2003; born at 2008.5) arise from cross-era interactions when spanning respondents bridge BHPS and USoc clusters.

**Sub-sampling test (USoc capped at n=9,500 to match BHPS):**

```
                             ε=1.0 H₀ bars    ε=0.70 H₀ bars
BHPS-only (n~9.5k):         3 (stable)        10
USoc full (n~27k):           4 (stable)        17
USoc sub-sampled (n=9.5k):   2.2 ± 0.7        24.8 ± 2.6
```

- At ε=1.0: The 4th USoc component is **sample-size-dependent** — disappears at matched n (mean 2.2, range 1–3)
- At ε=0.70: Sub-sampled USoc has **more** components than either full sample (sparser MaxMin landmarks)
- Per-year VR β₀ at matched n: USoc-sub = 8.5 vs BHPS = 6.1 (p=0.0035) — **genuine fine-scale difference**

**Paper implications:**
1. Post-2008 trajectory space is genuinely more topologically complex at fine scales (near the manifold knee), independent of sample size
2. Coarse-scale (ε=1.0) component counts are landmark- and sample-size-sensitive — not robust topological invariants
3. The specific death years (1996.5, 2003) in the full-panel zigzag are cross-era effects, not datable economic events
4. The paper should claim increased fine-scale fragmentation, not specific-year structural breaks

Results: `results/trajectory_tda_zigzag/era_robustness/`

### Post-2008 deep dive (3-angle analysis)

Three complementary analyses to probe the source of post-2008 complexity.

**Analysis 1 — Sub-sampled Betti curves (n=8000, 15 reps/year):**
- AUC(β₀, ε=0.3–0.8): gradual BHPS-era rise (8.95→11.49), then step up at 2009 (→14.82) and plateau
- Pre-GFC (2005–07) AUC ~11.2 vs post-GFC (2009–12) AUC ~15.4; persists at matched n
- No GFC as temporary shock — the shift is permanent

**Analysis 2 — Persistence entropy + total persistence time series:**
- Total persistence H₀: BHPS trend +0.31/yr (p<0.0001), USoc flat −0.05/yr (p=0.49); step +3.21 at 2008–2009
- Entropy H₀ **drops** at 2009 (5.47→5.40, p<0.0001): more uneven lifetime distribution in USoc
- CUSUM changepoint: entropy at 2008, total persistence at 2006
- H₁ (loops): gradual increase, **not** discontinuous at GFC (pre-vs-post p=0.28)

**Analysis 3 — Spanning-individual embedding shift (key finding):**
- Spanning individuals (n=8,459 in both eras): embedding position stable (4.6% "outside" BHPS manifold vs 5% baseline)
- USoc-only newcomers (n=21,551): 11.9% "outside" BHPS manifold (Mann-Whitney p<10⁻⁶); PCs 1–4 significantly shifted
- **Critical decomposition:**
  - Spanning-only β₀(0.70) in 2009–2015: ~5.7 (matches BHPS reference ~6.0)
  - USoc-only β₀(0.70) in 2009–2015: ~9.5 (50% more complex)
  - Combined: ~8.1
- State composition: USoc-only has more Employed-Low (5.6% vs 3.4%), more Inactive-High (12.5% vs 8.5%)

**Verdict:** The post-2008 complexity shift is **survey coverage**, not GFC economic shock. Spanning individuals maintain BHPS-like topology; the 21k USoc newcomers occupy previously unsampled regions of embedding space. A gradual secular trend in total persistence during BHPS (changepoint ~2006) suggests labour market diversification was already underway.

**Paper framing:** "The post-2008 increase in topological complexity is driven primarily by USoc's expanded sampling frame capturing career trajectories absent from BHPS. Spanning individuals maintain stable topology across the survey transition, while a gradual secular increase in trajectory diversity within BHPS alone (1991–2008) is consistent with broader labour market flexibilisation."

Results: `results/trajectory_tda_zigzag/gfc_deepdive/`

### Wasserstein distance matrix (32 × 32 annual diagrams)

Two versions: full-sample (300 landmarks) and sub-sampled (n=8000, L=300, 10 reps).

**Block structure (sub-sampled W₂, H₀):**

| Block | Mean W₂ | Std |
|---|---|---|
| BHPS–BHPS (within) | 0.486 | 0.042 |
| BHPS–USoc (cross) | 0.752 | 0.105 |
| USoc–USoc (within) | 0.466 | 0.033 |

Cross-era distances are 1.5–1.6× within-era distances — clean two-block structure.

**Hierarchical clustering (Ward's):**
- k=2 perfectly separates BHPS (1991–2008) vs USoc (2009–2022) — no year misclassified
- k=3 splits BHPS into early (1991–92, 94–96, 99, 2001) vs late (1993, 97–98, 2000, 02–08)
- k=4 splits USoc into early USoc (2009–10, 2022) vs core USoc (2011–2021)

**Mantel test (W₂ vs temporal distance):**
- Full panel: Pearson r=0.768 (p<10⁻⁶), Spearman ρ=0.760 (p<10⁻⁶)
- Within-BHPS: r=0.423 (p<10⁻⁶) — moderate temporal ordering
- Within-USoc: r=0.144 (p=0.17) — **no significant temporal ordering**
  => USoc-era diagrams are topologically homogeneous across 14 years

**Consecutive-year jumps:** 2008→2009 is the 4th largest (0.507), behind 1992→93 (0.546), 2005→06 (0.538), 1993→94 (0.515). Not an outlier — consistent with survey transition rather than economic shock.

**H₁ (loops):** Minimal block structure — cross-era W₂(H₁) only 13% above within-era. Loop topology is stable across the survey transition.

Results: `results/trajectory_tda_zigzag/wasserstein/`

### Year-shuffle null model

Three complementary null models testing significance of Wasserstein matrix structure.

**Part A — Label permutation (n=1000):** Permute year labels on observed W₂ matrix.

| Statistic | Observed | Null mean±sd | p |
|---|---|---|---|
| Block ratio (cross/within) | 1.581 | 1.001±0.025 | <0.001 |
| Cross-era mean W₂ | 0.752 | 0.618±0.007 | <0.001 |
| Within-BHPS mean | 0.486 | 0.617±0.014 | <0.001 |
| Within-USoc mean | 0.466 | 0.618±0.019 | <0.001 |
| Consecutive-year mean | 0.467 | 0.618±0.027 | <0.001 |
| Mantel r (W₂ vs |Δt|) | 0.768 | 0.001±0.048 | <0.001 |

All six statistics reject the null with p<0.001. The temporal ordering is highly significant.

**Part B — Pool-draw pairs (n=100):** Draw two random subsets of n=8000 from full pool, compute W₂.
- Random-pool W₂: 0.503±0.165 (range 0.20–1.08)
- High variance: single pairs of random diagrams are noisy
- Observed cross-era (0.752) exceeds 94% of random pairs (p=0.06)

**Part C — Full pool-draw with block stats (n=50, 32 diagrams each):**
- Block ratio: observed 1.581 vs null 1.007±0.095 (p<0.001)
- Cross-era W₂: observed 0.752 vs null 0.481±0.042 (p<0.001)
- Consecutive-year mean: observed 0.467 vs null 0.476±0.026 (p=0.34, ns)

**Interpretation:**
- The BHPS–USoc block separation is **highly significant** under both label and pool-draw nulls
- The Mantel correlation (r=0.768) is genuine — topology tracks time
- Consecutive-year smoothness is NOT significant vs random subsets (p=0.34) — adjacent years are not unusually similar, consistent with landmark-sampling noise dominating year-to-year variation
- The dominant signal is the **era-level** (BHPS vs USoc) block structure, not fine year-to-year evolution

Results: `results/trajectory_tda_zigzag/wasserstein/null_model_results.json`

### Macroeconomic correlations

7 UK macro indicators (1991–2022) × 6 topological summaries, four specifications: raw, within-era, detrended, first-difference. BH-FDR correction throughout.

**Raw correlations surviving BH-FDR (17/42):**

Strongest associations (all r > 0.5):

| Macro indicator | Topological measure | r | p |
|---|---|---|---|
| Self-employment share | AUC(β₀) | +0.872 | <0.0001 |
| Self-employment share | TotalPers(H₀) | +0.846 | <0.0001 |
| Self-employment share | Entropy(H₀) | −0.792 | <0.0001 |
| Gini | Entropy(H₀) | +0.740 | <0.0001 |
| Employment rate | TotalPers(H₀) | +0.698 | <0.0001 |
| Employment rate | AUC(β₀) | +0.638 | 0.0001 |
| Employment rate | TotalPers(H₁) | +0.591 | 0.0004 |
| Gini | AUC(β₀) | −0.590 | 0.0004 |
| Part-time share | TotalPers(H₀) | +0.559 | 0.0009 |

**Detrended (10/35 survive):** Part-time share × TotalPers(H₀) strongest (r=+0.755). Unemployment flips sign after detrending (raw r=−0.45 → detrended r=+0.69) — interpretable as cyclical: unemployment spikes coincide with more fine-scale fragmentation year-to-year.

**First-difference: None survive BH-FDR.** Year-on-year changes in macro do not predict year-on-year changes in topology — consistent with topology tracking slow structural shifts (employment composition) not business-cycle fluctuations.

**Within-era:**
- BHPS: Employment rate (r=+0.82***), unemployment (r=−0.81***), part-time share (r=+0.80***) all strong — genuine labour-market structure correlations within a single survey
- USoc: Self-employment (r=+0.71**), inflation (r=−0.64*) significant; otherwise flat — topological measures are more stable within USoc

**Lagged:** No significant lag structure for GDP growth. Unemployment shows marginally stronger correlation when topo leads (r=−0.44 at lag+3) but this is likely driven by the level shift, not causal dynamics.

**Key interpretation:** The strongest correlates of topological complexity are labour market **composition** variables (self-employment share, part-time share, employment rate) not macroeconomic **performance** variables (GDP growth, inflation). This aligns perfectly with the survey-coverage explanation: USoc's broader sample captures more atypical employment arrangements, not economic shocks. Within BHPS, the genuine macro correlations (unemployment, employment rate) reflect secular labour-market tightening driving the gradual pre-2008 trend.

Results: `results/trajectory_tda_zigzag/macro_correlations/`

## Implementation Plan

See `notes/implementation-plan-2026-03.md` for detailed 4-phase plan.

## Computation

See `run/p03-zigzag` branch.
Key dependencies: dionysus (zigzag), gudhi (VR PH per snapshot), WSL bridge.
Computational note: hours not minutes; streaming algorithm for RAM efficiency.
