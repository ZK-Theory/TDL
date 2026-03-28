# P03 Implementation Plan — March 2026

## Current State Assessment

### What Exists

**Code infrastructure (complete):**
- `trajectory_tda/topology/zigzag.py` — full zigzag module: `AnnualSnapshot`, `ZigzagResult`, `create_annual_snapshots()`, `run_gudhi_zigzag()`, diamond construction, WSL bridge
- `trajectory_tda/scripts/run_zigzag.py` — 4-stage pipeline orchestrator (annual partition → VR PH per year → topological time series → full zigzag)
- `trajectory_tda/scripts/zigzag_dionysus_bridge.py` — dionysus 2 bridge via WSL
- `trajectory_tda/data/annual_partition.py` — annual partitioning of frozen PCA embeddings
- `tests/trajectory/test_zigzag.py` — unit tests for snapshot and zigzag classes

**Computed results (in `results/trajectory_tda_zigzag/`):**

| Stage | File | Content |
|---|---|---|
| 1 | `01_annual_counts.json` | 32 years (1991–2022), 4,729–28,632 individuals/year |
| 2 | `02_annual_diagrams.json` | Independent VR PH per year (500 landmarks) |
| 3 | `03_time_series.json` | β₀, total persistence H₀/H₁ time series |
| 4 | `04_zigzag_diagrams.json` | Full zigzag: 4 H₀ bars, 186,564 H₁ bars (150 landmarks) |

**Second run (`results/trajectory_tda_zigzag_h1/`):** 68 H₀ bars, 263 H₁ bars (75 landmarks).

**Paper materials:** `_project.md` with metadata; empty `drafts/`, empty `notes/`.

### Key Findings in Existing Results

**Zigzag H₀ (connected components) — 4 bars at 150 landmarks:**
1. **1991–2022.5 (31.5y)** — dominant connected component spanning entire panel
2. **1991–2003.0 (12.0y)** — secondary cluster persisting through pre-USoc era, merging ~2003
3. **1991–1996.5 (5.5y)** — early-1990s cluster (ERM recession period), dies mid-decade
4. **2008.5–2022.5 (14.0y)** — **new cluster born at GFC**, persists through austerity and pandemic

This is the central finding: the GFC created a structurally distinct trajectory cluster that had no pre-2008 analogue. The early-1990s recession produced a short-lived fragment; the GFC produced a durable one.

**Independent annual β₀ series:** Remarkably flat (234–274 at 500 landmarks, threshold 0.05). No clear recession signature in pointwise Betti numbers — the structural change is only visible through cross-year zigzag tracking, not per-year snapshots.

**Total persistence H₀:** Upward trend (61.9 in 1991 → 79.1 in 2010), but confounded with the 5× BHPS-to-USoc sample size jump at 2009.

### Critical Issues Requiring Resolution

1. **Sample size discontinuity (BHPS→USoc):** 9,587 individuals in 2008 → 27,175 in 2009. This 3× jump will produce topological artefacts. Must be addressed either by (a) capping individuals per year to a common max, (b) using the same landmark count (already done — 500 per year for snapshots, 150 total for zigzag), or (c) running BHPS and USoc eras separately and comparing. The landmark subsampling partially mitigates this, but needs explicit discussion.

2. **Landmark sensitivity (zigzag):** The two zigzag runs produce radically different bar counts:
   - 150 landmarks → 4 H₀ bars, 186,564 H₁ bars
   - 75 landmarks → 68 H₀ bars, 263 H₁ bars
   
   This is a major concern. The 186,564 H₁ bars at 150 landmarks are almost certainly dominated by noise. The 4-bar vs 68-bar difference in H₀ suggests the topological resolution is highly parameter-dependent. Need systematic sensitivity analysis at multiple landmark counts (50, 100, 150, 200, 300) and explicit characterisation of which features are stable.

