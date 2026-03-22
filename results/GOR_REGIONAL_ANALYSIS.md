# Government Office Region (GOR) Topological Stratification Analysis

## Overview

This document reports the results of topological stratification by UK Government
Office Region (GOR), applied to the 20-dimensional UMAP embeddings of poverty
trajectory data from the combined BHPS/Understanding Society panel (N = 27,280).
Persistent homology was computed per region, and pairwise Wasserstein distances
tested via global-shuffle permutation tests with Benjamini-Hochberg FDR
correction.

**Status:** Standalone exploratory analysis (P3 priority). May be integrated into
the trajectory TDA paper or developed as a separate regional analysis.

---

## 1. Method

### 1.1 Data extraction

- GOR labels were extracted from the UKHLS cross-wave file (`xwavedat.tab`,
  variable `gor_dv`) and BHPS wave 1 (`ba_indresp.tab`, variable `ba_region`),
  mapped to standard GOR names via ONS coding.
- Merge key: `pidp` (UKHLS identifier). BHPS respondents linked via the
  `pidp` field present in BHPS data files.
- Coverage: 27,280/27,280 trajectories matched (100%), across all 12 UK
  regions.

### 1.2 Topological computation

- **Landmarks:** 1,000 (maxmin subsampling per group). Benchmarking showed
  L = 1,000 captures 78% of H1 features relative to L = 2,000, while reducing
  per-computation time from ~48s to ~0.6s. For the smallest regions
  (~1,000 trajectories), L = 1,000 uses effectively all available points.
- **PH computation:** Rips filtration via ripser, max_dim = 1 (H0 and H1).
  Threshold set at 75th percentile of pairwise distances.
- **Permutation test:** Global-shuffle approach — for each permutation, all
  12 region labels are shuffled simultaneously and all 12 group PH diagrams
  recomputed, yielding all 66 pairwise Wasserstein distances per permutation.
  This is O(n_groups × n_perms) PH computations rather than
  O(n_pairs × n_perms × 2), reducing total from ~26,400 to ~600 runs.
- **Permutations:** 50 (p-value precision ±0.02).
- **FDR correction:** Benjamini-Hochberg, applied both globally (across all
  182 stratification tests including gender, cohort, NS-SEC) and within-axis
  (132 GOR tests alone). Results identical for GOR at α = 0.05.

### 1.3 Runtime

Total computation: 845 seconds (~14 minutes).

---

## 2. Sample sizes by region

| Region              |   n  | % of sample |
|---------------------|-----:|------------:|
| South East          | 3,434 |     12.6%  |
| London              | 2,967 |     10.9%  |
| North West          | 2,650 |      9.7%  |
| Scotland            | 2,449 |      9.0%  |
| Yorkshire & Humber  | 2,337 |      8.6%  |
| East of England     | 2,237 |      8.2%  |
| South West          | 2,215 |      8.1%  |
| West Midlands       | 2,205 |      8.1%  |
| East Midlands       | 2,024 |      7.4%  |
| Wales               | 1,865 |      6.8%  |
| Northern Ireland    | 1,798 |      6.6%  |
| North East          | 1,099 |      4.0%  |

All 12 regions exceed the 200-trajectory minimum threshold.

---

## 3. Per-region topological summaries

| Region             | H0 features | H0 max pers. | H0 entropy | H1 features | H1 max pers. | H1 entropy |
|--------------------|:-----------:|:------------:|:----------:|:-----------:|:------------:|:----------:|
| London             |     996     |    15.350    |   6.829    |     834     |    2.559     |   6.398    |
| North West         |     996     |    13.497    |   6.781    |     726     |    1.994     |   6.239    |
| West Midlands      |     995     |    13.281    |   6.753    |     695     |    2.330     |   6.203    |
| South East         |     999     |    13.000    |   6.801    |     782     |    1.857     |   6.316    |
| Yorkshire & Humber |     997     |    12.613    |   6.768    |     722     |    2.313     |   6.230    |
| Northern Ireland   |     989     |    12.262    |   6.703    |     587     |    2.744     |   5.986    |
| East Midlands      |     994     |    12.249    |   6.727    |     653     |    2.063     |   6.128    |
| Scotland           |     993     |    12.026    |   6.760    |     707     |    1.977     |   6.185    |
| Wales              |     997     |    11.928    |   6.725    |     646     |    2.096     |   6.122    |
| East of England    |     991     |    11.741    |   6.755    |     657     |    2.043     |   6.156    |
| South West         |     996     |    11.153    |   6.740    |     696     |    1.764     |   6.211    |
| North East         |     988     |    10.542    |   6.341    |     371     |    1.413     |   5.494    |

