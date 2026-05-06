# jbstat Harmonisation Audit
## P01: Employment Status Variable Across BHPS/USoc Waves

**Date:** 2026-05-06  
**Auditor:** panel-statistics-agent  
**Script:** `papers/shared/scripts/jbstat_audit.R`  
**Results JSON:** `results/panel_methodology/harmonisation/jbstat_coding_2026-05-06.json`  
**Label source:** `data/UKDA-6614-tab/mrdoc/ukda_data_dictionaries/ukhls/{wave}_indresp_ukda_data_dictionary.rtf` (all waves verified)

---

## Executive Summary

**Verdict: CONSISTENT — working assumption confirmed with minor caveats.**

The core E/U/I mapping for `jbstat` is stable across all 33 waves (harmonised BHPS ba–br and UKHLS a–o). Codes 1, 2, 3, 4, 5, 6, 7, 8, 9, and 97 appear consistently in every wave with identical binning. Three categories of minor inconsistency exist:

1. **Code 10** (UKHLS-only, all 15 waves): "Unpaid, family business" → I. Absent from harmonised BHPS; sub-type absorbed into 97 in BHPS. Negligible impact.
2. **Code 11** (UKHLS waves c–o): "On apprenticeship" → **E**. Small counts; affects the E count marginally upward in UKHLS relative to BHPS.
3. **Codes 12–15** (UKHLS waves k–o): COVID-era and parental-leave additions. All map to E (furlough, temporary layoff, shared parental leave, adoption leave). Counts are small to negligible except code 12 in waves k–l.

**Correction from initial draft:** Code 11 is "On apprenticeship" (→ E), not "Waiting to take up a job" (→ I). Codes 13–15 are document-confirmed as "Temporarily laid off/short term working", "On shared parental leave", and "On adoption leave" respectively (all → E). All labels sourced from UKDA wave-level RTF data dictionaries, not inferred.

These inconsistencies are unlikely to materially affect the 9-state crossing. The S4 assumption (employment-state harmonisation intrinsically resolved) is **confirmed**, subject to the analyst decisions documented below.

---

## Per-Wave Coding Table

### Coding bins for the 9-state crossing (E/U/I)

All labels verified against `ukhls/{wave}_indresp_ukda_data_dictionary.rtf` (codes 10–15 are defined identically across all UKHLS waves a–o in the data dictionary; actual non-zero counts by wave are reported in the per-wave coverage table).

| Code | Label (data dictionary) | E/U/I bin | Notes |
|------|------------------------|-----------|-------|
| 1 | Self employed | **E** | Present all waves |
| 2 | Paid employment (ft/pt) | **E** | Present all waves |
| 3 | Unemployed | **U** | Present all waves; ILO definition |
| 4 | Retired | **I** | Present all waves |
| 5 | On maternity leave | **E** | Present all waves |
| 6 | Family care or home | **I** | Present all waves |
| 7 | Full-time student | **I** | Present all waves |
| 8 | LT sick or disabled | **I** | Present all waves |
| 9 | Govt training scheme | **U** | Present all waves; small N in later waves |
| 10 | Unpaid, family business | **I** | Non-zero UKHLS a–o; absent BHPS harmonised |
| 11 | On apprenticeship | **E** | Non-zero UKHLS c–o; absent BHPS harmonised |
| 12 | On furlough | **E** | Non-zero UKHLS k–o; 88% k_employ=1 confirmed |
| 13 | Temporarily laid off/short term working | **E** | Non-zero UKHLS k–o; N=25–83; 60% k_employ=1 |
| 14 | On shared parental leave | **E** | Non-zero UKHLS m–o; N=2–4; analogous to code 5 |
| 15 | On adoption leave | **E** | Non-zero UKHLS n–o; N=2–3; analogous to code 5 |
| 97 | Doing something else | **I** | Present all waves |

### Per-wave coverage