3. **No null model yet:** The paper's credibility depends on showing that zigzag features align with economic events non-randomly. Two null models needed:
   - **Year-shuffle null:** Permute the mapping from year labels to point clouds; re-run zigzag. Tests whether the alignment of bar births/deaths with recession dates is coincidental.
   - **Markov null (from P01):** Generate trajectory clouds from the fitted Markov-1 chain, partition by year, run zigzag. Tests whether Markov dynamics reproduce the zigzag structure.

4. **No Wasserstein analysis between annual diagrams:** P01 established Wasserstein as the superior test statistic. Pairwise Wasserstein distances between annual PDs would give a "topological dissimilarity matrix" over time — directly testable against macroeconomic similarity.

5. **No link to macroeconomic indicators:** The qualitative alignment with the GFC is suggestive but needs quantitative testing against GDP growth rate, unemployment rate, Gini coefficient. Rank correlation between topological time series and economic indicators.

---

## Implementation Plan

### Phase 1: Computation Resolution (Code + Computation)

**1.1 Landmark sensitivity analysis for zigzag** — HIGH PRIORITY
- Run `run_zigzag.py --skip-stages 1 2 3` at landmark counts: 75, 100, 150, 200, 300
- For each: record n_H₀_bars, n_H₁_bars, and bar birth/death years
- Identify which H₀ features are stable across ≥3 landmark settings
- Expected output: sensitivity table showing convergence behaviour
- File: `trajectory_tda/scripts/run_zigzag_sensitivity.py` (new)
- Result: `results/trajectory_tda_zigzag/sensitivity/`

**1.2 Sample-size normalisation strategy**
- Compute zigzag separately for BHPS era (1991–2008) and USoc era (2009–2022)
- Also compute the combined run with fixed per-year landmark caps at 200, 500
- Compare whether the GFC H₀ bar survives when the sample transition is removed
- This is the most important robustness check: a reviewer will immediately spot the 3× jump

**1.3 Wasserstein distance matrix between annual diagrams**
- Use `gudhi.wasserstein.wasserstein_distance()` on the 32 × 32 annual diagram pairs
- Compute for both H₀ and H₁ separately
- Output: 32 × 32 symmetric distance matrices
- File: `trajectory_tda/analysis/annual_wasserstein.py` (new)
- Result: `results/trajectory_tda_zigzag/annual_wasserstein_h0.npy`, `..._h1.npy`

**1.4 Year-shuffle null model for zigzag**
- Permute year labels n=100 times; for each: re-run zigzag stage 4
- Test statistic: number of H₀ bars with lifetime > 5 years that have birth/death aligning with recession dates (within ±1 year)
- Also: total H₀ bar count, max bar lifetime, median bar lifetime
- File: `trajectory_tda/validation/zigzag_null_tests.py` (new)
- Result: `results/trajectory_tda_zigzag/null_year_shuffle/`
- **Note:** Each zigzag run takes minutes-to-hours. 100 permutations may require batching overnight.

**1.5 Markov-1 null for zigzag (optional — depends on reviewer expectations)**
- Generate 100 synthetic panels from fitted Markov-1 transition matrix (from P01)
- Embed each synthetic panel identically (n-gram + frozen PCA)
- Partition by year; run zigzag
- Tests whether Markov dynamics reproduce the observed zigzag structure
- Computationally expensive — only if Phase 1.4 results are strong

### Phase 2: Analysis (Code + Computation)

**2.1 Macroeconomic correlation**
- Obtain UK GDP growth, unemployment rate, Gini coefficient annual series 1991–2022 (ONS)
- Compute Spearman rank correlation between topological time series (β₀, total persistence H₀, Wasserstein to baseline year) and each economic indicator
- Use bootstrap confidence intervals (n=1000) because time series are short (n=32)
- Also: cross-correlation at lags 0, ±1, ±2 years to test whether topology leads/lags economics
- File: `trajectory_tda/analysis/macro_correlation.py` (new)
- Result: `results/trajectory_tda_zigzag/macro_correlations.json`

**2.2 Era-specific zigzag interpretation**
- BHPS era (1991–2008): Does the 1993 recession cluster replicate?
- USoc era (2009–2022): Does the GFC cluster persist when the BHPS transition is removed?
- Combined era: Are the cross-survey features artifacts of the sample merge?

