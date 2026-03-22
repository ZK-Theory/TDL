# Agent 3: New Analyses — ✅ ALL TASKS COMPLETE

**Core plan reference:** `trajectory_tda/plan-fourthDraftMajorRevision.md` — Phase 3 step 3, Phase 4 steps 1–2, Phase 6 step 6
**Orchestration:** `trajectory_tda/agent-plans/00-orchestration.md`
**Handoff:** `trajectory_tda/agent-plans/AGENT3_HANDOFF_AGENT5.md`
**Completion date:** 2026-03-14

## Scope

Create three new analysis scripts and extend the escape logistic regression. All four code targets are unique to this agent — no file conflicts with other agents.

## Files You Own (EXCLUSIVE WRITE)

- `trajectory_tda/analysis/intra_regime_compactness.py` (NEW)
- `trajectory_tda/analysis/nssec_missingness.py` (NEW)
- `trajectory_tda/analysis/bootstrap_null_stability.py` (NEW)
- `trajectory_tda/analysis/age_stratified.py` (EDIT)

**DO NOT edit any other existing files.**

## Task A: Intra-Regime Compactness Test (Phase 3, Concern #2)

**Purpose:** Test whether GMM regime assignments are order-dependent by comparing within-regime compactness on observed vs order-shuffled embeddings.

**Create:** `trajectory_tda/analysis/intra_regime_compactness.py`

**Algorithm:**
1. Load observed trajectories and GMM regime assignments (from `05_analysis.json` or recompute)
2. Compute observed n-gram embedding (unigrams + bigrams)
3. Fit PCA on observed n-gram vectors → save PCA transform (loadings)
4. Project observed embeddings through PCA → observed PCA-20D coordinates
5. For each GMM regime k, compute mean within-regime pairwise Euclidean distance in PCA-20D
6. For i in 1..500:
   a. Order-shuffle each trajectory (shuffle temporal order within each person's state sequence)
   b. Compute shuffled n-gram embedding
   c. Project through the **FROZEN** PCA transform (from step 3 — do NOT refit PCA)
   d. Using the **ORIGINAL** GMM regime assignments (from step 1 — do NOT reassign), compute within-regime pairwise distances
7. For each regime: compare observed compactness vs null distribution (z-score, p-value)

**CRITICAL:** PCA loadings must be frozen from the observed data. Re-fitting PCA on each shuffle confounds the comparison with rotation. The existing null pipeline in `permutation_nulls.py` already freezes PCA — follow the same pattern.

**Output:** JSON with per-regime { observed_compactness, null_mean, null_std, z_score, p_value }

**Interpretation:** If compactness is indistinguishable under order-shuffle, GMM regimes are not order-dependent (supporting the "parallel analyses" framing). If compactness changes significantly, regime structure is partially order-dependent.

## Task B: NS-SEC Missingness Analysis (Phase 4, Concern #5)

**Purpose:** Test whether the 39.1% missing parental NS-SEC is non-random with respect to trajectory characteristics.

**Create:** `trajectory_tda/analysis/nssec_missingness.py`

**Analysis:**
1. Load trajectory data with covariates (from pipeline outputs or `06_stratified.json`)
2. Split into NS-SEC-present (n≈16,623) and NS-SEC-absent (n≈10,657)
3. Compare:
   - Regime distribution (chi-squared test for independence: regime × NS-SEC availability)
   - State frequency distributions (mean E/U/I rates, mean L/M/H rates)
   - Trajectory characteristics (mean length, mean stability, dominant state distribution)
   - Birth cohort distribution
4. Logistic regression predicting missingness (NS-SEC absent = 1) from:
   - Regime assignment
   - Mean income level
   - Employment rate
   - Trajectory length
   - Birth cohort
5. Report whether the subsample used for stratified analysis is representative

**Output:** JSON with test results, comparison tables, logistic regression coefficients

## Task C: Bootstrap Null Stability (Phase 6, Concern: ARI instability)

**Purpose:** Verify that null-model p-values are stable across bootstrap regime assignments, given the bootstrap ARI lower CI of 0.461.

**Create:** `trajectory_tda/analysis/bootstrap_null_stability.py`

**Algorithm:**
1. Load observed embeddings
2. For b in 1..25 bootstrap draws:
   a. Fit GMM on bootstrap-resampled embeddings → get regime assignments for full sample
   b. Run order-shuffle null (n=100 permutations) using bootstrap regime assignments
   c. Run Markov-1 null (n=100 permutations) using bootstrap regime assignments
   d. Record p-values for H₀ and H₁
3. Report distribution of p-values across 25 bootstrap draws:
   - Order-shuffle H₀: should remain significant (p < 0.05) across all draws
   - Markov-1 H₀: should remain non-significant across all draws
   - Any draw where qualitative conclusion flips is a flag

**Note:** Use n=100 permutations per bootstrap draw (not 500) to keep compute feasible. 25 × 100 = 2,500 total permutations per null type.

**Output:** JSON with per-bootstrap-draw p-values + summary statistics

## Task D: Extend Escape Logistic Regression (Phase 4, Concern #7)

**Edit:** `trajectory_tda/analysis/age_stratified.py`

**Changes to `escape_logistic_regression()` and `_build_escape_dataframe()`:**

1. **Add predictors:** `birth_cohort` is already computed in `_build_escape_dataframe()` but never added to the model. Add it. Also add `parental_ns_sec` (where available) and `initial_regime` as predictors.

2. **Categorical encoding:** Use one-hot encoding for `birth_cohort` (5 bins), `initial_regime` (k categories), and `parental_ns_sec` (3 categories). Drop one reference category each to avoid collinearity.

3. **Confidence intervals:** Add `model.conf_int(alpha=0.05)` to output. Report 95% CIs for all odds ratios.

4. **Separation diagnostics:**
   - Fit standard Logit first to capture the baseline
   - Check for extreme coefficients (|β| > 10) or extreme p-values (< 10⁻⁵⁰) as separation indicators
   - Implement Firth penalised regression as the **primary** estimation method (not fallback). Use `firthlogist` package if available, or `statsmodels` L2-penalised logit with small penalty.
   - Report both standard and Firth estimates side by side if they differ meaningfully

5. **Output format:** Return dict with { coefficients, odds_ratios, confidence_intervals_95, p_values, pseudo_r2, aic, bic, separation_detected: bool, firth_used: bool }

## Handoff Summary (produce when complete)

Report to Agent 5 (Paper):

**From Task A (intra-regime compactness):**
- Per-regime compactness: observed vs null, z-scores, p-values
- Overall conclusion: are regimes order-dependent?

**From Task B (NS-SEC missingness):**
- Chi-squared test result (statistic, p-value)
- Key differences between NS-SEC present vs absent groups
- Whether the stratified subsample is representative

**From Task C (bootstrap null stability):**
- p-value ranges across 25 bootstrap draws for order-shuffle and Markov-1
- Whether any draws flip the qualitative conclusion
- Summary: are null-model results robust to regime assignment instability?

**From Task D (escape regression):**
- New odds ratios with 95% CIs for all predictors
- Whether Firth correction was needed (probably yes)
- Key changes from original model (age-only) to extended model
- Whether separation was detected and how it was handled

## Verification

- Task A: verify PCA loadings are frozen (compare explained variance from observed vs refit on shuffled — they should differ if Done correctly, since we use observed loadings)
- Task B: verify n_present + n_absent = total sample size
- Task C: verify observed p-values from bootstrap draw 1 approximately match the main analysis p-values
- Task D: `python -m pytest tests/trajectory/ -v` — ensure existing tests still pass
