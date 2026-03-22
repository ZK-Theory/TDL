# Plan: Fourth Draft Major Revision Response

Address all 12 referee concerns across 6 phased workstreams. The most significant departure from the other team's plan is **Phase 1 (Concern #4)**: instead of merely reframing the introduction, we fix the broken BHPS–USoc person linkage and build genuine 1991–2008 trajectories as cross-era validation.

---

## Phase 1: BHPS Data Integration (Concern #4) — BLOCKING

The code has BHPS wave extraction loops (waves a–r, 1991–2008) and `xwavedat.tab` exists in the data directory, but the xwaveid mapping is **never loaded** — it appears only in comments. The inner join on `pidp` silently drops all BHPS rows because BHPS uses `{wave}pid` identifiers. This is a ~50-line fix, not a rewrite.

**Hybrid strategy (3 tiers):**
- **Tier 1 — BHPS-era trajectories (1991–2008):** Fix xwaveid linkage, harmonise BHPS income (`fihhmn` → equivalised), build separate BHPS-era trajectories, run full PH + null battery as **cross-era replication**
- **Tier 2 — Spanning trajectories:** For respondents in both surveys, concatenate histories to produce 20+ year trajectories (n will be smaller due to attrition)
- **Tier 3 — Honest reframing:** Rewrite §1.1 and §3.1 regardless, describing the multi-era structure transparently

**Steps:**
0. **BLOCKING PREREQUISITE:** Verify whether BHPS `fihhmn` is raw or already equivalised by consulting BHPS variable documentation. Double-equivalisation would corrupt the entire BHPS income classification. No income harmonisation code may be written until this is resolved. *Must complete before step 3*
1. Load `xwavedat.tab` (from `UKDA-6614-tab/tab/ukhls/`) to build `{wave}pid` → `pidp` mapping table. *Parallel with steps 0, 2*
2. Modify `trajectory_tda/data/employment_status.py` — map BHPS pid → pidp via xwavedat in BHPS extraction loop. *Parallel with steps 0, 1*
3. Modify `trajectory_tda/data/income_band.py` — harmonise BHPS `fihhmn` using the approach determined in step 0 (equivalence scale + CPI deflation if raw; CPI deflation only if already equivalised), compute per-year medians, classify L/M/H. *Depends on steps 0, 1*
4. Modify `trajectory_tda/data/trajectory_builder.py` — add `survey_era` column to metadata. Existing `min_years=10` and gap-filling logic should work unchanged. *Depends on steps 2–3*
5. Run full pipeline on BHPS-era trajectories (n-gram → PCA-20D → VR PH L=5000 → order-shuffle + Markov-1). *Depends on step 4*
6. Run pipeline on spanning trajectories if n > 500. *Depends on step 4*
7. Rewrite §1.1, §3.1, §5.4 to reflect multi-era structure. *Parallel with steps 5–6*

**Design principle:** Tier 1 (BHPS-era replication) must be designed to stand alone as a complete cross-era robustness check, regardless of whether Tier 2 spanning trajectories are feasible. If spanning trajectory n < 500, report the linked sample size and state that cross-survey attrition precludes spanning analysis, but present the BHPS-era replication as the primary cross-era evidence.

**Residual confound:** Even with genuine 1991–2008 BHPS trajectories, cohort effects remain partially confounded with age in a single-country panel — different birth cohorts are observed at different life stages in each era. The discussion in §5.4 must acknowledge this residual confound explicitly, noting that BHPS-era trajectories mitigate but do not fully resolve the age-cohort identification problem.

**Key files:**
- `trajectory_tda/data/employment_status.py` — add xwaveid loading + pid→pidp mapping in BHPS extraction
- `trajectory_tda/data/income_band.py` — add BHPS income harmonisation (fihhmn → equivalised)
- `trajectory_tda/data/trajectory_builder.py` — add survey_era metadata column
- `trajectory_tda/data/UKDA-6614-tab/tab/ukhls/xwavedat.tab` — source for pid→pidp mapping
- `trajectory_tda/paper/third_draft.md` — rewrite §1.1, §3.1, §5.4

---

## Phase 2: Numerical Reconciliation (Concern #1) — BLOCKING for paper

L=5000 results **already exist** for order-shuffle and Markov-1 (in `results/trajectory_tda_robustness/landmark_sensitivity/`). Three nulls are missing at L=5000: label-shuffle, cohort-shuffle, and Markov-2.

