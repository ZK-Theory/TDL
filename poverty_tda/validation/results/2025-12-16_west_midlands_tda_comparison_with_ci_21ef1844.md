# west_midlands_tda_comparison_with_ci

**Generated:** 2025-12-16T13:11:37.553466
**Region:** West Midlands
**Observations:** 1,638

## Description

Comparison of TDA methods against traditional methods for predicting 
life expectancy in West Midlands. Includes bootstrap 95% confidence intervals (n=1000).
Key finding: Morse-Smale (83.4%) significantly outperforms K-means (45.5%) - CIs don't overlap.

## Data Sources

- **LSOA Boundaries:** ONS LSOA 2021
- **Deprivation:** IMD 2019
- **Life Expectancy:** ONS 2016-2018

## Outcome Variable

**life_expectancy_male**: Male life expectancy at birth (years) by LAD

## Results

### Method Ranking (by η²)

| Rank | Method | Clusters | η² | Variance Explained |
|------|--------|----------|----|--------------------|
| 1 | Morse-Smale (TDA) | 206 | 0.8340 | 83.4% 🏆 |
| 2 | K-means | 10 | 0.4549 | 45.5%  |

## Key Findings

**Best performing method:** Morse-Smale (TDA) (η² = 0.8340)

## Notes

- Bootstrap CIs: n=1000 iterations
- MS: 0.8340 [0.8233, 0.8805]
- K-means: 0.4549 [0.4000, 0.5151]
- CIs do not overlap - difference is statistically significant
- 100x100 regional surface used for MS

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files

- `poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson`
- `poverty_tda/validation/data/england_imd_2019.csv`
- `data/raw/outcomes/life_expectancy_processed.csv`
- `poverty_tda/validation/mobility_surface_west_midlands.vti`

### Output Files
