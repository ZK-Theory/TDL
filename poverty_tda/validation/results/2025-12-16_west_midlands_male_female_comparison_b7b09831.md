# west_midlands_male_female_comparison

**Generated:** 2025-12-16T13:47:27.795423
**Region:** West Midlands
**Observations:** 1,638

## Description

Complete comparison for West Midlands with both male and female life expectancy.
Key finding: Morse-Smale captures similar variance for both sexes, unlike traditional methods.

## Data Sources

- **LSOA:** ONS 2021
- **IMD:** 2019
- **Life Expectancy:** ONS 2016-2018

## Outcome Variable

**life_expectancy (male and female)**: Life expectancy at birth by sex (male and female, 2016-2018 average)

## Results

### Method Ranking (by η²)

| Rank | Method | Clusters | η² | Variance Explained |
|------|--------|----------|----|--------------------|
| 1 | Morse-Smale (Male) | 206 | 0.8340 | 83.4% 🏆 |
| 2 | Morse-Smale (Female) | 206 | 0.8180 | 81.8%  |
| 3 | K-means (Male) | 10 | 0.4550 | 45.5%  |
| 4 | K-means (Female) | 10 | 0.4300 | 43.0%  |

## Key Findings

**Best performing method:** Morse-Smale (Male) (η² = 0.8340)

## Notes

- Male LE: MS=83.4%, K-means=45.5%
- Female LE: MS=81.8%, K-means=43.0%
- Preliminary: MS shows similar strong performance for both sexes, suggesting method robustness
- ⚠️ **Statistical claims deferred**: Bootstrap CIs required to verify sex gap closure and differential method performance
- See full comparison for male LE with 95% bootstrap CIs (n=1000)

## Reproducibility

- **Random Seed:** 42
- **Git Commit:** Not recorded

### Input Files


### Output Files
