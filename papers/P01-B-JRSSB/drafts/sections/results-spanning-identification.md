# §4.3 Spanning-Individual Identification: Inferential Re-analysis, ε* Robustness, and Balance

This working file rewrites the spanning-individual identification result (slots into
§4.3.2/§4.3.3) around the T1.9b inferential re-analysis, with $\varepsilon^*$ robustness,
$W_2$ corroboration, and the demographic-balance / matched-subset / age-stratified
identification checks. It supersedes the v1 §4.3.2 single-scale Table 4 (Betti-0 at
$\varepsilon^*=0.70$).

## Identification problem

The pool-draw null (§4.3.1) establishes that the cross-era block structure is real, but
not its source. The spanning-individual decomposition adjudicates between genuine economic
restructuring and survey-frame expansion: under the parallel-trends-style identification
condition, if the post-2008 change reflected economic restructuring, spanning individuals
(observed in both surveys) would track newcomers into the new topology; if it reflected
frame expansion, spanning individuals would retain era-1 topology while newcomers occupy
previously unsampled embedding regions. The discriminating quantity is the era-2 $H_0$
structure of newcomers relative to spanning individuals.

## Inferential re-analysis (T1.9b)

The v1 decomposition rested on a single-scale Betti-0 point estimate, which a reviewer
correctly flagged as $\varepsilon^*$-dependent. The T1.9b inferential re-analysis
(`spanning_betti_inference_2026-06-20.json`; matched $n = 8{,}000$ per group, frozen PCA
loadings, $B = 1{,}000$ permutations and $B = 1{,}000$ bootstrap resamples, seed 42,
homology dimension $H_0$, locked $\varepsilon^* = 0.54$) evaluates three statistics — the
single-$\varepsilon$ $\beta_0$ ratio, the windowed $\beta_0$-AUC ratio, and the matched
2-Wasserstein distance $W_2$ — across four $\varepsilon^*$ values, each with a
permutation p-value and a bootstrap confidence interval.

**Table 4. Spanning vs newcomer $H_0$ structure: three statistics across four $\varepsilon^*$** *(provisional label; final number set at v2 assembly; ratios are newcomer-to-spanning, direction newcomers > spanning throughout)*

| $\varepsilon^*$ | Single-$\varepsilon$ $\beta_0$ ratio (perm p; 95% boot CI) | Windowed $\beta_0$-AUC ratio (perm p; 95% boot CI) | Matched $W_2$ (perm p) |
|---|---|---|---|
| 0.54 (locked) | 1.60 (p = 0.025; [1.09, 2.04]) | 1.127 (p = 0.001; [1.095, 1.173]) | 2.536 (p = 0.001) |
| 0.65 | 1.50 (p = 0.341; [0.92, 2.83]) | 1.129 (p = 0.001; [1.097, 1.174]) | 2.536 (p = 0.001) |
| 0.70 | 1.25 (p = 0.636; [0.75, 3.01]) | 1.129 (p = 0.001; [1.097, 1.175]) | 2.536 (p = 0.001) |
| 0.80 | 1.50 (p = 0.586; [0.50, 3.00]) | 1.129 (p = 0.001; [1.098, 1.175]) | 2.536 (p = 0.001) |

The three statistics differ sharply in robustness. The single-$\varepsilon$ $\beta_0$
ratio — the original v1 statistic — is significant only at the locked
$\varepsilon^* = 0.54$ (p = 0.025) and not at 0.65, 0.70, or 0.80, with bootstrap
intervals that span parity; it is too scale-sensitive to carry the conclusion. The
windowed $\beta_0$-AUC ratio, which integrates the Betti-0 curve over a window rather than
reading it at one scale, is significant at every $\varepsilon^*$ (p = 0.001) with
bootstrap intervals strictly above parity (lower bounds 1.09–1.10), and the matched $W_2$
rejects equality of the $H_0$ persistence diagrams at every $\varepsilon^*$ (p = 0.001).
The direction is consistent throughout: newcomers carry more $H_0$ structure than spanning
individuals.

