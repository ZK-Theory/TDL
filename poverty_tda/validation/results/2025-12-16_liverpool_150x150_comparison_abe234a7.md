# liverpool_150x150_comparison

**Generated:** 2025-12-16T14:19:53.073946
**Region:** Liverpool
**Observations:** 286

## Description

Liverpool single-LAD comparison at 150x150 resolution. Matches kriging benchmark (63% vs 62%). K-means outperforms MS in single-LAD case.

## Data Sources

- **LSOA:** ONS 2021
- **IMD:** 2019
- **Life Expectancy:** ONS 2016-2018

## Outcome Variable

**life_expectancy_male**: 

## Results

### Method Ranking (by η²)

| Rank | Method | Clusters | η² | Variance Explained |
|------|--------|----------|----|--------------------|
| 1 | K-means | 10 | 0.7970 | 79.7% 🏆 |
| 2 | Morse-Smale | 64 | 0.6190 | 61.9%  |

## Key Findings

**Best performing method:** K-means (η² = 0.7970)

## Notes

- Single LAD - no cross-LAD variance
- MS matches kriging benchmark: 62% vs 63%
- K-means 79.7% > MS 61.9% in single-LAD case
- 64 MS basins at 150x150

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