**2.3 H₁ filtering and interpretation**
- The 186,564 H₁ bars at 150 landmarks need triage:
  - Apply persistence threshold (drop bars below 2× median lifetime)
  - Report only long-lived H₁ features (>5 years)
  - Characterise: do any H₁ features align with specific economic episodes?
- The 75-landmark run's 263 H₁ bars are more tractable — analyse these for interpretability

**2.4 Annual snapshot comparison with Wasserstein**
- Using the 32×32 Wasserstein distance matrix:
  - MDS/UMAP embedding of the distance matrix → 2D "topological trajectory of the UK labour market"
  - Identify clusters of topologically similar years
  - Test whether recession years cluster together in topological space

### Phase 3: Paper Draft (Writing)

**3.1 Structure** (following P01 conventions)

1. **Abstract** — Lead with: zigzag persistence on 32 years of UK panel data reveals that the 2008 financial crisis created a structurally distinct trajectory cluster with no pre-crisis analogue, while the 1993 recession produced only a transient fragment. Per-year independent PH cannot detect this; only cross-year tracking does.

2. **Introduction**
   - 1.1 Motivation: Economic crises and structural change in labour markets
   - 1.2 Research gap: Existing TDA for time series uses sliding windows on single subjects; no application of zigzag to population-level panel snapshots across decades
   - 1.3 Contribution: (a) first application of zigzag PH to longitudinal social science data; (b) topological signatures of economic recessions; (c) formal null model testing of zigzag features
   - Roadmap sentence

3. **Literature Review**
   - 2.1 Business cycles and labour market dynamics (economics/sociology)
   - 2.2 Time-varying topology: zigzag PH foundations (Carlsson & de Silva 2010)
   - 2.3 TDA in time-series analysis (Gidea & Katz for financial; Myers et al. for sliding-window PH; Perea & Harer for SW1PerS)
   - 2.4 Connection to P01 — this paper tracks how the topology P01 characterised *changes over time*

4. **Data and Methods**
   - 3.1 Data: BHPS (1991–2008) + USoc (2009–2023), combined panel, 9-state employment-income space
   - 3.2 Embedding: frozen PCA loadings from P01's full-sample fit; annual partitioning
   - 3.3 Independent annual VR PH: Ripser with maxmin landmarks per year
   - 3.4 Diamond zigzag construction: formal definition of the tower P₁ ↪ P₁∪P₂ ↩ P₂ ↪ ...
   - 3.5 Dionysus 2 implementation details
   - 3.6 Topological time series: β₀, total persistence, Wasserstein from a baseline year
   - 3.7 Null model: year-shuffle permutation test
   - 3.8 Macroeconomic correlation methodology

5. **Results**
   - 4.1 Annual snapshot descriptives: sample sizes, individual counts, coverage
   - 4.2 Independent annual PH: β₀ and total persistence time series → flat β₀, trending total persistence
   - 4.3 Full zigzag H₀: the four-bar result; birth of the GFC cluster; death of the 1993 fragment
   - 4.4 Zigzag H₁: filtering and interpretation of long-lived loops
   - 4.5 Landmark sensitivity: convergence analysis
   - 4.6 Null model results: year-shuffle p-values
   - 4.7 Wasserstein distance matrix: topological dissimilarity across years
   - 4.8 Macroeconomic correlation: Spearman ρ, cross-correlations
   - 4.9 Era-specific robustness (BHPS-only, USoc-only)

6. **Discussion**
   - 5.1 What zigzag adds over independent PH: the GFC cluster is invisible in per-year β₀
   - 5.2 Asymmetric recession signatures: 1993 transient vs 2008 durable
   - 5.3 Methodological contribution: zigzag PH for panel data
   - 5.4 Limitations: landmark sensitivity, BHPS/USoc merge, missing 2023 data, confounds with survey design changes
   - 5.5 Connections to P01, P02, and implications for P04–P06

7. **Conclusion**

8. **References**

**3.2 Figures plan**

