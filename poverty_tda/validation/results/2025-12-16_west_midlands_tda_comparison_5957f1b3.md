# west_midlands_tda_comparison

**Generated:** 2025-12-16T12:33:55.060653
**Region:** West Midlands
**Observations:** 1,638

## Description

Comparison of TDA methods (Morse-Smale, Mapper) against traditional 
spatial statistics (LISA, Gi*) and clustering (K-means, DBSCAN) for predicting 
life expectancy. Key finding: Morse-Smale at high resolution explains 83.4% of 
variance, nearly 2x K-means (45.5%).

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
| 3 | Mapper (TDA) | 15 | 0.1740 | 17.4%  |
| 4 | LISA | 5 | 0.1719 | 17.2%  |
| 5 | Gi* | 3 | 0.1525 | 15.2%  |
| 6 | DBSCAN | 10 | 0.1003 | 10.0%  |

## Key Findings

**Best performing method:** Morse-Smale (TDA) (η² = 0.8340)

## Notes

- National 75x75 surface: only 7 basins in WM (eta2=9%)
- Regional 100x100 surface: 206 basins (eta2=83.4%)
- Resolution critical for MS performance
- TDA adds substantial value at appropriate resolution

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files

- `poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson`
- `poverty_tda/validation/data/england_imd_2019.csv`
- `data/raw/outcomes/life_expectancy_processed.csv`

### Output Files

- `poverty_tda/validation/mobility_surface_west_midlands.vti`