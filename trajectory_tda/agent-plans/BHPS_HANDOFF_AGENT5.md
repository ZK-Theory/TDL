# Agent 1 → Agent 5 Handoff: BHPS Pipeline Results

**Date:** 2026-03-15
**Status:** All tasks complete. Both BHPS-era and spanning TDA pipelines ran successfully.
**Null tests:** All rerun at n=500 permutations (plan-required count). Total compute: 5.5 hours.

---

## 1. BHPS `fihhmn` Determination

**Finding:** BHPS `fihhmn` is **raw (unequivalised)** monthly net household income. This was verified by inspecting the BHPS SN5151 data files: `ahhresp.tab` contains both `afihhmn` (raw income) and `aeq_moecd` (modified OECD equivalence scale) as separate columns, confirming that fihhmn is the pre-equivalisation value.

**Harmonisation approach:** The pipeline equivalises raw income by dividing `fihhmn` by `eq_moecd` from the household response file (hhresp), matching the modified OECD scale used in USoc's pre-equivalised `fihhmnnet1_dv`. This was verified at runtime: DEBUG logs confirm "equivalised income using eq_moecd" for each BHPS wave, with mean equivalised income of ~£902/month for wave a (1991), a plausible value. Year-specific medians were then computed from the equivalised income, and L/M/H bands classified using 60%/100% of contemporary median (matching the existing USoc approach).

**Income column resolution:** BHPS indresp files contain both `afihhmn` (raw income) and `afihhmni` (imputation flag, values 0/1). The extraction correctly selects `afihhmn` via a prioritised search order that checks for the income variable before the imputation flag.

---

## 2. BHPS-Era Sample

| Metric | Value |
|--------|-------|
| Trajectories | 8,509 |
| Mean length | 14.5 years |
| Year range | 1991–2008 |
| Persons (employment) | 32,290 |
| Persons (income) | 29,018 |

---

## 3. Spanning Sample

| Metric | Value |
|--------|-------|
| Total trajectories (all eras) | 32,763 |
| Spanning trajectories | **8,459** |
| BHPS-only | 2,753 |
| USoc-only | 21,551 |
| Sufficient for TDA | **Yes** (≥ 500) |

---

## 4. BHPS-Era PH Results

| Metric | H₀ | H₁ |
|--------|-----|-----|
| Total persistence | 10,763.2 | 823.0 |
| Persistent loops | — | 1,114 |

Computed via maxmin VR, L=5000 landmarks, PCA-20D embedding.

---

## 5. BHPS-Era Null Results (n=500 permutations)

| Null Model | H₀ p-value | H₁ p-value | H₀ observed | H₀ null mean |
|------------|-----------|-----------|-------------|--------------|
| Label shuffle | 0.272 | 0.396 | 10,763.2 | 10,740.1 |
| Cohort shuffle | 0.272 | 0.396 | 10,763.2 | 10,740.1 |
| Order shuffle | **0.000** | 0.520 | 10,763.2 | 9,906.1 |
| Markov-1 | 1.000 | 1.000 | 10,763.2 | 12,753.8 |

**Interpretation:**
- **Order shuffle H₀ p=0.00**: Sequential ordering of states matters — random permutation destroys H₀ structure. Consistent with USoc findings.
- **Markov-1 p=1.0**: Markov-1 null generates *more* persistence than observed, indicating observed trajectories have *less* topological complexity than unconstrained Markov chains. Same pattern as USoc.
- **Label/cohort shuffle non-significant**: Label permutation does not significantly change persistence structure, as expected for this test type.

---

## 6. Spanning Null Results (n=500 permutations)

| Null Model | H₀ p-value | H₁ p-value | H₀ observed | H₀ null mean |
|------------|-----------|-----------|-------------|--------------|
| Label shuffle | 0.856 | 0.772 | 12,853.4 | 12,903.0 |
| Order shuffle | **0.000** | 0.374 | 12,853.4 | 11,940.5 |
| Markov-1 | 1.000 | 1.000 | 12,853.4 | 15,596.5 |

Same qualitative pattern as BHPS-only and USoc-only: order matters (H₀), Markov overshoots.

---

## 7. BHPS-Era Regime Structure (k=8 optimal)

