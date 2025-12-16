# Outcome Data Download Guide

This guide helps you download the outcome data needed for TDA comparison protocol validation.

## Required Datasets

### 1. Life Expectancy by Local Authority (ONS)

**Source:** Office for National Statistics  
**Independence from IMD:** HIGH (not used in IMD construction)

**Download Steps:**
1. Go to: https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies/datasets/lifeexpectancyatbirthandatage65bylocalareasuk
2. Click "Download the complete dataset" or look for the Excel/CSV download
3. Save to: `data/raw/outcomes/life_expectancy_by_lad.xlsx`

**Alternative (NOMIS):**
1. Go to: https://www.nomisweb.co.uk/
2. Search for "life expectancy"
3. Select "Life expectancy at birth" and filter by Local Authority

**Columns needed:**
- `area_code` (LAD code like E06000001)
- `area_name` (LAD name)
- `life_expectancy_male` (at birth)
- `life_expectancy_female` (at birth)
- Period: 2017-2019 or 2018-2020

---

### 2. GCSE Attainment by Local Authority (DfE)

**Source:** Department for Education, Explore Education Statistics  
**Independence from IMD:** MEDIUM (education domain related but separate)

**Download Steps:**
1. Go to: https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-performance
2. Click on the latest release (e.g., "Academic year 2022/23")
3. Scroll to "All data files" section
4. Download "Local authority data" (CSV format)
5. Save to: `data/raw/outcomes/ks4_attainment_by_lad.csv`

**Direct link (may change):**
https://explore-education-statistics.service.gov.uk/data-catalogue/key-stage-4-performance

**Columns needed:**
- `la_code` (LAD code)
- `la_name` (LAD name)
- `avg_att8` (Average Attainment 8 score)
- `pt_ebacc_e_ptq_ee` (% entering EBacc)
- Academic year: 2018/19 or 2022/23

---

### 3. Internal Migration by Local Authority (ONS) - Optional

**Source:** ONS Internal Migration  
**Independence from IMD:** HIGH (behavioral choice data)

**Download Steps:**
1. Go to: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/migrationwithintheuk/datasets/internalmigrationbylocauthoritiesinenglandandwales
2. Download the Excel workbook
3. Save to: `data/raw/outcomes/internal_migration_by_lad.xlsx`

**Columns needed:**
- LAD code
- In-migration count
- Out-migration count
- Net internal migration

---

## After Download: Processing

Once files are downloaded, run the processing script:

```python
from poverty_tda.data.download_outcomes import process_life_expectancy, process_gcse_attainment
from pathlib import Path

output_dir = Path("data/raw/outcomes")

# Process life expectancy
le_df = process_life_expectancy(output_dir / "life_expectancy_by_lad.xlsx")
le_df.to_csv(output_dir / "life_expectancy_processed.csv", index=False)

# Process GCSE
ks4_df = process_gcse_attainment(output_dir / "ks4_attainment_by_lad.csv")
ks4_df.to_csv(output_dir / "gcse_attainment_processed.csv", index=False)
```

---

## Data Dictionary for Validation

| Outcome | Column Name | Unit | Expected Correlation with Deprivation |
|---------|-------------|------|--------------------------------------|
| Male life expectancy | `life_expectancy_male` | Years | Negative (r ≈ -0.7) |
| Female life expectancy | `life_expectancy_female` | Years | Negative (r ≈ -0.7) |
| Attainment 8 | `avg_att8` | Points | Negative (r ≈ -0.5) |
| Net migration | `net_internal_migration` | Persons | Varies by area type |

---

## Quick Verification

After downloading, verify data quality:

```python
import pandas as pd

# Check life expectancy
le_df = pd.read_excel("data/raw/outcomes/life_expectancy_by_lad.xlsx")
print(f"Life expectancy: {len(le_df)} rows")
print(f"LAD codes present: {'E06' in str(le_df.iloc[0])}")

# Check GCSE
ks4_df = pd.read_csv("data/raw/outcomes/ks4_attainment_by_lad.csv")
print(f"GCSE attainment: {len(ks4_df)} rows")
print(f"Columns: {ks4_df.columns.tolist()[:5]}")
```
