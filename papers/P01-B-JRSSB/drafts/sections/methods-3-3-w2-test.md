# §3.3 Test Statistics: Mean-vs-Mean $W_2$ Construction, Landscape $L^2$, and Effect Sizes

This working file rewrites §3.3 around the test statistic the code actually computes — the
mean-vs-mean ratio $T$ with a BCa bootstrap interval and a standardised permutation effect
size $d_{\mathrm{perm}}$ — which v1's plain permutation-count description omits, and adds the
persistence-landscape $L^2$ complement and the exchangeability statement underlying every
permutation $p$-value in this paper. It supersedes v1 §3.3 in full.

## Scalar statistic: total persistence

Total persistence in homological degree $q$ is $\mathrm{TP}_q = \sum_i \ell_i$, summing the
lifetimes $\ell_i = d_i - b_i$ of all finite persistence pairs. The scalar permutation test
reports the one-sided $p$-value $p = (r+1)/(B+1)$, where $r$ is the number of null
realisations with $\mathrm{TP}_q^{\mathrm{null}} \geq \mathrm{TP}_q^{\mathrm{obs}}$. This
statistic collapses each diagram to a single number and is retained (§4.2) as a coarse,
easily audited companion to the diagram-level tests below, not as a primary test.

## Diagram-level statistic: mean-vs-mean $W_2$ ratio

For each null realisation $b = 1,\ldots,B$, compute the 2-Wasserstein distance
$W_2(D_q^{\mathrm{obs}}, D_q^{\mathrm{null}_b})$ under the $\ell^2$ ground metric and
diagonal projection defined in §3.1. Summarise the observed-to-null distances by their mean,
$$
\overline{W}_{\mathrm{obs,null}} = \frac{1}{B}\sum_{b=1}^{B} W_2\big(D_q^{\mathrm{obs}},
D_q^{\mathrm{null}_b}\big),
$$
and compute an analogous **null-null baseline** by pairing surrogate draws against one
another, $\overline{W}_{\mathrm{null,null}}$: the mean $W_2$ distance within the null
ensemble itself, which estimates how much diagram-to-diagram variation the null process
produces on its own. The test statistic is the ratio
$$
T = \frac{\overline{W}_{\mathrm{obs,null}}}{\overline{W}_{\mathrm{null,null}}},
$$
so that $T \approx 1$ indicates the observed diagram is indistinguishable, in $W_2$, from a
typical null diagram, and $T \gg 1$ indicates the observed diagram sits further from the
null ensemble than null diagrams sit from each other
(`compute_w2_ratio_bca_ci`, `trajectory_tda/topology/vectorisation.py`).

**Confidence interval.** $T$ is reported with a 95% bias-corrected-and-accelerated (BCa)
bootstrap interval, computed via `scipy.stats.bootstrap(method="BCa")` with $9{,}999$
bootstrap replicates (seed 42), resampling the observed-null and null-null distance arrays
independently and recomputing the ratio of resampled means at each replicate; BCa corrects
for both bias and skewness in the ratio statistic's sampling distribution, which a
symmetric percentile interval would not.

**Permutation $p$-value.** Let $\{\overline{W}^{(j)}_{\mathrm{null,null}}\}$ be the
reference distribution of null-null mean statistics. The permutation $p$-value is
$$
p = \frac{r+1}{B+1}, \qquad r = \#\Big\{j : \overline{W}^{(j)}_{\mathrm{null,null}} \geq
\overline{W}_{\mathrm{obs,null}}\Big\},
$$
i.e. the proportion of the null-null reference distribution that equals or exceeds the
observed statistic (a lower-tail variant, testing for the observed statistic being
implausibly *small* relative to the null-null spread, is also computed but not used as the
primary test in this paper).

**Effect size.** Alongside $T$ and $p$, we report a standardised permutation effect size
$$
d_{\mathrm{perm}} = \frac{\overline{W}_{\mathrm{obs,null}} - \overline{W}_{\mathrm{null,null}}}
{s_{\mathrm{null,null}}},
$$
where $s_{\mathrm{null,null}}$ is the standard deviation of the null-null reference
distribution — a Cohen's-$d$-style standardisation of the same mean-vs-mean contrast that
$T$ expresses as a ratio. $T$ and $d_{\mathrm{perm}}$ are reported together because they
answer slightly different questions: $T$ is scale-free (how many null-to-null distances
does the observed-to-null gap span, as a multiple) and $d_{\mathrm{perm}}$ is expressed in
null-null standard-deviation units (how many null-null standard deviations separate the
observed statistic from the null-null mean).

