# greater_manchester_ks4_comparison

**Generated:** 2025-12-16T14:40:15.603412
**Region:** Greater Manchester
**Observations:** 1,636

## Description

KS4 (GCSE attainment) comparison for Greater Manchester. 
MS explains 82.4% of KS4 variance and 73.6% of LE variance.

## Data Sources

- **LSOA:** ONS 2021
- **IMD:** 2019
- **KS4:** DfE 2024/25
- **LE:** ONS 2016-2018

## Outcome Variable

**attainment8_average and life_expectancy_male**: KS4 attainment (Attainment 8 score) and life expectancy (male, 2016-2018 average)

## Results

### Method Ranking (by η²)

| Rank | Method | Clusters | η² | Variance Explained |
|------|--------|----------|----|--------------------|
| 1 | MS (KS4) | 283 | 0.8240 | 82.4% 🏆 |
| 2 | MS (LE) | 283 | 0.7360 | 73.6%  |
| 3 | K-means (KS4) | 10 | 0.4380 | 43.8%  |
| 4 | K-means (LE) | 10 | 0.3280 | 32.8%  |

## Key Findings

**Best method for KS4:** MS (KS4) (η² = 0.8240)
**Best overall method:** MS (LE) (η² = 0.7360)

## Notes

- MS: LE=73.6%, KS4=82.4%
- K-means: LE=32.8%, KS4=43.8%
- MS dominates both health and education outcomes
- 150x150 regional surface used; 283 MS basins
- For KS4-specific prediction, MS (KS4) is optimal; for health outcomes, MS (LE) is best
- Bootstrap CIs not computed for this outcome-specific comparison; see full comparison for LE bootstrap results

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
