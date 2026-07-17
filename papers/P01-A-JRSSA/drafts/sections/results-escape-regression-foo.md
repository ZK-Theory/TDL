# §4.5 Regime Stickiness, Conditional Escape, and Family-of-Origin Geometry

Overlapping ten-year career-phase windows (step five years) identify a small conditional-escape population inside the wider regime typology. A *starter* is an individual whose first window falls in one of the two disadvantaged regimes, R2 (Inactive Low) or R6 (Low-Income Churn); an *escape* is any subsequent window outside R2/R6. In the descriptive window assignment, 7,453 individuals begin as disadvantaged starters and 416 ever escape, an observed escape rate of 5.58%. The corresponding working-age rate is higher, 386 escapes among 2,163 disadvantaged starters (17.85%), which is why the regression analysis below treats conditional escape as a restricted, window-based outcome rather than as the full-sample regime-prevalence contrast used in the first descriptive pass.

Those descriptive rates are vulnerable to panel continuity. The inverse-probability-weighting (IPW) model was built from verified longitudinal weights rather than the unavailable `lwtresp` variable, falling back through `{wave}_indinub_lw` for UKHLS wave c onward, BHPS longitudinal alternatives where available, and `lw_base = 1` for BHPS wave ba. The propensity model has AUC = 0.7137 and an effective sample size of 57,035 after p1/p99 trimming. A structural feature of the design drives the extreme tail of the raw weights: recent entrants cannot satisfy the ten-year continuity criterion by construction, so the most recent birth cohort carries a strongly negative propensity coefficient (`birth_cohort_group1990+` = −6.196, implying a selection probability near 0.002). This produces a raw maximum weight of 535.8943, reduced to 42.7808 after p1/p99 trimming, with the coefficient of variation falling from 1.3623 to 0.9942. A restricted-eligibility sensitivity (T1.29) shows that 25,372 of 27,280 analytical cases (93.01%) come from respondents who could in principle satisfy the ten-year continuity rule, but it does not remove the denominator limitation: permanent attritors remain unobserved. Under Manski-style attrition bounds (T1.15), the observed 5.58% overall escape rate has a full-pessimism lower bound of 0.44% and a partial-pessimism lower bound of 1.34%, so the qualitative conclusion that escape from disadvantaged starts is uncommon survives even maximally informative attrition.

The modelling sequence builds up the same conditional-escape outcome across three estimators of increasing robustness. Tier 1 is a clustered, Firth-penalised logit on first-window R2/R6 starters, chosen because the escape outcome is rare and several covariate cells are quasi-separated. Tier 2 adds a household random effect to the same conditional frame. The design-based headline then repeats the Tier 2 fixed-effect structure under survey-style clustering on family of origin (`foo_cluster`) with normalised IPW and multiple imputation of parental NS-SEC, because the weighted household random-effect variance could not be estimated reliably (see below). All three tiers agree on the substantive ordering; the design-based model is the headline.

**Table — Conditional-escape regression build-up and design-based headline** *(provisional label; final table number set at v2 assembly)*

| Model step | Estimator and frame | n | Main use | R6 vs R2 | Parental NS-SEC M vs H | Parental NS-SEC L vs H | Household variance |
|---|---:|---:|---|---:|---:|---:|---|
| Tier 1 | Clustered Firth logit, first-window R2/R6 starters | 6,173 | Rare-outcome baseline with quasi-separation control | OR = 18.5954 [10.0121, 37.2947], p < 1e-4 | OR = 1.0455, p = 0.8106 | OR = 1.2161, p = 0.3073 | Not modelled |
| Tier 2 | Unweighted household-RE GLMM, first-window R2/R6 starters | 6,173 | Adds household clustering | OR = 21.2916, p < 0.001 | OR = 1.0487, p = 0.8076 | OR = 1.2324, p = 0.3026 | ICC = 0.0595 |
| Headline | Design-based `survey::svyglm`, normalised IPW, 20 imputations, clustered on `foo_cluster` | 7,097 | Primary adjusted result | log OR = 3.5516 (OR = 34.8691), p < 0.001 | log OR = 0.0911 (OR = 1.0954), p = 0.6858 | log OR = 0.1067 (OR = 1.1126), p = 0.6409 | Weighted household RE not estimable |
| Diagnostic companion | Unweighted household-RE GLMM on the headline model frame | 7,097 | Variance reference only | log OR = 3.3988 (OR = 29.9282) | log OR = −0.0089 (OR = 0.9911) | log OR = 0.0377 (OR = 1.0384) | ICC = 0.0622 |

The design-based headline is reported in full in the coefficient table below; cluster-robust standard errors use the `foo_cluster` design with Rubin-pooled imputation variance, and all twenty imputation chains passed the trace-drift convergence screen.

**Table — Design-based headline (`survey::svyglm`): full coefficients** *(provisional label; final table number set at v2 assembly)*

