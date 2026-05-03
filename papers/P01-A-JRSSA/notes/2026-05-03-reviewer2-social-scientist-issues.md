# Reviewer 2 (Quantitative Social Scientist) — Issue Decomposition

**Date:** 2026-05-03
**Reviewer type:** UK panel data / survey methodology expert
**Source review:** "Survey Data & Empirical Claims Review"
**Severity framework:** Uses reviewer's own Critical / High / Medium / Low–Medium ratings

This document decomposes every point in the review into individually addressable issues for integration into the master revision plan. Issues are numbered S1–S14 to distinguish from the TDA reviewer's H1–M5/L1–L3 numbering.

---

## S1/S2 — Revised Sample Construction: Continuity Filter + Survey Weights [CRITICAL]

*This section was substantially expanded on 2026-05-03 based on a detailed methodological proposal from R2 that unifies the continuity-filter problem (original S1) and the survey-weights problem (original S2) into a five-component revised sample construction.*

### S1.1 The problem precisely

The "10 consecutive years" selection rule retains 27,280 from 118,000+ (≈23%). The selection mechanism is non-random in the worst possible direction: the individuals most likely to be excluded are those with unemployment spells, caring gaps, health-driven inactivity, poverty-driven housing instability, and benefit-claim transitions — all of which cause survey non-contact and income non-response. The paper then studies disadvantage, churning, and escape from low-income regimes using a sample from which the most disadvantaged and most churning individuals have been systematically removed.

This is not a missing-data problem that can be patched. It is a **sample frame problem**: the analytic population is not "UK working-age adults" but "UK adults who were continuously observable in a household panel for a decade," which is a substantively different population with a different career trajectory distribution.

Start-year range 2009–2013 excludes refreshment samples (ethnic minority boost) and late entrants. The absent Supplement §S2 (promised in v1 §7.3) is noted.

USoc provides `lwtresp` longitudinal weights for attrition correction. The paper uses no weights anywhere. The 56% female sample vs ~50–51% weighted population confirms differential attrition. Regime proportions are not population estimates without weighting.

### S1.2 Current state in v1

- §3.1 states the selection criterion and sample size but provides no analysis of who is excluded.
- §7.3 mentions panel attrition citing Watson & Wooden (2012) and references "Supplement §S2" for attrition analysis — but **S2 is not written**.
- No comparison of included vs excluded respondents on any observable characteristic.
- No survey weights used anywhere. The 56% female figure is reported without comment.

### S1.3 Classification

**Both** — extensive new computation AND substantial prose. This is the single largest revision block.

### S1.4 What a valid revised construction requires

Three things must be addressed simultaneously:
1. **Relaxing the continuity requirement** without introducing trajectory-length confounds into the embedding
2. **Correcting for selection into the analytic sample** using survey weights or model-based methods
3. **Being honest about the residual selected population** when the above cannot fully solve the problem

### S1.5 Strategy: Five-Component Revised Sample Construction

#### Component 1 — Gap-tolerant minimum-length rule

**Current flaw:** "Consecutive" does extra work beyond "sufficient length" — it excludes trajectories with gaps.

**Fix:** Replace the continuity filter with:

> *Retain individuals with at least 10 valid employment-income observations within any 14-year window, with gaps of at most 2 consecutive missing years.*

This relaxes "consecutive" to "sufficiently dense within a window." The 14-year outer window matches the maximum USoc observation period; the 10-of-14 threshold means trajectories with up to four missing waves are included. The existing forward-fill imputation (already used for 1–2 year gaps, affecting 4.9% of person-years) can be extended to handle gaps.

**Expected effect on sample size:** Analyses on similar UK panels (e.g., Berthoud & Blekesaune 2007 using BHPS) suggest a 10-of-14 rule with gap tolerance retains approximately 45–55% of eligible respondents rather than 23%.

**Handling variable trajectory length in the embedding:**

**(a) Length-variance standardisation.** For a trajectory of length $T$, the variance of a bigram frequency $\hat{p}_{ab} = c_{ab}/(T-1)$ is approximately $p_{ab}(1-p_{ab})/(T-1)$. Standardising by the asymptotic standard error before PCA upweights short trajectories appropriately:

$$\tilde{p}_{ab}^{(i)} = \frac{\hat{p}_{ab}^{(i)}}{\sqrt{\hat{p}_{ab}(1-\hat{p}_{ab})/(T_i - 1)}}$$

**(b) Trajectory length as a covariate.** Include $T_i$ (observed trajectory length) as an explicit variable in all regression models and as a stratification variable in permutation tests. This separates variation in n-gram frequencies due to career structure from variation due to observation length.

#### Component 2 — Two-stage inverse-probability weighting

USoc's `lwtresp` corrects for standard wave non-response but not the additional continuity selection imposed by the 10-year threshold.

**Step 1 — Wave-level response propensity.** For each individual, model the probability of having a valid employment-income observation in each wave as a function of time-stable covariates (age, gender, education, region, tenure type, ethnicity). This produces an inverse-probability-of-observation weight at the wave level. USoc's `indscub_xw` file provides the needed variables.

**Step 2 — Trajectory-level continuity propensity.** Model the probability of satisfying the trajectory inclusion rule (10+ valid observations in 14 waves) as a function of wave-1 observables. The inverse of this predicted probability, trimmed at the 1st and 99th percentiles to prevent extreme weights, is the trajectory-level selection weight.

**Combined weight:** $w_i = w_i^{\text{USoc}} \times w_i^{\text{continuity}}$ corrects for both standard panel attrition and additional continuity selection.

