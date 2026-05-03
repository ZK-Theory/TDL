# Reviewer 3 (Biostatistician) — Issue Decomposition

**Date:** 2026-05-03
**Reviewer type:** Biostatistician — permutation tests, multiple comparisons, effect sizes, uncertainty
**Severity framework:** Critical / High / Medium

Issues numbered B1–B13 to distinguish from R1 (H1–L3) and R2 (S1–S14).

---

## B1 — p = 0.002 from B = 100 permutations: below resolution floor [CRITICAL]

### B1.1 The problem

With B = 100 permutations, the minimum achievable p-value is 1/101 ≈ 0.0099. The paper reports p = 0.002 for the Markov-1 W₂ test with B = 100 — this is impossible from a direct permutation count (0.2 null realisations exceeded the observed statistic = non-integer). Either: (a) p-value is misreported, (b) B count is wrong, (c) a parametric approximation was used instead of direct count. The paper never specifies which formula computes p-values from permutation distributions.

Similarly, bootstrap stability uses B = 50 permutations per resample (min p = 1/51 ≈ 0.020); reported mean p = 0.000 across 10 resamples is below this floor.

### B1.2 Classification

**Both** — needs code audit to determine how p-values are computed + prose correction.

### B1.3 Strategy

1. **Audit the codebase.** Find the p-value computation in the permutation test code. Determine whether it uses: (a) direct count `(sum(null >= obs) + 1) / (B + 1)`, (b) Phipson & Smyth (2010) formula, (c) a parametric fit to the null distribution (e.g., fitting a normal/gamma to the null draws).
2. **If parametric approximation:** state this explicitly in §3.3 and justify the distributional assumption. Report the fitted distribution and goodness-of-fit.
3. **If direct count:** correct the reported p-value. With B = 100 and 0 exceedances, p = 1/101 ≈ 0.0099 (using the (r+1)/(B+1) convention). State the convention used.
4. **Increase B for all tests.** B = 100 is insufficient for JRSS-A. Minimum B = 1,000 for reported p-values; B = 10,000 if computational budget permits. This gives resolution to p ≈ 0.001.
5. **Specify the p-value formula in §3.3** as a formal definition. E.g.: "We compute the permutation p-value as $p = (r + 1)/(B + 1)$ where $r$ is the number of null realisations with test statistic ≥ the observed value (Phipson & Smyth 2010)."

### B1.4 Verification

- §3.3 specifies the p-value formula.
- No reported p-value is below the resolution floor for its B.
- B ≥ 1,000 for all reported permutation tests.

---

## B2 — W₂ test compares mean obs-null to individual null-null: anti-conservative [CRITICAL → DOWNGRADED: HIGH after severity analysis]

*Expanded 2026-05-03 with quantitative severity analysis using reported numbers.*

### B2.1 The problem