| Term | Estimate (log OR) | Cluster-robust SE | OR | p |
|---|---:|---:|---:|---:|
| Intercept | −7.3552 | 0.5817 | 0.0006 | < 0.001 |
| Regime R6 (vs R2) | 3.5516 | 0.3269 | 34.8691 | < 0.001 |
| Parental NS-SEC M (vs H) | 0.0911 | 0.2250 | 1.0954 | 0.6858 |
| Parental NS-SEC L (vs H) | 0.1067 | 0.2288 | 1.1126 | 0.6409 |
| Birth cohort 1950s | 1.6249 | 0.5079 | 5.0780 | 0.0014 |
| Birth cohort 1960s | 3.4967 | 0.5080 | 33.0023 | < 0.001 |
| Birth cohort 1970s | 3.8666 | 0.5166 | 47.7807 | < 0.001 |
| Birth cohort post-1980 | 3.9893 | 0.5192 | 54.0184 | < 0.001 |
| Sex female | −0.5961 | 0.1626 | 0.5510 | 0.0002 |
| Region 2 | −0.2543 | 0.4216 | 0.7755 | 0.5463 |
| Region 3 | −0.1849 | 0.4268 | 0.8312 | 0.6648 |
| Region 4 | −0.1779 | 0.4593 | 0.8370 | 0.6984 |
| Region 5 | −0.8860 | 0.4391 | 0.4124 | 0.0436 |
| Region 6 | −0.3745 | 0.4377 | 0.6877 | 0.3922 |
| Region 7 | −0.1062 | 0.4127 | 0.8992 | 0.7969 |
| Region 8 | −0.3022 | 0.4483 | 0.7392 | 0.5002 |
| Region 9 | −0.7350 | 0.4645 | 0.4796 | 0.1136 |
| Region 10 | −0.1996 | 0.4659 | 0.8191 | 0.6684 |
| Region 11 | −0.5702 | 0.4665 | 0.5654 | 0.2216 |
| Region 12 | −0.5355 | 0.4451 | 0.5853 | 0.2289 |

The substantive pattern is stable across the whole build-up. Starting in R6 rather than R2 is the dominant predictor of later escape: the conditional Firth logit gives OR = 18.5954, the household-RE GLMM gives OR = 21.2916, and the design-based headline gives OR = 34.8691, all with p < 0.001. The cohort gradient is also strong and ordered — earlier-born cohorts escape at far higher rates — which is expected, since earlier entrants are observed over more windows and have more opportunity to register an escape. Parental NS-SEC, by contrast, is small and statistically weak in every conditional tier: the M and L origin contrasts are non-significant under Firth penalisation, under the household-RE GLMM, and under the design-based headline (headline p = 0.6858 and p = 0.6409).

This null is not a sparsity artefact, and it should not be read as evidence that family origin is unimportant. The descriptive parental-class cross-tabulation over first-window R2/R6 starters is dense and balanced — H/M/L by R2/R6 counts of 1,435/462, 2,049/651, and 2,050/628 (n = 7,275, no sparse cells) — and a column-independence test does not reject (χ² = 0.5747, df = 2, p = 0.7503). Conditional on a disadvantaged start, parental class therefore does not even separate R2 from R6, let alone predict subsequent escape. The natural reading, which we offer descriptively rather than as a formal mediation estimate, is that parental class operates *upstream* — on selection into disadvantaged starting positions — rather than on conditional escape once a disadvantaged start has occurred. Conditioning on the initial regime consequently estimates a direct origin-to-escape pathway within disadvantaged starters, not the total family-origin effect on the trajectory regime in which a respondent begins. Formal mediation, in the Imai–Keele–Tingley or Baron–Kenny sense, is deferred to follow-up work; the earlier formal-mediation analyses (T1.21/T1.22) were superseded and are not reported here.

The household component is deliberately modest, and the weighted variant is a diagnostic rather than a finding. The unweighted conditional GLMM estimates household clustering at ICC = 0.0595 in the Tier 2 frame, and the unweighted diagnostic companion estimates ICC = 0.0622 on the headline model frame. The weighted household random-effect route is not substantively interpretable: the weighted `glmmTMB` diagnostic diverged to σ_u = 35.6066 and ICC = 0.9974, WeMix failed a bounded diagnostic with a negative-semi-definite matrix, and a full single-imputation WeMix smoke did not complete after 4,001.4 seconds on a household structure that is singleton-dominated (6,037 households across 7,097 individuals). The headline is consequently the design-based `svyglm` result, with the household variance reported only through the unweighted diagnostic companion.

### §4.5.1 Family-of-Origin Clustering in Local Persistence Features

A separate family-of-origin topology analysis asks whether siblings or same-FOO respondents occupy unusually similar local trajectory geometry. On the full 27,280-person analytical sample, the FOO clustering file contains 18,538 observed FOO clusters and 13,122 within-cluster unordered sibling pairs. In the primary topology-native arm, local persistence features reject the constrained-shuffle null (p = 0.0001999600), with observed mean within-pair distance 0.1132442 and an effect-size ratio of 0.8243. The three reported feature-level ICCs are all strictly above zero: max $H_0$ persistence ICC = 0.5810 [0.5711, 0.5905], total $H_1$ persistence ICC = 0.5096 [0.4961, 0.5222], and the first persistence-landscape integral ICC = 0.4728 [0.4522, 0.4925].

This supports a family-of-origin signature in trajectory geometry, but not a topology-specific signature. The registered comparator analysis reaches the same rejection threshold for raw 90-dimensional bigram coordinates (p = 0.0001999600; effect-size ratio = 0.6604; 90/90 ICC intervals above zero) and for 10-dimensional occupancy/change-count summaries (p = 0.0001999600; effect-size ratio = 0.6547; 10/10 ICC intervals above zero). The locked interpretation is therefore SUPPORT plus SIGNAL_NOT_TOPOLOGY_SPECIFIC: local persistent-homology summaries give a topology-native route to detecting family-coherent career geometry, while the comparator arms show that the coherence is broader trajectory structure rather than something uniquely visible only to persistence.