**What to weight:**
- **Descriptive statistics and regression:** use combined weights.
- **TDA pipeline (PCA, PH, Mapper):** cannot be directly weighted. Use **weighted bootstrap resampling** — draw trajectories with probability proportional to survey weight — to construct the point cloud submitted to TDA, then report sensitivity of diagram-level results.
- Report weighted + unweighted regime proportions side by side. Expected changes: R2/R6 expand, R1 contracts.

#### Component 3 — MICE for income non-response within observed waves

The current imputation handles employment-status gaps (forward-fill for 1–2 year gaps) but not **income non-response within observed waves**. USoc item non-response on household income runs at ~15–20% per wave, with higher rates among self-employed, benefit-claiming, and low-income households.

**Fix:** Multiple imputation by chained equations (MICE) for income non-response within observed waves, with predictors:
- Prior and subsequent wave income (exploiting longitudinal structure)
- Employment status (observed)
- Household composition
- Region and wave fixed effects

20 imputations, Rubin-pooled estimates for regime-membership and escape-rate statistics. Report TDA results for the **complete-case** point cloud as a robustness check.

#### Component 4 — Bounding analysis for permanent attritors

Even after Components 1–3, individuals who **leave the panel entirely** cannot be recovered. USoc wave-1 to wave-2 attrition is ~12%, rising to cumulative ~40% by wave 10. These are systematically more mobile, more economically unstable.

**Fix:** Manski-style worst-case bounds. Under pessimistic assumptions about attritors (all allocated to R2 or R6):

| Statistic | Current (continuity-selected) | Lower bound (pessimistic) |
|---|---|---|
| R6 Low-Income Churn share | 7.6% | ~12–15% (estimated) |
| R1 Secure High-Employment share | 27.0% | ~18–21% (estimated) |
| Overall escape rate | 5.6% | ~3–4% (estimated) |
| Working-age escape rate | 17.8% | ~11–14% (estimated) |

Report as a **named sensitivity analysis in §4.5 or §7.3**, not buried in supplement. The paper's core claim — escape from disadvantage is rare — is *strengthened* by showing the continuity filter probably makes it look less rare than it actually is.

#### Component 5 — Honest scope statement

**Fix:** Add to §3.1: "The analytic population is individuals with sufficient longitudinal engagement in USoc/BHPS to support trajectory reconstruction — a named limitation, not a silent filter." Plus:
- Reframe all population-level claims with "among continuously observed panel members" qualifier.
- Note start-year constraint (2009–2013 = post-crisis entrants only).
- Note 56% female as consistent with differential attrition; report weighted sex ratio.

### S1.6 Decision: Full re-extraction vs sensitivity-only

The five-component proposal is the *ideal* revision. However, Components 1 and 3 require **re-extracting and re-embedding the entire sample**, which means re-running the full TDA pipeline (PCA, GMM, PH, Mapper, null batteries) on a new point cloud. This is a major computational undertaking that interacts with every R1 issue (H1, H2, M3, M4, M5, L3 all reference specific results from the current 27,280-point cloud).

**Pragmatic decision tree:**

- **Option A (full re-extraction):** Implement Components 1–5 as the primary analysis. Current 27,280 sample becomes a robustness check. All R1 computational results must be re-run. Total additional wall-clock: ~150–200 h on top of R1 work.
- **Option B (sensitivity-only):** Keep the 27,280 sample as the primary analysis. Implement Components 2, 4, 5 (weighting, bounding, scope statement) in full. Implement Component 1 as a **sensitivity check** (re-extract with 10-of-14 rule, run GMM only, report regime-structure stability without re-running full TDA pipeline). Defer Component 3 (MICE for income) to supplement as a robustness note. Total additional wall-clock: ~25–40 h.

**Recommendation:** Option B for the initial v2 submission, with Option A designated as a revision-response strategy if the journal requires it. Option B addresses the reviewer's critical concern (honest scope, weighted estimates, bounding analysis) without requiring a full pipeline re-run.

### S1.7 Artefacts

**Under Option B (recommended):**
- `papers/P01-A-JRSSA/drafts/v2-supplement-S2-attrition.md` — full attrition analysis (included vs excluded).
- `results/trajectory_tda_integration/selection_sensitivity/gmm_10of14_<date>.json` — GMM on gap-tolerant sample.
- `results/trajectory_tda_integration/selection_sensitivity/ipw_weights_<date>.json` — two-stage IPW weights.
- Weighted descriptive statistics table (supplement or main text).
- Weighted + clustered logistic regression output.
- Bounding analysis table in §4.5 or §7.3.
- Updated §3.1 (selection-bias paragraph, scope statement, weighting note), §4.5 (bounds), §7.3, abstract.

**Under Option A (if required):**
- All of the above, plus full re-run of the TDA pipeline on the gap-tolerant sample.
- All R1 artefacts re-generated on the new sample.

### S1.8 Verification

- §S2 exists and reports included-vs-excluded comparison on ≥ 5 baseline characteristics.
- §3.1 contains an explicit selection-bias paragraph naming the direction of bias.
- §3.1 names the weight variable and explains which analyses are weighted.
- Table 2 has weighted column (or supplement equivalent).
- §4.5 logistic regression uses survey weights and household-clustered SEs.
- §4.5 or §7.3 reports bounding analysis for regime proportions and escape rates.
- The abstract and all regime-proportion claims are qualified as conditional on panel continuity.
- No sentence implies regime proportions are population estimates without qualification.