| Figure | Content | Data source |
|---|---|---|
| 1 | Zigzag tower construction (schematic) | Diagram |
| 2 | Annual β₀ and total persistence H₀ time series with recession bands | `03_time_series.json` |
| 3 | Zigzag H₀ barcode with year annotation | `04_zigzag_diagrams.json` |
| 4 | Zigzag H₁ barcode (filtered, long-lived features) | `04_zigzag_diagrams.json` |
| 5 | Landmark sensitivity: H₀ bar count vs landmark count | Sensitivity analysis |
| 6 | Wasserstein distance heatmap between annual diagrams | `annual_wasserstein_h0.npy` |
| 7 | MDS of Wasserstein distance matrix coloured by economic regime | Wasserstein matrix |
| 8 | Year-shuffle null distribution with observed test statistic | Null model results |
| 9 | Era-specific zigzag barcodes (BHPS-only, USoc-only) | Robustness runs |

### Phase 4: Review Preparation

- Run `/humanizer` on completed draft
- Cross-check all statistics against computation outputs
- Verify all figures reproduce from saved results
- Internal consistency check: every claim in the abstract must be supported by a numbered result in §4

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| GFC cluster is a sample-size artefact | HIGH | Era-specific runs (Phase 1.2) will determine this |
| Zigzag is too landmark-sensitive for robust claims | HIGH | Sensitivity analysis (Phase 1.1) — if no stable features, pivot paper framing to methodological comparison |
| Year-shuffle nulls fail (topology doesn't align with recession dates non-randomly) | MEDIUM | Paper can still frame as an exploratory methodological contribution |
| 100 zigzag permutations too expensive | LOW | Start with 50; report as preliminary |
| H₁ interpretation unclear (186K bars at 150 landmarks) | MEDIUM | Focus on 75-landmark run for interpretable H₁; discuss noise amplification as methodological finding |

## Estimated Timeline

| Phase | Tasks | Blocking? |
|---|---|---|
| 1.1–1.2 | Sensitivity + era-specific runs | Blocks Phase 3 |
| 1.3 | Wasserstein matrix | Independent |
| 1.4 | Year-shuffle null | Blocks Phase 3 §4.6 |
| 2.1 | Macro correlations | Blocks Phase 3 §4.8 |
| 2.2–2.4 | Analysis | Blocks Phase 3 |
| 3 | First draft | Depends on all above |
| 4 | Review preparation | Depends on Phase 3 |

## Reviewer Anticipation

A senior SMR reviewer will likely probe:

1. **"How do you know the GFC cluster isn't an artefact of the BHPS–USoc merge?"** → Phase 1.2 (era-specific runs) is the direct answer. If the GFC cluster appears in USoc-only zigzag, it's not a merge artefact.

2. **"Your β₀ time series is flat — where's the recession signal?"** → That's the point: per-year snapshots (independent PH) miss the structural change that zigzag detects. This contrast is a finding, not a limitation. Frame carefully.

3. **"186,564 H₁ bars — what's the signal-to-noise ratio?"** → Acknowledge this is noise-dominated at 150 landmarks. Report the 75-landmark run for interpretable H₁. Discuss persistence thresholds and the role of landmark counts in filtering.

4. **"What's the null model? How do you know recession alignment isn't coincidence?"** → Phase 1.4 year-shuffle provides the formal test.

5. **"Zigzag is sensitive to landmarks — how robust are your claims?"** → Phase 1.1 sensitivity table. If the 4-bar structure at 150 landmarks is fragile, the paper must be honest about this and frame this as a methodological finding about resolution/stability tradeoffs.

6. **"What does this add over simply plotting unemployment rates?"** → The topological analysis detects *structural* changes (clusters forming/dying) rather than *level* changes. A new cluster born at the GFC means the space of possible trajectories restructured, not just that more people became unemployed. This is a qualitatively different claim.

7. **"How does this connect to P01?"** → P01 characterises topology at a fixed point in time. P03 tracks how that topology evolves. The Markov memory ladder from P01 is the generative framework; P03 asks whether the topology P01 found is stable or whether economic shocks create and destroy topological features.