| Regime | n | Dominant State | Emp% | Low Inc% | Stability |
|--------|-----|---------------|------|----------|-----------|
| 0 | 780 | IL | 49.3% | 37.1% | 0.22 |
| 1 | 2,491 | EH | 94.4% | 0.2% | 0.83 |
| 2 | 662 | EH | 56.5% | 11.8% | 0.46 |
| 3 | 375 | EM | 51.2% | 44.4% | 0.20 |
| 4 | 776 | EH | 47.3% | 10.4% | 0.46 |
| 5 | 1,626 | IL | 0.0% | 43.8% | 0.44 |
| 6 | 868 | EH | 62.0% | 24.4% | 0.31 |
| 7 | 931 | EH | 91.4% | 28.8% | 0.40 |

**Comparison with USoc-era (k=7):** BHPS finds k=8, one more regime. The core regime types are comparable:
- **Stable employed high-income**: Regime 1 (BHPS, stability=0.83) ↔ USoc stable employment regime
- **Economically inactive, low income**: Regime 5 (BHPS, emp=0.0%, stability=0.44) ↔ USoc inactivity regime
- **Churning/mixed regimes**: Regimes 0, 3, 6 (BHPS, stability 0.20–0.31) ↔ USoc transitional regimes

The additional BHPS regime (k=8 vs k=7) may reflect the longer trajectory length (14.5 vs ~11 years) providing more granularity, or genuine structural differences in 1990s labour market dynamics.

---

## 8. State Distribution Comparison: BHPS vs USoc

| State | BHPS (%) | USoc (%) | Spanning (%) |
|-------|---------|---------|-------------|
| EH | 42.7 | 36.9 | 40.2 |
| EM | 12.8 | 14.1 | 13.5 |
| EL | 4.5 | 7.1 | 5.4 |
| IH | 9.6 | 12.8 | 10.5 |
| IM | 12.7 | 12.4 | 13.0 |
| IL | 14.8 | 13.1 | 14.3 |
| UH | 0.6 | 0.9 | 0.6 |
| UM | 0.7 | 1.0 | 0.8 |
| UL | 1.7 | 1.7 | 1.6 |

**Key differences:**
- BHPS has higher EH (42.7% vs 36.9%) — consistent with pre-2008 full employment era
- USoc has higher EL (7.1% vs 4.5%) and IH (12.8% vs 9.6%) — more low-paid employment and high-income inactivity in post-2008 era
- Unemployment rates similar (~3% total in both eras)
- Spanning trajectories intermediate, as expected

---

## 9. Code Changes Summary

### Modified files:
- **`trajectory_tda/data/income_band.py`**: Fixed BHPS income column selection order (`fihhmn` before `fihhmni`); fixed `[] or USOC_WAVES` truthiness bug to `usoc_waves if usoc_waves is not None else USOC_WAVES`
- **`trajectory_tda/data/employment_status.py`**: Same truthiness bug fix for wave list parameters
- **`trajectory_tda/data/trajectory_builder.py`**: Added `survey_era` column to metadata (`bhps_only` / `usoc_only` / `spanning`)

### New files:
- `trajectory_tda/scripts/bhps_pipeline.py` — BHPS-only trajectory extraction
- `trajectory_tda/scripts/bhps_tda_pipeline.py` — BHPS TDA pipeline (steps 3-6)
- `trajectory_tda/scripts/spanning_pipeline.py` — Spanning trajectory extraction + TDA pipeline
- `trajectory_tda/scripts/bhps_build_steps.py` — Step-by-step build helper
- `trajectory_tda/scripts/bhps_verify_counts.py` — Verification script

### Results directories:
- `results/trajectory_tda_bhps/` — BHPS-era pipeline results (all checkpoints)
- `results/trajectory_tda_spanning/` — Spanning pipeline results (all checkpoints)

---

## 10. Unexpected Findings

1. **BHPS finds k=8 regimes vs USoc k=7**: The additional regime may warrant discussion. Could be an artefact of longer trajectories or genuine structural change.

2. **Cohort shuffle falls back to label shuffle**: The cohort_shuffle null type falls back to label_shuffle when no cohort information is provided. This is consistent behaviour (the BHPS pipeline didn't pass cohort data). The cohort_shuffle results are therefore identical to label_shuffle.

3. **H₁ p-values non-significant across all nulls**: H₁ (loop) structure is not significantly different from any null model in the BHPS sample, same as USoc. This suggests the topological signal is primarily in H₀ (connected components / clusters).

4. **Order shuffle H₀ p=0.00 in both eras**: The most important null test (does sequential ordering matter?) gives the same strong result in BHPS (1991-2008) as in USoc (2009-2022). This is strong cross-era replication.
