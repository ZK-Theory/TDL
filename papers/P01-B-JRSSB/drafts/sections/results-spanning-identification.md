# §4.3 Spanning-Individual Identification: Inferential Re-analysis, ε* Robustness, and Balance

## Identification problem

The pool-draw null (§4.3.1) establishes that the cross-era block structure is real, but not its source. The spanning-individual decomposition adjudicates between genuine economic restructuring and survey-frame expansion: under the parallel-trends-style identification condition, if the post-2008 change reflected economic restructuring, spanning individuals (observed in both surveys) would track newcomers into the new topology; if it reflected frame expansion, spanning individuals would retain era-1 topology while newcomers occupy previously unsampled embedding regions. The discriminating quantity is the era-2 $H_0$ structure of newcomers relative to spanning individuals.

## Inferential re-analysis

The v1 decomposition rested on a single-scale Betti-0 point estimate, which a reviewer correctly flagged as $\varepsilon^*$-dependent. The inferential re-analysis (matched $n = 8{,}000$ per group, frozen PCA loadings, $B = 1{,}000$ permutations and $B = 1{,}000$ bootstrap resamples, seed 42, homology dimension $H_0$, locked $\varepsilon^* = 0.54$) evaluates three statistics — the single-$\varepsilon$ $\beta_0$ ratio, the windowed $\beta_0$-AUC ratio, and the matched 2-Wasserstein distance $W_2$ — across four $\varepsilon^*$ values, each with a permutation p-value and a bootstrap confidence interval.

**Table 4. Spanning vs newcomer $H_0$ structure: three statistics across four $\varepsilon^*$** *(ratios are newcomer-to-spanning, direction newcomers > spanning throughout)*

| $\varepsilon^*$ | Single-$\varepsilon$ $\beta_0$ ratio (perm p; 95% boot CI) | Windowed $\beta_0$-AUC ratio (perm p; 95% boot CI) | Matched $W_2$ (perm p) |
|---|---|---|---|
| 0.54 (locked) | 1.60 (p = 0.025; [1.09, 2.04]) | 1.127 (p = 0.001; [1.095, 1.173]) | 2.536 (p = 0.001) |
| 0.65 | 1.50 (p = 0.341; [0.92, 2.83]) | 1.129 (p = 0.001; [1.097, 1.174]) | 2.536 (p = 0.001) |
| 0.70 | 1.25 (p = 0.636; [0.75, 3.01]) | 1.129 (p = 0.001; [1.097, 1.175]) | 2.536 (p = 0.001) |
| 0.80 | 1.50 (p = 0.586; [0.50, 3.00]) | 1.129 (p = 0.001; [1.098, 1.175]) | 2.536 (p = 0.001) |

The three statistics differ sharply in robustness. The single-$\varepsilon$ $\beta_0$ ratio — the original v1 statistic — is significant only at the locked $\varepsilon^* = 0.54$ (p = 0.025) and not at 0.65, 0.70, or 0.80, with bootstrap intervals that span parity; it is too scale-sensitive to carry the conclusion. The windowed $\beta_0$-AUC ratio, which integrates the Betti-0 curve over a window rather than reading it at one scale, is significant at every $\varepsilon^*$ (p = 0.001) with bootstrap intervals strictly above parity (lower bounds 1.09–1.10), and the matched $W_2$ rejects equality of the $H_0$ persistence diagrams at every $\varepsilon^*$ (p = 0.001). The direction is consistent throughout: newcomers carry more $H_0$ structure than spanning individuals.

This resolves the earlier 'divergent' descriptive pattern, in which the single-$\varepsilon$ ratio and $W_2$ pointed one way while a *full*-interval $\beta_0$-AUC ratio (0.938–0.939, i.e. below parity) pointed the other. The windowed-AUC and $W_2$ results describe a robust association between newcomer status and greater $H_0$ structure across the reported $\varepsilon^*$ choices; they do not identify the source of that association or establish a causal survey-frame effect.

## Demographic balance and identification robustness

The spanning and newcomer populations are not exchangeable, which bears directly on the identification condition. The balance diagnostic (spanning $n = 5{,}895$, newcomer $n = 21{,}385$) shows a large age gap and moderate imbalances in qualification and employment, with sex well balanced:

**Balance table — spanning vs newcomer (standardised mean differences)**

| Covariate | Spanning mean | Newcomer mean | SMD |
|---|---:|---:|---:|
| Age at first observation | 35.26 | 44.66 | −0.617 |
| Female | 0.560 | 0.559 | 0.002 |
| Highest qualification (`hiqual_dv`) | 4.27 | 3.52 | 0.300 |
| Employed | 0.686 | 0.594 | 0.193 |

Spanning individuals are roughly nine years younger on average than newcomers (SMD −0.617), more qualified (SMD 0.300), and more often employed (SMD 0.193). Because age is a strong structural driver of trajectory topology — the disadvantaged-regime population is heavily retirement-age (86.1% of Inactive-Low window observations are aged 60+, per the age-stratified analysis) — this imbalance is a candidate confound for the spanning-vs-newcomer contrast and must be controlled.

Two identification-robustness designs are specified to remove it: a 1:1 nearest-neighbour propensity match (logit propensity, caliper 0.2) yielding $n = 5{,}627$ per group, and an age-restricted stratum (ages 30–55) with spanning $n = 3{,}010$ (mean age 41.1) and newcomer $n = 10{,}629$ (mean age 42.71), which closes the age gap by construction.

The topological comparison on the matched and age-stratified subsets is specified as a pending robustness check. No matched or age-stratified Betti values are reported here; the comparison is awaited before the identification finding can be considered fully corroborated.

## Interpretation

Taken with the pool-draw null (§4.3.1), the spanning-individual evidence is a robust descriptive association: newcomers have greater $H_0$ structure than spanning individuals across the reported $\varepsilon^*$ choices. It is not identification or causal evidence for survey-frame expansion, because the matched and age-stratified checks remain pending and the observed age and covariate imbalance can explain part or all of the contrast.