---

## S3 — USoc income variable not specified [HIGH]

### S3.1 Reviewer claim

The paper does not specify which USoc income variable is used. Candidates: `fihhmnnet3_dv` (monthly net), `fihhmngrs_dv` (gross), `hhnetinc_dv`. The choice matters for the low-income threshold.

### S3.2 Current state in v1

§3.1 says "equivalised household income" with "modified OECD scale (`eq_moecd`)" but does not name the raw income variable.

### S3.3 Classification

**Prose-only** — the variable is already chosen in the codebase; it just needs to be stated.

### S3.4 Strategy

1. **Identify the exact variable in the codebase.** Check `trajectory_tda/data/income_band.py` or equivalent for the USoc variable name.
2. **State it in §3.1** with a one-sentence justification (net vs gross, before/after housing costs).
3. **Clarify the equivalisation procedure:** which scale (modified OECD — already stated), applied to which base variable, producing which derived variable.

### S3.5 Verification

- §3.1 names the exact USoc income variable (e.g., `fihhmnnet3_dv`) and states whether it is gross or net, before or after housing costs.

---

## S4 — `jbstat` harmonisation undocumented; BHPS–USoc state spaces partially non-comparable [HIGH]

### S4.1 Reviewer claim

(a) `jbstat` coding changed across USoc waves (zero-hours, gig work categories). No harmonisation documented. (b) BHPS uses different `jbstat` categories; ILO-unemployment distinction absent in early BHPS waves; "inactive" encompasses different sub-reasons. The nine-state crossing is "almost certainly not identical across surveys." (c) Zero-hours/gig workers classified as "employed" but with income profiles like unemployed — the EL state (5.7%) likely contains a significant gig component.

### S4.2 Current state in v1

§3.1 states the nine-state crossing but provides no documentation of how `jbstat` was harmonised across waves or surveys.

### S4.3 Classification

**Both** — needs documentation of the harmonisation procedure (prose) AND ideally a sensitivity check (computation).

### S4.4 Strategy

1. **Document the harmonisation procedure.** Write a new supplement sub-section (within S1 or as a new S6) specifying: (a) which `jbstat` codes map to E/U/I in each USoc wave; (b) how wave-to-wave coding changes were handled; (c) which BHPS variables (`jbhas`, `jboff`, `jbstat`) were used and how they map to the same E/U/I classification; (d) how the ILO-unemployment definition was applied in early BHPS waves where it was not a native category.
2. **Acknowledge the non-comparability in §6.2.** Add a paragraph stating that the BHPS and USoc state spaces are constructed to be as comparable as possible but are not identical, and list the specific differences (ILO unemployment definition, inactive sub-categories). Downgrade the "replication" language to "cross-era robustness check in a partially comparable state space."
3. **Zero-hours/gig economy note.** Add a brief discussion in §3.1 or §7.3 acknowledging that EL contains zero-hours and gig workers whose employment is substantively different from standard employment. Note that USoc added a zero-hours contract indicator in later waves; report the proportion of EL individuals on zero-hours contracts if the data permits.
4. **Sensitivity: exclude zero-hours from "employed."** If feasible, reclassify zero-hours contract holders as a distinct state or as "unemployed" and check whether regime structure changes. If infeasible within scope, flag as future work with an honest assessment of the likely impact.

### S4.5 Artefacts

- New supplement section: "Employment status harmonisation across USoc waves and BHPS–USoc linkage."
- Updated §3.1, §6.2 prose.

### S4.6 Verification

- A reader can reconstruct the E/U/I classification from the supplement for any USoc wave and any BHPS wave.
- §6.2 does not call the BHPS analysis "replication" without noting state-space non-comparability.

---

## S5 — Household clustering in the logistic regression [HIGH]

*This section was substantially expanded on 2026-05-03 with quantitative bias estimates, a three-tier model hierarchy, and analysis of the clustering-separation interaction.*

### S5.1 The problem

The paper models escape from disadvantaged regimes using logistic regression on *n* = 4,832 individuals. The outcome and all predictors (initial regime, age, birth cohort, parental NS-SEC) are individual-level. But the income variable that defines regime membership is **equivalised household income** — two adults in the same household share an identical income state in every wave, are assigned to the same or closely related regimes by construction, and their escape outcomes are correlated through shared household economic shocks.

This is a two-level clustering problem. Standard logistic regression assumes independent observations. When observations are clustered within households, the estimated standard errors are **anticonservative** — too small, producing CIs that are too narrow and p-values that are too small.

### S5.2 Quantitative bias estimate

For binary outcomes in panel social data, household-level ICCs for labour market outcomes typically run 0.10–0.35. For income-band-based regime membership, the ICC is likely toward the higher end (the escape event is partly a household-level event via equivalised income).

| ICC | Mean HH size | DEFF | Effective *n* | SE inflation |
|---|---|---|---|---|
| 0.15 (conservative) | 2.3 | 1.20 | ~4,027 | ×1.10 |
| 0.25 (realistic) | 2.3 | 1.33 | ~3,632 | ×1.15 |

**Impact on headline results:**

| Result | Nominal (unclustered) | Clustered-corrected (estimated) |
|---|---|---|
| R6 vs R2 escape OR = 20.56, CI [10.65, 39.69] | $p < 10^{-19}$ | Still highly significant; CI widens modestly |
| Age OR = 0.93/year | $p = 0.006$ | Likely survives; may move to $p \approx 0.01\text{–}0.02$ |
| 1960s cohort OR = 23.8 | $p < 0.001$ | Survives if CI is wide enough — but see S9 separation |
| **Parental NS-SEC non-significant** | Not reported | **Vulnerable — see §S5.3** |

