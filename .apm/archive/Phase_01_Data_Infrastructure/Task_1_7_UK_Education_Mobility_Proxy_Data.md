---
agent: Agent_Poverty_Data
task_ref: Task 1.7
status: Completed
ad_hoc_delegation: false
compatibility_issues: false
important_findings: true
---

# Task Log: Task 1.7 - UK Education & Mobility Proxy Data

## Summary
Implemented education data module (POLAR4 + IMD education domain) and social mobility proxy calculator with validation against Social Mobility Commission patterns. All 27 unit tests pass; 6 integration/validation tests ready for execution with real data.

## Details

### Education Data Module (`education.py`)
- `download_polar4_data()`: Downloads POLAR4 HE participation data from Office for Students (~174MB ZIP)
- `load_polar4_data()`: Loads postcode-level POLAR4 quintiles (1=lowest participation, 5=highest)
- `get_education_from_imd()`: Extracts education domain metrics from IMD data as lightweight alternative
- `load_ks4_outcomes()`: Placeholder for KS4 GCSE data (LSOA-level not publicly available)
- `compute_educational_upward()`: Combines IMD education domain with POLAR4 for educational mobility indicator

### Mobility Proxy Module (`mobility_proxy.py`)
Implements the formula: **mobility_proxy = α×DeprivationChange + β×EducationalUpward + γ×IncomeGrowth**

Default weights: α=0.4, β=0.3, γ=0.3

Core functions:
- `compute_deprivation_change()`: Calculates IMD rank change (with/without baseline)
- `compute_income_growth()`: Derives income indicator from IMD income domain
- `compute_mobility_proxy()`: Main function combining all components
- `aggregate_to_lad()`: Aggregates LSOA-level proxy to LAD level (mean/median/weighted)
- `get_mobility_quintiles()`: Classifies LSOAs into mobility quintiles (1-5)
- `validate_against_smc()`: Validates against Social Mobility Commission patterns

### SMC Validation Patterns
Built-in validation checks:
- **Top mobility LADs**: Westminster, Kensington and Chelsea, Camden (should be in top 30%)
- **Bottom mobility LADs**: Mansfield, Bolsover, Barnsley (should be in bottom 30%)
- **Industrial North check**: Blackpool, Middlesbrough, Hull should be below national average

### Data Sources
- **POLAR4**: Office for Students - https://www.officeforstudents.org.uk/data-and-analysis/young-participation-by-area/
- **IMD Education Domain**: Uses Task 1.6 outputs (preferred lightweight option)
- **SMC Patterns**: Based on State of the Nation reports

## Important Findings
- **LSOA-level KS4 data not publicly available**: Used IMD Education domain as proxy, which incorporates KS4 attainment
- **POLAR4 is postcode-level**: Requires postcode-to-LSOA mapping for integration (fallback to IMD-only implemented)
- **IMD Education domain preferred**: More practical than downloading 174MB POLAR4 file for most use cases

## Output
- Created files:
  - `poverty_tda/data/education.py` - Education data loader (381 lines)
  - `poverty_tda/data/mobility_proxy.py` - Mobility proxy calculator (507 lines)
  - `tests/poverty/test_mobility_proxy.py` - Test suite (33 tests total)
  - `poverty_tda/data/raw/education/.gitkeep` - Directory placeholder
- Modified files:
  - `poverty_tda/data/__init__.py` - Added exports for education and mobility functions

## Issues
None

## Next Steps
- Run integration tests with `pytest -m integration` to validate against real IMD data
- Run validation tests with `pytest -m validation` to check SMC pattern alignment
- Integration with Task 1.8 (Geospatial Data Processor) for spatial mobility analysis
- Consider adding postcode-to-LSOA mapping for full POLAR4 integration
