# 2020 COVID Crash Validation Report: G&K Methodology

## Executive Summary

**Event**: 2020 COVID-19 Crash  
**Crisis Date**: 2020-03-16 (COVID-19 market crash)  
**Validation Status**: **FAIL**  
**Best Kendall-tau**: **0.5586** (L2_norm_variance)

This report validates the 2020 COVID-19 market crash using the complete Gidea & Katz (2018) trend detection methodology.

**Note**: The COVID-19 crash was not included in the original G&K (2018) paper. This validation tests the methodology's **generalizability** to novel crisis types (pandemic-driven vs. financial crises).

---

## Methodology: Complete G&K (2018) Approach

### Three-Stage Pipeline

1. **L^p Norm Computation**
   - 50-day sliding windows over 4 US indices
   - Vietoris-Rips persistence (H₁ homology)
   - Persistence landscapes → L¹ and L² norms

2. **Rolling Statistics** (500-day windows)
   - Variance
   - Spectral density at low frequencies (PRIMARY METRIC)
   - ACF lag-1

3. **Kendall-Tau Trend Analysis** (250-day pre-crisis window)
   - Measures monotonic trend strength
   - τ ≈ +1: Strong upward trend (pre-crisis signal)

---

## Results: 2020 COVID-19 Crash

### Analysis Parameters

- **Crisis Date**: 2020-03-16
- **Analysis Window**: 2019-03-19 to 2020-03-13
- **Observations**: 250 trading days
- **Rolling Window**: 500 days
- **Pre-crisis Window**: 250 days

### Kendall-Tau Results (All 6 G&K Statistics)

| Metric | Kendall-tau (τ) | P-value | N | Status |
|--------|-----------------|---------|---|--------|
| L2_norm_variance | 0.5586 | 1.59e-39 | 250 |  |
| L2_norm_acf_lag1 | -0.5480 | 4.19e-38 | 250 |  |
| L1_norm_acf_lag1 | -0.5016 | 3.29e-32 | 250 |  |
| L1_norm_variance | 0.1676 | 7.94e-05 | 250 |  |
| L2_norm_spectral_density_low | 0.0841 | 4.77e-02 | 250 |  |
| L1_norm_spectral_density_low | -0.0717 | 9.11e-02 | 250 |  |


### Best Performing Metric

- **Metric**: L2_norm_variance
- **Kendall-tau**: 0.5586
- **Interpretation**: Moderate trend detected

---

## Comparison to G&K (2018) Methodology

| Aspect | G&K Paper (2018) | Our Validation |
|--------|------------------|----------------|
| **2020 COVID Crash** | Not studied (post-publication) | τ = 0.5586 (L2_norm_variance) |
| **Methodology** | Complete (rolling stats) | Complete (rolling stats) |
| **Success Threshold** | τ ≥ 0.70 | τ ≥ 0.70 |
| **Status** | N/A | FAIL |

### Key Findings

⚠ **PARTIAL VALIDATION**: Our result (τ = 0.5586) is below threshold

The COVID-19 crash represents a **novel crisis type** (pandemic-driven) compared to the financial crises studied by G&K (dotcom bubble, Lehman collapse). The weaker signal may reflect the rapid, exogenous nature of the pandemic shock vs. gradual financial buildups.

### COVID-19 vs. Financial Crises

**Key Differences:**
- **Speed**: COVID crash occurred over ~4 weeks (Feb-Mar 2020) vs. months-long buildups
- **Cause**: Exogenous health shock vs. endogenous financial imbalances
- **Market Structure**: Higher correlation across assets during pandemic

These differences may explain different τ values compared to 2008 GFC (τ=0.92) and 2000 dotcom (τ=0.75).

---

## Visualizations

See [2020_covid_validation_complete.png](figures/2020_covid_validation_complete.png) for:
1. Raw L^p norms time series
2. Rolling variance with Kendall-tau trend line
3. Rolling spectral density (primary G&K metric)
4. Summary statistics panel

---

## Validation Status: FAIL

⚠ **PARTIAL VALIDATION**

The G&K methodology shows moderate signals for COVID crash:
- Best metric: L2_norm_variance (τ = 0.5586)
- Below threshold: τ = 0.5586 < 0.70

**Possible Explanations**:
1. **Rapid onset**: COVID crash happened in weeks, not months
2. **Exogenous shock**: Less financial market buildup vs. endogenous crises
3. **Data limitations**: Pre-crisis window may not capture pandemic-specific signals

**Note**: Even with moderate τ, the trend is statistically significant (p < 0.001).


---

## Cross-Event Comparison

| Event | Crisis Date | Best τ | Best Metric | Status |
|-------|------------|--------|-------------|--------|
| 2000 Dotcom | 2000-03-10 | 0.7504 | L¹ Variance | PASS |
| 2008 GFC | 2008-09-15 | 0.9165 | L² Variance | PASS |
| 2020 COVID | 2020-03-16 | 0.5586 | L2_norm_variance | FAIL |

**Observation**: COVID shows weaker trends than 2008/2000, possibly due to its rapid, exogenous nature.

---

## References

- Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series: Landscapes of crashes. *Physica A: Statistical Mechanics and its Applications*, 491, 820-834.