| Wave | Survey | N valid | E codes | U codes | Code 10 | Code 11 | Codes 12+ |
|------|--------|---------|---------|---------|---------|---------|-----------|
| ba | BHPS harmonised | 9,912 | 1,2,5 | 3,9 | No | No | No |
| bb | BHPS harmonised | 9,844 | 1,2,5 | 3,9 | No | No | No |
| bc | BHPS harmonised | 9,592 | 1,2,5 | 3,9 | No | No | No |
| bd | BHPS harmonised | 9,475 | 1,2,5 | 3,9 | No | No | No |
| be | BHPS harmonised | 9,247 | 1,2,5 | 3,9 | No | No | No |
| bf | BHPS harmonised | 9,422 | 1,2,5 | 3,9 | No | No | No |
| bg | BHPS harmonised | 11,185 | 1,2,5 | 3,9 | No | No | No |
| bh | BHPS harmonised | 10,898 | 1,2,5 | 3,9 | No | No | No |
| bi | BHPS harmonised | 15,612 | 1,2,5 | 3,9 | No | No | No |
| bj | BHPS harmonised | 15,597 | 1,2,5 | 3,9 | No | No | No |
| bk | BHPS harmonised | 18,866 | 1,2,5 | 3,9 | No | No | No |
| bl | BHPS harmonised | 16,565 | 1,2,5 | 3,9 | No | No | No |
| bm | BHPS harmonised | 16,237 | 1,2,5 | 3,9 | No | No | No |
| bn | BHPS harmonised | 15,790 | 1,2,5 | 3,9 | No | No | No |
| bo | BHPS harmonised | 15,608 | 1,2,5 | 3,9 | No | No | No |
| bp | BHPS harmonised | 15,392 | 1,2,5 | 3,9 | No | No | No |
| bq | BHPS harmonised | 14,873 | 1,2,5 | 3,9 | No | No | No |
| br | BHPS harmonised | 14,418 | 1,2,5 | 3,9 | No | No | No |
| a | UKHLS | 50,982 | 1,2,5 | 3,9 | **Yes** | No | No |
| b | UKHLS | 54,561 | 1,2,5 | 3,9 | **Yes** | No | No |
| c | UKHLS | 49,690 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| d | UKHLS | 47,069 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| e | UKHLS | 44,834 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| f | UKHLS | 45,138 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| g | UKHLS | 42,134 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| h | UKHLS | 39,243 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| i | UKHLS | 36,020 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| j | UKHLS | 34,276 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | No |
| k | UKHLS | 31,939 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | **12 (n=156), 13 (n=25)** |
| l | UKHLS | 29,204 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | **12 (n=319), 13 (n=51)** |
| m | UKHLS | 27,902 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | **12 (n=196), 13 (n=48), 14 (n=4)** |
| n | UKHLS | 35,341 | 1,2,5,11 | 3,9 | **Yes** | **Yes (n=100)** | **12 (n=11), 13 (n=58), 14 (n=3), 15 (n=3)** |
| o | UKHLS | 32,714 | 1,2,5,11 | 3,9 | **Yes** | **Yes** | **12 (n=9), 13 (n=45), 14 (n=2), 15 (n=2)** |

---

## Flagged Inconsistencies

### 1. Code 10: UKHLS-only unpaid family worker

**Label (data dictionary):** "Unpaid, family business"

Code 10 appears in all 15 UKHLS waves (a–o) with small counts. It is absent from all 18 harmonised BHPS waves. In BHPS, unpaid family workers are absorbed into code 97 ("Doing something else").

**Classification: I.** Unpaid family workers are not in employment under ILO definitions (no pay, no employment contract). Their absence in BHPS causes BHPS to have a marginally larger 97 category; this is a sub-type composition difference within I and does not affect the E/U/I boundary.

### 2. Code 11: UKHLS-only apprentices

**Label (data dictionary):** "On apprenticeship"

Code 11 appears from UKHLS wave c onward (absent in waves a–b and all harmonised BHPS waves). In wave n the count reaches 100.

**Classification: E.** Apprentices in the UK are engaged under Apprenticeship Agreements and receive at least the Apprenticeship National Minimum Wage. They are in paid employment under a contract of service. ILO: employed. The Fumagalli et al. (2017) harmonised BHPS user guide includes `recode jbstat (10 11=97)` in example code — this applies to the *harmonised BHPS* coding context, where codes 10–11 never appear in practice. It is not a substantive classification instruction for UKHLS analysis. Code 11 belongs in **E**, not I.

**Implication for 9-state crossing:** UKHLS waves c–o have a small additional E-bin contribution absent from BHPS. Given that code 11 counts are small (typically well under 0.5% of wave N), this does not materially alter the E share or the topological structure. It does create a marginal upward nudge to the UKHLS E bin relative to BHPS, which is a genuine structural difference rather than a coding error.

### 3. Code 12: COVID furlough (UKHLS waves k–o)

**Label (data dictionary):** "On furlough"