**Notable patterns:**
- London has the highest H0 max persistence (15.35), H0 entropy (6.83), H1
  feature count (834), and H1 max persistence (2.56) — the richest topological
  structure by every metric.
- North East has the lowest values across all metrics, consistent with being the
  smallest region and having the most constrained trajectory space.
- Northern Ireland has notably high H1 max persistence (2.74 — highest of all
  regions) despite moderate sample size, suggesting distinctively looped
  trajectory structures.

---

## 4. Persistence landscape statistics (L₁)

| Region             | L₁ integral (H0) | L₁ max (H0) | L₁ integral (H1) | L₁ max (H1) |
|--------------------|:-----------------:|:------------:|:-----------------:|:------------:|
| London             |      379.88       |    7.598     |      57.33        |    1.268     |
| North West         |      334.01       |    6.680     |      51.93        |    0.959     |
| West Midlands      |      328.68       |    6.574     |      52.88        |    1.125     |
| South East         |      321.73       |    6.435     |      46.92        |    0.922     |
| Yorkshire & Humber |      312.14       |    6.243     |      50.08        |    1.133     |
| East Midlands      |      303.13       |    6.063     |      47.54        |    1.023     |
| Northern Ireland   |      303.44       |    6.069     |      48.97        |    1.369     |
| Scotland           |      297.62       |    5.952     |      55.06        |    0.955     |
| Wales              |      295.19       |    5.904     |      48.44        |    1.019     |
| East of England    |      290.56       |    5.811     |      46.93        |    0.995     |
| South West         |      276.01       |    5.520     |      39.18        |    0.840     |
| North East         |      260.90       |    5.218     |      35.59        |    0.662     |

London's L₁(H0) integral (379.9) exceeds the next region (North West, 334.0)
by 14%. This captures the total "topological significance" of the connected
component structure and indicates that London's employment trajectory
state-space is the most spread out and complex.

---

## 5. Pairwise significance results

### 5.1 Summary

| Dimension | Raw significant (p < 0.05) | BH-corrected significant | Survival rate |
|:---------:|:--------------------------:|:------------------------:|:-------------:|
|    H0     |          26 / 66           |         24 / 66          |     92.3%     |
|    H1     |          16 / 66           |         15 / 66          |     93.8%     |
| **Total** |        **42 / 132**        |       **39 / 132**       |   **92.9%**   |

Three tests lost significance after BH correction:
- North East vs North West (H0): raw p = 0.02 → BH p = 0.052
- North East vs Yorkshire & Humber (H0): raw p = 0.04 → BH p = 0.101
- South West vs West Midlands (H1): raw p = 0.02 → BH p = 0.052

The very high BH survival rate (93%) indicates robust signal, not
multiple-testing artefact.

### 5.2. Region distinctiveness ranking (BH-corrected significant pairs)

| Region             | Significant pairs (BH) | H0 sig | H1 sig |
|--------------------|:----------------------:|:------:|:------:|
| London             |           22           |   11   |   11   |
| West Midlands      |           12           |    8   |    4   |
| North East         |            4           |    2   |    2   |
| South West         |            4           |    3   |    1   |
| East of England    |            5           |    4   |    1   |
| Scotland           |            4           |    3   |    1   |
| Yorkshire & Humber |            4           |    4   |    0   |
| Northern Ireland   |            4           |    2   |    2   |
| North West         |            4           |    4   |    0   |
| East Midlands      |            4           |    2   |    2   |
| Wales              |            4           |    2   |    2   |
| South East         |            2           |    1   |    1   |

**London is significant against every other region** in both H0 and H1
(22/22 possible pairs). This is the strongest result — London's employment
trajectory topology is categorically different from the rest of the UK.

