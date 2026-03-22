# west_midlands_full_comparison_corrected

**Generated:** 2025-12-16T13:30:17.830184
**Region:** West Midlands
**Observations:** 1,638

## Description

Full 6-method comparison for West Midlands. Corrected to remove 
anomalous Mapper result. All methods use bootstrap 95% CIs (n=1000).

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
| 1 | Morse-Smale (TDA) | 206 | 0.8340 | 83.4% 🏆 |
| 2 | K-means | 10 | 0.4550 | 45.5%  |
| 3 | Mapper (TDA) | 15 | 0.1740 | 17.4%  |
| 4 | LISA | 5 | 0.1740 | 17.4%  |
| 5 | Gi* | 3 | 0.1590 | 15.9%  |
| 6 | DBSCAN | 11 | 0.1000 | 10.0%  |

## Key Findings

**Best performing method:** Morse-Smale (TDA) (η² = 0.8340)

## Notes

- Corrected: Mapper from 168 clusters to 15 (consistent with GM)

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