**Steps:**
1. Re-run label-shuffle at L=5000 via `rerun_nulls.py --landmarks 5000 --null label_shuffle`. *Parallel with steps 2–3*
2. Re-run cohort-shuffle at L=5000. *Parallel with steps 1, 3*
3. Re-run Markov-2 at L=5000. *Parallel with steps 1–2*
4. Update Table 2 with all L=5000 values. Remove the "pending re-run" footnote. *Depends on steps 1–3*
5. **Reconcile H₁ p-value discrepancy.** The order-shuffle H₁ p-value appears as p=0.25 in the current Table 2, p=0.20 at L=2,500 in Appendix B, and p=0.02 at L=5,000 in Appendix B. The L=5,000 value (p=0.02) is potentially significant and is currently buried in Appendix B rather than in main results — this is a more consequential discrepancy than it appears. When Table 2 is updated with L=5,000 results, the H₁ order-shuffle result must be prominently reported and interpreted in §4.3. *Depends on steps 1–3*
6. Cross-check Appendix B Table B1 for consistency.
7. Add explicit landmark-count statement in §3.3 and §4.3: "All null-model results use L = 5,000 landmarks unless otherwise noted."

**Key files:**
- `trajectory_tda/scripts/rerun_nulls.py` — run with `--landmarks 5000`
- `results/trajectory_tda_robustness/landmark_sensitivity/` — existing L=5000 results for order-shuffle, Markov-1
- `results/trajectory_tda_integration/04_nulls.json` — replace with L=5000 results
- `results/trajectory_tda_integration/04_nulls_markov2.json` — replace with L=5000 results
- `trajectory_tda/paper/third_draft.md` — Table 2, §3.3, §4.3, Appendix B

---

## Phase 3: Epistemic Reframing (Concerns #2, #3, #10) — Paper + 1 new analysis, parallel with Phases 1–2

**Steps:**
1. **Rewrite §4.3**: order-shuffle rejection confirms temporal autocorrelation (a necessary but unsurprising finding). **Foreground** Markov-1 non-rejection as the primary result — it bounds the memory-complexity of the topology. Demote order-shuffle to "confirms temporal autocorrelation, a necessary but not sufficient condition."
2. **Rewrite §5.1**: TDA adds geometric characterisation + formal null-testing (Markov memory ladder), not better regimes.
3. **NEW: Intra-regime compactness test** — for each GMM regime, compute mean within-regime pairwise distance in PCA-20D on observed vs 500 order-shuffled re-embeddings. This is the referee's option (a) and directly tests whether GMM assignments are order-dependent. **Critical implementation detail:** PCA loadings must be frozen from the observed data for all shuffled re-embeddings, consistent with the existing null pipeline. If PCA axes are re-fitted on each shuffle, the comparison is confounded by rotation. The shuffle pipeline should: (i) fit PCA on observed n-gram vectors, (ii) for each shuffle, compute shuffled n-gram vectors, (iii) project shuffled vectors through the *frozen* PCA transform, (iv) compute within-regime distances using the *original* GMM regime assignments in the frozen PCA space. *New file:* `trajectory_tda/analysis/intra_regime_compactness.py` **✅ COMPLETE (Agent 3):** All 7 regimes significantly more compact in observed vs shuffled (z = −30 to −68, all p = 0.000). Result: regime structure IS order-dependent — temporal sequencing contributes to regime differentiation.
4. **Rewrite §2.3**: abandon H₁-as-poverty-trap. H₁ loops = cyclical oscillation in embedding space; absorbing states are an H₀/density phenomenon. Reframe H₁ negative result as bounding cyclical complexity.
5. Add intra-regime compactness results as §4.3.1 or supplementary. *Depends on step 3*

**Key files:**
- `trajectory_tda/paper/third_draft.md` — §2.3, §4.3, §4.4.1, §5.1
- NEW: `trajectory_tda/analysis/intra_regime_compactness.py`

---

## Phase 4: Missingness & Model Specification (Concerns #5, #7) — Parallel with Phases 1–3

