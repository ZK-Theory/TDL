# §3.4.2 Spanning-Individual Decomposition: Knee Algorithm, AUC/$W_2$ Statistics, Identification Check

## Spanning individuals and the identification condition

Let $\mathcal{I}^*$ denote **spanning individuals**: those observed in both survey eras (BHPS pre-2008 and USoc post-2008). Let $\mathcal{I}_2$ denote **era-2 newcomers**: individuals observed only in USoc. The decomposition asks whether the era-1-to-era-2 topological change is driven by genuine change in spanning individuals' trajectories, or by newcomers occupying embedding regions the earlier survey frame did not sample — structurally analogous to a parallel-trends identification argument: if spanning individuals track newcomers into the new topology, the change reflects economic restructuring; if spanning individuals retain era-1-like topology while newcomers alone carry the new structure, the change reflects survey-frame expansion rather than a shared economic shift.

## Knee-detection algorithm for $\varepsilon^*$

$\varepsilon^*$ is the filtration scale at which the per-year Betti-0 descent curve has its sharpest bend, detected as follows (`detect_eps_star_knee`):

```
Input: beta0 curve b(eps) on a grid eps_1 < ... < eps_n; decrease_threshold = 0.05
1. Normalise both axes to [0,1]: x_n = (eps - eps_min)/(eps_max - eps_min),
                                  y_n = (b - b_min)/(b_max - b_min)
2. If range(b) < decrease_threshold * max(b): curve does not vary meaningfully
   -> DEGENERATE, return eps_1 (flat-curve fallback)
3. First and second discrete derivatives of y_n w.r.t. x_n: dy, d2y  (np.gradient)
4. curvature(eps) = |d2y| / (1 + dy^2)^1.5          # discrete Menger-style curvature
5. Restrict candidates to the structural descent region:
       descent_mask = { eps : b(eps) > decrease_threshold * max(b) }
6. eps* = argmax over descent_mask of curvature(eps)
7. If y_n(eps*) < degeneracy_threshold (0.1): flag eps* as lying in the flat tail
   -> DEGENERATE (unreliable knee)
Output: (eps*, is_degenerate)
```

The descent-region restriction (step 5) excludes the flat large-$\varepsilon$ tail, where apparent curvature is numerical noise rather than topological structure, from candidacy.

**Per-year aggregation.** The knee is computed independently for each of the 32 BHPS/USoc survey years (1991-2022, $\varepsilon$ grid $0.05$-$2.00$ in steps of $0.01$), and the canonical scale is the **median** of the 32 per-year knees: $\varepsilon^* = 0.54$ (Q25 $= 0.46$, Q75 $= 0.63$, range $[0.05, 0.83]$). Four years (2003, 2005, 2011, 2019) are flagged degenerate under step 2/7 and excluded from the median. The canonical value for all inferential statistics in this paper is $\varepsilon^* = 0.54$.

## Three statistics: single-$\varepsilon$ ratio, windowed AUC ratio, matched $W_2$

The original v1 test statistic was a single-scale block ratio, $\mathrm{BR}^{\mathrm{span}} = \beta_0(\varepsilon^*; X_t^{\mathrm{new}}) / \beta_0(\varepsilon^*; X_t^*)$, read at one filtration value. A reviewer correctly flagged this as $\varepsilon^*$-dependent, and the re-analysis replaces it with three statistics evaluated across four $\varepsilon^* \in \{0.54, 0.65, 0.70, 0.80\}$:

1. **Single-$\varepsilon$ $\beta_0$ ratio** (retained, corroborative only): the original block ratio $\mathrm{BR}^{\mathrm{span}}$ read at each $\varepsilon^*$.
2. **Windowed $\beta_0$-AUC ratio** (headline statistic): integrating the Betti-0 curve over a window $[\varepsilon_{\mathrm{lo}}, \varepsilon^*]$ rather than reading it at one scale removes the single-scale sensitivity,
   $$
   \mathrm{AUC\text{-}ratio}(\varepsilon^*) = \frac{\int_{\varepsilon_{\mathrm{lo}}}^{\varepsilon^*}
   \beta_0(\varepsilon; X_t^{\mathrm{new}})\,d\varepsilon}
   {\int_{\varepsilon_{\mathrm{lo}}}^{\varepsilon^*} \beta_0(\varepsilon; X_t^*)\,d\varepsilon},
   \qquad \varepsilon_{\mathrm{lo}} = 0.1115,
   $$
   with $\varepsilon_{\mathrm{lo}}$ fixed across all four $\varepsilon^*$ so that only the upper integration limit varies with the canonical-scale choice.
3. **Matched 2-Wasserstein distance** $W_2$ between the $H_0$ diagrams of a size-matched newcomer/spanning sample: a scale-independent diagram-level comparison, constant across the four $\varepsilon^*$ values by construction (it does not depend on a single filtration cutoff).

**Why AUC replaces single-$\varepsilon$ as the headline statistic.** The single-$\varepsilon$ ratio is a point estimate of a continuous curve and inherits that curve's local noise; the windowed AUC integrates over a range and is materially less sensitive to the exact $\varepsilon^*$ choice, which is itself an estimated (median-of-32-years) quantity rather than a fixed design parameter. Reporting a statistic that is robust to the $\varepsilon^*$ estimation step is required precisely because $\varepsilon^*$ carries its own uncertainty (Q25-Q75 spread $0.46$-$0.63$ above).

Robustness of each statistic to the $\varepsilon^*$ choice is assessed by recomputing all three at all four $\varepsilon^*$ values and checking (a) sign/direction consistency of the ratio statistics, (b) whether the 95% bootstrap CI excludes parity (ratio $=1$) at each $\varepsilon^*$, and (c) whether the conclusion changes under $\varepsilon^* = 0.70$ (the value used in the original, unjustified v1 text) versus the locked $\varepsilon^*=0.54$. Per-$\varepsilon^*$ results and the resulting outcome classification are reported in §4.3.

## Identification check

The spanning/newcomer decomposition's validity depends on an identification condition that is not automatically satisfied: if spanning individuals differ systematically from newcomers on covariates that are themselves structural drivers of trajectory topology (age being the clearest candidate, given the age-stratified disadvantaged-regime concentration reported elsewhere in this paper), an observed spanning/newcomer topological difference is confounded rather than informative about frame expansion versus economic change. We therefore treat the identification check as a **mandatory part of the decomposition method**, not an optional robustness appendix: every reported spanning/newcomer comparison in this paper is accompanied by (i) a demographic balance diagnostic (standardised mean differences on age, sex, highest qualification, and employment status at first observation) and (ii) two covariate-adjustment designs computed against that diagnostic — a 1:1 nearest-neighbour propensity match (logit propensity, caliper $0.2$) and an age-restricted stratum (ages 30-55) that closes the age gap by construction. Balance-table values and the matched/age-stratified sample sizes are reported in §4.3.
