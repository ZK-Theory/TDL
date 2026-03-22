# merseyside_150x150_comparison

**Generated:** 2025-12-16T14:19:53.074946
**Region:** Merseyside
**Observations:** 889

## Description

Merseyside 5-LAD comparison at 150x150 resolution. MS achieves 95.4% - highest yet. Exceeds kriging benchmark by 32pp.

## Data Sources

- **LSOA:** ONS 2021
- **IMD:** 2019
- **Life Expectancy:** ONS 2016-2018

## Outcome Variable

**life_expectancy (male and female)**: 

## Results

### Method Ranking (by η²)

| Rank | Method | Clusters | η² | Variance Explained |
|------|--------|----------|----|--------------------|
| 1 | Morse-Smale (Female) | 145 | 0.9580 | 95.8% 🏆 |
| 2 | Morse-Smale (Male) | 145 | 0.9540 | 95.4%  |
| 3 | K-means (Female) | 10 | 0.6650 | 66.5%  |
| 4 | K-means (Male) | 10 | 0.6480 | 64.8%  |

## Key Findings

**Best performing method:** Morse-Smale (Female) (η² = 0.9580)

## Notes

- 5 LADs: Liverpool, Knowsley, Sefton, St. Helens, Wirral
- MS 95.4%/95.8% (M/F) - highest performance
- Exceeds Liverpool kriging benchmark by 32pp
- 145 MS basins at 150x150

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
