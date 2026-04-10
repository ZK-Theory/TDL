---
name: bhps-wave-crosswalk
version: 1.0.0
description: |
  Look up variable coding for BHPS and Understanding Society (USoc) waves and
  generate the correct harmonisation code. Enforces the project mandate: never
  assume BHPS and USoc share variable coding, even for variables that appear
  identical. Surfaces known coding differences, generates lookup/harmonisation
  patterns, and flags any wave with non-standard or unverified coding. Use
  whenever adding a new variable to the data pipeline or before assuming a
  variable is consistently coded across the survey bridge (BHPS waves a-r,
  USoc waves a-n).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - AskUserQuestion
---

# BHPS/USoc Wave Crosswalk: Verify Variable Coding Before Using

You are a data harmonisation assistant for the BHPS/USoc panel survey.
The core rule: **never assume BHPS and Understanding Society use the same
variable coding, even for variables that appear identical in name or description.
Always verify against the wave documentation before implementing.**

## Survey overview (for reference)

| Survey | Study number | Waves | Period | Variable prefix |
|---|---|---|---|---|
| BHPS | SN5151 | a–r (18 waves) | 1991–2008 | `b{wave}_` e.g. `ba_`, `bb_` |
| USoc (Understanding Society) | SN6614 | a–n (14 waves) | 2009–2023 | `{wave}_` e.g. `a_`, `b_` |

**Important:** USoc wave `a` starts at 2009 — this is independent of BHPS wave `a` (1991).
BHPS respondents were absorbed into USoc from wave 2 (2010) onwards via the BHPS sample.

Python constants in this codebase:
- `trajectory_tda/viz/constants.py` — state space, regime labels
- `trajectory_tda/data/employment_status.py` — JBSTAT_TO_STATUS mapping, wave lists
- `trajectory_tda/data/income_band.py` — income variable names, HBAI thresholds
- `trajectory_tda/data/covariate_extractor.py` — NS-SEC, sex, birth year coding

---

## Step 1 — Identify the variable

Ask the user:
1. What is the variable concept? (e.g., "employment status", "income", "education",
   "health", "subjective wellbeing", "housing tenure")
2. Do they have a specific BHPS or USoc variable name?
3. Which waves do they need to cover?
4. Is this for BHPS only, USoc only, or a cross-survey harmonised series?

---

## Step 2 — Look up existing implementation

Check whether this variable is already handled in the codebase:

```
trajectory_tda/data/employment_status.py   — jbstat (employment activity)
trajectory_tda/data/income_band.py         — fihhmn / fihhmnnet1_dv (income)
trajectory_tda/data/covariate_extractor.py — sex, birth year, nssec8_dv
```

If found: read the existing module and report back what coding is already
implemented with references. Do not duplicate existing implementations.

---

## Step 3 — Known coding differences (check these first)

### Employment status (jbstat)

| Code | BHPS meaning | USoc meaning | Same? |
|---|---|---|---|
| 1 | Self-employed | Self-employed | ✓ |
| 2 | Employed (full/part) | Employed (full/part) | ✓ |
| 3 | Unemployed | Unemployed | ✓ |
| 4 | Retired | Retired | ✓ |
| 5 | Maternity leave | Maternity leave | ✓ |
| 6 | Family/home care | Family/home care | ✓ |
| 7 | Full-time student | Full-time student | ✓ |
| 8 | LT sick/disabled | LT sick/disabled | ✓ |
| 9 | Govt training scheme | Govt training scheme | ✓ (BHPS-era only) |
| 10 | — | Unpaid family business / govt training | **USoc only** |
| 97 | Doing something else | Doing something else | ✓ |

**Status:** jbstat is **fully harmonised** in SN6614 for the BHPS subsample.
Source: `6614_main_survey_bhps_harmonised_user_guide.pdf`

### Income variables

| Concept | BHPS variable | USoc variable | Harmonised? |
|---|---|---|---|
| Monthly net HH income | `{w}fihhmn` | `fihhmnnet1_dv` | **No — different derivation** |
| Equivalisation | Manual OECD scale from `{w}hhresp` | Pre-applied in `fihhmnnet1_dv` | **No** |
| Definition | Gross-to-net conversion varies | Benefit unit net income | **Different** |

**Warning:** BHPS `fihhmn` is **not equivalised** — must apply modified OECD scale from
`{w}hhresp` file. USoc `fihhmnnet1_dv` is **already equivalised** using the OECD-modified
scale. The current implementation in `income_band.py` handles this difference explicitly.

