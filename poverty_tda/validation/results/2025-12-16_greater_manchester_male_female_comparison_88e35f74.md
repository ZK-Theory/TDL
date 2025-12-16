# greater_manchester_male_female_comparison

**Generated:** 2025-12-16T13:47:27.798439
**Region:** Greater Manchester
**Observations:** 1,636

## Description

Complete comparison for Greater Manchester with both male and female life expectancy.
Key finding: Morse-Smale captures similar variance for both sexes, unlike traditional methods.

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
| 1 | Morse-Smale (Male) | 283 | 0.7360 | 73.6% 🏆 |
| 2 | Morse-Smale (Female) | 283 | 0.7280 | 72.8%  |
| 3 | K-means (Female) | 10 | 0.3320 | 33.2%  |
| 4 | K-means (Male) | 10 | 0.3280 | 32.8%  |

## Key Findings

**Best performing method:** Morse-Smale (Male) (η² = 0.7360)

## Notes

- Male LE: MS=73.6%, K-means=32.8%
- Female LE: MS=72.8%, K-means=33.2%
- MS closes sex gap seen in Liverpool benchmark (63% male vs 39% female)
- TDA captures factors affecting female health that linear methods miss

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