The very large ORs (20.56, 23.8) survive a 10–15% SE inflation. **Parental NS-SEC is the vulnerable finding.**

### S5.3 Why parental NS-SEC is the vulnerable finding

The paper's most sociologically consequential claim is that parental class origin is non-significant after conditioning on initial regime. Clustering correction makes this *harder* to establish — inflated SEs make it more difficult to detect any effect. The NS-SEC null result may be a **combination of**:

1. **Non-random missingness bias** (S7) — suppressing the true effect
2. **Household clustering** — inflating standard errors
3. **Genuine non-significance**

These three sources are not distinguishable without addressing all three simultaneously.

**Family-of-origin clustering (second clustering structure).** Parental NS-SEC is measured at the *parental household* level. Adults in the analytic sample who grew up in the same household share an *identical* parental NS-SEC value. For siblings who both appear in the USoc panel, their NS-SEC is not just correlated — it is identical. Standard clustered SEs on current household do not account for this family-of-origin clustering. A full treatment requires a cross-classified random effects model with both current-household and family-of-origin random effects.

### S5.4 Current state in v1

Not discussed. The logistic regression in §4.5 reports no clustering adjustment.

### S5.5 Classification

**Both** — needs re-estimation with corrected model AND substantial prose additions.

### S5.6 Strategy: Three-tier model hierarchy

#### Tier 1 (minimum fix): Clustered standard errors

Refit with SEs clustered on `hidp` (USoc household identifier). One-line change in statsmodels/R/Stata. Does not change point estimates; widens CIs by $\sqrt{\text{DEFF}} \approx 1.10\text{–}1.15$.

#### Tier 2 (better fix): Mixed-effects logistic regression

Replace standard logistic regression with a **GLMM** with random intercept for current household:

$$\log \frac{P(\text{escape}_{ij})}{1 - P(\text{escape}_{ij})} = \beta_0 + \beta_1 \text{regime}_i + \beta_2 \text{age}_i + \beta_3 \text{cohort}_i + \beta_4 \text{NS-SEC}_i + u_j$$

where $u_j \sim \mathcal{N}(0, \sigma^2_u)$ is the household random effect and $j$ indexes households. Directly models the ICC, separates within-household from between-household variance, gives correct SEs. The estimated $\hat{\sigma}^2_u$ is directly interpretable: if close to zero, clustering is negligible.

#### Tier 3 (best fix): Cross-classified random effects

For a complete treatment of the parental NS-SEC claim:

$$\log \frac{P(\text{escape}_{ijk})}{1 - P(\text{escape}_{ijk})} = \mathbf{x}_{ijk}'\boldsymbol{\beta} + u_j^{\text{HH}} + u_k^{\text{FOO}}$$

where $u_j^{\text{HH}}$ is the current-household effect and $u_k^{\text{FOO}}$ is the family-of-origin effect. This accounts for siblings sharing both parental NS-SEC and early-life economic environment. Family-of-origin links available via `ppid` (parent personal identifier) in USoc's `xwavedat`.

### S5.7 Interaction with quasi-separation (S9)

The clustering and separation problems interact: clustered SEs are already inflated, but near-separation inflates SEs further in an asymmetric way. The combination means reported CIs are neither correctly sized (too narrow from ignored clustering) nor correctly shaped (asymmetric near separation). **Both corrections must be applied simultaneously** — see S9 for the Firth penalisation component.

### S5.8 For TDA analyses

PH and Mapper operate on the point cloud and do not produce standard errors in the conventional sense. The null-model tests use permutation p-values that do not assume independence. Note this distinction: "Permutation tests are valid under exchangeability of trajectories within each null model; household clustering does not affect permutation validity because the null distributions are computed by resampling the same (clustered) data."

### S5.9 Family-of-origin clustering: USoc data implementation

*Added 2026-05-03 based on USoc data structure specialist input.*

#### Variables for constructing family-of-origin links

The cross-wave file `xwavedat.dta` contains:
- **`pidp`** — permanent individual identifier, stable across all waves and surveys.
- **`ppid`** — `pidp` of the respondent's natural/adoptive father, if the father is a panel member. Non-zero only when the father was directly interviewed.
- **`mpid`** — `pidp` of the respondent's natural/adoptive mother, if she is a panel member. Same condition.

Two respondents are siblings if they share the same non-zero `ppid` **or** `mpid`.

#### Construction procedure (connected components)

1. **Build parent-child edge list** from `xwavedat`: extract (child `pidp`, parent `pidp`) pairs from both `ppid` and `mpid` columns, dropping zeros/missings.
2. **Extract sibling pairs** via shared parent: two children sharing the same `parent_pidp` are siblings.
3. **Compute connected components** using `igraph::components()` in R (or union-find). This handles multi-sibling families, half-siblings via one shared parent, and multigenerational chains.
4. **Assign singleton cluster IDs** to individuals with no identified sibling — use their own `pidp`. Singletons contribute no within-cluster variance in the GLMM and do not bias the estimate.

```r
library(igraph)
edges <- sibling_pairs  # data.frame with col1=pidp_i, col2=pidp_j
g <- graph_from_data_frame(edges, directed = FALSE)
comp <- components(g)
foo_cluster <- data.frame(
  pidp = as.integer(names(comp$membership)),
  foo_id = comp$membership
)
```

#### Coverage limitations