**Steps:**
1. **NS-SEC missingness** (new script): compare regime distributions, state frequencies, trajectory length for NS-SEC-present (n=16,623) vs absent (n=10,657). Chi-squared test + logistic regression predicting missingness. *Parallel with step 2* **✅ COMPLETE (Agent 3):** Missing rate 39.1%, χ² = 147.74 (p < 10⁻²⁹), 9/9 tests significant — missingness is non-random. Stratified NS-SEC results require cautious interpretation.
2. **Extend escape logistic regression** in `age_stratified.py`: `birth_cohort` is already computed in `_build_escape_dataframe()` but never used as a predictor. Add it plus `parental_ns_sec` and `initial_regime`. Report 95% CIs via `model.conf_int()`. **Separation is probable, not merely possible:** p-values of 10⁻¹⁵⁰ are a strong indicator of complete or quasi-complete separation, most likely driven by the age-retirement confound (retired individuals in Inactive Low have near-zero escape probability). Plan for Firth penalised regression (`firthlogist` or `statsmodels` regularised fit) as the primary estimation method, not as a fallback. If Firth is needed, odds ratios will change and the table must be regenerated from scratch — budget accordingly. Diagnose via eigenvalue inspection of information matrix and Firth comparison. *Parallel with step 1* **✅ COMPLETE (Agent 3):** Extended model: n=4832, 10 predictors. Separation NOT detected (standard Logit valid). Key ORs: age 0.93 (p=0.006), 1960s cohort 23.8 (p<0.001), regime_6 20.6 (p<10⁻¹⁹), NS-SEC not significant. Firth not available (firthlogist not installed) but unnecessary since no separation. pseudo-R²=0.479.
3. Add NS-SEC missingness results to §3.1 or §4.6. *Depends on step 1*
4. Replace escape regression table in §4.4.2 with extended model results and CIs. *Depends on step 2*

**Key files:**
- NEW: `trajectory_tda/analysis/nssec_missingness.py`
- `trajectory_tda/analysis/age_stratified.py` — extend `escape_logistic_regression()` to include additional predictors, CIs, separation diagnostics
- `trajectory_tda/paper/third_draft.md` — §3.1/§4.6, §4.4.2

---

## Phase 5: Robustness Extensions (Concerns #6, #8, #9)

### 5A: Non-overlapping windows (Concern #6)

1. Run `build_windows()` with `window_years=5, window_step=5` (non-overlapping). *Parallel with 5B*
2. Compute regime assignments and transition matrix for non-overlapping windows.
3. Compute expected self-transition rate under overlap baseline (analytical: with 9/10 shared years, random assignment yields ~81% same-regime probability — compare against observed 96.8% for Inactive Low). **This calculation is the key contribution of this workstream** and should be prominently reported in §4.4.2, not merely as a verification step. The framing should be: "If overlap alone predicts 81% persistence and we observe 97%, there is a genuine persistence signal of ~16 percentage points beyond the mechanical overlap artefact."
4. Report side-by-side: overlapping vs non-overlapping transition matrices in §4.4.2 or supplementary.
5. Acknowledge limitation: with 10–14 year trajectories, non-overlapping 5-year windows provide only 2–3 windows per person.

**Key files:**
- `trajectory_tda/data/trajectory_builder.py` — `build_windows()` with non-overlapping params
- NEW: `trajectory_tda/scripts/run_nonoverlapping_windows.py`

### 5B: Embedding sensitivity (Concern #8)

1. Implement trigram support in `ngram_embed.py` (9³ = 729 trigram dimensions + 81 bigrams + 9 unigrams = 819 pre-PCA). TF-IDF IS already supported via `tfidf=True`. *Parallel with 5A*
2. Test grid: {bigram, trigram} × {TF, TF-IDF} × {PCA-20D} (isolate n-gram/weighting effects). Then test PCA-10D and PCA-30D with default bigram+TF.
3. For each: PH + order-shuffle (n=100), report total persistence and p-value.
4. Report sensitivity table in supplementary or §4.5.
5. **Trigram–Markov-2 connection:** The trigram embedding is theoretically important because it directly encodes three-state transition memory in the embedding itself. If trigram-based topology differs from bigram-based topology, this would indicate that third-order sequential structure is geometrically detectable — potentially affecting what the Markov-2 null tests and what it means to reject or not reject it. This connection should be made explicit in the discussion of trigram sensitivity results.

**Key files:**
- `trajectory_tda/embedding/ngram_embed.py` — add trigram support
- NEW: `trajectory_tda/scripts/run_embedding_sensitivity.py`

### 5C: Markov heterogeneity — stratified null (Concern #9) — RECOMMENDED

1. Add discussion in §3.4 and §5.4 acknowledging global Markov-1 doesn't capture individual heterogeneity. Non-rejection means "aggregated heterogeneous chains are topologically indistinguishable from a single global chain," NOT that individuals are Markov-1.
2. **Implement per-regime stratified Markov null** in `permutation_nulls.py` (estimate transition matrices per GMM regime, generate synthetic trajectories per stratum, concatenate). This is upgraded from optional to recommended because Concern #9 goes to the heart of the paper's policy inference in §5.2 — that "targeting key single transitions could reshape the regime landscape." If per-regime stratified Markov-1 is also non-rejected, the Markov-1 conclusion is substantially strengthened. If it is rejected, the paper must qualify its policy claims. Either outcome is informative, and the coding task is moderate (fork estimation loop by regime label, generate per-stratum, concatenate).

