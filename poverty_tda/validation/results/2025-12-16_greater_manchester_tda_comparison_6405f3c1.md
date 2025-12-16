# greater_manchester_tda_comparison

**Generated:** 2025-12-16T13:17:26.825740
**Region:** Greater Manchester
**Observations:** 1,636

## Description

Replication of West Midlands comparison in Greater Manchester.
Confirms TDA (Morse-Smale) advantage: MS explains 73.6% of life expectancy variance
vs K-means 32.8%. CIs don't overlap - difference statistically significant.

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
| 1 | Morse-Smale (TDA) | 283 | 0.7364 | 73.6% 🏆 |
| 2 | K-means | 10 | 0.3276 | 32.8%  |

## Key Findings

**Best performing method:** Morse-Smale (TDA) (η² = 0.7364)

## Notes

- Replication of West Midlands protocol
- MS: 0.7364 [0.7168, 0.8037]
- K-means: 0.3276 [0.2749, 0.3873]
- CIs do not overlap - significant difference
- MS explains 2.2x more variance than K-means

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files

- `poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson`
- `poverty_tda/validation/data/england_imd_2019.csv`
- `data/raw/outcomes/life_expectancy_processed.csv`
- `poverty_tda/validation/mobility_surface_greater_manchester.vti`