This resolves the earlier T1.9 "divergent" result (`spanning_AUC_W2_2026-06-09.json`),
in which the single-$\varepsilon$ ratio and $W_2$ pointed one way while a *full*-interval
$\beta_0$-AUC ratio (0.938–0.939, i.e. below parity) pointed the other. The divergence was
an artefact of integrating the Betti-0 curve over the full $[0, \varepsilon^*]$ interval,
where the near-zero-scale regime dominates; the windowed AUC isolates the discriminating
band and removes the contradiction. The T1.9b decision rule — locked-$\varepsilon$
windowed-AUC p < 0.05, locked-$\varepsilon$ bootstrap CI excluding parity, direction
consistency across all $\varepsilon^*$, and significant $W_2$ — is satisfied, yielding the
outcome **newcomers carry more $H_0$ structure, robustly across $\varepsilon^*$ and
corroborated by $W_2$**.

> **[DRAFTING NOTE — prose-direction lock.]** The result file records this as a
> *mechanical* T1.9b outcome (`newcomers_robust`) and states that the manuscript-facing
> prose-direction lock is deferred to Manager review (pending a vault `[DECISION]` entry).
> The conclusion above is drafted per the Task Prompt instruction to treat the 2026-06-20
> inferential result as the §4.3 headline; the substantive framing should be confirmed
> against the `[DECISION]` lock before v2 assembly.

## Demographic balance and identification robustness

The spanning and newcomer populations are not exchangeable, which bears directly on the
identification condition. The balance diagnostic (T1.17; `balance_2026-05-14.json`;
spanning $n = 5{,}895$, newcomer $n = 21{,}385$) shows a large age gap and moderate
imbalances in qualification and employment, with sex well balanced:

**Balance table — spanning vs newcomer (standardised mean differences)** *(provisional label)*

| Covariate | Spanning mean | Newcomer mean | SMD |
|---|---:|---:|---:|
| Age at first observation | 35.26 | 44.66 | −0.617 |
| Female | 0.560 | 0.559 | 0.002 |
| Highest qualification (`hiqual_dv`) | 4.27 | 3.52 | 0.300 |
| Employed | 0.686 | 0.594 | 0.193 |

Spanning individuals are roughly nine years younger on average than newcomers
(SMD −0.617), more qualified (SMD 0.300), and more often employed (SMD 0.193). Because age
is a strong structural driver of trajectory topology — the disadvantaged-regime population
is heavily retirement-age (86.1% of Inactive-Low window observations are aged 60+, per the
age-stratified analysis `p2_5_age_stratified.json`) — this imbalance is a candidate
confound for the spanning-vs-newcomer contrast and must be controlled.

Two identification-robustness designs are specified to remove it
(`matched_subset_2026-05-14.json`): a 1:1 nearest-neighbour propensity match (logit
propensity, caliper 0.2) yielding $n = 5{,}627$ per group, and an age-restricted stratum
(ages 30–55) with spanning $n = 3{,}010$ (mean age 41.1) and newcomer $n = 10{,}629$
(mean age 42.71), which closes the age gap by construction.

> **[DRAFTING NOTE — pending TDA rerun.]** The Betti comparison on the matched and
> age-stratified subsets requires a TDA-pipeline rerun on the subset pidp lists, which was
> escalated to the TDA agent and is **not yet committed** under `results/`
> (`balance_2026-05-14.json` and `matched_subset_2026-05-14.json` both record the
> escalation). The matched/age-stratified $H_0$ confirmation of the newcomers-robust
> finding is therefore stated here as a specified, pending robustness check, not as a
> reported result. No matched/age-stratified Betti values are fabricated; this is flagged
> for the Manager as a dependency on the TDA agent.

## Interpretation

Taken with the pool-draw null (§4.3.1), the spanning-individual evidence supports the
survey-frame-expansion reading of the dominant post-2008 $H_0$ change: spanning
individuals retain era-1-like topology while newcomers, who carry significantly and
robustly more $H_0$ structure, occupy embedding regions the BHPS frame under-sampled. The
strength of this reading is currently bounded by the pending matched/age-stratified
confirmation and by the Manager-deferred prose-direction lock noted above.