| Source | Coverage | Notes |
|---|---|---|
| `ppid`/`mpid` in `xwavedat` | ~15–25% of all respondents; **~10–15% of analytic sample** (working-age adults whose parents may be elderly/deceased) | Only when parent was directly interviewed |
| BHPS genealogy file (`bhps_all.dta`) | Substantially higher for BHPS-origin subsample | Co-residence based across all 18 BHPS waves; links parent-child pairs even if parent was never the identified respondent. Covers most of the 8,459 spanning individuals. |
| Wave-1 household proxy (`hidp` wave 1) | Young co-resident adults only (aged 16–24 at entry) | Captures co-resident siblings at baseline; misses adult siblings who had already left home |

**Implication for the cross-classified GLMM:** The family-of-origin random effect can only be estimated for the minority with identified siblings. The rest are treated as singletons, effectively setting their family-of-origin variance contribution to zero. The model therefore *underestimates* the family-of-origin ICC — making it a **conservative** test of whether family-of-origin clustering matters.

#### ICC pre-check procedure

Before fitting the full cross-classified model, compute the family-of-origin ICC via a null GLMM:

```r
library(lme4)
m_foo <- glmer(escaped ~ 1 + (1 | foo_id),
               data = analytic_sample,
               family = binomial,
               control = glmerControl(optimizer = "bobyqa"))
icc_foo <- VarCorr(m_foo)$foo_id[1] / (VarCorr(m_foo)$foo_id[1] + pi^2/3)
```

**Decision thresholds:**
- ICC < 0.02 → family-of-origin clustering negligible; current-household clustered SEs sufficient.
- ICC 0.02–0.05 → borderline; report sensitivity with and without family-of-origin level.
- ICC > 0.05 → cross-classified model required.

Given low `ppid`/`mpid` coverage, the ICC will be estimated with wide uncertainty. A sensitivity analysis comparing results with and without the family-of-origin level is the appropriate approach regardless of the point estimate.

### S5.10 Additional data requirements

1. **Report the number of unique households** in the sample. If the ratio of individuals to households is close to 1, clustering is minimal; if many households contribute 2+ members, the concern is serious.
2. **Address the shared-income-state construction** in prose: two partners with the same household income but different employment statuses occupy different cells in the nine-state space. The income dimension is shared but the employment dimension is not.
3. **Compute the number of identified sibling clusters** and their size distribution in the analytic sample.

### S5.11 Pragmatic decision

- **Minimum for v2:** Tier 1 (clustered SEs on `hidp`) + Firth penalisation (S9). Report unique household count and ICC estimate.
- **Full for v2 if time permits:** Tier 2 (mixed-effects logistic) + Firth. Report $\hat{\sigma}^2_u$.
- **Tier 3 (cross-classified GLMM):** Only if the paper wants to make strong claims about parental class after proper variance decomposition. Recommended for the revision-response if journal requests it. Requires: (a) constructing the `foo_id` via the procedure above; (b) ICC pre-check; (c) using the BHPS genealogy file to improve coverage for spanning individuals.
- **The bigger payoff from Tier 3** is not the random effects estimate itself but the **within-sibling consistency constraint on parental NS-SEC imputation** (see S7.4 Component 6) — which is where the most important bias in the parental class finding actually lives.

### S5.11 Net assessment

Clustering alone does not overturn the main regression findings — the initial regime effect (OR = 20.56) and age effect are large enough to survive. But it materially affects two claims:

1. **"Parental NS-SEC is non-significant."** This is non-significant in a model with inflated test statistics (from quasi-separation) that simultaneously has deflated SEs (from ignored clustering) — two biases in opposite directions on the same coefficient. True precision is unknown without the corrected model.
2. **"Initial regime is stronger than parental class."** This comparative claim cannot be supported by a model with these specification errors.

### S5.12 Verification

- §4.5 logistic regression reports household-clustered SEs (minimum) or GLMM with household random effect.
- §3.1 states the number of unique households and acknowledges within-household income correlation.
- All ORs have correctly-sized 95% CIs.
- The NS-SEC null result is explicitly qualified as conditional on the modelling choices (clustering, missingness, mediation).
- §4.5 or supplement reports the estimated ICC / $\hat{\sigma}^2_u$.

---

## S6 — Escape rate calculation conditioned on panel continuity [HIGH]

### S6.1 Reviewer claim

The 5.6% escape rate conditions on being continuously observable for 10 years while in a disadvantaged regime. Individuals who escape disadvantage by leaving the panel (e.g., into employment that reduces survey contact) are excluded. The 5.6% "almost certainly underestimates population escape rates" — panel conditioning bias makes disadvantage appear more absorbing than it is.

### S6.2 Current state in v1

§4.5 reports escape rates without discussing the selection conditioning. §7.3 mentions attrition generally but does not connect it to the escape rate calculation.

### S6.3 Classification

**Prose + optional computation** (bounds analysis).

### S6.4 Strategy

1. **Add an explicit caveat to §4.5** stating that the escape rate is conditional on panel continuity and that the direction of bias is toward underestimation (individuals who escape may be more likely to leave the panel).
2. **Compute a bounds analysis (optional but recommended).** Among individuals who *start* in a disadvantaged regime but drop out before completing 10 years: what is their last observed state? If a substantial fraction are last observed in employment or mid/high income, this provides evidence that attrition-driven escape is non-trivial. Report upper and lower bounds on the escape rate under different assumptions about attritors.
3. **Reframe the headline claim.** "Escape from disadvantaged regimes is rare" → "Among continuously observed panel members, escape from disadvantaged regimes is rare (5.6%); this conditions on panel continuity and likely underestimates the population rate."
4. **Update the abstract** to qualify the escape rate.