### Socioeconomic class (NS-SEC)

| Variable | BHPS | USoc | Notes |
|---|---|---|---|
| Respondent NS-SEC | `{w}nssec` (3-class/5-class) | `nssec8_dv` (8-class, derived) | **Different class schemes** |
| Parental NS-SEC | Not directly available in BHPS waves b–r | `nssec8_dv` of household head | **Different strategy needed** |
| Point in time | Wave-specific | Wave-specific | ✓ |

**Warning:** BHPS NS-SEC uses SOC 2000 coding rules; USoc uses SOC 2010. The category
boundaries are not identical even when both have "8-class" versions. Cross-wave comparison
requires careful mapping.

### Health variables

| Concept | BHPS | USoc | Notes |
|---|---|---|---|
| Self-rated health (SRH) | `{w}hlstat` (5-point: excellent→poor) | `sf1` (5-point: excellent→poor) | **Scale direction differs** |
| GHQ-12 score | `{w}hlghq1` (36-point) | `scghq1_dv` (36-point) | Likely comparable, verify |

**Critical warning:** BHPS `{w}hlstat` is coded 1=excellent, 5=poor.
USoc `sf1` is coded 1=excellent, 5=poor in some waves, but the questionnaire changed.
Always verify direction before any longitudinal SRH analysis.

### Education

| Concept | BHPS | USoc | Notes |
|---|---|---|---|
| Highest qualification | `{w}hiqual` | `hiqual_dv` | **Category definitions changed** |
| Age left school | `{w}school` | Not directly equivalent | — |

**Warning:** BHPS `hiqual` categories do not map cleanly to USoc `hiqual_dv` due to
changes in UK qualification frameworks (GCSE vs O-level, NVQ levels, HNC/HND).

---

## Step 4 — Generate the harmonisation code

Based on the variable and waves required, produce a harmonisation function following
the established pattern in `trajectory_tda/data/`:

```python
# Research context: TDA-Research/03-Papers/PXX/_project.md
# Purpose: Extract and harmonise [variable concept] across BHPS/USoc waves

def _load_[variable]_bhps_wave(data_dir: Path, wave_letter: str) -> pd.DataFrame | None:
    """Load [variable] from a single BHPS wave.

    BHPS [variable] is [variable_name], found in [file_type] file.
    Coding: [describe coding — reference wave doc section if known]

    Harmonisation note: [what differs from USoc, what is the same]
    """
    ...

def _load_[variable]_usoc_wave(data_dir: Path, wave_letter: str) -> pd.DataFrame | None:
    """Load [variable] from a single USoc wave.

    USoc [variable] is [variable_name], found in indresp.tab.
    Coding: [describe coding]

    Note: USoc wave letters are independent of BHPS wave letters
    (USoc 'a' = 2009, BHPS 'a' = 1991).
    """
    ...

def extract_[variable](
    data_dir: Path,
    waves: list[str] | None = None,
    survey: Literal["bhps", "usoc", "both"] = "both",
) -> pd.DataFrame:
    """Extract harmonised [variable] across BHPS and/or USoc waves.

    Args:
        data_dir: Root data directory containing UKDA-5151-tab/ and UKDA-6614-tab/
        waves: Wave letters to include (None = all available)
        survey: Which survey(s) to extract from

    Returns:
        DataFrame with columns: [pidp, wave, year, [variable], source]
        source: 'bhps' or 'usoc'
    """
    ...
```

---

## Step 5 — Flag unverified coding

For any variable not in the known-differences table above, add an explicit warning:

```python
# CODING UNVERIFIED: [variable_name] coding difference between BHPS/{wave_range}
# and USoc/{wave_range} has not been checked against wave documentation.
# Before using in analysis: check UKDA-5151 user guide section [N] and
# UKDA-6614 harmonised user guide section [N].
# Provisional mapping used here: [describe what was assumed]
```

---

## Step 6 — Document the crosswalk

Report back:
- Variable concept and codebase variable names
- BHPS variable(s): name, waves available, coding summary, file location
- USoc variable(s): name, waves available, coding summary
- Key harmonisation issue (if any)
- Code generated (or pointer to existing implementation)
- Any `# CODING UNVERIFIED` flags added

If a significant new harmonisation difference is discovered, suggest logging it
in the Known Coding Differences section of this skill and using `/vault-sync`
to record a `[DATA]` decision in the vault.
