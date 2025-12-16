# UK Data Service Access Guide for UKHLS Mobility Analysis

This guide walks through obtaining Understanding Society (UKHLS) data with geographic identifiers for the poverty TDA mobility analysis.

## Quick Start Checklist

### Phase 1: Account Setup (If Not Complete)
- [ ] Register at https://ukdataservice.ac.uk/
- [ ] Complete Safe Researcher Training (if required for Special Licence)
- [ ] Verify you can log in to the data catalog

### Phase 2: Data Access Applications

#### Standard End User Licence (Immediate Access)
These datasets are available with standard account:

| Dataset | Catalog Number | Key Variables | Access Level |
|---------|---------------|---------------|--------------|
| UKHLS Main Survey | SN 6614 | Income, occupation, demographics | Standard |
| BHPS Harmonized | SN 3909 | Historical income (1991-2008) | Standard |

#### Special Licence Required (Apply via catalog)
For geographic identifiers (LSOA/MSOA), you need Special Licence:

| Dataset | Catalog Number | Geographic Level | Variables |
|---------|---------------|------------------|-----------|
| UKHLS Geographic Identifiers | SN 6666 | LSOA, MSOA, LAD | lsoa11, msoa11, lad11cd |
| UKHLS Neighbourhood | SN 7248 | LSOA-level linked data | Area characteristics |

### Phase 3: Download Required Files

Once approved, download these files:

#### From SN 6614 (Main Survey):
```
# For each wave a-k (waves 1-11):
{letter}_indresp.dta      # Individual responses (income, occupation)
{letter}_hhresp.dta       # Household responses
{letter}_indall.dta       # All individuals (including non-responders)
```

Key variables:
- `fihhmnnet1_dv` - Monthly household net income (derived)
- `jbsoc10_cc` - Current occupation (SOC 2010)
- `pidp` - Person identifier (stable across waves)
- `hidp` - Household identifier

#### From SN 6666 (Geographic Identifiers):
```
{letter}_lsoa11.dta       # LSOA 2011 identifiers
{letter}_msoa11.dta       # MSOA 2011 identifiers (if available)
```

Key variables:
- `lsoa11` - Lower Super Output Area (2011 boundaries)
- `msoa11` - Middle Super Output Area (2011 boundaries)
- `lad11cd` - Local Authority District code

### Phase 4: Data Preparation

```python
from poverty_tda.data.ukhls_mobility import (
    load_ukhls_income_panel,
    run_mobility_analysis_pipeline
)

# Point to your downloaded data directory
data_dir = "/path/to/ukhls/stata/stata13_se"

# Check available waves
import os
for f in os.listdir(data_dir):
    if f.endswith('_indresp.dta'):
        print(f"Found: {f}")

# Run pipeline
results = run_mobility_analysis_pipeline(
    data_dir=data_dir,
    output_dir="./output/mobility",
    wave_start=1,
    wave_end=11,
    geographic_level='msoa'  # MSOA recommended for sample stability
)
```

---

## Understanding UKHLS Geographic Access Tiers

### Standard End User Licence
- **What you get**: Main survey variables, Government Office Region (GOR), urban/rural
- **What you DON'T get**: LSOA, MSOA, postcode, exact coordinates
- **Application time**: Immediate download after registration

### Special Licence Access
- **What you get**: LSOA, MSOA, LAD identifiers
- **Requirements**: 
  - Institutional affiliation (university)
  - Research purpose statement
  - Data security declaration
- **Application time**: 1-4 weeks typically
- **How to apply**: Through UK Data Service catalog, click "Order Special Licence" on SN 6666

### Secure Access (SecureLab)
- **What you get**: Exact postcodes, Output Areas (OA), linked admin data
- **Requirements**: 
  - Accredited Researcher status
  - Approved project
  - Access only via Secure Research Service
- **Application time**: 2-6 months
- **When needed**: Only if LSOA is insufficient (it should be fine for this project)

---

## Sample Variables Reference

### Income Variables (from indresp files)

| Variable | Description | Notes |
|----------|-------------|-------|
| `fihhmnnet1_dv` | Monthly HH net income | Best income measure (derived, equivalised) |
| `fimnlabgrs_dv` | Gross labour income (individual) | Before tax |
| `paygl` | Last gross pay | From employment |
| `fiyrdia` | Annual income from all sources | Comprehensive but needs careful handling |