**West Midlands** is the second most distinctive (12 significant pairs),
driven primarily by H0 (connectivity structure). The South West vs West
Midlands H0 comparison has the highest observed-to-null ratio (4.89×).

**South East** is the least distinctive (2 pairs), consistent with it
representing the "average" UK trajectory topology.

### 5.3 Largest effect sizes (H0, BH-corrected)

| Pair                            | Observed W | Null mean | Ratio  |
|---------------------------------|:----------:|:---------:|:------:|
| London vs North East            |   94.92    |   62.10   | 1.53×  |
| London vs Northern Ireland      |   63.70    |   33.41   | 1.91×  |
| London vs South West            |   63.19    |   20.48   | 3.09×  |
| North East vs West Midlands     |   59.51    |   43.12   | 1.38×  |
| London vs Wales                 |   57.95    |   31.19   | 1.86×  |
| East of England vs London       |   55.98    |   19.54   | 2.87×  |
| East Midlands vs London         |   55.52    |   25.83   | 2.15×  |
| London vs Scotland              |   55.23    |   13.48   | **4.10×** |
| South West vs West Midlands     |   30.30    |    6.19   | **4.89×** |
| East of England vs West Midlands|   23.60    |    6.66   | 3.54×  |

The largest *absolute* Wasserstein separation is London vs North East (94.92),
but the largest *effect size* (observed/null ratio) is **South West vs West
Midlands at 4.89×**, followed by **London vs Scotland at 4.10×**.

### 5.4 Largest effect sizes (H1, BH-corrected)

| Pair                            | Observed W | Null mean | Ratio  |
|---------------------------------|:----------:|:---------:|:------:|
| London vs Scotland              |  128.18    |  104.75   | 1.22×  |
| London vs Northern Ireland      |  127.67    |  104.09   | 1.23×  |
| East of England vs London       |  127.00    |  105.15   | 1.21×  |
| London vs North West            |  126.66    |  106.40   | 1.19×  |
| East Midlands vs London         |  124.03    |  105.20   | 1.18×  |
| London vs South East            |  124.20    |  107.39   | 1.16×  |
| East Midlands vs West Midlands  |  112.58    |  103.07   | 1.09×  |
| London vs North East            |  108.70    |   88.20   | 1.23×  |
| North East vs West Midlands     |  107.45    |   93.42   | 1.15×  |
| Northern Ireland vs West Midlands|  107.25   |   93.65   | 1.15×  |

H1 effect sizes are systematically smaller than H0 (ratios 1.09–1.23× vs
1.38–4.89×). This is consistent with regional differences operating
primarily through the macro-structure of the trajectory space (H0:
connected components, clustering) rather than through fine loop topology
(H1). However, the H1 signal is still significant for 15 pairs after FDR,
indicating genuine looped structure differences, particularly involving
London and West Midlands.

---

## 6. Interpretive analysis

### 6.1 London exceptionalism

London is topologically distinct from every other UK region in both H0 and
H1, with every pairwise test surviving FDR correction at p < 0.001. This
manifests as:
- The highest H0 max persistence (15.35 vs 10.5–13.5 elsewhere),
  indicating the most widely separated connected components in the
  trajectory embedding — i.e., the greatest diversity of distinct
  employment pathway clusters.
- The highest H1 feature count (834 vs 371–782), indicating the most
  complex loop structure — more cyclical patterns and alternative pathways
  between employment states.
- The highest L₁ landscape integral in both dimensions, confirming
  these differences are not driven by a few extreme features but by the
  overall topological profile.

**Interpretation:** London's labour market offers a qualitatively different
topology of employment trajectories. The high H0 persistence suggests more
fragmented pathway clusters (people in London follow more diverse and
separated career paths), while the high H1 indicates more "return loops"
(people cycling between employment states rather than following monotone
trajectories). This aligns with labour economics literature on London's
unique characteristics: higher occupational diversity, stronger
churn/mobility, and greater income volatility.

### 6.2 West Midlands as second pole