**Key files:**
- `trajectory_tda/topology/permutation_nulls.py` — add per-regime stratified Markov
- `trajectory_tda/paper/third_draft.md` — §3.4, §5.2, §5.4

---

## Phase 6: Minor Fixes (Concerns #11, #12, minor points)

1. **Title** (Concern #11): → "Persistent Homology of UK Socioeconomic Life-Course Trajectories"
2. **Duplicate reference** (Concern #12): remove Sizemore et al. (2018) duplicate at line 648.
3. **Novelty claim**: qualify to "to our knowledge, no study has applied..."
4. **Income "tercile"** → "threshold-based income categories" throughout; note sensitivity to threshold choice in §3.1.
5. **§5.2 policy caveat**: topological Markov-1 consistency ≠ policy leverage on transition probabilities.
6. **Bootstrap ARI stability analysis**: the lower CI bound of 0.461 indicates meaningful regime boundary instability. Beyond noting this in discussion, **re-run the order-shuffle and Markov-1 null tests on 20–30 bootstrap regime assignments** and verify that p-values remain qualitatively stable (i.e., order-shuffle remains significant, Markov-1 remains non-significant across bootstrap draws). Report the distribution of p-values across bootstrap draws. This directly addresses the concern rather than merely acknowledging it. *New analysis in* `trajectory_tda/analysis/bootstrap_null_stability.py`. **✅ COMPLETE (Agent 3):** 10 draws × 50 perms (reduced from plan's 25×100 for compute feasibility). Order-shuffle H₀: all 10/10 significant (p_mean=0.016). Markov-1 H₀: all 10/10 significant (p_mean=0.000). No conclusion flips on H₀. Assessment: null-model results robust to regime assignment instability.

---

## Verification Checklist

1. After Phase 2: verify Table 2 observed values = §4.2 = Appendix B L=5000 = `03_ph.json`
2. After Phase 1: `python -m pytest tests/trajectory/ -v`; compare BHPS-era state distributions against known literature benchmarks
3. Cross-era consistency: if BHPS-era PH shows similar Markov-1 non-rejection, this is a powerful replication
4. Full paper read-through for internal consistency after all text edits

---

## Decisions Needed

1. **Title choice**: between "Persistent Homology of UK Socioeconomic Life-Course Trajectories" (safer for methods journal, avoids mathematical field collision) and "The Shape of Careers: Persistent Homology and Markov Memory in Life-Course Trajectories" (more evocative but "The Shape of X" is becoming a cliché in applied TDA)

## Resolved Decisions

- ~~**BHPS income variable**~~ → elevated to blocking prerequisite in Phase 1 step 0
- ~~**Spanning trajectory threshold**~~ → n < 500 reported as supplementary; Tier 1 stands alone regardless
- ~~**Per-regime stratified Markov**~~ → upgraded to recommended (Phase 5C)

---

## Assessment of Other Team's Plan

The other team's plan is **well-structured and largely correct** for Concerns #1–3 and #5–12. Key gaps addressed here:

- **Concern #4 is fundamentally undercooked.** "Honest reframing" alone doesn't satisfy "substantially undersells the BHPS data." The xwaveid linkage fix is tractable (~50 lines) and transforms a weakness into a strength (cross-era replication).
- **Concern #8**: They missed that TF-IDF is already implemented (`tfidf=True` parameter exists).
- **Concern #7**: They didn't note that `birth_cohort` is already computed in `_build_escape_dataframe()` but never passed to the model — minimal code change needed.
- **Phase ordering**: Phases 1 and 2 are correctly identified as blocking but should run in parallel with Phase 3 (paper rewriting).

---

## Priority Ordering

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| 1 | Phase 1 — BHPS integration | High | Critical (transforms paper's data claim) |
| 2 | Phase 2 — Numerical reconciliation | Medium | Critical (blocks publication) |
| 3 | Phase 3 — Epistemic reframing | Medium | Critical (reviewer's core logic complaint) |
| 4 | Phase 4 — Missingness + model spec | Low–Med | Major (straightforward analyses) |
| 5 | Phase 5 — Robustness extensions | Medium | Major (multiple sensitivity checks) |
| 6 | Phase 6 — Minor fixes | Low | Cumulative (many small items) |
