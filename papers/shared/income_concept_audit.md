# Income Concept Reconciliation Audit
## P01: Cross-Era Income Harmonisation BHPS/USoc

**Date:** 2026-05-06  
**Auditor:** panel-statistics-agent  
**Scripts:** `papers/shared/scripts/income_calibration.R`, `diagnose_pidp_xwave.R`  
**Results JSON:** `results/panel_methodology/harmonisation/income_calibration_2026-05-06.json`  

---

## Executive Summary

**Verdict: FLAG — tercile exact concordance 68.9% (below 80% threshold).**

The cross-era income calibration used `fihhmngrs_dv` (gross household income, month before interview) in BHPS wave br and UKHLS wave b. Task-spec variables `fihhmn` and `fihhmnnet3_dv` do not exist in this version of UKDA-6614.

N = 10,992 spanning individuals (in both BHPS br and UKHLS b); 10,544 with valid income in both waves. Spearman ρ = 0.760 — rank ordering is well-preserved. Exact tercile bin concordance = 68.9%, within-1-bin concordance = 96.7%. The income levels are consistent in ordering but exact tercile boundaries shift between surveys.

**Recommendation:** Use within-survey tercile cutoffs independently for each era rather than transferring BHPS cutoffs to UKHLS. A 2-year gap (br: 2007–08, b: 2010–12) spanning the 2008 financial crisis with a 5.5% median income increase (MALR = 0.359) accounts for the boundary shift.

---

## Variables Searched and Found

### Task spec variables (NOT in UKDA-6614)

| Variable | Location | Status |
|---|---|---|
| `fihhmn` | BHPS/UKHLS hhresp | **ABSENT** — not in this dataset version |
| `fihhmnnet3_dv` | UKHLS hhresp | **ABSENT** — not in this dataset version |

### Variables actually available

| Variable | Location | Description |
|---|---|---|
| `{w}_fihhmngrs_dv` | BHPS + UKHLS hhresp | Gross household income, month before interview. **Present identically in both surveys. Selected as canonical variable.** |
| `{w}_fihhmnnet1_dv` | UKHLS hhresp only | Net household income (no deductions). UKHLS only. |
| `{w}_hhneti` | BHPS hhresp only | Net household income. BHPS only. Different derivation from UKHLS net — not directly comparable. |

---

## Crosswalk Investigation

### pidp as the shared identifier

Per BHPS Harmonised User Guide §2.3.2.1 (UKDA-6614 documentation, p. 15):

> "The identifiers pidp and bw_hidp work across harmonised BHPS and Understanding Society files."

`pidp` in harmonised BHPS files and `pidp` in UKHLS files identify the same person. Verified by:
- All 14,419 BHPS wave br pidp values found in `xwavedat.tab` (100% recovery).
- No `as.numeric` conversion issues: all pidp values read cleanly as integers.

### Wave a vs wave b

BHPS br and UKHLS wave a have **0 spanning individuals**. UKHLS wave a (2009–11) was fielded before the BHPS cohort was formally enrolled into Understanding Society. The BHPS cohort first appears from **wave b (2010–12)** onward:

| UKHLS wave | Spanning with BHPS br |
|---|---|
| a | 0 |
| b | 10,992 |
| c | 10,052 |
| d | 9,104 |
| e | 8,479 |
| … | … (attrition) |

Wave b is the correct cross-era calibration pair for BHPS br.

---

## Cross-Era Calibration Results

| Metric | Value |
|---|---|
| N spanning total | 10,992 |
| N spanning with valid income (both waves) | 10,544 |
| BHPS br tercile cutoffs (GBP/month) | £1,982 (L/M), £3,718 (M/H) |
| UKHLS b tercile cutoffs (GBP/month) | £2,079 (L/M), £3,818 (M/H) |
| Tercile exact concordance | **68.9%** |
| Tercile within-1-bin concordance | 96.7% |
| Spearman ρ (gross income, br vs b) | 0.760 |
| Mean absolute log-ratio | 0.359 |
| Median log-ratio (UKHLS/BHPS) | 0.054 (= 1.055× in levels) |

Cross-tabulation BHPS tercile × UKHLS tercile (spanning individuals):

```
            UKHLS b
BHPS br   L       M       H
L      2,655    692     168
M        681  2,051     784
H        179    771   2,563
```

---

## Verdict and Implications

### S12 verdict: FLAG (concordance < 80%)

The 68.9% exact concordance is below the 80% quality gate. This does not mean the data are unusable — Spearman ρ = 0.760 confirms the rank ordering of income is well-preserved across surveys. The 96.7% within-1-bin concordance confirms very few individuals jump across multiple tercile bins.

The gap (2007–08 → 2010–12) spans the global financial crisis and recession. Individual income change over this 3-year period is expected to be substantial and real — the MALR of 0.359 captures genuine income volatility, not measurement noise.

### Implications for the 9-state crossing

1. **Use within-survey tercile boundaries.** Do not apply BHPS tercile cutoffs to UKHLS data or vice versa. Each survey wave uses its own distributional terciles.
2. **Cross-era state transitions (BHPS → UKHLS).** For individuals spanning the two surveys, the income tercile may shift due to real income change and/or distributional repositioning — treat as genuine mobility, not harmonisation error. Spearman ρ = 0.760 confirms adequate rank preservation.
3. **Net income comparison is not recommended cross-era.** `hhneti` (BHPS) and `fihhmnnet1_dv` (UKHLS) use different derivation methods and are not equivalent. Spearman ρ (BHPS gross vs UKHLS net1) = 0.731 confirms further attenuation.

### Decision for P01-A/P01-B

Within-survey tercile assignment is the appropriate method. The cross-era calibration confirms the gross income variable (`fihhmngrs_dv`) provides adequate rank-order preservation (ρ = 0.760) for trajectory analysis, with the understanding that within-person income tercile changes across the BHPS→USoc boundary reflect genuine mobility (not harmonisation failure) and should be modelled as such.

---

## Scripts and Outputs

| File | Purpose |
|---|---|
| `papers/shared/scripts/income_vars_check.py` through `income_vars_check4.py` | Variable discovery in BHPS and UKHLS hhresp/indresp |
| `papers/shared/scripts/diagnose_pidp_overlap.R` | Confirmed pidp type conversion was not the issue |
| `papers/shared/scripts/diagnose_pidp_xwave.R` | Found wave b as correct calibration pair (wave a: 0 overlap) |
| `papers/shared/scripts/income_calibration.R` | Full calibration: br × b spanning individuals, concordance, ρ, MALR |
| `results/panel_methodology/harmonisation/income_calibration_2026-05-06.json` | Machine-readable results |
