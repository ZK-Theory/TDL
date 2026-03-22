# Methodology Audit Results

**Date:** 2026-02-22
**Regions tested:** West Midlands (1638 LSOAs, 7 LADs), Greater Manchester (1636 LSOAs, 10 LADs)
**Script:** `poverty_tda/validation/diagnostic_overfitting.py`

---

## Executive Summary

**The headline results (MS η² = 73–95%) are not valid.** Two critical methodological failures were confirmed:

1. **The outcome variable is at LAD level**, giving only 7 (WM) or 10 (GM) unique values for ~1600 LSOAs. LAD labels alone achieve η² = 1.000. Any partition that detects LAD boundaries will get near-perfect η² trivially.

2. **K-means at matched cluster count matches MS performance.** At k=200 (matching MS basin count), K-means achieves η² = 0.812 (WM) and 0.756 (GM) — close to the reported MS values. The "2× advantage" over K-means was an artefact of comparing k=200 vs k≤14.

> [!CAUTION]
> The existing paper draft's headline claim — "Morse-Smale basins explain 73-83% of life expectancy variance, nearly 2× K-means" — cannot be supported. The η² metric is meaningless with LAD-level outcomes, and the comparison was unfair.

---

## Detailed Findings

### Test 1: Random Partition Baseline

A random partition into k=200 groups achieves η² ≈ 12.2% from pure noise, matching the theoretical expectation of (k-1)/(N-1).

| Region | k | Random mean η² | Theoretical E[η²] | 95th pctl |
|--------|---|----------------|-------------------|-----------|
| WM | 200 | 0.122 | 0.122 | 0.142 |
| GM | 200 | 0.121 | 0.122 | 0.138 |

**Implication:** Any method using 200 groups starts with a 12% "free" η² just from noise.

### Test 2: K-means at Matched k

η² scales monotonically with k. K-means at k=200 performs comparably to reported MS results.

| k | WM η² | WM ω² | GM η² | GM ω² |
|---|-------|-------|-------|-------|
| 5 | 0.247 | 0.245 | 0.208 | 0.206 |
| 10 | 0.455 | 0.452 | 0.328 | 0.324 |
| 15 | 0.482 | 0.478 | 0.427 | 0.422 |
| 20 | 0.505 | 0.499 | 0.404 | 0.397 |
| 50 | 0.631 | 0.619 | 0.580 | 0.567 |
| 100 | 0.712 | 0.693 | 0.663 | 0.642 |
| **200** | **0.812** | **0.786** | **0.756** | **0.722** |

**Implication:** Previously reported MS η²=0.834 (WM) / 0.736 (GM) is within range of K-means at matched k. No evidence of topological advantage beyond partition count.

### Test 3: Interpolation Sensitivity

**Not completed** — VTK/TTK not available in this Python environment. Still needs testing when VTK is available.

### Test 4: LAD-Level Collapse (CRITICAL)

| Region | LSOAs | Unique outcomes | LADs | LAD η² |
|--------|-------|----------------|------|--------|
| WM | 1638 | **7** | 7 | **1.000** |
| GM | 1636 | **10** | 10 | **1.000** |

**Implication:** Life expectancy is at LAD level. All LSOAs in the same LAD share the same LE value. LAD labels achieve η² = 1.0 (perfect prediction) with only k=7 or k=10 groups. MS basins at k=200 are a massively over-parameterised partition predicting ~7 values. The reported η² of 0.83 is actually *worse* than the trivial LAD partition (η²=1.0), suggesting MS basins don't even perfectly align with LAD boundaries.

### Test 5: Cross-Validated R²

With only 7 or 10 distinct outcome values, leave-one-LAD-out CV produces numerically unstable R² (values like -10²⁷). This confirms that the outcome resolution is fundamentally insufficient for meaningful regression.

---

## Phase 1.5: Re-validation with LSOA-Level Outcomes (2026-02-22)

After identifying that life expectancy was at LAD level, we discovered that the IMD 2019 data already contains **13 genuine LSOA-level outcome variables** (domain and sub-domain scores). These have 1000+ unique values per region — resolution ratio ~72%, far above the 10% threshold.

### Resolution Check (Health Deprivation Score, WM)

| Metric | Value | Status |
|--------|-------|--------|
| LSOAs | 1638 | — |
| Unique outcome values | 1176 | — |
| Resolution ratio | 71.8% | ✅ PASS |
| LAD-as-partition η² | 0.187 | Much < 1.0 — genuine LSOA variation |

### Matched-k Results with LSOA-Level Outcomes

| Region | Outcome | MS k | MS η² | MS ω² | KM η² (matched k) | KM ω² | Δ (MS − KM) |
|--------|---------|------|-------|-------|-------------------|-------|-------------|
| WM | Health Deprivation | 206 | 0.457 | 0.379 | 0.869 | 0.850 | **−0.413** |
| WM | Education Score | 206 | 0.494 | — | 0.881 | 0.864 | **−0.387** |
| GM | Health Deprivation | 283 | 0.484 | — | 0.905 | 0.886 | **−0.422** |

### K-means Scaling with k (WM, Health Deprivation)

| k | KM η² | KM ω² | vs MS at k=206 |
|---|-------|-------|----------------|
| 5 | 0.483 | 0.481 | KM k=5 ≈ MS k=206 |
| 10 | 0.640 | 0.637 | KM k=10 > MS k=206 |
| 50 | 0.807 | 0.801 | — |
| 100 | 0.841 | 0.831 | — |
| 206 | 0.869 | 0.850 | — |

### Phase 1.5 Conclusions

> [!CAUTION]
> **MS basins have no predictive advantage over K-means at any k.** K-means at just k=5 (using spatial coordinates + IMD) matches MS at k=206 in outcome explanation. This is consistent across regions and outcome variables.