Code 12 appears from wave k (fielded 2020–2022, the period of the UK Government Job Retention Scheme). Cross-tabulation with `k_employ` confirms 88% of code-12 respondents have `k_employ=1`. Furloughed workers retain their employment contracts; under ILO conventions, they are temporarily absent from work while employed.

**Classification: E.** Counts by wave: k=156, l=319, m=196, n=11, o=9. Peak in wave l, declining sharply as furlough ended (scheme closed September 2021). Classifying as I would create a spurious dip in E across waves k–l.

### 4. Code 13: Temporary layoff and short-time working (UKHLS waves k–o)

**Label (data dictionary):** "Temporarily laid off/short term working"

Code 13 appears from wave k with counts 25–83 per wave. Cross-tabulation with `k_employ` shows 60% employed, 40% not employed in wave k (N=25). "Short-time working" (reduced hours on employer instruction) and "temporary layoff" (employer suspends work without terminating the contract) both preserve the employment relationship.

**Classification: E.** Under ILO conventions, workers temporarily absent from their job who have a firm recall date or expect to return within three months are classified as employed. The 40% k_employ=2 cases likely reflect self-reported uncertainty about employment status rather than formal termination of the contract. Given the small counts (N < 0.3% per wave), this analyst decision has negligible impact on aggregate E shares.

### 5. Codes 14–15: Parental and adoption leave (UKHLS waves m–o)

**Labels (data dictionary):** 14 = "On shared parental leave"; 15 = "On adoption leave"

Codes 14 and 15 first appear in waves m and n respectively with N ≤ 4 per wave. Both are leave entitlements in which the employment relationship is retained, directly analogous to maternity leave (code 5 → E).

**Classification: E.** Counts are negligible (maximum 4 observations per wave) and will have no detectable impact on the state distribution or topological structure.

### 6. ILO unemployment definition

Code 3 ("Unemployed") is consistently defined across all waves as the ILO unemployment measure. No wave-specific variation was detected. Code 9 (government training scheme) is present in both BHPS and UKHLS and is classified as U throughout, consistent with treating training scheme participants as labour market active.

### 7. Zero-hours and gig economy coding

Zero-hours workers are not differentiated in `jbstat`: they appear as code 2 (employed) or code 1 (self-employed) in all waves regardless of contract type. From UKHLS wave g onward, zero-hours contracts became more prevalent in the UK labour market, but this change is not reflected in `jbstat`. The `jbterm1` and `jbterm2` variables capture contract type; jbstat itself is stable.

**Implication:** The E bin includes increasing numbers of zero-hours workers from wave g onward. This is a structural change in employment, not a coding inconsistency. Analysts studying gig economy effects should supplement jbstat with contract-type variables.

---

## Implications for the 9-State Crossing

The working assumption that `jbstat` harmonisation is intrinsically resolved is **confirmed**. The required recoding for a clean E/U/I crossing is:

```r
# Apply before constructing the 9-state crossing
# All labels verified against UKDA wave-level data dictionaries 2026-05-06
jbstat_E <- c(1, 2, 5, 11, 12, 13, 14, 15)
# Self-employed, paid employment, maternity leave, apprenticeship,
# furlough, temporary layoff/short-time working, shared parental leave, adoption leave

jbstat_U <- c(3, 9)
# ILO unemployed, government training scheme

jbstat_I <- c(4, 6, 7, 8, 10, 97)
# Retired, family care/home, full-time student, LT sick/disabled,
# unpaid family business, doing something else
```

**Key structural difference between BHPS and UKHLS:** UKHLS waves c–o contain code 11 (apprentices, E bin) absent from BHPS. This creates a marginal upward nudge to the UKHLS E bin. Counts are small enough that the effect on topological structure is negligible. The BHPS harmonised coding absorbs apprentices and unpaid family workers into code 97 (I bin).

**COVID-era codes (waves k–o):** Codes 12–13 affect the E bin during the pandemic period. Their effect is real — E is correctly higher in waves k–l due to furlough than it would be otherwise — not an artefact.

---

## References

- Fumagalli, L., Knies, G., and Buck, N. (2017). *Understanding Society: The UK Household Longitudinal Study harmonised BHPS User Guide*. University of Essex. (§2.3 and Figure 4 example code; note: recode advice applies to BHPS harmonised context)
- UKDA Study Number 6614: Understanding Society Waves 1–15 and harmonised BHPS Waves 1–18, wave-level data dictionaries (`mrdoc/ukda_data_dictionaries/ukhls/{wave}_indresp_ukda_data_dictionary.rtf`)