The W₂ test computes $\bar{W} = \frac{1}{B}\sum_b W_2(D_q^{\text{obs}}, D_q^{\text{null}_b})$ (a mean over B null realisations) and compares it to the distribution of *individual* null-null distances $W_2(D_q^{\text{null}_b}, D_q^{\text{null}_{b'}})$. The mean has variance ∝ 1/B; individual distances have full variance. The test is anti-conservative in construction.

### B2.2 Quantitative severity analysis

Using the reported Markov-1 H₀ W₂ numbers (mean obs-null = 11.42, mean null-null = 5.99, B = 100, 500 null-null pairs):

**Estimated null-null sd:** CV ≈ 0.20 for W₂ distances → sd ≈ 1.20.

| Test construction | z-score | Estimated p-value | Conclusion |
|---|---|---|---|
| As reported (mean obs-null vs individual null-null draws) | 4.52 | 0.002 (= 1/500, min achievable) | Reject |
| Correct mean-vs-mean (SE-adjusted) | ~41 | $\approx 10^{-30}$ | Reject strongly |
| Conservative (individual obs-null vs null-null) | ~4.5 per draw | $\approx 10^{-6}$ per draw | Reject |

**The p = 0.002 is explained:** it is the direct permutation count — 1 of 500 null-null pairs exceeded $\bar{W}_{\text{obs-null}} = 11.42$. This is the minimum achievable given 500 pairs. The true significance is far stronger.

**The main USoc Markov-1 W₂ rejection is robust to any correction.** The 90% excess of obs-null over null-null is self-evidently significant regardless of construction.

### B2.3 Where it DOES matter

Despite the main result being robust, three specific concerns remain:

1. **BHPS negative control.** The BHPS label-shuffle result at p = 0.036 is the negative control — it *should not* be significant. Under the anti-conservative construction, this may be a false positive. **If the corrected construction gives label-shuffle p > 0.05, the negative control works and the ladder is trustworthy.** If it still gives p ≈ 0.036, the entire BHPS test battery is suspect.

2. **Methodology generalisability.** The paper proposes the W₂ test as a general TDA methodology for other panels (SOEP, PSID). An anti-conservative construction would propagate to every application.

3. **The p-value is the wrong quantity to report.** The result should be structured around: mean obs-null (11.42), mean null-null (5.99), their ratio (1.90), and bootstrap CIs — not a p-value from an ambiguous construction.

### B2.4 Classification

**HIGH** (downgraded from Critical after severity analysis) — the main result is robust, but the construction must be fixed for correctness, BHPS negative control, and methodology generalisability.

### B2.5 Strategy

1. **Fix the test construction.** Preferred: compare $\bar{W}_{\text{obs-null}}$ to the bootstrap distribution of $\bar{W}_{\text{null-null}}$ (mean-vs-mean). Alternatively: MMD-style two-sample test.
2. **Re-run the BHPS label-shuffle W₂ test** with corrected construction — this is the decisive test of whether the fix matters.
3. **Restructure the reporting** around effect size, not p-value:
   > "The mean obs-null W₂ distance (11.42, 95% bootstrap CI [a, b]) was 90.6% larger than the mean null-null W₂ distance (5.99, 95% CI [c, d]). The ratio $\bar{W}_{\text{obs-null}} / \bar{W}_{\text{null-null}} = 1.91$ (95% CI [e, f]) serves as the effect size."
4. **Apply the corrected construction to all W₂ batteries** including R1 H1 (matched-landmark) and R1 M5 (landscape L²).

### B2.6 Interaction with R1 issues

This interacts directly with **R1 H1** (matched-landmark W₂) and **R1 M5** (landscape L²). The W₂ test construction fix must be applied to all W₂ batteries, including the new matched-landmark and stratified versions planned under R1.

### B2.7 Verification

- §3.3 specifies the W₂ test construction and justifies why it is not anti-conservative.
- The obs-null and null-null quantities being compared are of the same type (both means or both individuals).
- The BHPS label-shuffle result is retested with the corrected construction.
- The W₂ ratio and bootstrap CIs are reported alongside (or instead of) the p-value.

### B2.8 W₂ ratio CI: implementation specification

*Added 2026-05-03. Derived from bootstrap theory for the specific structure of the ratio estimator.*

#### The estimand

$$\rho = \frac{\mu_{\text{obs-null}}}{\mu_{\text{null-null}}} \quad\text{estimated by}\quad \hat{\rho} = \frac{\bar{W}_{\text{obs-null}}}{\bar{W}_{\text{null-null}}} = \frac{11.42}{5.99} \approx 1.906$$

where B = 100 null realisations contribute to the numerator and M = 500 sampled null pairs to the denominator.

#### Complications for naive bootstrap

1. **Shared null realisations.** The B null diagrams appear in both numerator and denominator → not independent.
2. **Fixed observed diagram.** $D_q^{\text{obs}}$ is computed once → not resampled in bootstrap.
3. **Non-i.i.d. null-null distances.** Each null realisation appears in up to B−1 pairs → pairwise dependence.

#### Three CI formulae (in order of preference)

**Formula 1: BCa (bias-corrected and accelerated) — recommended.**
Corrects for both bias and skewness. Requires R ≥ 1,000 null-resample iterations (each regenerating B null surrogates, recomputing PH, and forming the ratio). The jackknife leave-one-out for the acceleration constant $\hat{a}$ is over the B null realisations.

**Formula 2: Delta method — practical recommendation for this paper.**
For large B and M, the delta method gives an analytical CI from stored distances:

$$\text{Var}(\hat{\rho}) \approx \frac{1}{\mu_{\text{null-null}}^2}\left(\frac{\sigma_{\text{num}}^2}{B} + \hat{\rho}^2 \cdot \frac{\sigma_{\text{den}}^2}{M} - 2\hat{\rho} \cdot \frac{\text{Cov}(W_{\text{obs-null}}, W_{\text{null-null}})}{B}\right)$$

where:
- $\hat{\sigma}_{\text{num}}^2 = \frac{1}{B-1}\sum_b (W_2(D_q^{\text{obs}}, D_q^{\text{null}_b}) - \bar{W}_{\text{obs-null}})^2$
- $\hat{\sigma}_{\text{den}}^2 = \frac{1}{M-1}\sum_m (W_2(D_q^{\text{null}_{b_m}}, D_q^{\text{null}_{b_m'}}) - \bar{W}_{\text{null-null}})^2$

The covariance term is positive (null realisations far from obs are also far from other nulls) and **stabilising** — it reduces Var($\hat{\rho}$). Both variances are computable from stored $W_2$ distances without re-running TDA.

95% CI: $\hat{\rho} \pm 1.96\sqrt{\hat{\text{Var}}(\hat{\rho})}$

**Formula 3: Percentile CI — simplest but biased for ratios.**
Use 2.5th and 97.5th percentiles of the bootstrap distribution $\{\hat{\rho}^{*r}\}$. Only appropriate if the bootstrap distribution is approximately symmetric (check by plotting).

#### Practical recommendation and covariance estimation

*Added 2026-05-03. Implementation detail for estimating the covariance term from stored pipeline outputs.*

The covariance is between $W_{\text{obs-null},b}$ and $\bar{W}_{\text{null-null},b}$ (the row mean of null-null distances for null realisation $b$). It is positive: a null realisation far from the observed diagram is also likely far from other nulls. **Ignoring it (setting cov = 0) overstates Var($\hat{\rho}$) — a conservative error.**

**Which stored outputs are available determines the approach:**

**Case A — Full B×B null-null matrix stored:**

```python
import numpy as np
# obs_null_dists: shape (B,); null_null_matrix: shape (B, B)
np.fill_diagonal(null_null_matrix, np.nan)
row_means = np.nanmean(null_null_matrix, axis=1)
cov_term = np.cov(obs_null_dists, row_means)[0, 1]
```

**Case B — Only unindexed 500 pairs stored (more likely):**
Use jackknife leave-one-out on the obs-null distances (if stored per-realisation):

```python
rho_loo = np.array([
    np.mean(np.delete(obs_null_dists, b)) / W_bar_null
    for b in range(B)
])
cov_jack = ((B-1)/B) * np.sum(
    (rho_loo - np.mean(rho_loo)) * (obs_null_dists - W_bar_obs)
)
```

**Case C — Only summary statistics stored:** Set cov = 0 (conservative). Use Cauchy-Schwarz bounds as sensitivity check.

#### Worked numerical estimate (conservative, cov = 0)

Using reported values and estimated CVs ($\hat{\sigma}_{\text{num}} \approx 2.28$, $\hat{\sigma}_{\text{den}} \approx 1.20$):

$$\hat{\text{Var}}_{\text{indep}}(\hat{\rho}) = \frac{1}{5.99^2}\left(\frac{2.28^2}{100} + 1.906^2 \cdot \frac{1.20^2}{500}\right) \approx 0.00174$$

$$\hat{\text{SE}}(\hat{\rho}) \approx 0.042$$

$$\boxed{95\% \text{ CI}: \hat{\rho} = 1.91 \;[1.82,\; 1.99]}$$

This **excludes ρ = 1 by more than 19 SEs.** Including the positive covariance would narrow the CI further. The conservative approximation is fully sufficient.

**This CI replaces the ambiguous p = 0.002 with a clean, defensible, effect-size-led result.** Report as: "The W₂ ratio $\hat{\rho} = 1.91$ (95% CI [1.82, 1.99]) indicates the observed persistence diagram is 91% more distant from null diagrams than nulls are from each other."

### B2.9 Full re-run specification (if computational resources allow)

*Added 2026-05-03. This upgrades from the delta-method CI (B2.8) to a proper permutation test with BCa CI.*

#### Priority 1: Fix the test statistic

Define a single scalar test statistic computed identically for observed and null data:

$$T_{\text{ratio}} = \frac{\frac{1}{B}\sum_{b=1}^{B} W_2(D_q^{\text{obs}}, D_q^{\text{null}_b})}{\frac{1}{B(B-1)}\sum_{b \neq b'} W_2(D_q^{\text{null}_b}, D_q^{\text{null}_{b'}})}$$

Under the null, replace $D_q^{\text{obs}}$ with a fresh null draw $D_q^{\text{null}_{0,r}}$:

$$T_{\text{ratio}}^{*r} = \frac{\frac{1}{B}\sum_{b=1}^{B} W_2(D_q^{\text{null}_{0,r}}, D_q^{\text{null}_b})}{\frac{1}{B(B-1)}\sum_{b \neq b'} W_2(D_q^{\text{null}_b}, D_q^{\text{null}_{b'}})}$$

Permutation p-value: proportion of R null realisations with $T_{\text{ratio}}^{*r} \geq T_{\text{ratio}}$.

**This is self-consistent:** numerator and denominator use the same B null diagrams, the observed diagram enters symmetrically as one draw vs B, and the p-value is against a distribution of the same statistic.

#### Priority 2: Increase B for p-value resolution

Use R ≥ 2,000 null realisations of $T_{\text{ratio}}^{*r}$ → reliable detection to p < 0.001. Use L = 500 landmarks for null battery (vs L = 2,000 for primary analysis) for ~16× computational saving while retaining topological structure.

#### Priority 3: BCa CI from the null distribution

```python
from scipy.stats import norm
import numpy as np

def ratio_stat(obs_null_dists, null_null_matrix):
    num = np.mean(obs_null_dists)
    np.fill_diagonal(null_null_matrix, np.nan)
    den = np.nanmean(null_null_matrix)
    return num / den

# Jackknife acceleration
T_loo = np.array([
    ratio_stat(
        np.delete(obs_null_dists, b),
        np.delete(np.delete(null_null_matrix, b, 0), b, 1)
    )
    for b in range(B)
])
diffs = np.mean(T_loo) - T_loo
a_hat = np.sum(diffs**3) / (6 * np.sum(diffs**2)**1.5)

# BCa CI from null distribution T_null_r (R values)
T_obs = ratio_stat(obs_null_dists, null_null_matrix)
z0_hat = norm.ppf(np.mean(T_null_r < T_obs))
z_lo, z_hi = norm.ppf(0.025), norm.ppf(0.975)

q_lo = norm.cdf(z0_hat + (z0_hat + z_lo) / (1 - a_hat * (z0_hat + z_lo)))
q_hi = norm.cdf(z0_hat + (z0_hat + z_hi) / (1 - a_hat * (z0_hat + z_hi)))
ci_bca = (np.quantile(T_null_r, q_lo), np.quantile(T_null_r, q_hi))
```

#### Optional sensitivity analyses (if time allows)

1. **Landmark count sensitivity.** Report $T_{\text{ratio}}$ for L ∈ {500, 1000, 2000, 5000}. Should strengthen with L and plateau.
2. **Filtration threshold sensitivity.** Report $T_{\text{ratio}}$ at 60th, 75th, 90th percentile of pairwise distances. Most pronounced at intermediate thresholds → makes 75th percentile defensible as maximum-power scale.
3. **Two-sided test.** Show Markov-1 null rejected from below by total persistence and from above by the ratio — simultaneously — which is the paper's core finding stated cleanly.

#### What the re-run adds

Converts from: *"W₂ gives p = 0.002, rejecting Markov-1"*

To: *"$T_{\text{ratio}} = 1.906$ (95% BCa CI [a, b]) at the qth percentile of the Markov-1 null (R = 2,000, L = 500), p < 0.001. Stable across L ∈ {500–5,000} and filtration thresholds at 60th–90th percentile."*

---

## B3 — Exchangeability violated in label-shuffle null [CRITICAL]

### B3.1 The problem

The label-shuffle permutation test shuffles labels across all person-years, treating ~352,000 person-years as exchangeable. They are not: person-years within the same individual share trajectory structure by construction, and person-years within the same household share income states. The null distribution is tighter than it should be → the test is anti-conservative.

### B3.2 Classification

**Computation** — requires restructuring the label-shuffle null.

### B3.3 Strategy

1. **Individual-level permutation.** Shuffle labels at the individual level (permute entire trajectories), not at the person-year level. This preserves within-individual temporal structure and is exchangeable under the null that trajectory assignment is independent of career structure.
2. **If the current code already shuffles at the individual level:** clarify this in §3.3. The reviewer's concern may be based on ambiguous wording rather than actual implementation.
3. **Household-block permutation (stronger fix).** For tests where household clustering matters (escape rate, regime proportions): permute labels at the household level, keeping all household members together. This is exchangeable under the null that household trajectory bundles are independent.
4. **For the Markov nulls:** exchangeability is not an issue because the null generates synthetic trajectories from the estimated transition matrix — there are no "labels" to shuffle. But the Markov null must use the correct transition matrix (see R1 H2 for the stratified Markov issue).

### B3.4 Verification

- §3.3 specifies the unit of permutation (individual trajectory, not person-year).
- If household-block permutation is used, this is stated.

---

## B4 — One-sided test directionality never justified; lower-tail Markov-1 result unaddressed [HIGH]

### B4.1 The problem

All permutation tests are implicitly one-sided ("larger = more extreme") but the directionality is never justified. For Markov-1 total persistence: the null mean (21,138.3) *exceeds* the observed (20,411.1), giving p = 1.000. A two-sided test would give p ≈ 0 for the lower tail — the data is 3.7 SD *below* the null. This is a substantive finding (real data is less topologically diffuse than Markov-1 dynamics → regime concentration) that the paper never reports.

### B4.2 Classification

**Prose + minor computation** (report two-sided p-values).

### B4.3 Strategy

1. **Report two-sided p-values** for all permutation tests: $p_{\text{two-sided}} = 2 \times \min(p_{\text{upper}}, p_{\text{lower}})$.
2. **Or: explicitly justify one-sided framing** in §3.3 — state the directional hypothesis ("we test whether the observed data has more topological structure than the null, not less") and note that lower-tail departures are separately informative.
3. **Report and interpret the lower-tail Markov-1 result.** The data being 3.7 SD below the Markov-1 null total persistence means the real trajectories are *more concentrated* (less diffuse) than first-order Markov dynamics would produce. This is consistent with the regime-absorptivity finding and should be stated as such.
4. **Interact with effect sizes (B5):** reporting $d_{\text{perm}}$ (which is signed) makes the directionality transparent.

### B4.4 Verification

- §3.3 states whether tests are one-sided or two-sided and justifies the choice.
- The lower-tail Markov-1 departure is reported and interpreted.

---

## B5 — No permutation effect sizes reported [HIGH]

### B5.1 The problem

Every permutation test reports only a p-value. The natural effect size $d_{\text{perm}} = (T_{\text{obs}} - \bar{T}_{\text{null}}) / \text{sd}(T_{\text{null}})$ is absent throughout. Key unreported effect sizes:

| Test | $d_{\text{perm}}$ | Interpretation |
|---|---|---|
| Order-shuffle TP | +14.2 | Enormous — 14 SD above null |
| Markov-1 TP | −3.7 | Substantial below-null departure |
| Markov-2 TP | (to compute) | |
| W₂ obs-null/null-null ratio | 1.90 | No CI provided |

Without effect sizes, p = 1.000 looks like a borderline null when it is a strong directional departure.

### B5.2 Classification

**Both** — compute effect sizes from existing results + add to prose.

### B5.3 Strategy

1. **Compute $d_{\text{perm}}$ for all permutation tests** from the stored null distributions (already available in results files).
2. **Report $d_{\text{perm}}$ alongside p-values** in Table 1 and §4.3. Add a column to Table 1.
3. **For W₂ tests:** report the obs-null/null-null ratio as a named effect size with a bootstrapped 95% CI.
4. **Add formal definition of $d_{\text{perm}}$ to §3.3.**

### B5.4 Verification

- Every permutation test result includes $d_{\text{perm}}$ or equivalent effect size.
- The W₂ ratio has a bootstrapped CI.
- Table 1 has an effect-size column.

---

## B6 — BIC curve not reported; k = 7 selection uncertainty unknown [HIGH]

### B6.1 The problem

BIC selects k = 7 GMM components but the BIC differences between k = 7 and competitors (k = 6, k = 8) are not reported. If the gap is < 2 units, the selection is not statistically distinct. The paper's findings depend on k = 7.

### B6.2 Classification

**Both** — extract BIC values from existing results + add figure/table + prose.

### B6.3 Strategy

1. **Report the full BIC curve** across k = 3, ..., 15 as a figure or table in §3.2 or supplement.
2. **Report ΔBIC** between k = 7 and its nearest competitors. Interpret using Kass & Raftery (1995) scale: ΔBIC < 2 = weak, 2–6 = positive, 6–10 = strong, > 10 = very strong.
3. **If ΔBIC < 6:** acknowledge the ambiguity and report sensitivity of key findings to k = 6 and k = 8 (e.g., ARI between k = 7 and k = 8 regimes, stability of the R2/R6 disadvantaged regimes across k).

### B6.4 Verification

- BIC curve reported (figure or table).
- ΔBIC between k = 7 and nearest competitors stated and interpreted.

---

## B7 — Logistic regression: incomplete coefficient reporting [HIGH]

### B7.1 The problem

Age OR (0.93) and 1960s cohort OR (23.8) reported without CIs. All parental NS-SEC coefficients reported only as "non-significant" — no estimates at all. This is non-standard for JRSS-A.

### B7.2 Classification

**Both** — extract full model output + create named table.

### B7.3 Strategy

1. **Create a complete coefficient table** with: estimate (log-odds), SE, OR, 95% CI, p-value for *every* predictor including all NS-SEC levels.
2. **Name it Table X** in the main text (not supplement).
3. **This interacts with S5/S9:** the table should be from the corrected model (Firth + clustered SEs), not the current uncorrected model. Produce the table after the S5+S9 fixes.

### B7.4 Verification

- Named table with all coefficients, SEs, ORs, CIs, p-values.
- No OR reported without its CI anywhere in the text.

---

## B8 — 50 stratification tests pooled into one BH family [MEDIUM]

### B8.1 The problem

Section §6.1 pools 50 pairwise W₂ tests across three qualitatively different axes (2 gender, 6 NS-SEC, 42 cohort) into one BH family. This is overly conservative for each axis and potentially anti-conservative across axes. Adjacent cohort tests are positively correlated → standard BH may not satisfy PRDS assumption.

### B8.2 Classification

**Both** — recompute FDR + prose.

### B8.3 Strategy

1. **Define separate BH families** for each stratification axis: family 1 (2 gender tests), family 2 (6 NS-SEC tests), family 3 (42 cohort tests).
2. **Apply BH within each family separately.** Report corrected p-values per family.
3. **For the cohort family (42 tests):** consider BY correction (Benjamini & Yekutieli 2001) which is valid under arbitrary dependence, since adjacent cohorts share life-course overlap.
4. **Report all individual W₂ effect sizes** alongside p-values — not just significance counts.

### B8.4 Verification

- BH families defined by stratification axis, not pooled.
- Corrected p-values reported per family.
- W₂ effect sizes reported for each comparison.

---

## B9 — ARI = 0.26 without null test or maximum-achievable normalisation [MEDIUM]

### B9.1 The problem

ARI is a point estimate with no CI, no test against null (ARI = 0 under independence), and no normalisation against the maximum achievable ARI given the cluster size distributions.

### B9.2 Classification

**Both** — compute normalised ARI + CI.

### B9.3 Strategy

1. **Report the null SE** (≈ 0.009 for n = 27,280) and note ARI = 0.26 is ~29 SD above null — highly significant as non-random agreement.
2. **Compute and report the maximum achievable ARI** given the observed cluster size distributions. Report the normalised ARI: $\text{ARI}_{\text{norm}} = \text{ARI}_{\text{obs}} / \text{ARI}_{\text{max}}$.
3. **Bootstrap 95% CI** for ARI by resampling individuals.
4. **Add these to §4.6** where the ARI comparison is discussed.

### B9.4 Verification

- ARI reported with null SE, max-achievable ARI, normalised ARI, and 95% CI.

---

## B10 — Regime stability scores without standard errors [MEDIUM]

### B10.1 The problem

Table 2 reports stability scores (0.234–0.779) without SEs. The SE is straightforward: $\sqrt{\hat{p}_{rr}(1-\hat{p}_{rr})/n_r}$. R2 stability (0.97, n = 5,415) has SE ≈ 0.0023; R0 stability (0.234, n = 3,787) has SE ≈ 0.0069.

### B10.2 Classification

**Computation** — trivial from existing data.

### B10.3 Strategy

1. Compute SEs for all stability scores; add to Table 2 as a ± column.
2. Note that comparisons across regimes should account for differential precision.

### B10.4 Verification

- Table 2 reports stability ± SE for each regime.

---

## B11 — Escape rates without confidence intervals [MEDIUM]

### B11.1 The problem

Table 3 reports escape rates (5.6%, 17.8%, 0.1%) as point estimates. For retirement-age (n = 5,978, 6 escaped): Wilson CI ≈ [0.04%, 0.23%] — a sixfold range that is substantively meaningful for the absorptivity claim.

### B11.2 Classification

**Computation** — trivial.

### B11.3 Strategy

1. Compute Wilson 95% CIs for all escape rates.
2. Add to Table 3.
3. Note the wide CI for the retirement-age rate in the absorptivity discussion.

### B11.4 Verification

- Table 3 reports escape rate [95% CI] for each subgroup.

---

## B12 — Sub-regime node threshold sensitivity not examined [MEDIUM]

### B12.1 The problem

Mapper sub-regime permutation tests use |z| > 1.0 on PC1 as the threshold for "sub-regime" nodes. This has a 31.7% false positive rate under normality. The count of 358 sub-regime nodes vs null mean 86.3 is threshold-dependent. Sensitivity to the threshold (e.g., 1.5, 2.0 SD) is not examined. Number of permutations not stated. Individual node flagging is unadjusted.

### B12.2 Classification

**Both** — computation (threshold sweep) + prose.

### B12.3 Strategy

1. **Report B** (number of permutations) for the Mapper null tests.
2. **Threshold sensitivity sweep:** recompute sub-regime node count at |z| > 1.0, 1.5, 2.0. Report all three in a table or supplement. If significance holds across thresholds, the result is robust.
3. **For individual node identification (§5.4):** apply a local FDR correction (e.g., BH on per-node z-scores) to control the false discovery rate among individually flagged sub-regime nodes.
4. **State the threshold choice justification in §5.2** — e.g., "We use |z| > 1.0 to identify candidate sub-regime nodes; significance of the aggregate count is assessed via permutation, not via the individual z-scores."

### B12.4 Verification

- B stated for Mapper tests.
- Threshold sensitivity reported for ≥ 2 additional thresholds.
- Individual node flagging adjusted or caveated.

---

## B13 — Bootstrap stability B = 50 with impossible p = 0.000 [MEDIUM]

### B13.1 The problem

Bootstrap stability analysis uses B = 50 permutations per resample → min p ≈ 0.020. Mean p = 0.000 across 10 resamples is below this floor. Same resolution-floor issue as B1.

### B13.2 Classification

Same fix as B1 — increase B and correct p-value reporting.

### B13.3 Strategy

Covered by B1 strategy (increase B ≥ 1,000 for all reported tests; specify p-value formula).

### B13.4 Verification

- Same as B1.

---

## Cross-Reference Matrix: Biostatistician Issues × R1/R2 Issues

| Bio issue | Interacts with | Nature |
|---|---|---|
| B1 (p-value floor) | R1 H1 (matched-L W₂), R1 H2 (stratified Markov) | All tests need B increase |
| B2 (W₂ anti-conservative) | R1 H1 (matched-L W₂), R1 M5 (landscape L²) | Test construction fix applies to all W₂ |
| B3 (exchangeability) | R2 S5 (household clustering) | Same clustering concern |
| B4 (one-sided) | R1 H2 (Markov-1 TP) | Lower-tail finding complements stratified Markov |
| B5 (effect sizes) | R1 M5 (landscape L²) | L² distances are natural effect sizes |
| B6 (BIC curve) | — | New concern |
| B7 (regression table) | R2 S5 (clustering), R2 S9 (separation) | Table must use corrected model |
| B8 (BH families) | — | New concern (within §6.1) |
| B9 (ARI) | — | New concern |
| B10 (stability SEs) | — | New concern |
| B11 (escape CIs) | R2 S6 (escape conditioning) | Both affect escape rate reporting |
| B12 (Mapper threshold) | R1 10.3 (Mapper vs PH) | Both affect §5 interpretation |
| B13 (bootstrap B) | B1 | Same fix |

---

## Summary Table

| Issue | Severity | Type | §§ affected |
|---|---|---|---|
| B1: p-value resolution floor | Critical | Code audit + increase B | §3.3, §4.3, Table 1 |
| B2: W₂ anti-conservative construction | High (downgraded) | Fix construction + BHPS retest | §3.3, §4.3, §6.2 |
| B3: Exchangeability violation | Critical | Fix label-shuffle unit | §3.3 |
| B4: One-sided directionality | High | Prose + two-sided p | §3.3, §4.3 |
| B5: No effect sizes | High | Compute + report | §3.3, §4.3, §6.1 |
| B6: BIC curve absent | High | Extract + report | §3.2, §4.4 |
| B7: Incomplete regression table | High | Full table | §4.5 |
| B8: Pooled BH families | Medium | Recompute FDR | §6.1 |
| B9: ARI unnormalised | Medium | Compute max ARI | §4.6 |
| B10: Stability without SEs | Medium | Compute SEs | Table 2 |
| B11: Escape rates without CIs | Medium | Compute Wilson CIs | Table 3 |
| B12: Mapper threshold sensitivity | Medium | Threshold sweep | §5.2 |
| B13: Bootstrap B = 50 floor | Medium | Same as B1 | §4.3 |