### Geographic Variables (from lsoa11 files)

| Variable | Description | Grain |
|----------|-------------|-------|
| `lsoa11` | LSOA 2011 code | ~1,500 people |
| `msoa11` | MSOA 2011 code | ~7,500 people |
| `lad11cd` | LAD 2011 code | ~150,000 people |
| `gor_dv` | Government Office Region | Available in main survey (no Special Licence) |

### Sample Identifiers

| Variable | Description | Persistence |
|----------|-------------|-------------|
| `pidp` | Person ID | Stable across all waves (use this for tracking) |
| `hidp` | Household ID | Can change if HH composition changes |
| `pno` | Person number within HH | Changes if HH changes |

---

## Sample Code: Verify You Can Access Geographic Data

```python
import pandas as pd

# Test loading wave 11 (most recent in standard UKHLS)
wave = 'k'  # Wave 11

# Load individual response
try:
    indresp = pd.read_stata(
        f'/path/to/ukhls/{wave}_indresp.dta',
        columns=['pidp', f'{wave}_fihhmnnet1_dv']
    )
    print(f"✓ Main survey loaded: {len(indresp)} individuals")
except Exception as e:
    print(f"✗ Error loading main survey: {e}")

# Test geographic identifiers (requires Special Licence)
try:
    geo = pd.read_stata(
        f'/path/to/ukhls/{wave}_lsoa11.dta',
        columns=['pidp', 'lsoa11']
    )
    print(f"✓ Geographic identifiers loaded: {len(geo)} records")
    print(f"  Unique LSOAs: {geo['lsoa11'].nunique()}")
except FileNotFoundError:
    print("✗ Geographic file not found - apply for Special Licence")
except Exception as e:
    print(f"✗ Error loading geographic data: {e}")
```

---

## Fallback: If Special Licence Takes Too Long

If you need to proceed before geographic access is granted:

### Option A: Use Government Office Region (GOR)
Available in standard UKHLS, provides 12 regions:
- North East, North West, Yorkshire, East Midlands, West Midlands
- East of England, London, South East, South West
- Wales, Scotland, Northern Ireland

```python
# GOR is in the main file (no Special Licence needed)
indresp = pd.read_stata(f'{wave}_indresp.dta', columns=['pidp', 'gor_dv', 'fihhmnnet1_dv'])
```

**Limitation**: 12 regions is too coarse for TDA, but useful for validation.

### Option B: Use Published LAD-Level Mobility Estimates
- Social Mobility Commission Social Mobility Index
- Resolution Foundation regional wage tracking
- Can validate TDA methodology at LAD level

### Option C: Combine with Other Sources
- BCS70 (1970 birth cohort) has intergenerational data
- BHPS has historical geographic identifiers
- ONS migration data provides residential mobility patterns

---

## Timeline Expectations

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Account setup | Same day | - |
| Standard data download | Same day | Account |
| Special Licence application | 1-4 weeks | Research statement |
| Data preparation | 1 week | Downloaded files |
| Mobility computation | 2-3 days | Prepared data |
| Surface construction | 1 day | MSOA centroids |
| TTK analysis | 1-2 hours | Mobility surface |

**Total**: 3-6 weeks from account to results

---

## Troubleshooting

### "File not found" for geographic identifiers
→ You need to download SN 6666 separately from SN 6614. Apply for Special Licence.

### Very few individuals with geographic data
→ Check that you're merging on `pidp` correctly. Geographic file may have different wave prefix.

### Low sample size per MSOA
→ Expected. With ~40K households across ~7K MSOAs, you get ~5-6 per MSOA. This is why MSOA (not LSOA) is recommended.

### Income values look wrong
→ Use `fihhmnnet1_dv` (derived, cleaned) not raw payment variables. Check for -8, -9 codes (refusal, don't know).

---

## Contact for Issues

- UK Data Service Help: https://ukdataservice.ac.uk/help/
- UKHLS User Support: https://www.understandingsociety.ac.uk/help/
- CeLSIUS (for ONS-LS): https://www.ucl.ac.uk/ioe/research-centres/centre-for-longitudinal-study-information-and-user-support-celsius