### S6.5 Verification

- §4.5 contains an explicit panel-conditioning caveat on the escape rate.
- The abstract does not state 5.6% without qualification.

---

## S7 — Complete-case parental NS-SEC regression with non-random 39.1% missingness [HIGH]

*Expanded 2026-05-03 with within-sibling consistency constraint on MI and parental NS-SEC measurement issues.*

### S7.1 Reviewer claim

Parental NS-SEC is missing for 39.1%, missingness is non-random (χ² = 147.74, p < 10⁻²⁹), and the regression uses complete cases only (n = 4,832 from 7,453). If NS-SEC is more likely missing for lower-status trajectories, the complete-case regression systematically understates the parental class effect, potentially generating the observed null result. This is "a specification error, not merely a caveat."

### S7.2 Current state in v1

§4.5 acknowledges non-random missingness but proceeds with complete-case analysis. §7.3 lists it as a limitation.

### S7.3 Classification

**Both** — needs multiple imputation AND prose revisions.

### S7.4 Strategy

1. **Implement multiple imputation for parental NS-SEC.** Use the `mice` framework (or Python equivalent) with predictors: age, sex, birth cohort, initial regime, region, education, housing tenure. Generate m = 20 imputed datasets, run the logistic regression on each, pool estimates using Rubin's rules.
2. **Compare MI results to complete-case results.** If parental NS-SEC becomes significant under MI, the §7.1 conclusion must be revised: "Initial regime mediates the effect of parental class on escape, but class origin retains a direct effect that complete-case analysis obscured."
3. **Report both complete-case and MI results** in §4.5 (or Table in supplement). State which is the primary analysis and why.
4. **Reframe the claim in §7.1.** The current "initial regime — not parental class — is the strongest predictor" must become conditional: "In complete-case analysis [and/or under multiple imputation], initial regime is a stronger predictor than parental NS-SEC, though the latter's effect may be attenuated by non-random missingness."
5. **Address the endogeneity concern** (see S8 below) in the same rewrite.
6. **Within-sibling consistency constraint (if Tier 3 family-of-origin clustering is implemented).** Parental NS-SEC is by definition constant within a family of origin — siblings share the same parental class. Standard individual-level MICE applied to a variable that is constant within families will produce imputed values that *differ* between siblings, which is incoherent. The correct approach imputes at the family-of-origin level:
   - For sibling clusters where ≥ 1 sibling has observed NS-SEC: assign the observed value to all siblings.
   - For sibling clusters where all are missing: impute once at the cluster level using cluster-level predictors (mean education, mean early-career income across siblings, region).
   - For singletons (no identified siblings): standard individual-level MICE.
   - This requires custom imputation code but is conceptually straightforward.

### S7.5 Parental NS-SEC measurement issues

*Added 2026-05-03.*

Parental NS-SEC is measured in two distinct ways depending on whether the parent is a panel member:

| Parent status | Source | Measurement |
|---|---|---|
| Parent in panel (non-zero `ppid`/`mpid`) | Parent's own `indresp` responses | Direct, contemporaneous |
| Parent not in panel (majority) | Child's retrospective report (`paedqf` and related variables in `indresp`) | Subject to recall error, social desirability bias, missing data concentrated in lower-class origins |

The 39.1% missingness is partially attributable to these measurement issues (not just panel non-response). Individuals whose parental class is *harder to measure* are systematically from lower parental class origins — the complete-case analysis therefore excludes them, biasing the NS-SEC coefficient toward zero.

**References:** Breen & Jonsson (2005) on measurement error in retrospective parental class.

### S7.6 Artefacts

- MI analysis output: `results/trajectory_tda_integration/escape_regression/mi_nssec_<date>.json`.
- If sibling-consistent MI: `results/trajectory_tda_integration/escape_regression/mi_nssec_sibling_consistent_<date>.json`.
- Updated §4.5 and §7.1 prose.

### S7.7 Verification

- §4.5 reports MI results alongside complete-case results.
- The "class origin adds little" claim is appropriately qualified.
- If sibling clusters are used: imputed NS-SEC is identical within sibling clusters.
- §4.5 or supplement notes the two distinct measurement sources for parental NS-SEC.

---

## S8 — Endogeneity: initial regime mediates parental class [HIGH — embedded in S7]

### S8.1 Reviewer claim

Initial regime is itself a function of prior trajectory, which is a function of parental class. Using initial regime as a covariate to test whether parental class predicts escape "after conditioning" is mediation analysis without the formal framework. The null NS-SEC result "establishes only that the pathway from class origin to escape runs through trajectory type — which is exactly what life-course sociologists would expect."

### S8.2 Strategy

1. **Acknowledge the mediation structure explicitly in §4.5.** Add: "Initial regime is itself partly determined by parental class; conditioning on it absorbs the indirect effect. The non-significance of NS-SEC after conditioning on initial regime is consistent with full mediation — class origin shapes which regime an individual enters, and regime determines escape probability."
2. **Consider a formal mediation decomposition** (Baron & Kenny or causal mediation analysis). Estimate the total effect of NS-SEC on escape (without regime in the model), the direct effect (with regime), and the indirect effect (mediated through regime). This is a natural extension of the existing regression.
3. **Rewrite §7.1** to replace "initial regime — not parental class" with a mediation-aware framing: "Parental class operates on escape probability primarily through its effect on initial regime placement."