**This corrects a gap in v1**, whose §3.3 describes only the plain permutation-count
$p$-value and does not mention the mean-vs-mean $T$ ratio, the BCa interval, or
$d_{\mathrm{perm}}$ — all of which are computed and reported in every Stage-1 result file
(`usoc_headline_frozen_2026-05-28.json`, `stratified_w2_bh_per_family_2026-07-09.json`,
`markov2_alpha_sweep_summary_2026-06-16.json`) but were never described in prose.

## Persistence-landscape $L^2$ distance (mandatory complement)

The persistence landscape $\lambda_q$ of a diagram $D_q$ is a sequence of piecewise-linear
functions summarising the diagram at successive ranks (Bubenik, 2015); the persistence
landscape $L^2$ distance between two diagrams is $\|\lambda_q - \lambda_q'\|_{L^2}$, computed
here on landscapes truncated to the first $k_{\max} = 5$ layers and evaluated on a grid of
$200$ points. The landscape map is $1$-Lipschitz with respect to the bottleneck distance
(Bubenik, 2015), giving landscape $L^2$ a different, and occasionally divergent, stability
profile from $W_2$: a diagram with a small number of large persistence pairs can move $W_2$
substantially with little landscape effect, and vice versa for many small pairs. **We
report persistence-landscape $L^2$ distances as the mandatory complementary metric wherever
a $W_2$ test is reported** (never $W_2$ alone), using the identical mean-vs-mean $T$/BCa/
$d_{\mathrm{perm}}$ construction above with $W_2$ replaced by $\|\lambda_q - \lambda_q'\|_{L^2}$
throughout.

**This closes ISSUE M1**: v1 commits to this dual-metric reporting in prose but Tables 1-5
never contain a landscape $L^2$ value. Every Stage-1 result file computed for this paper
carries paired `w2_pvalue`/`landscape_l2_pvalue` (and paired `t_ratio`/`landscape_t_ratio`,
`d_perm`/`landscape_d_perm`) fields, so §4.2's tables (T2.16) can populate the landscape
column directly from committed data rather than requiring a new computation pass.

## Exchangeability and the validity of the permutation $p$-value

Every permutation $p$-value in this paper (Levels 1-5 and 4b, §3.2) rests on the same
exchangeability assumption: **under the null hypothesis, an individual's observed
trajectory is exchangeable with a surrogate trajectory drawn from the fitted null-generating
process for that level**, so that the observed diagram and each null draw are realisations
of the same underlying random process, and the null-null reference distribution and the
observed-vs-null distances are commensurable. Concretely, the unit of permutation is the
individual trajectory (state sequence), not individual state-transitions or landmark
points: each surrogate trajectory is generated by drawing a full synthetic sequence for
each observed individual, at that individual's observed length and (for the Markov levels)
starting condition, and only then re-embedded and landmarked as a whole cloud. This
individual-trajectory-level permutation is what licenses treating the $B$ null draws as
exchangeable replicates of the same generative process as the observed cloud; permuting at
a finer grain (e.g. individual state-transitions independently of trajectory membership)
would not preserve the within-individual dependence structure the null models are designed
to test against.

## Interpretation: scalar/diagram discrepancy

The scalar (total persistence) and diagram-level ($W_2$, landscape $L^2$) statistics can
disagree, and the disagreement is itself informative rather than a contradiction to be
resolved: total persistence collapses a diagram to one number and is insensitive to
*where* persistence pairs sit relative to the null ensemble, whereas $W_2$ and landscape
$L^2$ compare the full diagram geometry. A scalar non-rejection alongside a diagram-level
rejection indicates that the observed and null diagrams have similar aggregate persistence
but differ in shape or location — exactly the discrepancy reported for the Markov-1 rung in
§4.2. We do not claim a formal equivalence between $W_2$ and maximum mean discrepancy (MMD)
here; the connection is suggestive (both are distances between empirical distributions over
a metric space) but the specific kernels and embeddings differ, and no such equivalence is
asserted or required for the tests in this paper.

## Issues (for Manager review before v2 assembly)

- `notation.md` does not yet define $T$, $d_{\mathrm{perm}}$, or the BCa-interval notation;
  recommend adding these to the shared file alongside the ground-metric lock (§3.1 Issues)
  so P01-A does not diverge on the same objects.