However, MS does explain real variance above the random baseline (η²≈0.46 vs random η²≈0.13), so the basins capture *some* structure. The core issue is that K-means does this more efficiently.

### Test 3: Interpolation Sensitivity (NOW RESOLVED)

| Region | Method | Basins | η² (Health) | η² (Education) |
|--------|--------|--------|-------------|----------------|
| WM | Linear | 186 | 0.429 | 0.436 |
| WM | Cubic | 206 | 0.457 | 0.494 |
| GM | Linear | 263 | 0.458 | 0.450 |
| GM | Cubic | 283 | 0.484 | 0.479 |

Basin ratio ≈ 1.08–1.11 (cubic creates ~10% more basins). η² difference ≈ 3pp. **Interpolation is NOT a major artefact source.**

### Test 5: Cross-Validated R² (CRITICAL NEW FINDING)

| Region | Outcome | Method | In-sample R² | 5-fold CV R² | LOO-LAD R² | Overfitting Gap |
|--------|---------|--------|-------------|-------------|------------|-----------------|
| WM | Health | MS basins | 0.694 | 0.003 | −0.189 | **0.689** |
| WM | Health | KM matched k | 0.616 | 0.001 | −0.189 | **0.616** |
| WM | Health | **IMD only** | **0.791** | **0.757** | **0.733** | **0.033** |
| WM | Education | MS basins | 0.494 | −0.137 | −0.459 | **0.631** |
| WM | Education | KM matched k | 0.881 | 0.409 | 0.050 | **0.472** |
| WM | Education | **IMD only** | **0.767** | **0.731** | **0.747** | **0.036** |
| GM | Health | MS basins | 0.484 | −0.287 | −0.971 | **0.771** |
| GM | Health | KM matched k | 0.905 | 0.181 | −0.483 | **0.725** |
| GM | Health | **IMD only** | **0.829** | **0.805** | **0.754** | **0.024** |
| GM | Education | MS basins | 0.479 | −0.271 | −0.689 | **0.750** |
| GM | Education | KM matched k | 0.900 | 0.175 | −0.168 | **0.724** |
| GM | Education | **IMD only** | **0.825** | **0.819** | **0.801** | **0.006** |

> [!CAUTION]
> **Both MS basins and K-means at high k massively overfit.** MS: R² drops from 0.48–0.69 to negative values out-of-sample. K-means: R² drops from 0.62–0.91 to 0.00–0.18 random CV and often negative LOO-LAD. In contrast, **raw IMD score alone achieves R²=0.77–0.83 in-sample and R²=0.73–0.80 LOO-LAD** — stable and generalisable.

---

## What This Means for the Paper

### Claims That Must Be Withdrawn

1. ❌ "MS basins explain 73-83% of life expectancy variance" — outcome was at LAD level
2. ❌ "TDA is 2× better than K-means" — unfair comparison (k=200 vs k≤14) AND K-means wins at matched k
3. ❌ "Bootstrap CIs [0.72, 0.85]" — i.i.d. bootstrap on spatially autocorrelated LAD-level data
4. ❌ Any in-sample R² as headline — massive overfitting (gap ≈ 0.6–0.8)

### Claims That Survive

1. ✅ MS basins provide a principled topological decomposition — structural claim, not predictive
2. ✅ Interpolation is not creating spurious topology — cubic/linear ratio ≈ 1.1
3. ⚠️ The poverty trap concept (basin = trap) has policy relevance — conceptual, not dependent on η²
4. ⚠️ Barrier heights may correlate with dynamics (untested with longitudinal data)

### The Surprising Positive Finding

**Raw IMD score alone is the best predictor.** A single scalar (overall IMD) explains 77–83% of Health/Education domain variance in-sample AND cross-validates at 73–80%. This means:
- The **domains are highly correlated** (deprivation is a unitary construct)
- Neither MS nor K-means partitions add value beyond what the continuous IMD score already provides
- The TDA value proposition must shift entirely from *prediction* to *structural discovery*

---

## Corrective Actions Required

### Immediate (Before Any Further Analysis)

1. **Do not report η² or R² for MS basins as evidence of predictive advantage** — they overfit
2. **Always use matched-k comparisons** — never compare methods at different k
3. **Report ω² instead of η²** — adjusts for degrees of freedom
4. **Headline metric must be out-of-sample** — LOO-LAD R² or spatial block CV

### Strategic Pivot Options

1. **Approach B (Multidimensional PH):** Treat 7D IMD domain scores as a point cloud — no prediction claim, pure topological structure discovery. Uncontaminated by any of the above issues.
2. **Approach A (Justice Infrastructure Coverage):** PH on facility point clouds — holes = coverage gaps. Entirely independent of the MS η² issue.
3. **Reframe MS paper:** Focus on topological features (basins, barriers, separatrices) as interpretable structural decomposition, explicitly NOT claiming predictive advantage over K-means.

---

## Raw Results

- [WM / Health Deprivation](file:///c:/Projects/TDL/poverty_tda/validation/diagnostic_results/diagnostic_west_midlands_health_deprivation_score_2026-02-22.json)
- [WM / Education Score](file:///c:/Projects/TDL/poverty_tda/validation/diagnostic_results/diagnostic_west_midlands_education_score_2026-02-22.json)
- [GM / Health Deprivation](file:///c:/Projects/TDL/poverty_tda/validation/diagnostic_results/diagnostic_greater_manchester_health_deprivation_score_2026-02-22.json)
- [GM / Education Score](file:///c:/Projects/TDL/poverty_tda/validation/diagnostic_results/diagnostic_greater_manchester_education_score_2026-02-22.json)