### S8.3 Verification

- §4.5 explicitly names the mediation structure.
- §7.1 does not claim class origin is "unimportant" — only that its effect is mediated.

---

## S9 — Quasi-separation and Firth penalisation [HIGH — interacts with S5]

*This section was substantially expanded on 2026-05-03 to detail the clustering-separation interaction and specify Firth's method as the required fix.*

### S9.1 The problem

McFadden's pseudo-R² = 0.479 is unusually high for social mobility research. Combined with very large ORs (20.56 for regime, 23.8 for 1960s cohort), this is a signature of **quasi-complete separation**: some predictor combination almost perfectly predicts the outcome in a subset of cases.

**Most likely source:** The age-regime interaction. Virtually all retirement-age Inactive Low individuals (R2, age ≥ 60) have escape rate 0.1%, making the outcome nearly deterministic for that cell. Maximum likelihood estimates are unstable near separation, and SEs are unreliable regardless of clustering.

### S9.2 Interaction with clustering (S5)

The clustering and separation problems **compound**: clustered SEs are inflated for clustered data, but near-separation inflates SEs further in an asymmetric way. The combination means reported CIs are:
- **Too narrow** due to ignored clustering
- **Incorrectly shaped** (asymmetric near separation)
- **Neither correctly sized nor correctly shaped**

Both corrections must be applied simultaneously. A model with clustered SEs but no separation correction, or Firth correction but no clustering, is still misspecified.

### S9.3 Strategy

1. **Diagnose separation.** Check for zero-escape cells in the initial-regime × cohort × age cross-classification. Report the cross-tabulation. The R2 regime has 0.1% working-age escape — this is the near-zero cell causing separation.
2. **Apply Firth's penalised likelihood** (Firth 1993). Firth adds a Jeffreys prior penalty to the log-likelihood, producing finite, stable estimates in the presence of separation. Available in R (`logistf` package), Stata (`firthlogit`), Python (`firthlogit` or custom implementation). Firth produces **smaller, more conservative OR estimates** near separation — the 1960s cohort OR of 23.8 will almost certainly shrink, and its CI will narrow in a statistically honest way.
3. **Report CIs for all ORs** — especially the 1960s cohort. If the CI under standard ML is extremely wide (e.g., [2, 280]), flag explicitly.
4. **Report the predicted probability distribution.** If many predicted probabilities cluster near 0 or 1, separation is confirmed.
5. **Interpret pseudo-R² in §4.5:** "The high pseudo-R² (0.479) is driven primarily by the near-zero escape rate from R2 at retirement age, which approaches complete separation. Firth-penalised estimates are reported as the primary specification."
6. **Combine with S5 clustering correction.** The minimum acceptable model for v2 is: Firth-penalised logistic regression with SEs clustered on `hidp`. The better model is: Firth-penalised GLMM with household random intercept.

### S9.4 Artefacts

- Firth-penalised regression output: `results/trajectory_tda_integration/escape_regression/firth_clustered_<date>.json`.
- Cross-tabulation of escape × regime × cohort × age (diagnosis table).
- Predicted probability histogram.

### S9.5 Verification

- All ORs have 95% CIs (profile-likelihood CIs from Firth, not Wald).
- The pseudo-R² is interpreted, not just reported.
- Separation risk is diagnosed and documented with the cross-tabulation.
- Firth penalisation is the primary (or at minimum robustness-check) specification.
- The S5 clustering correction is applied simultaneously.

---

## S10 — BHPS–USoc "replication" uses shared PCA, overlapping sample, non-comparable state space [MEDIUM]

### S10.1 Reviewer claim

BHPS and USoc are not independent: 8,459 spanning individuals appear in both, the embedding uses shared frozen PCA loadings, and the state space is partially non-comparable. This is "a robustness check in a partially overlapping dataset under shared embedding geometry," not "independent replication."

### S10.2 Current state in v1

§6.2 calls it "cross-era replication" and draws substantive conclusions about the regime structure "reflecting genuine career landscape features."

### S10.3 Strategy

1. **Rename throughout:** "cross-era replication" → "cross-era robustness check" or "cross-era consistency analysis."
2. **Report the overlap explicitly.** State how many individuals appear in both the USoc and BHPS analysis samples (the reviewer says 8,459 spanning individuals — verify this against the data).
3. **Run a non-overlapping sensitivity check.** Exclude the ~8,459 spanning individuals from the BHPS sample and rerun the GMM and PH analysis on the remaining BHPS-only individuals. If results hold, the non-independence concern is empirically addressed.
4. **Discuss the shared PCA loadings.** The frozen PCA is a deliberate methodological choice (ensures comparable embedding geometry); state this explicitly and note that it means the BHPS analysis tests consistency of the *data* under a shared geometric framework, not independence of the framework itself.
5. **Cross-reference S4** (state space non-comparability) in §6.2.

### S10.4 Verification

- No instance of "replication" in §6.2 without "robustness" or "consistency" qualifier.
- The spanning-individual count is reported.

---

## S11 — Annual median anchor for income bands not specified [MEDIUM]

### S11.1 Reviewer claim

Income bands use "contemporary equivalised household income median" but the paper doesn't specify whose median: the USoc survey sample, the wider UK (from HBAI/FRS), or the full Understanding Society respondent base. This determines whether 60% of median is calibrated to the national poverty line or the selected sample's distribution.

### S11.2 Strategy