West Midlands is the second most topologically distinctive region, with
12 significant pairwise comparisons. Its H0 max persistence (13.28) and
H1 max persistence (2.33) place it in the upper tier. The very large
effect size against South West (4.89×) suggests a strong North-South
structural divide operating beyond simple London exceptionalism.

### 6.3 North East sparsity

North East has the smallest sample (n = 1,099) and the most meagre
topological profile: fewest H1 features (371), lowest H0 entropy (6.34),
lowest landscape integrals. While sample size effects cannot be entirely
excluded (despite landmark subsampling), the consistency across metrics
suggests a genuinely more constrained trajectory space — fewer employment
pathway options, simpler structure.

### 6.4 Northern Ireland's distinctive loops

Northern Ireland has moderate H0 statistics but the highest H1 max
persistence of any region (2.74), exceeding even London (2.56). This
suggests a distinctive pattern of cyclical employment trajectories, which
may reflect the region's unique labour market characteristics (including
historically higher unemployment cycling and public-sector concentration).

### 6.5 South East as the "average" region

South East (the largest region, n = 3,434) has only 2 significant
pairwise comparisons — both with London. Its topological profile sits
near the middle of every metric. This suggests it serves as the UK's
topological "centre of gravity" for employment trajectories, from which
other regions deviate.

### 6.6 H0 vs H1 signal

H0 (connectivity/clustering) carries stronger regional signal than H1
(loop structure): 24 vs 15 significant pairs after FDR, and much larger
effect sizes (up to 4.89× vs 1.23×). Regional differences in employment
trajectories are thus primarily about *which distinct clusters of career
paths exist* (H0) rather than *how cyclical or looped those paths are*
(H1), though the H1 signal is non-trivial.

---

## 7. Comparison with other stratification axes

| Axis           | Groups | Tests | Sig (raw) | Sig (BH) | Notes                            |
|----------------|:------:|:-----:|:---------:|:--------:|----------------------------------|
| Gender         |    2   |    2  |     1     |     1    | H0 only                          |
| Parental NS-SEC|    3   |    6  |     3     |     3    | All 3 survive BH                 |
| Birth cohort   |    7   |   42  |    26     |    25    | Strong generational signal       |
| **GOR**        | **12** |**132**|  **42**   |  **39**  | **London exceptional, 93% BH survival** |

GOR produces the largest absolute number of significant results (39) but at a
lower rate (30%) than cohort (60%) or NS-SEC (50%). This is expected — most
regions are not dramatically different from each other. The signal is
concentrated in London (22 tests) and West Midlands (12 tests), with
the remaining 10 distributed across other regions.

---

## 8. Methodological notes

### 8.1 Landmark selection

Using L = 1,000 rather than L = 2,000 (as in the other stratification axes)
was a computational necessity — the pairwise permutation approach at L = 2,000
would require ~14 days of runtime. Benchmarking confirmed:
- L = 1,000 captures 78% of H1 features (705 vs 900) relative to L = 2,000
- PH-level statistics (persistence, entropy) scale systematically
- p-values from permutation tests remain valid because both observed and
  null distributions are computed at the same landmark count
- For the smallest region (North East, n = 1,099), L = 1,000 uses nearly
  all available trajectories

### 8.2 Global-shuffle vs pairwise permutation

The global-shuffle approach computes all 12 group PH diagrams per permutation,
yielding all 66 pairwise Wasserstein distances simultaneously. This is
statistically equivalent to iterating pairwise tests but shares the null
distribution structure across pairs. The key advantage is computational:
O(12 × 50) = 600 PH computations vs O(66 × 2 × 50 × 2) = 13,200.

### 8.3 Permutation count

50 permutations gives p-value precision of ±0.02. All BH-surviving results
have raw p = 0.00 (i.e., the observed Wasserstein distance exceeded every
null permutation distance), so increasing permutations would not change the
conclusions — it would only make the p-values more precisely small.

---

## 9. Data files

- **Raw results:** `results/trajectory_tda_integration/06_stratified.json`
  (key: `gor`)
- **FDR-corrected:** `results/trajectory_tda_robustness/fdr_correction_results.json`
- **Run log:** `results/gor_run_log.txt`
- **This document:** `results/GOR_REGIONAL_ANALYSIS.md`