1. **State the median source in §3.1.** Check the codebase — is the median computed from the analysis sample (27,280), the full USoc wave respondent pool, or an external source (HBAI)?
2. **If sample median:** acknowledge that the continuity-selected sample has higher median income than the population, so the 60% threshold is *higher* than the official poverty line, making the low-income classification more conservative (fewer people classified as low-income than under population median).
3. **If external median:** cite the source (HBAI, FRS) and note the year-by-year matching.
4. **Report the numerical thresholds** (at least for a reference year) so the reader can calibrate.

### S11.3 Verification

- §3.1 states which population's annual median defines the 60%/120% thresholds.

---

## S12 — BHPS `fihhmn` vs USoc income concepts differ [MEDIUM]

### S12.1 Reviewer claim

BHPS `fihhmn` is point-in-time net monthly household income at interview. USoc income (e.g., `fihhmnnet3_dv`) is an annualised monthly average. Equivalising both doesn't resolve the conceptual difference. No harmonisation check is reported.

### S12.2 Strategy

1. **Document the income variable difference in §3.1 or §6.2.** State exactly which variable is used in each survey and how they differ conceptually.
2. **Compute a cross-era calibration check.** For the ~8,459 spanning individuals, compare their last BHPS income band with their first USoc income band. If concordance is high (>80% same band), the practical impact is small. Report the concordance rate.
3. **Acknowledge in §6.2** that the cross-era comparison involves partially non-comparable income measurement and state the direction of likely bias.

### S12.3 Verification

- §6.2 or §3.1 names both income variables and states their conceptual difference.

---

## S13 — State space design: sparse unemployment states waste embedding dimensions [LOW–MEDIUM]

### S13.1 Reviewer claim

The UL/UM/UH states collectively account for 2.0% of dominant trajectories. In the 81-dimensional bigram vector, 27 of 81 columns reference a U origin or destination — near-zero for 98% of the sample. PCA on vectors with 27+ near-zero dimensions "could introduce noise." The state space effectively collapses to 6 states for most individuals.

### S13.2 Strategy

1. **Add a brief discussion in §3.1 or §7.3** acknowledging the sparse U states and their consequences for the embedding.
2. **Report the effective dimensionality** of the bigram matrix (how many of the 81 columns have non-trivial variance). If PCA extracts 20 components explaining >95% of variance from the non-degenerate subspace, the noise concern is limited.
3. **Sensitivity: 6-state (E/I × L/M/H) embedding.** If computationally feasible, re-embed with the unemployment states collapsed into inactive (or into employed, depending on conceptual preference) and compare regime structure. If ARI > 0.9 between 9-state and 6-state regimes, report this as evidence that the U states do not drive the results.
4. **Justify retaining the U states** on substantive grounds: unemployment is conceptually distinct from inactivity in welfare-state research, even if empirically rare in the panel. Collapsing U into I or E would be a substantive choice, not merely a technical simplification.

### S13.3 Verification

- §3.1 or §7.3 discusses the sparsity of U states and its implications.
- The effective dimensionality of the bigram space is reported (main text or supplement).

---

## S14 — BHPS retention rate differential (85% BHPS vs 23% USoc) [MEDIUM — embedded in S1]

### S14.1 Reviewer claim

BHPS retains ~85% of original sample members (8,509 from ~10,000) vs USoc's 23%. "BHPS continuity-survivors are a different kind of selected sample than USoc continuity-survivors." The differential selection is not discussed.

### S14.2 Strategy

1. **Explain the differential in §6.2 or §3.1.** BHPS ran for 18 waves with a stable original sample and minimal refreshment; USoc has 118,000+ respondents including boost samples, many of whom were never intended for long panels. The denominator difference (10,000 original vs 118,000 total) explains much of the rate difference.
2. **Report the USoc denominator correctly.** If the 118,000 includes boost/refreshment samples never designed for longitudinal follow-up, the effective denominator for a continuity comparison is much smaller. Compute: of USoc original-sample members (IP/GP sample, not ethnic minority boost or immigrant/emigrant samples), how many satisfy the 10-year criterion? This rate should be much closer to the BHPS rate.
3. **Acknowledge that despite denominator adjustment, the two continuity-selected samples are not identically constructed.** The BHPS sample entered a mature panel; USoc respondents entered a new panel during a recession.

### S14.3 Verification

- §6.2 explains the retention rate differential with appropriate denominator discussion.

---

## Cross-Reference Matrix: Social Scientist Issues × TDA Reviewer Issues

| Social scientist issue | Interacts with TDA reviewer issue | Nature of interaction |
|---|---|---|
| S1 (continuity filter) | — | New concern, no TDA counterpart |
| S2 (survey weights) | — | New concern |
| S3 (income variable) | — | New concern |
| S4 (jbstat harmonisation) | L3 (BHPS H₁ window length) | Both affect BHPS comparability |
| S5 (household clustering) | M5/L2 (W₂ p-values) | Clustering affects SE interpretation |
| S6 (escape rate bias) | — | New concern |
| S7 (NS-SEC missingness) | — | New concern (but v1 acknowledges) |
| S8 (endogeneity) | — | New concern |
| S9 (pseudo-R²) | — | New concern |
| S10 (BHPS "replication") | L3 (BHPS H₁) | Both reframe §6.2 |
| S11 (median anchor) | — | New concern |
| S12 (BHPS income variable) | L3 (BHPS comparability) | Both affect cross-era analysis |
| S13 (sparse U states) | — | New concern |
| S14 (BHPS retention) | S10 | Both affect §6.2 framing |
